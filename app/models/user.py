from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.ml_model import MLModel
    from app.models.prediction_log import PredictionLog


class User(Base):
    """
    User account table.

    Design decisions:
    - UUID primary key: prevents ID enumeration attacks
    - email + username both unique and indexed: fast lookups
    - server_default for timestamps: DB server generates time, not app
    - is_superuser: simple role flag (can be expanded to RBAC later)
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    models: Mapped[list[MLModel]] = relationship(
        "MLModel", back_populates="owner", cascade="all, delete-orphan"
    )
    prediction_logs: Mapped[list[PredictionLog]] = relationship(
        "PredictionLog", back_populates="user", cascade="all, delete-orphan"
    )
