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

**Bootstrap complete; T-001 shipped; the functional spec is approved.** The repo holds the workflow scaffolding, the CMMess instructions and user story, and the backend skeleton from T-001. **Product scope is settled** — read `docs/functional-spec.md` before speccing anything, and cite its FR ids in every spec's Acceptance Criteria.

**Landed this bootstrap:** all Layer B2 docs (`architecture-facts.md`, `authority-docs-by-area.md`, `contract-sync.md`) and all seven Layer A living docs; `CLAUDE.md` (root) and `.cursor/rules/qa-role.mdc`; the three checklists filled (spec-authoring, close-out, and packaging-preflight resolved as defer-TBD); a fresh CMMess `README.md`. The instructions mirror received three edits — add `api-contract.md` to Tier 2, repoint Rule 12 at `docs/contract-sync.md`, and repoint §3's review-agent config at `.cursor/rules/qa-role.mdc`. All kept docs were de-referenced from the soon-to-be-deleted scaffolds so nothing dangles.

**Scaffolding deleted; slot gate clean.** The template `layer-a/`, `layer-b2/`, `layer-b1-example/`, `agent-config/*.template.md`, `teaching/`, `diagrams/`, `INSTANTIATE.md`, and `SETUP.md` are removed. The slot gate returns only the three intentional ADOPT-IF markers (in `contract-sync.md`, `sub-agents.md`, `skills.md`) — the written-down "revisit when X" triggers, which stay.

**T-001 shipped and closed out (2026-07-22) — first full loop trip complete.** The backend skeleton is live: FastAPI `GET /health` through a typed Pydantic model, one passing pytest, ruff+mypy strict clean, `docs/api-contract.md` seeded in the same commit (Rule 12), root `.gitignore`. Commit `0a3e2a2` on `main` (direct commit — tolerated once; branch→PR resumes at T-002 when CI exists). Dev → Cursor QA → PM read-verify → human runtime test all exercised for real. Full record: `docs/completed_development.md` § T-001. Backend venv lives at `backend/.venv` (`source .venv/bin/activate` before `uvicorn app.main:app`). Note: the PM is temporarily running as a Claude Code instance (Desktop MCP bug anthropics/claude-code#79971).

**Functional spec drafted (2026-07-22), commit `11d6705` — DRAFT, not signed off.** `docs/functional-spec.md` enumerates v1 behavior as FR-001–FR-063 so task specs cite FR ids in their Acceptance Criteria. It sits between `user_story.md` (story-level why) and the per-task specs, and points at `architecture-facts.md` for hard constraints rather than restating them. Three Senior Architect decisions were taken to write it:

1. **One seeding path, two ingress routes.** UNS-detected downtime and person-reported downtime both produce a downtime event carrying its ingress `source`; a single seeding path turns an event into a work order. The manual path is specified to work when the broker has published nothing for that asset (FR-021) — this is the "front-end-triggered work orders, not dependent on UNS" MVP requirement, stated testably.
2. **MVP includes both the UNS/MQTT leg and real auth** — login with per-endpoint role re-checks. Dev and demo therefore need a broker with simulated messages.
3. **The work order→downtime-event link stays structurally optional (nullable), populated by both v1 origins and asserted in tests.** This resolves a real collision: the chosen "every WO traces to an event" model contradicts `architecture-facts.md`'s standing rule that a WO must never *require* a downtime event, and would foreclose the preventive-maintenance extension `user_story.md` mandates staying open. Nullable keeps a later preventive origin additive instead of a migration relaxing NOT NULL on live rows.

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
- **Environment ground truth unconfirmed:** instructions §2 records the repo at `/Users/walkerreynolds/PycharmProjects/agenticdevops-mini-cmms`, but the PM instance runs from `D:\GitHub\agenticdevops-mini-cmms` on Windows. This becomes load-bearing at T-002 (CI runner OS) and affects the handoff's own `source .venv/bin/activate` line. Rule 19 — the human's statement decides it.

## Immediate next steps

1. **Human: confirm the environment ground truth** (Windows `D:\GitHub\...` vs. the POSIX path in instructions §2). This blocks T-002 — it decides the CI runner OS.
2. **PM: spec T-002** — renderer scaffold + green CI (carries `ci.yml`; branch→PR→merge discipline resumes here). Unblocked by the FS; waiting only on #1.
3. **PM: re-plan the task breakdown against `functional-spec.md`.** The queued list predates the FS and no longer reflects v1's real shape.
4. **Human: decide on `docs/design-guide.md`** — author it, or leave it *(to author)*. Blocks the first UI spec, not T-002.
5. Human: sync the four constitution edits into the Claude Project instructions field (if still relevant while the PM runs as Claude Code).

**Note on sequencing:** v1 is materially bigger than "reactive CMMS" implied at bootstrap — it carries the MQTT/UNS leg *and* real auth (DEC-009). Task breakdown after T-002 must be re-planned against `functional-spec.md` rather than extrapolated from the original scaffold split. `data-model.md` and `uns-contract.md` are both still *(to author)* and each gates real work: the data model gates every persistence task, the UNS contract gates FR-010–FR-014 and FR-020.

## Architecture authorities by area (read the one you're touching)

The full index is in `docs/authority-docs-by-area.md`. Short version: architecture constraints → `architecture-facts.md` (every spec) · **product behavior / v1 scope → `functional-spec.md` (live — approved 2026-07-22)** · persistence → `data-model.md` *(to author)* · REST boundary → `api-contract.md` *(live — seeded by T-001)* · UNS/MQTT → `uns-contract.md` *(to author)* · boundary-change sync → `contract-sync.md` · auth/roles → `architecture-facts.md` § Security · UI → `design-guide.md` *(to author)* · packaging → `packaging.md` *(to author)*.

## Standing notes

- **Keep the instructions mirror in sync.** Canonical project instructions live in the Claude Project field; the git-tracked mirror is `docs/claude_project_instructions.md`. When the instructions change, rewrite the mirror in the same turn. If the two diverge, the Project copy wins. *(Four edits are currently mirror-only and need mirroring into the Project field: the `api-contract.md` Tier-2 addition, the Rule 12 repoint at `docs/contract-sync.md`, §3's review-agent config repoint at `.cursor/rules/qa-role.mdc`, and `functional-spec.md` added to Tier 1 with `design-guide.md` corrected to *(to author)* in Tier 2.)*
- **No repo doc is attached to the Claude Project.** Every living doc is read on demand from the repo so it can't go stale.
- **The six foundational architecture choices** (separate-service topology, server-side role enforcement, SQLAlchemy+Alembic dual-engine persistence, live-broker UNS, the two-ingress/one-seeding-path work-order model with its nullable event link, and v1 scope) are recorded in `decision-log.md` as DEC-004–009 and enforced via `architecture-facts.md`. Don't relitigate from memory.
