from __future__ import annotations
import uuid
from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class PrivacyLog(Base):
    __tablename__ = "privacy_logs"

    id:             Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id:  Mapped[str]   = mapped_column(String(36), ForeignKey("experiments.id"), nullable=False, index=True)
    round_num:      Mapped[int]   = mapped_column(Integer, nullable=False)
    epsilon_round:  Mapped[float] = mapped_column(Float, nullable=False)
    epsilon_total:  Mapped[float] = mapped_column(Float, nullable=False)
    delta:          Mapped[float] = mapped_column(Float, nullable=False)
    noise_mult:     Mapped[float] = mapped_column(Float, nullable=False)
    clip_norm:      Mapped[float] = mapped_column(Float, nullable=False)
    recorded_at:    Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="privacy_logs")
