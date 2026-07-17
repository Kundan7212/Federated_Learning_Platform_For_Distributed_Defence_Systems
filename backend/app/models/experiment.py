from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Experiment(Base):
    __tablename__ = "experiments"

    id:           Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name:         Mapped[str]           = mapped_column(String(200), nullable=False)
    description:  Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    algorithm:    Mapped[str]           = mapped_column(String(50), nullable=False)
    dataset:      Mapped[str]           = mapped_column(String(50), nullable=False)
    model_type:   Mapped[str]           = mapped_column(String(50), nullable=False)
    num_clients:  Mapped[int]           = mapped_column(Integer, nullable=False)
    rounds:       Mapped[int]           = mapped_column(Integer, nullable=False)
    local_epochs: Mapped[int]           = mapped_column(Integer, nullable=False)
    batch_size:   Mapped[int]           = mapped_column(Integer, nullable=False)
    learning_rate: Mapped[float]        = mapped_column(Float, nullable=False)
    partition_method: Mapped[str]       = mapped_column(String(50), nullable=False)

    config_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    dp_enabled:  Mapped[bool]           = mapped_column(default=False)
    sa_enabled:  Mapped[bool]           = mapped_column(default=False)
    noise_mult:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_grad_norm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status:       Mapped[str]           = mapped_column(String(20), default="pending")
    # pending | running | completed | failed | cancelled

    final_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    best_accuracy:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    final_loss:     Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    total_epsilon:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_message:  Mapped[Optional[str]]   = mapped_column(String(1000), nullable=True)

    owner_id:   Mapped[str]           = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime]      = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    owner:        Mapped["User"]       = relationship("User", back_populates="experiments")
    round_metrics: Mapped[list]        = relationship("RoundMetric", back_populates="experiment", cascade="all, delete-orphan")
    privacy_logs: Mapped[list]         = relationship("PrivacyLog", back_populates="experiment", cascade="all, delete-orphan")

    @property
    def duration_seconds(self) -> Optional[float]:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    def __repr__(self) -> str:
        return f"<Experiment {self.id[:8]} {self.algorithm} {self.status}>"
