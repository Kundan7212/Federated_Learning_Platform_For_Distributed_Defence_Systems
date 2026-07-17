from fastapi import APIRouter
from app.api.v1 import auth, experiments, training, privacy, metrics

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(experiments.router)
router.include_router(training.router)
router.include_router(privacy.router)
router.include_router(metrics.router)
