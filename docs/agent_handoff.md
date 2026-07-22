# CMMess — Agent Handoff

> **Format: always-current. Updated every turn, not end-of-session.** This is the first thing every agent reads. It answers "where are we right now?" — keep it true.

## Read me first in any new session

Mandatory before responding to the human:

1. This file — state of play.
2. `docs/completed_development.md` *most-recent entries only* — what just shipped.
3. `docs/project_management.md` task table — live task status.
4. `docs/bug_log.md` — active bugs.
5. `docs/backlog.md` — prioritized "what's next" *(created when the first backlog item is queued; until then see `project_management.md` § Queued)*.
6. `docs/functional-spec.md` — the enumerated v1/MVP behavior (FR-001–FR-063). **APPROVED**; task specs cite its FR ids in Acceptance Criteria.

Then read what's relevant per the Tier-1/Tier-2 list in the project instructions, and the one authority doc for the area you're touching (`docs/authority-docs-by-area.md`).

## Current state

**T-001, T-002 and T-003 have all shipped; BUG-001 is fixed; there are no active bugs.** The repo holds the workflow scaffolding, the backend (FastAPI `/health` + the full v1 persisted schema), the Electron/React renderer, and a three-job CI that is green on `main`. **Product scope is settled** — read `docs/functional-spec.md` before speccing anything, and cite its FR ids in every spec's Acceptance Criteria.

**The frontier is the first domain task, and it is not yet specced.** Everything to date is infrastructure: no endpoint beyond `/health`, no auth, no domain services, no UNS. Per `docs/project_management.md` § Queued the next task in dependency order is **auth and roles (FR-001–FR-005)**, which needs a password-hashing decision (`data-model.md` § 7) and adds the hashing dependency to `backend/requirements.txt`.

**Landed this bootstrap:** all Layer B2 docs (`architecture-facts.md`, `authority-docs-by-area.md`, `contract-sync.md`) and all seven Layer A living docs; `CLAUDE.md` (root) and `.cursor/rules/qa-role.mdc`; the three checklists filled (spec-authoring, close-out, and packaging-preflight resolved as defer-TBD); a fresh CMMess `README.md`. The instructions mirror received three edits — add `api-contract.md` to Tier 2, repoint Rule 12 at `docs/contract-sync.md`, and repoint §3's review-agent config at `.cursor/rules/qa-role.mdc`. All kept docs were de-referenced from the soon-to-be-deleted scaffolds so nothing dangles.

**Scaffolding deleted; slot gate clean.** The template `layer-a/`, `layer-b2/`, `layer-b1-example/`, `agent-config/*.template.md`, `teaching/`, `diagrams/`, `INSTANTIATE.md`, and `SETUP.md` are removed. The slot gate returns only the three intentional ADOPT-IF markers (in `contract-sync.md`, `sub-agents.md`, `skills.md`) — the written-down "revisit when X" triggers, which stay.

