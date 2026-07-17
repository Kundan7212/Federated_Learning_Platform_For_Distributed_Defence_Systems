from __future__ import annotations
from typing import Dict, List, Optional
from sqlalchemy.orm import Session

from app.models.experiment import Experiment
from app.models.privacy_log import PrivacyLog
from config.hyperparams import DEFAULT_TARGET_EPSILON


class PrivacyService:

    @staticmethod
    def get_privacy_summary(db: Session, experiment_id: str) -> Optional[Dict]:
        exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
        if exp is None:
            return None

        logs = (
            db.query(PrivacyLog)
            .filter(PrivacyLog.experiment_id == experiment_id)
            .order_by(PrivacyLog.round_num)
            .all()
        )

        target_epsilon = (
            exp.config_json.get("differential_privacy", {}).get("target_epsilon", DEFAULT_TARGET_EPSILON)
            if exp.config_json else DEFAULT_TARGET_EPSILON
        )

        if not logs:
            return {
                "experiment_id":  experiment_id,
                "dp_enabled":     exp.dp_enabled,
                "total_epsilon":  exp.total_epsilon,
                "target_epsilon": target_epsilon,
                "rounds_logged":  0,
                "history":        [],
            }

        history = [
            {
                "round":         log.round_num,
                "epsilon_round": log.epsilon_round,
                "epsilon_total": log.epsilon_total,
                "delta":         log.delta,
                "noise_mult":    log.noise_mult,
                "clip_norm":     log.clip_norm,
            }
            for log in logs
        ]

        return {
            "experiment_id":  experiment_id,
            "dp_enabled":     exp.dp_enabled,
            "total_epsilon":  logs[-1].epsilon_total if logs else 0.0,
            "target_epsilon": target_epsilon,
            "rounds_logged":  len(logs),
            "history":        history,
        }

    @staticmethod
    def get_platform_privacy_overview(db: Session) -> Dict:
        exps = db.query(Experiment).filter(Experiment.dp_enabled.is_(True)).all()
        total_exps = len(exps)
        total_epsilon_consumed = sum(
            e.total_epsilon for e in exps if e.total_epsilon is not None
        )
        completed = [e for e in exps if e.status == "completed"]
        avg_epsilon = (
            total_epsilon_consumed / len(completed) if completed else 0.0
        )
        return {
            "total_dp_experiments":     total_exps,
            "total_epsilon_consumed":   round(total_epsilon_consumed, 4),
            "avg_epsilon_per_run":      round(avg_epsilon, 4),
            "completed_dp_experiments": len(completed),
        }
