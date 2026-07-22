# Task T-003 — Persistence foundation: SQLAlchemy models + dual-engine Alembic

## 1. Background

First persistence task. It stands up the storage layer the entire domain phase sits
on: SQLAlchemy 2.0 models for the four v1 tables, Alembic wired to run on **both**
SQLite and Postgres, and the initial migration that creates the schema.

**No API endpoints, no auth logic, no domain services, no UNS.** Those are separate
tasks. This task's job is that the schema exists, is correct, and provably migrates
on both engines — nothing more. Getting persistence right before anything depends on
it is the cheapest ordering; a schema defect found after five features are built on
it is a refactor.

**Branch from `main` after T-002 has merged**, so this task's PR runs against a real
CI workflow.

Authority docs consulted: **`docs/data-model.md`** (the schema authority — this task
implements it; **§ 1 engine-portability rules are binding**), `docs/architecture-facts.md`
(§ Persistence & migrations, § Derived vs. authoritative state),
`docs/decision-log.md` (DEC-006 dual-engine, DEC-008 nullable event link, **DEC-010
synchronous SQLAlchemy**), `docs/functional-spec.md` (the FRs the columns serve),
`docs/contract-sync.md` (Rule 12 — schema changes move with `data-model.md`),
`docs/devops_pipeline.md` (the CI runbook this task extends).

**FRs served (storage only — no behavior is implemented here):** FR-002, FR-005,
FR-020–FR-027, FR-030–FR-036, FR-040–FR-041, FR-051.

## 2. What Already Exists (Do Not Rewrite)

**`backend/` from T-001 — build on it, do not replace it.**

- `backend/app/main.py` — FastAPI app with `GET /health` and the `HealthResponse`
  Pydantic model. **Leave the existing endpoint and model untouched.** This task may
  add imports/wiring to this file only if genuinely required; it adds no endpoint.
- `backend/requirements.txt` — six deps. **Edit to add**, do not regenerate or
  re-pin the existing entries.
- `backend/pyproject.toml` — ruff (E/F/I/W) and mypy strict, both clean from
  `backend/`. **New code must satisfy the existing configuration.** Do not relax
  strictness, do not add per-module `ignore_errors`, and do not add blanket `# type:
  ignore`. If a dependency genuinely lacks stubs, add a narrowly-scoped
  `[[tool.mypy.overrides]]` for that module only, and say so in the PR.
- `backend/tests/` — the existing health test must keep passing.

**`docs/data-model.md`** — the schema authority, already written. This task
*implements* it. Do not redesign the schema; if you believe the doc is wrong, **stop
and flag it to the PM** rather than implementing something different (see § 6).

**T-002 artifacts** (present once T-002 merges): `.github/workflows/ci.yml`, the
renderer, `package.json`. This task **edits `ci.yml`** and touches nothing else of
T-002's.

**Does not exist yet:** any SQLAlchemy model, any Alembic setup, any database file,
any settings/config module.

## 3. What to Build

### 3.1 Configuration

1. **`backend/app/config.py`** — a small settings module exposing the database URL,
   read from environment variable **`CMMESS_DATABASE_URL`**, defaulting to a local
   SQLite file (`sqlite:///./cmmess.db`, resolved relative to `backend/`). No other
   settings in this task — the seeding threshold (FR-035) belongs to the seeding
   task.

### 3.2 Database plumbing

2. **`backend/app/db.py`** — the sync SQLAlchemy 2.0 foundation (DEC-010):
   - A `DeclarativeBase` subclass whose `MetaData` carries an explicit
     **`naming_convention`** for `ix`, `uq`, `ck`, `fk`, `pk` (`data-model.md` § 1.5).
     This is required for Alembic batch mode on SQLite; without it the first
     constraint-altering migration fails.
   - A sync `Engine` and a `sessionmaker`.
   - A session-per-request dependency suitable for FastAPI, closing the session on
     exit.
   - **Sync only** — no `create_async_engine`, no `AsyncSession`, no async driver
     (DEC-010).

### 3.3 The models

