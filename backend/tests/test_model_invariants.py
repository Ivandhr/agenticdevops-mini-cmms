"""The schema invariants that are worth a test.

The engine fixture migrates a fresh SQLite file inside pytest's `tmp_path`
and disposes of it; no test opens a database it did not create.
"""

from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Engine,
    Enum,
    create_engine,
    func,
    select,
)
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from alembic import command
from app.config import DATABASE_URL_ENV_VAR
from app.db import utcnow
from app.models import Asset, Base, DowntimeEvent, Identity, WorkOrder

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    """A migrated, throwaway SQLite database.

    Migrated rather than `create_all`-ed, so these tests exercise the schema
    the migration actually ships.
    """
    url = f"sqlite:///{(tmp_path / 'invariants.db').as_posix()}"
    monkeypatch.setenv(DATABASE_URL_ENV_VAR, url)
    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")

    engine = create_engine(url)
    try:
        yield engine
    finally:
        engine.dispose()


def make_asset(session: Session, uns_path: str) -> Asset:
    asset = Asset(uns_path=uns_path)
    session.add(asset)
    session.commit()
    return asset


def open_event(asset: Asset, started_at: datetime | None = None) -> DowntimeEvent:
    """An event with no `ended_at` — i.e. the asset is down."""
    return DowntimeEvent(
        asset_id=asset.id,
        source="uns",
        started_at=started_at if started_at is not None else utcnow(),
    )


def count_events(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(DowntimeEvent)) or 0


# --- one open downtime event per asset (FR-026, data-model.md § 4.1) ---------


def test_second_open_event_for_one_asset_is_rejected(engine: Engine) -> None:
    with Session(engine) as session:
        asset = make_asset(session, "site/line1/press")
        session.add(open_event(asset))
        session.commit()

        session.add(open_event(asset))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_a_closed_event_frees_the_asset_to_break_again(engine: Engine) -> None:
    """The index constrains *open* events only.

    A unique index on `asset_id` alone would also block this, which would let
    an asset break exactly once and then never again.
    """
    with Session(engine) as session:
        asset = make_asset(session, "site/line1/press")
        first = open_event(asset)
        session.add(first)
        session.commit()

        first.ended_at = utcnow()
        session.commit()

        session.add(open_event(asset))
        session.commit()  # must not raise

        assert count_events(session) == 2


def test_two_assets_can_be_down_at_once(engine: Engine) -> None:
    with Session(engine) as session:
        press = make_asset(session, "site/line1/press")
        oven = make_asset(session, "site/line1/oven")

        session.add(open_event(press))
        session.add(open_event(oven))
        session.commit()

        assert count_events(session) == 2


# --- the work-order → event link stays optional (DEC-008, § 4.2) -------------


def test_work_order_persists_without_a_downtime_event(engine: Engine) -> None:
    with Session(engine) as session:
        asset = make_asset(session, "site/line1/press")
        session.add(
            WorkOrder(
                asset_id=asset.id,
                downtime_event_id=None,
                origin="manual_downtime",
                status="new",
            )
        )
        session.commit()

        stored = session.scalars(select(WorkOrder)).one()
        assert stored.downtime_event_id is None


# --- timestamps survive the round trip aware (data-model.md § 1.3) -----------


def test_utc_datetimes_come_back_aware_from_sqlite(engine: Engine) -> None:
    """SQLite has no timezone-aware storage: it discards the offset and hands
    back a naive datetime, so duration arithmetic that works on Postgres
    raises `TypeError` here. The value must round-trip *through the database*
    for this test to prove anything — hence the second session.
    """
    started_at = utcnow() - timedelta(minutes=17)

    with Session(engine) as session:
        asset = make_asset(session, "site/line1/press")
        session.add(open_event(asset, started_at=started_at))
        session.commit()

    with Session(engine) as session:
        event = session.scalars(select(DowntimeEvent)).one()

        assert event.started_at.tzinfo is not None
        # The operation the app performs on every open event: how long down?
        assert utcnow() - event.started_at >= timedelta(minutes=17)
        assert event.started_at == started_at


def test_naive_datetimes_are_refused(engine: Engine) -> None:
    """The application owns the offset; a naive value is a defect, not a
    default to be guessed at."""
    with Session(engine) as session:
        asset = make_asset(session, "site/line1/press")
        session.add(open_event(asset, started_at=datetime.now()))
        with pytest.raises(StatementError, match="naive datetime"):
            session.commit()
        session.rollback()


# --- properties of the schema as a whole ------------------------------------


def test_no_derived_value_is_stored() -> None:
    """`data-model.md` § 3 — duration and up/down status are derived, always."""
    forbidden = {"duration", "is_down", "current_status"}
    for table in Base.metadata.tables.values():
        stored = {column.name for column in table.columns}
        assert not stored & forbidden, f"{table.name} stores a derived value"


def test_no_native_enums_and_no_check_constraints() -> None:
    """`data-model.md` § 1.1 — enumerated values are plain strings, validated
    in the application layer, so `work_order.origin` stays additively
    extensible (FR-032)."""
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert not isinstance(column.type, Enum), f"{table.name}.{column.name}"
            if isinstance(column.type, Boolean):
                assert not column.type.create_constraint
        for constraint in table.constraints:
            assert not isinstance(constraint, CheckConstraint), table.name


def test_no_foreign_key_declares_a_cascade() -> None:
    """`data-model.md` § 5 — a cascade is a mechanism for silently destroying
    the maintenance history."""
    for table in Base.metadata.tables.values():
        for foreign_key in table.foreign_keys:
            assert foreign_key.ondelete is None
            assert foreign_key.onupdate is None


def test_identity_username_is_unique(engine: Engine) -> None:
    with Session(engine) as session:
        session.add(Identity(username="ana", password_hash="x", role="planner"))
        session.commit()

        session.add(Identity(username="ana", password_hash="y", role="user"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
