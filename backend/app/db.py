"""Synchronous SQLAlchemy 2.0 foundation.

Sync only, by DEC-010: no async engine, no `AsyncSession`, no async driver.
Any future route handler that touches the database is `def`, not `async def`,
so Starlette runs it in its threadpool.
"""

from collections.abc import Iterator
from datetime import UTC, datetime

from sqlalchemy import DateTime, Engine, MetaData, create_engine
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import get_database_url

#: Deterministic constraint names, required for Alembic batch mode on SQLite
#: (`data-model.md` § 1.5). SQLite cannot ALTER most constraints; Alembic
#: emulates it by rebuilding the table, which it can only do when every
#: constraint has a name it can predict.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class UtcDateTime(TypeDecorator[datetime]):
    """`DateTime(timezone=True)` that always hands back an aware UTC value.

    Identical DDL on both engines — this adds no schema of its own. What it
    adds is `data-model.md` § 1.3's defense: SQLite has no timezone-aware
    storage, so it silently discards the offset and returns a *naive*
    datetime, while Postgres returns an aware one. Downtime duration
    (`ended_at - started_at`) then works on one engine and raises
    ``TypeError: can't subtract offset-naive and offset-aware datetimes`` on
    the other — in deployment, from code that passed every local test.

    Naive values are rejected on the way in rather than quietly assumed to be
    UTC: the application owns the offset, the database does not.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError(
                "naive datetime reached the ORM; timestamps must be "
                "timezone-aware UTC (data-model.md § 1.3)"
            )
        return value.astimezone(UTC)

    def process_result_value(
        self, value: datetime | None, dialect: Dialect
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """Declarative base carrying the naming convention every model inherits."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def utcnow() -> datetime:
    """Timezone-aware UTC now — timestamps are generated here, never by the
    database (`data-model.md` § 1.3: no `server_default`)."""
    return datetime.now(UTC)


engine: Engine = create_engine(get_database_url())

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    """FastAPI dependency: one session per request, closed on the way out."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