3. **SQLAlchemy 2.0 declarative models** (typed, `Mapped[...]` / `mapped_column`
   style so they satisfy mypy strict) for the four tables in `docs/data-model.md`
   § 2 — `identity`, `asset`, `downtime_event`, `work_order` — with exactly the
   columns, nullability, uniqueness, and indexes that document specifies.

   Organize as a package (e.g. `backend/app/models/`) with one module per entity and
   an `__init__.py` re-exporting them, so every model is imported by the time Alembic
   autogenerate inspects the metadata.

   **Non-negotiable specifics from `data-model.md` § 1** — these are the ones a
   plausible implementation gets wrong:

   - **`Uuid` primary keys**, generated in Python. No autoincrement integers, no
     database-side default.
   - **`String` columns for every enumerated value** (`identity.role`,
     `downtime_event.source`, `work_order.origin`, `work_order.status`). **No
     `sa.Enum`, no `native_enum`, no `CHECK` constraint on them.** Validation lives
     in the application layer. This is what keeps `origin` additively extensible
     (FR-032, DEC-008).
   - **`DateTime(timezone=True)` for every timestamp**, values generated in Python
     as timezone-aware UTC. **No `server_default=func.now()`, no
     `CURRENT_TIMESTAMP`.**
   - **`work_order.downtime_event_id` is NULLABLE.** Deliberate (DEC-008,
     `data-model.md` § 4.2). Do not "tighten" it.
   - **No `ondelete`/`onupdate` cascades on any foreign key** (`data-model.md` § 5).
   - **No stored derived values** — no `duration`, no `is_down`, no
     `current_status` column anywhere (`data-model.md` § 3).

### 3.4 Alembic, dual-engine

4. **Alembic scaffolding under `backend/`** — `alembic.ini`, `alembic/env.py`,
   `alembic/script.py.mako`, `alembic/versions/`.

   `env.py` must:
   - Read the database URL from the same config module as the app (§ 3.1), **not**
     from a hardcoded `sqlalchemy.url` in `alembic.ini`.
   - Set **`render_as_batch=True`** in the migration context — required so SQLite
     constraint changes work at all (`data-model.md` § 1.5).
   - Target the models' `MetaData` so autogenerate sees all four tables.

5. **One initial migration** creating all four tables, their foreign keys, their
   indexes (`data-model.md` § 2), and the **partial unique index** enforcing one open
   downtime event per asset:

   ```
   UNIQUE INDEX on downtime_event (asset_id) WHERE ended_at IS NULL
   ```

   Expressed through Alembic's `op.create_index(..., sqlite_where=…, postgresql_where=…)`
   or the equivalent portable form — **not** `op.execute()` with raw SQL
   (`data-model.md` § 1.4).

   The migration must be **reversible**: `downgrade()` drops what `upgrade()`
   created.

### 3.5 Tests

6. **Tests under `backend/tests/`.** Every test uses a **throwaway database** — a
   `tmp_path` SQLite file or in-memory engine created and destroyed by the test.

   > **Hard rule, from CLAUDE.md's first non-negotiable:** no test, fixture, or
   > helper may read, write, delete, or reset the dev database (`cmmess.db`) or any
   > other real database. Do not add a fixture that drops tables on a shared engine.
   > If you find yourself writing cleanup that deletes a `.db` file you did not
   > create in that same test, stop.

   Required properties (see Acceptance Criteria for the full list):
   - `alembic upgrade head` on an empty SQLite database creates all four tables.
   - `downgrade base` then `upgrade head` round-trips cleanly.
   - The partial unique index **rejects** a second *open* event for the same asset,
     and **permits** a new open event once the previous one has `ended_at` set.
   - A timezone-aware UTC datetime written and read back still supports subtraction
     against another aware datetime.

### 3.6 CI — the Postgres leg

7. **`.github/workflows/ci.yml`** — add a **third job**: `migrations-postgres`, on
   **`ubuntu-latest`**, with a **Postgres service container**, that installs the
   backend requirements and runs `alembic upgrade head` (then `downgrade base`)
   against that Postgres instance. Hard gate.

   Existing jobs are unchanged: the Windows backend job and the Windows renderer
   job keep their runners, their runtime pins, and their soft/hard split.

   **Why a Linux runner for this one job:** GitHub Actions service containers do not
   run on Windows runners. Without a Linux job there is no way to execute a
   migration against a real Postgres, and DEC-006's "runs on both engines" would be
   an assertion no test backs. Windows remains the dev-parity gate; this job exists
   solely to prove the Postgres leg.

