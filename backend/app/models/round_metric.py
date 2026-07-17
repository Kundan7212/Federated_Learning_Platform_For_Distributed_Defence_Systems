from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class RoundMetric(Base):
    __tablename__ = "round_metrics"

    id:            Mapped[str]           = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    experiment_id: Mapped[str]           = mapped_column(String(36), ForeignKey("experiments.id"), nullable=False, index=True)
    round_num:     Mapped[int]           = mapped_column(Integer, nullable=False)
    accuracy:      Mapped[float]         = mapped_column(Float, nullable=False)
    loss:          Mapped[float]         = mapped_column(Float, nullable=False)
    extra:         Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recorded_at:   Mapped[datetime]      = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="round_metrics")

    def __repr__(self) -> str:
        return f"<RoundMetric exp={self.experiment_id[:8]} round={self.round_num} acc={self.accuracy:.4f}>"
