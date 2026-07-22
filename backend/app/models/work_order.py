"""`work_order` — the maintenance job (`data-model.md` § 2.4)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UtcDateTime, utcnow


class WorkOrder(Base):
    """Work seeded from a downtime event, then planned and executed."""

    __tablename__ = "work_order"
    __table_args__ = (
        # The Planner queue (FR-061).
        Index("ix_work_order_status", "status"),
        # "My work" (FR-062).
        Index("ix_work_order_assignee_id_status", "assignee_id", "status"),
        # Per-asset views.
        Index("ix_work_order_asset_id", "asset_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: Follows event corrections (FR-027) — updated by the domain layer in the
    #: same transaction, not by a database cascade (`data-model.md` § 4.3).
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("asset.id"), nullable=False
    )
    #: **Deliberately nullable (DEC-008, `data-model.md` § 4.2).** Both v1
    #: origins populate it and tests assert that; the schema stays loose so a
    #: later preventive-maintenance origin — which has no downtime event — is
    #: an additive change rather than a migration relaxing NOT NULL on live
    #: rows across two engines.
    downtime_event_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("downtime_event.id"), nullable=True
    )
    #: `uns_downtime` | `manual_downtime`, and extensible (FR-032). A plain
    #: string precisely so adding a member stays a one-line application change
    #: (`data-model.md` § 1.1).
    origin: Mapped[str] = mapped_column(String(), nullable=False)
    #: `new` | `planned` | `in_progress` | `complete` (functional-spec § 6).
    status: Mapped[str] = mapped_column(String(), nullable=False)
    #: Copied from the event at seeding, then independently editable (FR-036).
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    priority: Mapped[str | None] = mapped_column(String(), nullable=True)
    scheduled_start: Mapped[datetime | None] = mapped_column(
        UtcDateTime(), nullable=True
    )
    scheduled_end: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    #: Exactly one assignee — no join table (FR-041, A-3).
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("identity.id"), nullable=True
    )
    #: `NULL` ⇒ system-seeded. Nullable rather than pointing at a synthetic
    #: "system" account, which would be a fake person every query filtering
    #: real users must remember to exclude (`data-model.md` § 2.4).
    created_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("identity.id"), nullable=True
    )
    execution_notes: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utcnow
    )
    #: Set on the transition to `in_progress`.
    started_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    #: Set on the transition to `complete`.
    completed_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