8. **`docs/devops_pipeline.md`** — add the new job to the "What CI runs" table and
   the "What each guard protects" list, and record why that one job runs on Linux.

9. **`.gitignore`** — add local database artifacts (`*.db`, `*.sqlite3`) so a dev
   database can never be committed.

## 4. Acceptance Criteria

Verifiable properties. All backend commands run from `backend/`.

**Schema and migrations**

- [ ] `alembic upgrade head` against an empty SQLite database creates exactly the
      four tables of `docs/data-model.md` § 2, with the columns, nullability, and
      uniqueness that document specifies.
- [ ] `alembic downgrade base` followed by `alembic upgrade head` completes without
      error.
- [ ] `alembic upgrade head` succeeds against a real Postgres instance (proven by
      the new CI job).
- [ ] No migration file contains raw dialect SQL via `op.execute()`.
- [ ] `alembic revision --autogenerate` against a freshly-migrated database produces
      an **empty** migration — i.e. the models and the migration agree. *(A
      non-empty autogenerate here means the migration does not match the models,
      which is the defect that silently breaks the next migration.)*

**The invariants that matter**

- [ ] Inserting a second downtime event with `ended_at IS NULL` for an asset that
      already has an open event **fails** with an integrity error (FR-026).
- [ ] After the first event is given an `ended_at`, inserting a new open event for
      that same asset **succeeds**. *(The index must constrain open events only —
      an index that also blocks this would make an asset breakable exactly once.)*
- [ ] Two open events for *different* assets both succeed.
- [ ] `work_order.downtime_event_id` accepts `NULL` — a work order can be persisted
      with no downtime event (DEC-008).
- [ ] A timezone-aware UTC datetime persisted and read back can be subtracted from
      another aware datetime without a `TypeError`, **on SQLite**. *(This is
      `data-model.md` § 1.3's trap: SQLite discards offsets and returns naive
      datetimes. If this test passes only because the value never left Python, it
      proves nothing — it must round-trip through the database.)*
- [ ] No table has a stored `duration`, `is_down`, or `current_status` column.
- [ ] No enumerated column uses `sa.Enum`, a native database enum, or a `CHECK`
      constraint.
- [ ] No foreign key declares `ondelete` or `onupdate` cascade behavior.

**Tooling and hygiene**

- [ ] `pip install -r requirements.txt` succeeds.
- [ ] `pytest` passes, including the pre-existing `/health` test.
- [ ] `ruff check .` exits 0.
- [ ] `mypy .` exits 0 under the **existing** strict configuration, with no new
      blanket ignores and no relaxation of `pyproject.toml`.
- [ ] `uvicorn app.main:app` still boots and serves `/health`.
- [ ] No test reads, writes, or deletes any database it did not itself create.
- [ ] CI is green on the pull request, including the new Postgres job.
- [ ] No renderer or Electron file is modified.

## 5. Files to Modify

**New:**

- `backend/app/config.py`
- `backend/app/db.py`
- `backend/app/models/__init__.py`
- `backend/app/models/identity.py`
- `backend/app/models/asset.py`
- `backend/app/models/downtime_event.py`
- `backend/app/models/work_order.py`
- `backend/alembic.ini`
- `backend/alembic/env.py`
- `backend/alembic/script.py.mako`
- `backend/alembic/versions/<rev>_initial_schema.py`
- `backend/tests/test_migrations.py`
- `backend/tests/test_model_invariants.py`

**Edited (existing — do not recreate):**

- `backend/requirements.txt` — add SQLAlchemy 2.x, Alembic, and a Postgres driver
  (`psycopg[binary]`) for the CI Postgres job. Leave existing pins alone.
- `.github/workflows/ci.yml` — add the `migrations-postgres` job only
- `docs/devops_pipeline.md` — document the new job
- `.gitignore` — add `*.db`, `*.sqlite3`

**Explicitly not touched:** `backend/app/main.py` beyond wiring that is genuinely
required (no new endpoint), `backend/pyproject.toml` (except a narrowly-scoped mypy
override if a dependency truly lacks stubs), `docs/data-model.md` (unless § 6's
deviation clause applies), any renderer/Electron file, anything else under `docs/`.

