"""
Training Service — manages the full FL experiment lifecycle.

Architecture:
  - Each experiment runs in a daemon Python thread (not asyncio task)
    because PyTorch training is blocking and CPU-bound.
  - Metrics flow: training callback → WS manager.broadcast_from_thread()
  - DB writes happen inside the thread using a fresh SQLAlchemy session.
  - Cancellation: threading.Event checked in the metrics callback.
"""

from __future__ import annotations
import logging
import sys
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.database import SessionLocal
from app.models.experiment import Experiment
from app.models.privacy_log import PrivacyLog
from app.models.round_metric import RoundMetric
from app.websockets.manager import ConnectionManager
from fl_engine.exceptions import TrainingCancelledError
from config.hyperparams import (
    DEFAULT_TARGET_DELTA,
    DEFAULT_TARGET_EPSILON,
    is_secure_agg_compatible,
)

logger = logging.getLogger(__name__)


class PrivacyBudgetExceededError(Exception):
    """Raised inside the training callback when the cumulative privacy
    budget (ε) reaches or exceeds the configured ceiling — training stops
    automatically rather than silently exceeding the configured privacy guarantee."""


class _ExperimentState:
    __slots__ = ("thread", "stop_event", "current_round", "status")

    def __init__(self, thread: threading.Thread, stop_event: threading.Event):
        self.thread        = thread
        self.stop_event    = stop_event
        self.current_round = 0
        self.status        = "running"


