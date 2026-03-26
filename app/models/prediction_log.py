from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class PredictionLog(Base):
    """
    Immutable log of every prediction served.

    This table is append-only — predictions are never updated or deleted.
    Useful for auditing, debugging, and model performance monitoring.
    """

    __tablename__ = "prediction_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    model_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ml_models.id"), nullable=False
    )
    input_data: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    prediction: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    user: Mapped[User] = relationship("User", back_populates="prediction_logs")
