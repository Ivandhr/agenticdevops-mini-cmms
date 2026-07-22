# CMMess — Completed Development

> The full history of completed work. **Read the recent entries before assuming something isn't built.** Log an entry **only after reading the actual output files** — it records what was *built*, not what was planned.

## How to use this log

- **Entries are immutable once written**, except to add/update the "verified by human" line. A future reader who finds an older entry restating a mechanism should **not** "clean it up" — that's drift in the wrong direction.
- Newest entries at the top of `## Log`.
- When this file gets large, archive by release into `docs/archive/completed_development_<release>.md` and keep only recent entries live.

## Per-entry convention

The entry shape — header block, the required body sections in order, the length caps, and the anti-patterns — is owned by **`checklists/close-out.checklist.md`**. Follow it there.

The one line worth repeating because it's mandatory and cheap: every entry carries a **`User-facing impact:`** line, never omitted. `None.` is a valid, considered answer.

## Log

### T-003 — Persistence foundation: SQLAlchemy 2.0 models + dual-engine Alembic

**Date:** 2026-07-22
**Spec:** `docs/tasks/task_T-003_persistence-foundation.md`
**Verified by human:** 🟡 n/a — the schema has no user-visible surface. Proven by CI run `29939087883`: `alembic upgrade head` **and** `downgrade base` against a real Postgres 16 service container.

**What was built.** The storage layer the whole domain phase sits on (commit `c767055`), implementing `docs/data-model.md` § 2 as written: typed SQLAlchemy 2.0 declarative models for `identity`, `asset`, `downtime_event`, and `work_order`, a sync `Engine`/`sessionmaker` with a session-per-request dependency (DEC-010 — no async engine anywhere), and one reversible initial migration. `Uuid` PKs generated in Python; `String` for every enumerated column with no `sa.Enum` and no `CHECK`; no cascades; no stored derived values. The one-open-event-per-asset invariant (FR-026) is a **partial** unique index built through `op.create_index(..., sqlite_where=…, postgresql_where=…)` — no raw SQL — so a closed event frees the asset to break again.

`backend/app/config.py` reads `CMMESS_DATABASE_URL` (SQLite default, resolved relative to `backend/`); `alembic.ini` carries **no** `sqlalchemy.url`, so env.py resolves it through the same config and the app and its migrations cannot point at different databases. `render_as_batch=True` plus an explicit `MetaData` naming convention are both in place — required before the first constraint-altering migration on SQLite, and confusing to diagnose if added later.

Nine tests, each against a throwaway SQLite file under `tmp_path`. Three earn their keep beyond the obvious: `alembic` autogenerate against a freshly-migrated database is **empty** (models and migration agree — a non-empty diff silently corrupts the *next* migration); a UTC datetime survives a round trip **through the database** still aware; and the raw-SQL check parses the migration's AST rather than grepping, after a substring search matched the phrase inside its own docstring.

**Files touched.** NEW: `backend/app/config.py` · `backend/app/db.py` · `backend/app/models/{__init__,identity,asset,downtime_event,work_order}.py` · `backend/alembic.ini` · `backend/alembic/{env.py,script.py.mako}` · `backend/alembic/versions/02a388b50a5f_initial_schema.py` · `backend/tests/{test_migrations,test_model_invariants}.py`
MODIFIED: `backend/requirements.txt` (SQLAlchemy, Alembic, `psycopg[binary]`) · `.github/workflows/ci.yml` (new `migrations-postgres` job) · `docs/devops_pipeline.md` · `.gitignore` (`*.db`, `*.sqlite3`)

**Deviations from spec.** Three, all recorded rather than silent:
1. **Branched from the T-002 branch, not `main`** — the spec assumed T-002 had merged; it had not, and `ci.yml` (which this task must edit) existed only there. Procedural; the merge to `main` carried both.
2. **`app.db.UtcDateTime`**, a `TypeDecorator` over `DateTime(timezone=True)`, normalizes values in Python. **DDL is unchanged**, so `data-model.md` needs no edit (no Rule 12 trigger). It exists because the acceptance criterion demanding an aware datetime after a SQLite round trip is otherwise unsatisfiable — verified empirically first: plain `DateTime(timezone=True)` returns a *naive* datetime and duration arithmetic raises `TypeError`, exactly as `data-model.md` § 1.3 predicts.
3. **The migration uses `sa.DateTime(timezone=True)`**, not the app type autogenerate rendered. Identical DDL, and a migration that imports application code breaks the day that code is renamed.

**Architectural impact.** None — implements `docs/data-model.md` § 2 as written. First Linux CI job (`migrations-postgres`); rationale recorded in `docs/devops_pipeline.md`.

**User-facing impact.** None. The schema is invisible until the domain tasks land; no user-doc change beyond the CI runbook.

### T-002 — Renderer scaffold (Electron + React + TS), green CI, and the backend CORS allowlist

**Date:** 2026-07-22
**Spec:** `docs/tasks/task_T-002_renderer-scaffold-ci.md`
**Verified by human:** ✅ 2026-07-22 — with the backend running, the Electron window renders **"Backend healthy — ok"** (green), the success path, not a plausible-looking error state

