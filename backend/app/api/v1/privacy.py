from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.experiment import Experiment
from app.models.user import User
from app.services.privacy_service import PrivacyService

router = APIRouter(prefix="/privacy", tags=["Privacy"])

@router.get("/experiments/{experiment_id}/budget")
def get_experiment_budget(
    experiment_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    exp = db.query(Experiment).filter(
        Experiment.id == experiment_id,
        Experiment.owner_id == current_user.id,
    ).first()
    if exp is None:
        raise HTTPException(status_code=404, detail="Experiment not found")

    summary = PrivacyService.get_privacy_summary(db, experiment_id)
    return summary


@router.get("/overview")
def get_privacy_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return PrivacyService.get_platform_privacy_overview(db)


@router.get("/algorithms")
def list_privacy_algorithms():
    return {
        "differential_privacy": {
            "name":        "Gaussian Mechanism (DP-SGD)",
            "description": "Clips gradient updates and adds calibrated Gaussian noise. Provides (ε,δ)-differential privacy per round.",
            "parameters": [
                {"name": "noise_multiplier", "type": "float", "description": "σ — noise scale relative to sensitivity"},
                {"name": "max_grad_norm",    "type": "float", "description": "C — L2 clipping bound for updates"},
            ],
        },
        "secure_aggregation": {
            "name":        "Additive Secret Sharing",
            "description": "Each client's update is masked; masks cancel during aggregation so the server only sees the sum.",
            "parameters": [
                {"name": "num_shares", "type": "int", "description": "Number of shares per secret"},
            ],
        },
    }
