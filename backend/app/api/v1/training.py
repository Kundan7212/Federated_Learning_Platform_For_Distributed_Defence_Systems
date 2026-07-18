from __future__ import annotations
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import decode_access_token
from app.models.experiment import Experiment
from app.models.round_metric import RoundMetric
from app.models.user import User
from app.schemas.experiment import TrainingStatusResponse
from app.services.training_service import training_service
from app.websockets.manager import manager as ws_manager
from config.hyperparams import DEFAULT_TARGET_DELTA, DEFAULT_TARGET_EPSILON

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/training", tags=["Training"])


@router.post("/{experiment_id}/start", status_code=status.HTTP_202_ACCEPTED)
def start_training(
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
    if exp.status in ("running",):
        raise HTTPException(status_code=409, detail="Experiment is already running")
    if exp.status == "completed":
        raise HTTPException(status_code=409, detail="Experiment already completed")

    fl_cfg      = exp.config_json or {}
    privacy_cfg = {
        "differential_privacy": {
            "enabled":          exp.dp_enabled,
            "noise_multiplier": exp.noise_mult or 1.0,
            "max_grad_norm":    exp.max_grad_norm or 1.0,
            "target_epsilon":   DEFAULT_TARGET_EPSILON,
            "target_delta":     DEFAULT_TARGET_DELTA,
        },
        "secure_aggregation": {
            "enabled": exp.sa_enabled,
        },
    }

    try:
        training_service.start_experiment(
            experiment_id=experiment_id,
            fl_cfg=fl_cfg,
            privacy_cfg=privacy_cfg,
            ws_manager=ws_manager,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return {"message": "Training started", "experiment_id": experiment_id}


@router.post("/{experiment_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_training(
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

    cancelled = training_service.cancel_experiment(experiment_id)
    if not cancelled:
        raise HTTPException(status_code=409, detail="Experiment is not running")
    return {"message": "Cancellation requested", "experiment_id": experiment_id}


@router.get("/{experiment_id}/status", response_model=TrainingStatusResponse)
def get_training_status(
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

    latest_metric = (
        db.query(RoundMetric)
        .filter(RoundMetric.experiment_id == experiment_id)
        .order_by(RoundMetric.round_num.desc())
        .first()
    )

    current_round = latest_metric.round_num if latest_metric else 0
    total_rounds  = exp.rounds
    progress_pct  = round(current_round / total_rounds * 100, 1) if total_rounds > 0 else 0.0

    return TrainingStatusResponse(
        experiment_id=experiment_id,
        status=exp.status,
        current_round=current_round,
        total_rounds=total_rounds,
        latest_accuracy=latest_metric.accuracy if latest_metric else None,
        latest_loss=latest_metric.loss if latest_metric else None,
        total_epsilon=exp.total_epsilon,
        progress_pct=progress_pct,
    )


@router.websocket("/ws/{experiment_id}")
async def training_websocket(
    websocket: WebSocket,
    experiment_id: str,
):

    await websocket.accept()
    try:
        raw = await websocket.receive_text()
        auth_msg = json.loads(raw)
        token = auth_msg.get("token", "")
        email = decode_access_token(token)
        if not email:
            await websocket.send_text(json.dumps({"type": "error", "payload": {"detail": "Unauthorized"}}))
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4000)
        return

    ws_manager._connections[experiment_id].append(websocket)
    logger.info(f"WS auth OK, subscribed to {experiment_id[:8]}")

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=15.0)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"type": "heartbeat"}))
                continue
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, experiment_id)
        logger.info(f"WS disconnected from {experiment_id[:8]}")
    except Exception as e:
        ws_manager.disconnect(websocket, experiment_id)
        logger.warning(f"WS error for {experiment_id[:8]}: {e}")