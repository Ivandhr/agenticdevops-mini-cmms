"""`downtime_event` — the authoritative event log (`data-model.md` § 2.3)."""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Index, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, UtcDateTime, utcnow


class DowntimeEvent(Base):
    """A stoppage, however it reached the system (FR-020, FR-021).

    `ended_at IS NULL` means the event is **open** and the asset is down.
    Asset status is derived from that, never stored (`data-model.md` § 3).
    """

    __tablename__ = "downtime_event"
    __table_args__ = (
        # History queries: "what happened to this asset, most recent first".
        Index("ix_downtime_event_asset_id_started_at", "asset_id", "started_at"),
        # At most one *open* event per asset (FR-026, `data-model.md` § 4.1).
        # Partial, so the constraint applies only while the event is open — a
        # plain unique index on asset_id would let an asset break exactly once,
        # forever. Portable to both engines (`data-model.md` § 1.6); the
        # predicate is standard SQL, not dialect SQL.
        #
        # This lives in the database because the two ingress routes can race:
        # a broker message and a technician's tap can arrive in the same
        # instant, and an application-level check has a read-then-write window.
        # The seeding path treats the resulting integrity error as the expected
        # "already down" outcome, not a crash.
        Index(
            "uq_downtime_event_open_asset",
            "asset_id",
            unique=True,
            sqlite_where=text("ended_at IS NULL"),
            postgresql_where=text("ended_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    #: Correctable by a Planner (FR-027); the seeded work order follows in the
    #: same transaction (`data-model.md` § 4.3 — domain layer, not a cascade).
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("asset.id"), nullable=False
    )
    #: `uns` | `manual` — the ingress route (FR-020, FR-021). Plain string,
    #: validated in the application layer (`data-model.md` § 1.1).
    source: Mapped[str] = mapped_column(String(), nullable=False)
    started_at: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False)
    #: `NULL` ⇒ open ⇒ the asset is down.
    ended_at: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    #: What was observed. Immutable after creation (FR-036) — enforced by the
    #: domain layer exposing no update path, not by the database.
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    #: The reporting person for `manual`; `NULL` for `uns`.
    reported_by_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(), ForeignKey("identity.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=utcnow
    )
