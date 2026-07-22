# CMMess — DevOps Pipeline

> An operational **runbook**: what CI runs, what each guard protects, and the criteria for changing them. Anyone asking "what does CI do and why is this check failing?" should land *here*.

## What CI runs

`.github/workflows/ci.yml`, on every push to the main branch and every pull request.

**Runtime: Node 22 (LTS) + Python 3.12.** These are the versions specified by the human lead as the local/target toolchain, and CI pins them exactly. **Keep CI matching the version the human actually runs** — the workflow that produced Rule 19 / DEC-003 was CI drifting off the correct runtime for several round-trips. When the local toolchain moves, this pin moves in the same change, and the reason is recorded here.

**Runner OS: `windows-latest` for the backend and renderer jobs.** Same principle as the runtime pins — Windows is the confirmed ground truth for this project, so CI runs where the human runs. Windows is also where the platform-specific traps live (path separators, `.venv\Scripts\activate`, `localhost` resolving to `::1` while uvicorn binds IPv4); a Linux runner would pass straight over them. Recorded in T-002.

**One exception: `migrations-postgres` runs on `ubuntu-latest`.** GitHub Actions **service containers do not run on Windows runners**, and a service container is the only way to get a real Postgres in front of the migration. Without this job, DEC-006's "every migration runs on both engines" would be an assertion nothing executes — the Windows jobs only ever see SQLite, which is exactly the half-test `data-model.md` § 1.4 warns about. Windows remains the dev-parity gate; this job exists solely to prove the Postgres leg. Recorded in T-003.

Three jobs run: a Python job for the FastAPI backend and a Node job for the Electron/React renderer (the split-service topology, DEC-004), plus the Postgres migration job.

| Step | Command | Fails the build? |
|---|---|---|
| Install — backend | `pip install -r requirements.txt` | yes |
| Install — renderer | `npm ci` | yes |
| Typecheck — renderer | `tsc --noEmit` | yes |
| Typecheck — backend | `mypy` | no — soft (see promotion) |
| Lint — renderer | `eslint` | yes |
| Lint — backend | `ruff check` | no — soft (see promotion) |
| Test — backend | `pytest` | yes |
| Test — renderer | `vitest run` | yes |
| Migrate up — Postgres | `alembic upgrade head` | yes |
| Migrate down — Postgres | `alembic downgrade base` | yes |
| Generated-doc freshness | *(deferred — no generated docs yet)* | n/a |

**Read-only by default.** The workflow requests read-only repo permissions and never requests a write token. See "the drift-detecting agent" below for why that matters.

**Native-addon rebuild — not currently applicable.** The database is Python-side (SQLAlchemy on SQLite/Postgres, DEC-006), so there is no native Node addon such as `better-sqlite3` in the renderer or main to rebuild in CI. If a native Node dependency ever enters the Electron side, add its rebuild step here and note the ABI/version reality — that is exactly the kind of environment detail this section exists to hold (and it connects to Rule 14's native-module caution).

## What each guard protects

- **Install (both)** — the app actually resolves its dependencies on a clean checkout, not just on a machine with warm caches.
- **Typecheck — renderer (`tsc`)** — type errors before runtime, and it enforces the renderer half of the typed renderer↔backend REST surface (the TS types must line up with the Pydantic models — Rule 12 / `contract-sync.md`).
- **Typecheck — backend (`mypy`)** — type errors in the FastAPI/domain code.
- **Lint (`eslint` / `ruff`)** — style consistency and a class of common-bug patterns.
- **Test — backend (`pytest`)** — backend domain-logic regressions; the renderer↔backend contract and server-side role enforcement (DEC-005) are covered here by integration tests against a running backend, not mocked into triviality (per `architecture-facts.md` § Testing boundaries).
- **Test — renderer (`vitest`)** — pure renderer-logic regressions.
- **Migrations on Postgres (`alembic upgrade head`, then `downgrade base`)** — the deployment engine actually accepts the schema, and the migration reverses. This is the guard against the whole class of green-in-dev, broken-in-deployment failures `data-model.md` § 1 enumerates: a native enum, a dialect-specific `op.execute()`, a SQLite-only assumption. `pytest` on the Windows job covers the SQLite half; "it ran on SQLite" is half a test. The **down** leg matters as much as the up leg — a migration that cannot be reversed cannot be rolled back in deployment.
- **Generated-doc freshness** — will catch generated pages drifting from their source once any exist; deferred until then.

No ratchets are defined yet. The first likely one is the contract-drift CI check flagged as an adopt-if in `docs/contract-sync.md` — fail a contract change that ships with no matching doc change. The ratchet pattern: a check that fails on the forbidden pattern everywhere except an allowlist that may only shrink, so new code can't add the pattern and the pre-existing cases trend to zero.

## Soft checks and the promotion criterion

A check that will produce false positives on day one starts as a **non-blocking reminder** (warns, doesn't fail), and is promoted to a hard failure only after it has run clean across real merged PRs.

- **`mypy` (backend) — soft.** On a fresh codebase mypy is noisy against untyped third-party libraries; start advisory and promote once the backend has real, typed code and the noise is resolved.
- **`ruff` (backend) — soft, but expected to promote quickly.** Usually low false-positive; kept advisory only until the backend skeleton lands, then promoted.
- **Generated-doc freshness — deferred.** No generated docs exist yet; add and start soft when the first generated page appears.

Everything else (installs, `tsc`, `eslint`, `pytest`, `vitest`) is a hard gate from the first commit that has code to check.

## The drift-detecting agent — deliberately constrained

A documentation drift-detector may be added later. Its rules are fixed **in advance**, because the temptation to relax them arrives *after* it's useful:

1. **It drafts; a human approves.** It opens a pull request. It **never commits to the main branch**, never pushes, never merges. This is why CI requests no write token — the pipeline is a *checker*, not a *writer*.
2. **Auto-written, unverified docs are worse than missing docs**, because users trust documentation. A wrong page confidently answers with a falsehood. Generated prose never lands without a human reading it first.

If tempted to give CI write access "just to auto-fix the generated pages," don't — regeneration is a local step a human runs and commits; the CI ratchets exist precisely to catch the case where they forgot.

## First green build

The scaffold arrived in two slices, not one:

- **T-001 (backend skeleton)** shipped the Python side — `backend/requirements.txt`, the FastAPI app with `GET /health`, and one passing pytest. It created no `package.json` and no workflow file, so CI did not yet exist and the commit went direct to `main`.
- **T-002 (renderer scaffold + green CI)** shipped the Node side — `package.json` with a committed `package-lock.json`, the Electron/Vite/React/TypeScript skeleton, one passing vitest — **and `.github/workflows/ci.yml` itself**. This is the task where every step in the table above first has something real to run, and the first task gated by a pull request.