The exact module split inside `backend/app/models/` is the agent's call provided
every model is importable from the package root.

## 6. Coding-Agent Instructions

Read this spec file (`docs/tasks/task_T-003_persistence-foundation.md`) in full
before writing any code — **and read `docs/data-model.md` in full as well**, because
this task implements that document and § 1 of it is binding.

Implement the persistence foundation in `backend/`: a config module reading
`CMMESS_DATABASE_URL` (SQLite default), a sync SQLAlchemy 2.0 base with an explicit
`MetaData` naming convention, typed declarative models for `identity`, `asset`,
`downtime_event`, and `work_order` exactly as `docs/data-model.md` § 2 specifies,
Alembic wired with `render_as_batch=True` and reading its URL from the app config,
and one reversible initial migration creating all four tables plus the partial
unique index enforcing one open downtime event per asset. Add tests using throwaway
databases only. Extend `.github/workflows/ci.yml` with an `ubuntu-latest`
`migrations-postgres` job that runs the migration against a Postgres service
container, and document it in `docs/devops_pipeline.md`. **No endpoints, no auth, no
domain services, no UNS in this task.**

Hard constraints decided by this spec — do not re-decide these:

- **Never touch a real or dev database.** CLAUDE.md's first non-negotiable. Every
  test creates and destroys its own throwaway database. No fixture drops tables on a
  shared engine; nothing deletes a `.db` file it did not create in that same test.
- **Sync SQLAlchemy only (DEC-010).** No async engine, no `AsyncSession`, no async
  driver. Any future DB-touching route handler is `def`, not `async def`.
- **No native enums, no `CHECK` constraints on enumerated columns.** `String` plus
  application-layer validation. This is what keeps `work_order.origin` additively
  extensible (FR-032, DEC-008).
- **`DateTime(timezone=True)` everywhere; timestamps generated in Python; no server
  defaults.**
- **`work_order.downtime_event_id` stays nullable.** If tightening it feels
  obviously correct, re-read DEC-008 — the looseness is the point.
- **`render_as_batch=True` and an explicit `MetaData` naming convention.** Both are
  required for SQLite; omitting them works until the first constraint-altering
  migration and then fails confusingly.
- **The partial unique index must constrain open events only** — a plain unique
  index on `asset_id` would permit an asset to break exactly once, forever.
- **No raw dialect SQL in migrations** — `op.*` operations only.
- **Do not relax `backend/pyproject.toml`.** New code satisfies the existing strict
  mypy configuration. A narrowly-scoped per-module override for a genuinely
  stub-less dependency is acceptable and must be called out; blanket ignores are
  not.
- **Silencer decision:** no kept-but-unused symbols are expected. Model modules
  imported solely so Alembic sees them are **not** unused symbols — re-export them
  from `backend/app/models/__init__.py`, which is a real use, rather than reaching
  for a lint suppression. If you still believe you need a silencer, **stop and flag
  it to the PM.**
- **Deviation clause.** `docs/data-model.md` is the schema authority and this task
  implements it as written. If implementing it reveals the document is wrong or
  impossible, **stop and flag it to the PM** — do not silently implement a different
  schema. If the PM agrees a change is right, the model, the migration, **and
  `docs/data-model.md`** move in the same commit (Rule 12,
  `docs/contract-sync.md`).
- **Contract-sync (Rule 12):** `docs/data-model.md` is this task's contract doc. It
  is already written and the code must match it, so no edit is expected — an edit is
  required only under the deviation clause above. `docs/api-contract.md` is **N/A**:
  this task adds no endpoint and changes no request/response shape.
- **User-facing impact: None.** No user-visible surface changes — the schema is
  invisible until the domain tasks land. No user-doc change required beyond the
  `docs/devops_pipeline.md` CI documentation named above.
- **Structural-layout pre-flight (Rule 11): N/A** — no UI in this task.

Standing invariants: honor docs/architecture-facts.md and CLAUDE.md; the renderer
holds no business logic, DB, or MQTT/UNS access; authorization is enforced
server-side; keep contract docs (Rule 12) and user-docs (Rule 18) in the same
commit; migrations run on both SQLite and Postgres; never read/write/delete data
outside the app's own store; build with npm run build when done.
