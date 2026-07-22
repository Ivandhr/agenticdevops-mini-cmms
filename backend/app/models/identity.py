"""`identity` — users and their roles (`data-model.md` § 2.1)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UtcDateTime, utcnow


class Identity(Base):
    """A user account, provisioned by the instance operator (FR-005).

    Rows are never hard-deleted: work orders and downtime events reference
    identities as author, reporter, and assignee, so deleting a person would
    orphan or rewrite history. Deactivate with `is_active` instead
    (`data-model.md` § 2.1).
    """

    __tablename__ = "identity"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(), nullable=False, unique=True)
    #: A hash, never a recoverable secret. The algorithm is the auth task's
    #: call (`data-model.md` § 7).
    password_hash: Mapped[str] = mapped_column(String(), nullable=False)
    #: `user` | `planner` — a plain string, validated in the application layer
    #: (`data-model.md` § 1.1), FR-002.
    role: Mapped[str] = mapped_column(String(), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utcnow
    )
