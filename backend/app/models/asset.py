"""`asset` — the UNS discovery cache (`data-model.md` § 2.2)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UtcDateTime, utcnow


class Asset(Base):
    """A cache of UNS discovery — never the source of truth (DEC-007).

    Rebuilding the cache is an **upsert by `uns_path`**, never a
    delete-and-reinsert, and rows are never removed: an asset that disappears
    from the broker gets `is_present = False` and keeps its row and its `id`.
    The UNS is authoritative for what exists now; it has no authority over
    what happened (`data-model.md` § 2.2).
    """

    __tablename__ = "asset"

    #: A stable surrogate — deliberately *not* the asset's identity, so
    #: downtime and work-order history survives an asset briefly vanishing
    #: from the broker.
    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: The real identity of an asset (`architecture-facts.md`).
    uns_path: Mapped[str] = mapped_column(String(), nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String(), nullable=True)
    first_discovered_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utcnow
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utcnow
    )
    is_present: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
