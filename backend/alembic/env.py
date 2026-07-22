"""Alembic environment.

Two things here are load-bearing and easy to lose (`data-model.md` § 1.5):

* the URL comes from `app.config`, not from a hardcoded `sqlalchemy.url` in
  `alembic.ini`, so a migration always runs against whatever database the
  application itself would open;
* `render_as_batch=True`, because SQLite cannot `ALTER` most constraints —
  Alembic emulates it by rebuilding the table, and only batch mode does that.
  Omitting it works right up until the first constraint-altering migration,
  then fails with an unnamed-constraint error.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app import models
from app.config import get_database_url

# The Alembic Config object, providing access to alembic.ini.
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Importing the models package imports every model, so autogenerate compares
# against all four tables rather than silently against a subset.
target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to the script output instead of running it."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = create_engine(get_database_url(), poolclass=pool.NullPool)

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                render_as_batch=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