**What was built.** The Electron/Vite/React/TypeScript renderer skeleton and `.github/workflows/ci.yml` (commit `1417c5e`), making "CI green" true for the first time. One view calls `GET /health` at the literal `http://127.0.0.1:8000` — `127.0.0.1`, never `localhost`, which on Windows can resolve to `::1` while uvicorn binds IPv4 and presents as a dead backend — and renders either the reported status or a clearly distinct unreachable state. The main process is lifecycle-only per DEC-004 (`contextIsolation: true`, `nodeIntegration: false`, no backend calls, no IPC data channels, no DB, no MQTT). The response is consumed through a shared `HealthResponse` TS type in `src/renderer/api/types.ts`, and `docs/api-contract.md` gained that type's name and path in the same commit (Rule 12). Three vitest tests cover healthy / request-failure / non-2xx, and say in their own header that they prove renderer logic and **not** the boundary.

**The boundary was in fact broken on merge, and the tests could not see it.** Logged as **BUG-001**, with **TRAP-001** codified from it. The renderer's page origin (`:5173`) differs from the backend's (`:8000`), no `CORSMiddleware` existed, and `readHealth()` correctly collapses every failure into `unreachable` — so the app reported a dead backend while `curl` got 200 from it. The spec was amended (§ 3.4) to permit exactly one backend change, which shipped separately as **commit `f6fa20b`**: `allow_origins` of exactly `["http://127.0.0.1:5173"]`, no wildcard (auth lands next per DEC-005, and wildcard-plus-credentials is a real vulnerability), and `"null"` deliberately excluded — sandboxed iframes send it too, so it would be permanently loose. Three backend tests assert the header is emitted for the allowlisted origin and **absent** for an unlisted one and for `"null"`; the negative cases are what fail if a future CORS complaint is "fixed" with `["*"]`.

**Files touched.** NEW: `package.json` · `package-lock.json` · `tsconfig.json` · `eslint.config.mjs` · `vite.config.ts` · `vite.main.config.ts` · `index.html` · `src/main/main.ts` · `src/renderer/{main.tsx,App.tsx}` · `src/renderer/api/{types.ts,health.ts,health.test.ts}` · `.github/workflows/ci.yml`
MODIFIED: `docs/api-contract.md` (TS leg) · `docs/devops_pipeline.md` · `README.md` (Running locally) · `checklists/packaging-preflight.checklist.md` (packaged-origin blocker) · **later, for BUG-001:** `backend/app/main.py` · `backend/tests/test_health.py`

**Deviations from spec.** One, since corrected: the original spec forbade backend changes while requiring live backend health — contradictory constraints. The coding agent surfaced the conflict rather than violating the constraint, which is correct; the commit message's claim that the gap shipped "by PM decision" was inaccurate and is recorded as such in `docs/bug_log.md`.

**Architectural impact.** TRAP-001 codified — a renderer test with an injected `fetch` cannot see a browser-enforced boundary failure. See `docs/bug_log.md`.

**User-facing impact.** The project's first user-visible surface: an application window reporting backend health. `README.md` gained a "Running locally" section in the same commit (Rule 18).

### T-001 — Backend skeleton: FastAPI `GET /health`, test, tooling; API contract doc seeded

**Date:** 2026-07-22
**Spec:** `docs/tasks/task_T-001_backend-skeleton.md`
**Verified by human:** ✅ 2026-07-22 — booted `uvicorn app.main:app`; live `GET /health` returned 200 `{"status":"ok"}`

**What was built.** The Python/FastAPI backend skeleton (commit `0a3e2a2`): `backend/app/main.py` exposes `GET /health` through a typed Pydantic `HealthResponse` (`status: Literal["ok"]`) — the typed-boundary invariant honored from the very first endpoint. One pytest exercises it via `TestClient`, asserting 200 and the exact body. `backend/requirements.txt` holds exactly six deps (fastapi, uvicorn, pytest, httpx, ruff, mypy — no SQLAlchemy/Alembic/MQTT); `backend/pyproject.toml` configures ruff (E/F/I/W) and mypy strict (py311) so bare `ruff check .`, `mypy .`, and `pytest` all exit clean from `backend/`. The commit also seeds `docs/api-contract.md` with the `/health` entry (Rule 12, same commit; TypeScript leg N/A until the renderer lands) and a root `.gitignore`. Cursor QA: PASS on all checks. Known non-blocking: pytest surfaces a Starlette-internal deprecation warning — revisit at the next dependency bump.

**Files touched.** All NEW:
- `backend/app/__init__.py`
- `backend/app/main.py`
- `backend/tests/__init__.py`
- `backend/tests/test_health.py`
- `backend/requirements.txt`
- `backend/pyproject.toml`
- `docs/api-contract.md`
- `.gitignore`

**Deviations from spec.** One, procedural: committed directly to `main` rather than branch→PR — acceptable this once because no CI exists yet to gate a PR (that lands with T-002); branch→PR resumes from T-002 onward. Code content: none.

**Architectural impact.** None — first instance of the typed renderer↔backend boundary pattern per `docs/architecture-facts.md`; `docs/api-contract.md` now live (announced in `docs/authority-docs-by-area.md`'s terms as the REST-boundary authority).

**User-facing impact.** None. No user-visible surface exists yet; no user-doc changes required.
