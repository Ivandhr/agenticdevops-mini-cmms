# CMMess — Decision Log

> Numbered architectural decisions with rationale and date. When a spec touches an area a decision governs, read the decision **first** — it exists so the reasoning isn't relitigated from memory.

**Entry format:**
```
### DEC-NNN — <short decision title>

**Date:** YYYY-MM-DD
**Decision:** <what was decided, stated as a rule>
**Rationale:** <why — the trade-offs weighed>
**Supersedes:** <DEC-MMM, if this reverses an earlier decision — else "none">
```

**Conventions:**
- Numbered, append-only, ordered by number ascending. A reversal is a **new** DEC that names the one it supersedes; the old entry stays (history isn't rewritten).
- The decision is stated as a **rule** the specs can enforce, not a narrative.

## Log

### DEC-001 — Mechanical QA lives in the review agent; behavioral testing stays with the human

**Date:** 2026-07-21
**Decision:** The review agent (Cursor) owns mechanical QA — typecheck, lint, tests, and diffing the change against the spec's Acceptance Criteria. It is not given the human's behavioral/runtime-testing job; the human drives behavioral testing (feel and behavior).
**Rationale:** Separating "does it compile, pass, and match what was asked" from "does it feel and behave right" lets each participant catch what the other structurally can't, and keeps the human's pass from being spent re-verifying that the build works. Referenced as "Decision D1" in project instructions §3.
**Supersedes:** none *(inherited from the workflow template at project instantiation)*

### DEC-002 — No agent adopts the skills mechanism

**Date:** 2026-07-21
**Decision:** Value ships through the mechanism that fits each role — coding-agent config (`CLAUDE.md`), review-agent rules (`.cursor/rules/`), and PM checklists — not through a formal "skills" mechanism.
**Rationale:** No case was found where a skills mechanism beat the plain per-role mechanism; adopting it preemptively adds ceremony without a matching failure it prevents. The adopt-if trigger is recorded in `agent-config/skills.md`.
**Supersedes:** none *(inherited from the workflow template at project instantiation)*

### DEC-003 — Ground-truth deference is a numbered rule

**Date:** 2026-07-21
**Decision:** When the human states something about their own working environment or their own runtime observation, that is authoritative about a system the PM cannot see — act on it first, reason second (Rule 19). This is not blanket deference on code correctness, where reading the actual files remains the PM's check.
**Rationale:** Codified from a saga where the PM kept CI on the wrong runtime version for three round-trips after the human repeatedly named the right one. The observable world the human can see and the PM can't is the human's to call.
**Supersedes:** none *(inherited from the workflow template at project instantiation)*

### DEC-004 — Separate-service backend topology

**Date:** 2026-07-21
**Decision:** The FastAPI backend runs as a separate local service (`uvicorn`); the React/TypeScript renderer calls it directly over HTTP on localhost. The Electron main process is lifecycle-only (windows/app lifecycle) and never proxies data or domain calls between renderer and backend.
**Rationale:** Path of least resistance — one plain REST boundary, typed and testable end to end, instead of a two-hop IPC-then-HTTP chain; keeps main thin. Trade-off: two processes to launch in dev and orchestrate at package time, accepted for the simpler contract.
**Supersedes:** none

### DEC-005 — Server-side authorization; the renderer's role is display-only

**Date:** 2026-07-21
**Decision:** User vs. Planner authorization is enforced in the FastAPI backend, per action. Login issues a backend token/session; every protected endpoint independently re-checks the authenticated identity's role. The renderer may hide or show UI by role for UX, but that is never treated as access control.
**Rationale:** Single shared multi-user instance — client-side checks are trivially bypassed, and a hidden button is not security. Trade-off: an explicit role check on every protected endpoint, accepted as the only real boundary.
**Supersedes:** none

### DEC-006 — SQLAlchemy + Alembic, dual-engine (SQLite default, Postgres supported)

**Date:** 2026-07-21
**Decision:** All persistence goes through SQLAlchemy; migrations are authored with Alembic to run on both SQLite and Postgres, additive-first. SQLite is the default for v1/dev; Postgres is supported. No SQLite-only or Postgres-only SQL.
**Rationale:** The SQLite→Postgres path is a stated product requirement; a dialect shortcut now is an expensive refactor later. An ORM plus a migration tool gives portability and a versioned schema. Trade-off: ORM overhead and the discipline of engine-portable migrations, accepted for the portability guarantee.
**Supersedes:** none

### DEC-007 — UNS asset discovery over a live MQTT broker; the backend is the sole client

**Date:** 2026-07-21
**Decision:** Asset discovery is driven by a live MQTT broker (with simulated data in dev). The backend is the only MQTT client — nothing else subscribes or publishes. The UNS topic structure is an authoritative, documented contract (`docs/uns-contract.md`). The local asset registry is a cache of UNS discovery, never the source of truth.
**Rationale:** Matches how it will run, keeps a single ingestion point, and keeps the UNS authoritative for what assets exist so onboarding stays process-agnostic. Trade-off: dev needs a broker running with simulated messages, accepted since that mirrors production.
**Supersedes:** none

### DEC-008 — Two downtime ingress paths, one seeding path; the work-order→event link stays nullable

**Date:** 2026-07-22
**Decision:** Downtime reaches the system by two ingress routes — detected on the UNS (`source: uns`) or recorded by a person in the UI (`source: manual`) — and both produce a downtime event that flows through **exactly one** work-order seeding path. The manual route must function when the broker has published nothing for that asset. Three constraints on the model: (a) an asset has **at most one open downtime event**; a second stop signal attaches to the open one rather than creating a rival. (b) Seeding — never recording — is gated by a configurable minimum duration for UNS-sourced events; manual events always seed. (c) The work order's link to its originating downtime event is **structurally optional (nullable)**, populated by both v1 origins and asserted as a v1 invariant **in tests, not in the schema**.
**Rationale:** One seeding path means the manual route costs almost nothing to support and cannot drift from the automated one, and a manually reported stoppage moves the asset to `down` exactly as a detected one does — asset status stays truthful because it is derived from a single coherent event log. (a) follows from that derivation: two concurrent open events on one asset make "is it down, and for how long?" ill-defined. (b) keeps the event log complete and honest while stopping four-second blips from burying the Planner queue. (c) resolves a genuine collision — "every work order traces to a downtime event" contradicts `architecture-facts.md`'s standing rule that a work order must never *require* one, and would foreclose the preventive-maintenance extension `user_story.md` mandates staying open. A nullable link keeps a later preventive origin **additive**, instead of a migration that must relax a NOT NULL constraint on rows that already exist. Trade-off: v1's "every work order has an event" guarantee is enforced by tests rather than by the database, accepted because the alternative buys enforcement today at the cost of the product's stated future.
**Supersedes:** none *(fills the gap where `architecture-facts.md` § Canonical data formats had no backing decision; that section is amended to match)*

### DEC-009 — v1 scope: both ingress paths, real auth, operator-provisioned accounts

**Date:** 2026-07-22
**Decision:** v1 ships the MQTT/UNS discovery leg **and** the manual ingress path together, not manual-first with UNS deferred. v1 also ships real authentication — login issuing a backend session/token, with every protected endpoint re-checking role per action. Accounts are provisioned by the instance operator via backend command or configuration; v1 ships no registration, password-reset, or in-app account-management surface. `docs/functional-spec.md` is the authority for the resulting behavior.
**Rationale:** Shipping UNS in v1 proves the product's distinctive process-agnostic move early and matches DEC-007's "test it the way it runs" posture; deferring it would leave the manual path as the only exercised route and let the seeding path quietly specialize around it. Real auth is cheaper now than retrofitted — added after endpoints exist, it touches every endpoint and every test. Operator provisioning is the smallest thing that still onboards a real team, which the single-shared-multi-user premise requires; an admin UI is deferred, not denied. Trade-off: a materially larger MVP, and dev/demo now require a broker with simulated messages, accepted for a v1 that exercises every seam it ships.
**Supersedes:** none

### DEC-010 — Synchronous SQLAlchemy; FastAPI route handlers are `def`, not `async def`

**Date:** 2026-07-22
**Decision:** Persistence uses **synchronous** SQLAlchemy 2.0 — sync `Engine`, sync `Session`, no `asyncio` extension and no async driver. FastAPI route handlers that touch the database are declared `def` (not `async def`), so Starlette runs them in its threadpool and a blocking database call never occupies the event loop. The MQTT client (DEC-007), which is async, does **not** share a session with request handling; it performs its writes through the same sync session machinery inside a worker thread.
**Rationale:** Async SQLAlchemy buys throughput this product does not need — a maintenance team's request volume is trivial — and costs greenlet-backed sessions, an async driver per engine, and a second set of testing idioms, on a codebase that must stay portable across SQLite and Postgres (DEC-006). Sync sessions with `def` handlers is the path FastAPI explicitly supports and the one most reference material assumes, which matters for a coding-agent-authored codebase. The failure this decision prevents is the subtle one: an `async def` handler making a blocking database call compiles, typechecks, tests green, and silently serializes the whole server under concurrency — invisible until multiple users are on the shared instance, which is precisely the deployment this product targets. Trade-off: the async MQTT ingestion path must cross a thread boundary to persist, accepted as one well-defined seam rather than an async idiom spread across every module.
**Supersedes:** none
