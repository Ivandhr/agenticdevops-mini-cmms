"""The migration chain runs, reverses, and matches the models.

Every test builds its own SQLite file under pytest's `tmp_path` and points
`CMMESS_DATABASE_URL` at it, so alembic can only ever reach a database the
test itself created. Nothing here touches the dev database.
"""

import ast
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from alembic import command
from app.config import DATABASE_URL_ENV_VAR
from app.models import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]
VERSIONS_DIR = BACKEND_ROOT / "alembic" / "versions"

EXPECTED_TABLES = {"identity", "asset", "downtime_event", "work_order"}


def throwaway_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    """Point the app config at a fresh SQLite file inside `tmp_path`."""
    url = f"sqlite:///{(tmp_path / 'test.db').as_posix()}"
    monkeypatch.setenv(DATABASE_URL_ENV_VAR, url)
    return url


def alembic_config() -> Config:
    """Alembic configured exactly as the CLI would configure it.

    No URL is set here on purpose: env.py resolves it through `app.config`,
    so this exercises the same path a developer running `alembic upgrade head`
    takes.
    """
    return Config(str(BACKEND_ROOT / "alembic.ini"))


def test_upgrade_head_creates_the_four_tables(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = throwaway_database(tmp_path, monkeypatch)
    command.upgrade(alembic_config(), "head")

    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    assert EXPECTED_TABLES <= tables
    # Only alembic's own bookkeeping table beyond the schema.
    assert tables - EXPECTED_TABLES == {"alembic_version"}


def test_downgrade_base_then_upgrade_head_round_trips(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = throwaway_database(tmp_path, monkeypatch)
    config = alembic_config()

    command.upgrade(config, "head")
    command.downgrade(config, "base")

    engine = create_engine(url)
    try:
        assert not EXPECTED_TABLES & set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    command.upgrade(config, "head")

    engine = create_engine(url)
    try:
        assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_autogenerate_against_a_migrated_database_is_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The models and the migration agree.

    A non-empty diff here is the defect that silently breaks the *next*
    migration: autogenerate would fold this drift into it, and the migration
    would then be applied to databases that already have the schema.
    """
    url = throwaway_database(tmp_path, monkeypatch)
    command.upgrade(alembic_config(), "head")

    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            diff = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert diff == []


def execute_calls(source: str) -> list[str]:
    """Every `<something>.execute(...)` call in `source`, by callee name.

    Parsed rather than grepped: a substring search matches the phrase inside a
    comment or docstring too, so it reports violations that are not one — and
    a check that cries wolf gets deleted.
    """
    return [
        ast.unparse(node.func)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "execute"
    ]


def test_the_raw_sql_detector_detects_raw_sql() -> None:
    """Prove the check before trusting its silence (CLAUDE.md)."""
    assert execute_calls("op.execute('CREATE INDEX foo ON bar (baz)')") == [
        "op.execute"
    ]
    assert execute_calls("op.create_index('foo', 'bar', ['baz'])") == []


def test_no_migration_uses_raw_sql() -> None:
    """`op.*` operations only — raw SQL is where the dialects diverge (§ 1.4)."""
    migrations = sorted(VERSIONS_DIR.glob("*.py"))
    assert migrations, "expected at least the initial migration"

    for migration in migrations:
        found = execute_calls(migration.read_text(encoding="utf-8"))
        assert not found, (
            f"{migration.name} executes SQL directly ({found}); use op.*"
        )