**T-001 shipped and closed out (2026-07-22) — first full loop trip complete.** The backend skeleton is live: FastAPI `GET /health` through a typed Pydantic model, one passing pytest, ruff+mypy strict clean, `docs/api-contract.md` seeded in the same commit (Rule 12), root `.gitignore`. Commit `0a3e2a2` on `main` (direct commit — tolerated once; branch→PR resumes at T-002 when CI exists). Dev → Cursor QA → PM read-verify → human runtime test all exercised for real. Full record: `docs/completed_development.md` § T-001. Backend venv lives at `backend/.venv` (Windows: `.venv\Scripts\activate` before `uvicorn app.main:app`). Note: the PM is temporarily running as a Claude Code instance (Desktop MCP bug anthropics/claude-code#79971).

**Functional spec drafted (2026-07-22), commit `11d6705` — since APPROVED, see below.** `docs/functional-spec.md` enumerates v1 behavior as FR-001–FR-063 so task specs cite FR ids in their Acceptance Criteria. It sits between `user_story.md` (story-level why) and the per-task specs, and points at `architecture-facts.md` for hard constraints rather than restating them. Three Senior Architect decisions were taken to write it:

1. **One seeding path, two ingress routes.** UNS-detected downtime and person-reported downtime both produce a downtime event carrying its ingress `source`; a single seeding path turns an event into a work order. The manual path is specified to work when the broker has published nothing for that asset (FR-021) — this is the "front-end-triggered work orders, not dependent on UNS" MVP requirement, stated testably.
2. **MVP includes both the UNS/MQTT leg and real auth** — login with per-endpoint role re-checks. Dev and demo therefore need a broker with simulated messages.
3. **The work order→downtime-event link stays structurally optional (nullable), populated by both v1 origins and asserted in tests.** This resolves a real collision: the chosen "every WO traces to an event" model contradicts `architecture-facts.md`'s standing rule that a WO must never *require* a downtime event, and would foreclose the preventive-maintenance extension `user_story.md` mandates staying open. Nullable keeps a later preventive origin additive instead of a migration relaxing NOT NULL on live rows.

**T-003 shipped 2026-07-22 (commit `c767055`) — persistence foundation is live.** The four tables of `data-model.md` § 2 exist as typed SQLAlchemy 2.0 models with one reversible migration, sync-only per DEC-010. Anything touching persistence from here **builds on `backend/app/models/` and adds an Alembic revision — it does not create a second base or a parallel session factory.** Three things a later task will otherwise rediscover the hard way: timestamps go through `app.db.UtcDateTime` (plain `DateTime(timezone=True)` comes back *naive* from SQLite — verified, not theoretical); the migration's URL comes from `app.config`, never from `alembic.ini`; and `alembic` autogenerate must stay empty against a migrated database, which a test enforces. Full record: `docs/completed_development.md` § T-003. **It branched from the T-002 branch rather than `main`**, since T-002 had not merged and `ci.yml` lived only there.

**New in that task — a Linux CI job, and a new decision:**
- **`migrations-postgres` on `ubuntu-latest`.** GitHub Actions service containers do not run on Windows runners, so with CI pinned to `windows-latest` there is no way to execute a migration against a real Postgres — and DEC-006's "runs on both engines" would be an assertion no test backs. Windows stays the dev-parity gate; this one job exists solely to prove the Postgres leg.
- **DEC-010 — synchronous SQLAlchemy; DB-touching route handlers are `def`, not `async def`.** The failure it prevents is the quiet one: an `async def` handler making a blocking DB call compiles, typechecks, tests green, and silently serializes the whole server under concurrency — invisible until several users are on the shared instance, which is exactly this product's deployment.

Two acceptance criteria worth knowing about, because they catch defects that otherwise ship green: an **empty `alembic revision --autogenerate`** against a freshly-migrated database (a non-empty one means models and migration disagree, which breaks the *next* migration), and the partial index must **permit** a new open event once the previous one is resolved (a plain unique index on `asset_id` would let an asset break exactly once, forever).

**`docs/data-model.md` authored 2026-07-22 — the persistence authority is live.** Target schema for four tables (`identity`, `asset`, `downtime_event`, `work_order`), written against the approved FS and DEC-006/DEC-008. No persistence code exists yet; this is what the first persistence task implements. **§ 1 (engine-portability rules) is mandatory reading before any model or migration** — it exists because SQLite-vs-Postgres divergence is the failure mode that ships green in dev and breaks in deployment. The four rulings most likely to be violated by a plausible-looking implementation:

- **No native DB enums** — `String` + app-layer validation. A Postgres native enum makes adding the preventive origin (FR-032/DEC-008 require it to be additive) an `ALTER TYPE` migration on two engines; SQLite's `CHECK` emulation needs a full table rebuild to change.
- **Timezone-aware UTC datetimes, generated in Python, never a server default.** SQLite silently discards the offset and returns *naive* datetimes; Postgres returns *aware* ones. Identical duration arithmetic then works on one engine and raises `TypeError` on the other — and since SQLite is dev and Postgres is deployment, it fails in deployment from code that passed every local test.
- **The asset cache is upserted by `uns_path`; rows are never deleted.** "A cache rebuilt from the UNS" reads like a licence to truncate and repopulate, which would break every FK from `downtime_event`/`work_order` — or, with a cascade, silently erase the maintenance history of any asset briefly absent from the broker. The UNS is authoritative for what exists *now*, not for what *happened*.
- **`work_order.downtime_event_id` stays nullable** (DEC-008, § 4.2). The "every v1 WO has an event" guarantee is asserted in **tests**, deliberately not as `NOT NULL`.

The one-open-event-per-asset invariant (FR-026) is enforced by a **partial unique index**, verified portable to both engines — the two ingress routes can genuinely race, and application-level checking alone leaves a read-then-write window.

**T-002 shipped 2026-07-22 (commit `1417c5e`) — renderer + CI are live.** Electron/Vite/React/TS skeleton, one health view, three vitest tests, and `.github/workflows/ci.yml`; it closed the Rule 12 loop T-001 left open (the TypeScript leg of `GET /health`) and implements no FR — it is infrastructure. Standing constraints it established, which later tasks must not re-decide: CI on **`windows-latest`** with Node 22 / Python 3.12 and `contents: read`; `ruff` and `mypy` stay **soft** per the runbook's promotion criterion; the backend base URL is the literal `http://127.0.0.1:8000` — **not `localhost`**, which on Windows can resolve to `::1` while uvicorn binds IPv4 and presents as a dead backend; `package-lock.json` committed, since CI runs `npm ci`; no Electron launch or packaging step in CI.

**BUG-001 fixed 2026-07-22 (commit `f6fa20b`) — and it is the cautionary tale for every task that follows.** T-002 merged with a *provably broken* boundary that every gate called green: the renderer reported "backend unreachable" while the backend answered 200 to `curl`, because no `CORSMiddleware` existed and `readHealth()` correctly collapses every failure into one state. `backend/app/main.py` now allowlists exactly `http://127.0.0.1:5173` — **no wildcard** (auth lands next; wildcard-plus-credentials is a real vulnerability) and **not `"null"`** (sandboxed iframes send it too; the packaged `file://` case is a recorded blocker in `checklists/packaging-preflight.checklist.md`, and the packaged app **still cannot reach its own backend** until a custom scheme is registered). Verified the only way it could be — running the real app and confirming the **success** path renders. **TRAP-001 remains open and applies to every endpoint the domain tasks add:** a renderer test with an injected `fetch` never performs a cross-origin request, so it cannot see a browser-enforced failure. The standing remedy is an integration test against a running backend, which does not exist yet.

**FS approved 2026-07-22 — all nine open items resolved; held doc edits landed.** The Senior Architect answered every draft assumption (A-1–A-4) and open question (O-1–O-5); the answers and their rationale are recorded in `functional-spec.md` § 9 so they aren't relitigated. The five behavioral rulings worth knowing without opening the FS:

- **Seeding is gated; recording never is.** A configurable minimum duration suppresses the *work order* for a short UNS blip — the downtime event is still recorded in full, so derived asset status and downtime history stay honest. Manual events always seed. Threshold default is **PM-proposed at 5 minutes** (FR-035) and stands until the Senior Architect says otherwise — the one unconfirmed number in the FS.
- **At most one open downtime event per asset** (FR-026) — a second stop signal attaches to the open event instead of creating a rival. Follows from deriving status from the log.
- **Planner is a superset of User.** Planning, assignment, and downtime-event correction are the only exclusives (§5).
- **A Planner can correct a mis-logged event's asset, and the work order follows** (FR-027) — v1 has no void status, so without this a mis-log would corrupt an asset's history permanently.
- **`complete` is terminal**; no sign-off state, no in-app account management (operator provisioning, FR-005), no multi-assignee work orders.

All five held doc edits landed in the same turn: **DEC-008** (two ingress paths / one seeding path / nullable event link) and **DEC-009** (v1 scope) added; `architecture-facts.md` amended in two places (§ Canonical data formats rewritten — its `manual` origin had described manual *work-order* creation, which the ratified model contradicts; § Derived vs. authoritative state gained the one-open-event invariant); FS announced in `authority-docs-by-area.md`; FS added to the instructions-mirror Tier 1.

**Also remaining:**
- The human syncs **four** constitution edits into the canonical Claude Project instructions field: api-contract Tier 2, Rule 12 repoint, §3 review-agent config path, and now `functional-spec.md` in Tier 1 (plus the `design-guide.md` Tier-2 marker correction below).
- **`docs/design-guide.md` still does not exist.** Its three "live now" claims have been corrected to *(to author)* in `authority-docs-by-area.md` and the instructions mirror, so nothing now cites a doc that isn't there — but the **decision to author it is still open**, and it blocks the first UI spec. `architecture-facts.md` § Styling still names it as the token authority, which is correct as a forward reference.
- ~~Environment ground truth~~ **RESOLVED 2026-07-22: Windows is ground truth** (Rule 19). Instructions §2 corrected to `D:\GitHub\agenticdevops-mini-cmms`; venv activation is `.venv\Scripts\activate`; CI pins `windows-latest` (T-002).

## Immediate next steps

1. **PM: spec the auth task (T-004)** — FR-001–FR-005, including operator account provisioning. It is the next item in dependency order and the first task with real domain surface. It needs the **password-hashing decision** (`data-model.md` § 7) and adds the hashing dependency to `backend/requirements.txt`. It is also the natural home for the **first integration test against a running backend** — the standing remedy for TRAP-001, which no current test covers.
2. **Human: decide the two `data-model.md` § 7 open items** — the password-hashing algorithm (blocks the auth task) and whether `priority` is a free string or an ordered set with sorting semantics in the Planner queue (does not block; it ships as a free `String` and can tighten later).
3. **Human: decide on `docs/design-guide.md`** — author it, or leave it *(to author)*. Blocks the first real UI task.
4. **PM: author `docs/uns-contract.md`** — gates FR-010–FR-014 and FR-020. Can wait; the manual ingress path (FR-021) is specced to work with no broker, so the first usable slice does not depend on it.
5. Human: sync the constitution edits into the Claude Project instructions field (if still relevant while the PM runs as Claude Code). **Six**: api-contract Tier 2, Rule 12 repoint, §3 review-agent config path, `functional-spec.md` in Tier 1, `design-guide.md` marked *(to author)*, §2's repository path corrected to the Windows ground truth, and `data-model.md` flipped to live.

**Repo divergence worth deciding on.** `origin` (the working fork) and `upstream` have separate lineages: upstream carries its own T-003 implementation and is already at T-004, while this fork's `main` carries the T-001–T-003 line described above. The merge gets more expensive with every task landed on either side.

**Branch→PR discipline was not followed for T-003 or BUG-001** — both went to `main` directly at the human's instruction, with CI green on the push rather than on a PR. Recorded so the trail is accurate; the discipline stated in T-002's spec still stands for future tasks.

**Note on sequencing:** v1 is materially bigger than "reactive CMMS" implied at bootstrap — it carries the MQTT/UNS leg *and* real auth (DEC-009). Task breakdown from here is planned against `functional-spec.md`, not extrapolated from the original scaffold split (see `project_management.md` § Queued). `data-model.md` is now live and implemented; **`uns-contract.md` is the one remaining authority doc that gates real work** — FR-010–FR-014 and FR-020.

## Architecture authorities by area (read the one you're touching)

The full index is in `docs/authority-docs-by-area.md`. Short version: architecture constraints → `architecture-facts.md` (every spec) · **product behavior / v1 scope → `functional-spec.md` (live — approved 2026-07-22)** · **persistence → `data-model.md` (live — authored 2026-07-22; read § 1 before any model or migration)** · REST boundary → `api-contract.md` *(live — seeded by T-001)* · UNS/MQTT → `uns-contract.md` *(to author)* · boundary-change sync → `contract-sync.md` · auth/roles → `architecture-facts.md` § Security · UI → `design-guide.md` *(to author)* · packaging → `packaging.md` *(to author)*.

## Standing notes

- **Keep the instructions mirror in sync.** Canonical project instructions live in the Claude Project field; the git-tracked mirror is `docs/claude_project_instructions.md`. When the instructions change, rewrite the mirror in the same turn. If the two diverge, the Project copy wins. *(Four edits are currently mirror-only and need mirroring into the Project field: the `api-contract.md` Tier-2 addition, the Rule 12 repoint at `docs/contract-sync.md`, §3's review-agent config repoint at `.cursor/rules/qa-role.mdc`, and `functional-spec.md` added to Tier 1 with `design-guide.md` corrected to *(to author)* in Tier 2.)*
- **No repo doc is attached to the Claude Project.** Every living doc is read on demand from the repo so it can't go stale.
- **The seven foundational architecture choices** (separate-service topology, server-side role enforcement, SQLAlchemy+Alembic dual-engine persistence, live-broker UNS, the two-ingress/one-seeding-path work-order model with its nullable event link, v1 scope, and synchronous SQLAlchemy with `def` handlers) are recorded in `decision-log.md` as DEC-004–010 and enforced via `architecture-facts.md`. Don't relitigate from memory.