class TrainingService:
    """
    Singleton service that tracks and manages running FL experiments.
    """

    def __init__(self):
        self._active: Dict[str, _ExperimentState] = {}
        self._lock   = threading.Lock()

    def start_experiment(
        self,
        experiment_id: str,
        fl_cfg: dict,
        privacy_cfg: dict,
        ws_manager: ConnectionManager,
    ) -> None:
        """
        Spawn a background thread to run the FL experiment.
        Raises RuntimeError if the experiment is already running.
        """
        with self._lock:
            if experiment_id in self._active:
                raise RuntimeError(f"Experiment {experiment_id} is already running")

        stop_event = threading.Event()
        thread = threading.Thread(
            target=self._run,
            args=(experiment_id, fl_cfg, privacy_cfg, ws_manager, stop_event),
            daemon=True,
            name=f"fl-train-{experiment_id[:8]}",
        )

        state = _ExperimentState(thread=thread, stop_event=stop_event)
        with self._lock:
            self._active[experiment_id] = state

        thread.start()
        logger.info(f"Started training thread for experiment {experiment_id[:8]}")

    def cancel_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            state = self._active.get(experiment_id)
        if state is None:
            return False
        state.stop_event.set()
        logger.info(f"Cancellation requested for experiment {experiment_id[:8]}")
        return True

    def get_status(self, experiment_id: str) -> Optional[dict]:
        with self._lock:
            state = self._active.get(experiment_id)
        if state is None:
            return None
        return {
            "current_round": state.current_round,
            "status":        state.status,
            "is_alive":      state.thread.is_alive(),
        }

    def is_running(self, experiment_id: str) -> bool:
        with self._lock:
            state = self._active.get(experiment_id)
        return state is not None and state.thread.is_alive()

    def cleanup(self, experiment_id: str) -> None:
        with self._lock:
            self._active.pop(experiment_id, None)

    def _run(
        self,
        experiment_id: str,
        fl_cfg: dict,
        privacy_cfg: dict,
        ws_manager: ConnectionManager,
        stop_event: threading.Event,
    ) -> None:
        state = self._active.get(experiment_id)

        self._update_experiment(experiment_id, status="running", started_at=datetime.now(timezone.utc))
        ws_manager.broadcast_from_thread(experiment_id, {
            "type": "status_change",
            "payload": {"status": "running", "experiment_id": experiment_id},
        })

        round_accuracies = []
        round_losses     = []
        algorithm = fl_cfg.get("algorithm", "fedavg")

        sa_cfg = fl_cfg.get("secure_aggregation", {})
        if sa_cfg.get("enabled", False) and not is_secure_agg_compatible(algorithm):
            logger.info(
                f"Experiment {experiment_id[:8]}: Secure Aggregation requested "
                f"but '{algorithm}' is incompatible (pure async) — disabling."
            )
            fl_cfg = {**fl_cfg, "secure_aggregation": {**sa_cfg, "enabled": False}}

        dp_enabled = privacy_cfg.get("differential_privacy", {}).get("enabled", False)
        budget_tracker = None
        dp_mechanism   = None
        alert_sent     = False

        if dp_enabled:
            from privacy.budget_tracker import PrivacyBudgetTracker
            from privacy.differential_privacy import DPMechanism
            dp_sub = privacy_cfg.get("differential_privacy", {})
            budget_tracker = PrivacyBudgetTracker(
                max_epsilon=dp_sub.get("target_epsilon", DEFAULT_TARGET_EPSILON),
                target_delta=dp_sub.get("target_delta", DEFAULT_TARGET_DELTA),
            )
            dp_mechanism = DPMechanism(
                noise_multiplier=dp_sub.get("noise_multiplier", 1.0),
                max_grad_norm=dp_sub.get("max_grad_norm", 1.0),
                budget_tracker=budget_tracker,
            )

        def _account_dp_event(round_num: int, extras: dict, save_log: bool) -> None:
            nonlocal alert_sent
            # q (sampling_rate): synchronous algorithms have every client
            # participate every round (q=1); asynchronous algorithms only
            # fold in one client's update per accounted step, so q is
            # that client's selection probability (from its speed weight).
            if algorithm in ("fedavg", "fedprox"):
                q = 1.0
            else:
                q = float(extras.get("selection_prob", 1.0))

            budget_tracker.account_round(
                round_num=round_num,
                noise_multiplier=privacy_cfg.get("differential_privacy", {}).get("noise_multiplier", 1.0),
                max_grad_norm=privacy_cfg.get("differential_privacy", {}).get("max_grad_norm", 1.0),
                num_samples=fl_cfg.get("num_clients", 10) * fl_cfg.get("batch_size", 32) * fl_cfg.get("local_epochs", 2),
                lot_size=fl_cfg.get("batch_size", 32),
                sampling_rate=q,
            )
            if save_log:
                history = budget_tracker.get_history()
                if history:
                    latest = history[-1]
                    self._save_privacy_log(experiment_id, round_num, latest, dp_mechanism)

            if budget_tracker.is_alert and not alert_sent:
                alert_sent = True
                ws_manager.broadcast_from_thread(experiment_id, {
                    "type": "privacy_alert",
                    "payload": {
                        "experiment_id":   experiment_id,
                        "budget_used_pct": round(budget_tracker.budget_used_fraction * 100, 2),
                        "message": (
                            f"Privacy budget "
                            f"{round(budget_tracker.budget_used_fraction * 100, 1)}% consumed "
                            f"(alert threshold {round(budget_tracker.alert_threshold * 100)}%)."
                        ),
                    },
                })

            if budget_tracker.is_budget_exhausted:
                raise PrivacyBudgetExceededError(
                    f"Privacy budget exhausted: ε={budget_tracker.total_epsilon:.4f} "
                    f"reached the configured ceiling of {budget_tracker.max_epsilon:.4f}. "
                    f"Training stopped automatically to protect the privacy guarantee."
                )

        def on_round(round_num: int, accuracy: float, loss: float, **extras: Any):
            if stop_event.is_set():
                raise TrainingCancelledError("Training cancelled by user")

            if extras.get("dp_only"):
                if dp_enabled and budget_tracker:
                    _account_dp_event(round_num, extras, save_log=False)
                return

            if state:
                state.current_round = round_num

            round_accuracies.append(accuracy)
            round_losses.append(loss)

            self._save_round_metric(experiment_id, round_num, accuracy, loss, extras)

            if dp_enabled and budget_tracker:
                _account_dp_event(round_num, extras, save_log=True)

            total_rounds = fl_cfg.get("rounds", 5)
            progress_pct = round(round_num / total_rounds * 100, 1)

            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "round_update",
                "payload": {
                    "experiment_id": experiment_id,
                    "round_num":     round_num,
                    "total_rounds":  total_rounds,
                    "accuracy":      round(accuracy * 100, 4),
                    "loss":          round(loss, 6),
                    "progress_pct":  progress_pct,
                    "epsilon":       budget_tracker.total_epsilon if budget_tracker else None,
                    "budget_used_pct": round(budget_tracker.budget_used_fraction * 100, 2) if budget_tracker else None,
                    **{k: (round(v, 6) if isinstance(v, float) else v)
                       for k, v in extras.items()},
                },
            })

        try:

            fl_cfg = {**fl_cfg, "_stop_event": stop_event}
            from fl_engine.runner import run_experiment
            _, _, summary = run_experiment(
                cfg=fl_cfg,
                callback=on_round,
                seed=42,
            )

            final_acc  = round_accuracies[-1] if round_accuracies else 0.0
            best_acc   = max(round_accuracies) if round_accuracies else 0.0
            final_loss = round_losses[-1]      if round_losses     else 0.0
            total_eps  = budget_tracker.total_epsilon if budget_tracker else None

            self._update_experiment(
                experiment_id,
                status="completed",
                finished_at=datetime.now(timezone.utc),
                final_accuracy=final_acc,
                best_accuracy=best_acc,
                final_loss=final_loss,
                total_epsilon=total_eps,
            )

            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "complete",
                "payload": {
                    "experiment_id":  experiment_id,
                    "status":         "completed",
                    "final_accuracy": round(final_acc * 100, 4),
                    "best_accuracy":  round(best_acc * 100, 4),
                    "final_loss":     round(final_loss, 6),
                    "total_epsilon":  total_eps,
                    "summary":        summary,
                },
            })

        except TrainingCancelledError:
            self._update_experiment(experiment_id, status="cancelled", finished_at=datetime.now(timezone.utc))
            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "status_change",
                "payload": {"status": "cancelled", "experiment_id": experiment_id},
            })
            logger.info(f"Experiment {experiment_id[:8]} cancelled")

        except PrivacyBudgetExceededError as exc:
            error_msg = str(exc)
            self._update_experiment(
                experiment_id,
                status="cancelled",
                finished_at=datetime.now(timezone.utc),
                error_message=error_msg,
            )
            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "status_change",
                "payload": {"status": "cancelled", "experiment_id": experiment_id},
            })
            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "error",
                "payload": {"experiment_id": experiment_id, "error": error_msg},
            })
            logger.info(f"Experiment {experiment_id[:8]} stopped: privacy budget exhausted")

        except Exception as exc:
            logger.exception(f"Experiment {experiment_id[:8]} failed: {exc}")
            error_msg = str(exc)[:900]
            self._update_experiment(
                experiment_id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                error_message=error_msg,
            )
            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "status_change",
                "payload": {"status": "failed", "experiment_id": experiment_id},
            })
            ws_manager.broadcast_from_thread(experiment_id, {
                "type": "error",
                "payload": {
                    "experiment_id": experiment_id,
                    "status":        "failed",
                    "error":         error_msg,
                },
            })

        finally:
            if state:
                state.status = self._get_experiment_status(experiment_id)
            self.cleanup(experiment_id)

    def _update_experiment(self, experiment_id: str, **kwargs) -> None:
        db = SessionLocal()
        try:
            exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
            if exp:
                for k, v in kwargs.items():
                    setattr(exp, k, v)
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"DB update failed for {experiment_id[:8]}: {e}")
        finally:
            db.close()

    def _save_round_metric(
        self, experiment_id: str, round_num: int,
        accuracy: float, loss: float, extras: dict,
    ) -> None:
        db = SessionLocal()
        try:
            metric = RoundMetric(
                experiment_id=experiment_id,
                round_num=round_num,
                accuracy=accuracy,
                loss=loss,
                extra=extras if extras else None,
            )
            db.add(metric)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save round metric: {e}")
        finally:
            db.close()

    def _save_privacy_log(
        self, experiment_id: str, round_num: int,
        history_entry: dict, dp_mechanism,
    ) -> None:
        db = SessionLocal()
        try:
            log = PrivacyLog(
                experiment_id=experiment_id,
                round_num=round_num,
                epsilon_round=history_entry.get("epsilon_round", 0.0),
                epsilon_total=history_entry.get("epsilon_total", 0.0),
                delta=history_entry.get("delta", 1e-5),
                noise_mult=dp_mechanism.noise_multiplier if dp_mechanism else 1.0,
                clip_norm=dp_mechanism.max_grad_norm if dp_mechanism else 1.0,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to save privacy log: {e}")
        finally:
            db.close()

    def _get_experiment_status(self, experiment_id: str) -> str:
        db = SessionLocal()
        try:
            exp = db.query(Experiment).filter(Experiment.id == experiment_id).first()
            return exp.status if exp else "unknown"
        finally:
            db.close()


training_service = TrainingService()
