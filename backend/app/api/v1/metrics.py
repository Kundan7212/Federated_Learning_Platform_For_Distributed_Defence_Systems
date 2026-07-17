from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.experiment import Experiment
from app.models.round_metric import RoundMetric
from app.models.user import User
from app.services.training_service import training_service
from app.algorithms_meta import ALGORITHM_META

router = APIRouter(prefix="/metrics", tags=["Metrics"])

@router.get("/dashboard")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = db.query(Experiment).filter(Experiment.owner_id == current_user.id)

    total_experiments = base.count()
    running_count     = base.filter(Experiment.status == "running").count()
    completed_exps    = base.filter(Experiment.status == "completed").all()

    best_accuracy  = 0.0
    avg_accuracy   = 0.0
    if completed_exps:
        accs = [e.best_accuracy for e in completed_exps if e.best_accuracy is not None]
        if accs:
            best_accuracy = max(accs)
            avg_accuracy  = sum(accs) / len(accs)

    dp_experiments = base.filter(Experiment.dp_enabled.is_(True)).count()
    total_rounds   = db.query(func.count(RoundMetric.id)).scalar() or 0

    recent = (
        base.order_by(Experiment.created_at.desc()).limit(5).all()
    )

    return {
        "total_experiments": total_experiments,
        "running_count":     running_count,
        "completed_count":   len(completed_exps),
        "best_accuracy":     round(best_accuracy * 100, 2),
        "avg_accuracy":      round(avg_accuracy * 100, 2),
        "dp_experiments":    dp_experiments,
        "total_rounds":      total_rounds,
        "recent_experiments": [
            {
                "id":             e.id,
                "name":           e.name,
                "algorithm":      e.algorithm,
                "status":         e.status,
                "final_accuracy": round(e.final_accuracy * 100, 2) if e.final_accuracy else None,
                "created_at":     e.created_at.isoformat(),
            }
            for e in recent
        ],
    }


@router.get("/algorithms")
def get_algorithm_options():
    return ALGORITHM_META
