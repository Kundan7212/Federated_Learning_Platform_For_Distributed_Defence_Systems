from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.experiment import Experiment
from app.models.round_metric import RoundMetric
from app.models.privacy_log import PrivacyLog
from app.models.user import User
from app.schemas.experiment import (
    CreateExperimentRequest,
    ExperimentDetailResponse,
    ExperimentResponse,
    PrivacyLogResponse,
    RoundMetricResponse,
)
from config.hyperparams import (
    DEFAULT_TARGET_DELTA,
    DEFAULT_TARGET_EPSILON,
    generate_client_speed_weights,
    is_async_algorithm,
    is_secure_agg_compatible,
)

router = APIRouter(prefix="/experiments", tags=["Experiments"])


def _build_fl_cfg(req: CreateExperimentRequest) -> dict:
    fl = req.fl_config
    priv = req.privacy
    sa_enabled = priv.sa_enabled and is_secure_agg_compatible(fl.algorithm)

    async_extra = {}
    if is_async_algorithm(fl.algorithm):
        async_extra = {
            "client_speed_profile":  fl.client_speed_profile,
            "client_speed_weights":  generate_client_speed_weights(fl.client_speed_profile, fl.num_clients),
        }

    return {
        "algorithm":         fl.algorithm,
        "dataset":           fl.dataset,
        "model_type":        fl.model_type,
        "num_clients":       fl.num_clients,
        "rounds":            fl.rounds,
        "local_epochs":      fl.local_epochs,
        "batch_size":        fl.batch_size,
        "lr":                fl.learning_rate,
        "partition_method":  fl.partition_method,
        "dirichlet_alpha":   fl.dirichlet_alpha,
        "async_alpha":       fl.async_alpha,
        "async_concurrency": fl.async_concurrency,
        "async_updates_per_log": fl.async_updates_per_log,
        "fedfa_buffer_size": fl.fedfa_buffer_size,
        "fedprox_mu":        fl.fedprox_mu,
        "staleness_weighting": fl.staleness_weighting,

        **async_extra,

        "device":            "auto",
        "data_dir":          "/app/data",
        "results_dir":       "/app/results",
        "save_model":        False,   
        
        "differential_privacy": {
            "enabled":          priv.dp_enabled,
            "noise_multiplier": priv.noise_multiplier,
            "max_grad_norm":    priv.max_grad_norm,
            "target_epsilon":   DEFAULT_TARGET_EPSILON,
            "target_delta":     DEFAULT_TARGET_DELTA,
        },
        
        "secure_aggregation": {
            "enabled": sa_enabled,
        },
    }


@router.post("", response_model=ExperimentResponse, status_code=status.HTTP_201_CREATED)
def create_experiment(
    body: CreateExperimentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    
    fl = body.fl_config
    priv = body.privacy
    sa_enabled = priv.sa_enabled and is_secure_agg_compatible(fl.algorithm)

    exp = Experiment(
        name=body.name,
        description=body.description,
        algorithm=fl.algorithm,
        dataset=fl.dataset,
        model_type=fl.model_type,
        num_clients=fl.num_clients,
        rounds=fl.rounds,
        local_epochs=fl.local_epochs,
        batch_size=fl.batch_size,
        learning_rate=fl.learning_rate,
        partition_method=fl.partition_method,
        dp_enabled=priv.dp_enabled,
        sa_enabled=sa_enabled,
        noise_mult=priv.noise_multiplier if priv.dp_enabled else None,
        max_grad_norm=priv.max_grad_norm if priv.dp_enabled else None,
        config_json=_build_fl_cfg(body),
        owner_id=current_user.id,
        status="pending",
    )
    db.add(exp)
    db.commit()
    db.refresh(exp)
    return exp


@router.get("", response_model=List[ExperimentResponse])
def list_experiments(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Experiment)
        .filter(Experiment.owner_id == current_user.id)
        .order_by(Experiment.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{experiment_id}", response_model=ExperimentDetailResponse)
def get_experiment(
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

    metrics = (
        db.query(RoundMetric)
        .filter(RoundMetric.experiment_id == experiment_id)
        .order_by(RoundMetric.round_num)
        .all()
    )
    privacy_logs = (
        db.query(PrivacyLog)
        .filter(PrivacyLog.experiment_id == experiment_id)
        .order_by(PrivacyLog.round_num)
        .all()
    )

    return ExperimentDetailResponse(
        **ExperimentResponse.model_validate(exp).model_dump(),
        round_metrics=[RoundMetricResponse.model_validate(m) for m in metrics],
        privacy_logs=[PrivacyLogResponse.model_validate(p) for p in privacy_logs],
    )


@router.delete("/{experiment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_experiment(
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
    if exp.status == "running":
        raise HTTPException(status_code=409, detail="Cannot delete a running experiment")
    db.delete(exp)
    db.commit()
