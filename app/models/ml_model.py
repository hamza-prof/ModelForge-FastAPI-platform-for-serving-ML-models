from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class ModelStatus(str, enum.Enum):
    """
    Lifecycle states for an ML model.
    Using str mixin allows JSON serialization: ModelStatus.ACTIVE == "active"
    """

    UPLOADING = "uploading"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    FAILED = "failed"


class MLModel(Base):
    """
    ML model metadata table.

    Stores metadata about uploaded models — the actual model binary
    lives on disk at `file_path` (or S3 in production).
    """

    __tablename__ = "ml_models"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    framework: Mapped[str] = mapped_column(String(50))  # sklearn | torch | onnx
    file_path: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[ModelStatus] = mapped_column(
        Enum(ModelStatus), default=ModelStatus.UPLOADING
    )
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    owner: Mapped[User] = relationship("User", back_populates="models")

    __table_args__ = (
        UniqueConstraint("owner_id", "name", "version", name="uq_owner_model_version"),
    )
