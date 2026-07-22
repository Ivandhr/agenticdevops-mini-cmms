"""initial schema

The four v1 tables of `docs/data-model.md` § 2.

Two deliberate properties of this file:

* it uses `sa.DateTime(timezone=True)` rather than the application's
  `UtcDateTime` type. The DDL is identical — `UtcDateTime` only normalizes
  values in Python — and a migration that imports application code breaks the
  day that code is renamed. Migrations stay self-contained snapshots.
* every index is created with `op.create_index`, including the partial unique
  one. No `op.execute()`, no dialect SQL (`data-model.md` § 1.4).

Revision ID: 02a388b50a5f
Revises:
Create Date: 2026-07-22 18:24:59.098174

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "02a388b50a5f"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The predicate behind the one-open-event-per-asset invariant (FR-026).
#: `IS NULL` is standard SQL — the same text is valid on SQLite and Postgres.
_OPEN_EVENT = "ended_at IS NULL"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "identity",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_identity")),
        sa.UniqueConstraint("username", name=op.f("uq_identity_username")),
    )
    op.create_table(
        "asset",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("uns_path", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=True),
        sa.Column("first_discovered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_present", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_asset")),
        sa.UniqueConstraint("uns_path", name=op.f("uq_asset_uns_path")),
    )
    op.create_table(
        "downtime_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reported_by_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # No ondelete/onupdate anywhere: assets and identities are never
        # hard-deleted, and events are the historical record
        # (`data-model.md` § 5).
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["asset.id"],
            name=op.f("fk_downtime_event_asset_id_asset"),
        ),
        sa.ForeignKeyConstraint(
            ["reported_by_id"],
            ["identity.id"],
            name=op.f("fk_downtime_event_reported_by_id_identity"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_downtime_event")),
    )
    op.create_index(
        "ix_downtime_event_asset_id_started_at",
        "downtime_event",
        ["asset_id", "started_at"],
        unique=False,
    )
    # Partial, so it constrains *open* events only. A plain unique index on
    # asset_id would let an asset break exactly once, forever.
    op.create_index(
        "uq_downtime_event_open_asset",
        "downtime_event",
        ["asset_id"],
        unique=True,
        sqlite_where=sa.text(_OPEN_EVENT),
        postgresql_where=sa.text(_OPEN_EVENT),
    )
    op.create_table(
        "work_order",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        # Nullable on purpose — DEC-008, `data-model.md` § 4.2.
        sa.Column("downtime_event_id", sa.Uuid(), nullable=True),
        sa.Column("origin", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scheduled_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assignee_id", sa.Uuid(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("execution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["asset.id"],
            name=op.f("fk_work_order_asset_id_asset"),
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["identity.id"],
            name=op.f("fk_work_order_assignee_id_identity"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["identity.id"],
            name=op.f("fk_work_order_created_by_id_identity"),
        ),
        sa.ForeignKeyConstraint(
            ["downtime_event_id"],
            ["downtime_event.id"],
            name=op.f("fk_work_order_downtime_event_id_downtime_event"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_order")),
    )
    op.create_index("ix_work_order_asset_id", "work_order", ["asset_id"], unique=False)
    op.create_index(
        "ix_work_order_assignee_id_status",
        "work_order",
        ["assignee_id", "status"],
        unique=False,
    )
    op.create_index("ix_work_order_status", "work_order", ["status"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_work_order_status", table_name="work_order")
    op.drop_index("ix_work_order_assignee_id_status", table_name="work_order")
    op.drop_index("ix_work_order_asset_id", table_name="work_order")
    op.drop_table("work_order")
    op.drop_index("uq_downtime_event_open_asset", table_name="downtime_event")
    op.drop_index("ix_downtime_event_asset_id_started_at", table_name="downtime_event")
    op.drop_table("downtime_event")
    op.drop_table("asset")
    op.drop_table("identity")
