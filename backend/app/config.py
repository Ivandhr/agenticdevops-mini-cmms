"""Application settings.

The only setting in this task is the database URL. The seeding threshold
(FR-035) is deliberately not here — it belongs to the seeding task.
"""

import os
from pathlib import Path

#: `backend/` — the default SQLite file is resolved relative to it, so the URL
#: does not depend on the process's working directory.
BACKEND_ROOT = Path(__file__).resolve().parent.parent

DATABASE_URL_ENV_VAR = "CMMESS_DATABASE_URL"


def get_database_url() -> str:
    """The SQLAlchemy URL, from the environment or the local SQLite default.

    Read on every call rather than captured at import time so Alembic and the
    tests can point at a throwaway database by setting the environment
    variable.
    """
    configured = os.environ.get(DATABASE_URL_ENV_VAR)
    if configured:
        return configured
    return f"sqlite:///{(BACKEND_ROOT / 'cmmess.db').as_posix()}"
