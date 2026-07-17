from __future__ import annotations
import asyncio
import logging
import sys
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

sys.path.insert(0, "/app")

from app.core.config import get_settings
from app.core.database import create_tables
from app.api.v1.router import router as api_router
from app.websockets.manager import manager as ws_manager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title="Defence FL Platform",
    description=(
        "Privacy-Preserving Federated Learning Platform for Defence Intelligence. "
        "Supports FedAvg, FedAsync, FedFA, FedProx with Differential Privacy and Secure Aggregation."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting Defence FL Platform…")

    max_attempts = 10
    for attempt in range(1, max_attempts + 1):
        try:
            create_tables()
            logger.info("Database tables ready")
            break
        except Exception as e:
            if attempt == max_attempts:
                logger.error(f"Database init failed after {max_attempts} attempts: {e}")
                raise
            logger.warning(f"Database not ready yet (attempt {attempt}/{max_attempts}): {e}")
            await asyncio.sleep(2)

    loop = asyncio.get_running_loop()
    ws_manager.set_event_loop(loop)
    logger.info("WebSocket manager event loop registered")

    _seed_default_user()

    logger.info("Platform ready ✓")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down Defence FL Platform…")


def _seed_default_user():
    from app.core.database import SessionLocal
    from app.models.user import User
    from app.core.security import hash_password

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                email=settings.DEFAULT_ADMIN_EMAIL,
                username="Admin",
                hashed_password=hash_password(settings.DEFAULT_ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"Default admin user created: {settings.DEFAULT_ADMIN_EMAIL}")
    except Exception as e:
        db.rollback()
        logger.warning(f"Could not seed default user: {e}")
    finally:
        db.close()


app.include_router(api_router)

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ok", "service": "defence-fl-platform"}


@app.get("/", tags=["System"])
def root():
    return {
        "name":    "Defence FL Platform",
        "version": "1.0.0",
        "docs":    "/docs",
    }
