# CMMess — Agent Handoff

> **Format: always-current. Updated every turn, not end-of-session.** This is the first thing every agent reads. It answers "where are we right now?" — keep it true.

## Read me first in any new session

Mandatory before responding to the human:

1. This file — state of play.
2. `docs/completed_development.md` *most-recent entries only* — what just shipped.
3. `docs/project_management.md` task table — live task status.
4. `docs/bug_log.md` — active bugs.
5. `docs/backlog.md` — prioritized "what's next" *(created when the first backlog item is queued; until then see `project_management.md` § Queued)*.
6. `docs/functional-spec.md` — the enumerated v1/MVP behavior (FR-001–FR-063). **DRAFT under review**; task specs cite its FR ids in Acceptance Criteria.

Then read what's relevant per the Tier-1/Tier-2 list in the project instructions, and the one authority doc for the area you're touching (`docs/authority-docs-by-area.md`).

## Current state

**Bootstrap complete; T-001 shipped; the functional spec is drafted and under review.** The repo holds the workflow scaffolding, the CMMess instructions and user story, and the backend skeleton from T-001. **Product scope is now written down** — read `docs/functional-spec.md` before speccing anything.

**Landed this bootstrap:** all Layer B2 docs (`architecture-facts.md`, `authority-docs-by-area.md`, `contract-sync.md`) and all seven Layer A living docs; `CLAUDE.md` (root) and `.cursor/rules/qa-role.mdc`; the three checklists filled (spec-authoring, close-out, and packaging-preflight resolved as defer-TBD); a fresh CMMess `README.md`. The instructions mirror received three edits — add `api-contract.md` to Tier 2, repoint Rule 12 at `docs/contract-sync.md`, and repoint §3's review-agent config at `.cursor/rules/qa-role.mdc`. All kept docs were de-referenced from the soon-to-be-deleted scaffolds so nothing dangles.

**Scaffolding deleted; slot gate clean.** The template `layer-a/`, `layer-b2/`, `layer-b1-example/`, `agent-config/*.template.md`, `teaching/`, `diagrams/`, `INSTANTIATE.md`, and `SETUP.md` are removed. The slot gate returns only the three intentional ADOPT-IF markers (in `contract-sync.md`, `sub-agents.md`, `skills.md`) — the written-down "revisit when X" triggers, which stay.

**T-001 shipped and closed out (2026-07-22) — first full loop trip complete.** The backend skeleton is live: FastAPI `GET /health` through a typed Pydantic model, one passing pytest, ruff+mypy strict clean, `docs/api-contract.md` seeded in the same commit (Rule 12), root `.gitignore`. Commit `0a3e2a2` on `main` (direct commit — tolerated once; branch→PR resumes at T-002 when CI exists). Dev → Cursor QA → PM read-verify → human runtime test all exercised for real. Full record: `docs/completed_development.md` § T-001. Backend venv lives at `backend/.venv` (`source .venv/bin/activate` before `uvicorn app.main:app`). Note: the PM is temporarily running as a Claude Code instance (Desktop MCP bug anthropics/claude-code#79971).

**Functional spec drafted (2026-07-22), commit `11d6705` — DRAFT, not signed off.** `docs/functional-spec.md` enumerates v1 behavior as FR-001–FR-063 so task specs cite FR ids in their Acceptance Criteria. It sits between `user_story.md` (story-level why) and the per-task specs, and points at `architecture-facts.md` for hard constraints rather than restating them. Three Senior Architect decisions were taken to write it:

1. **One seeding path, two ingress routes.** UNS-detected downtime and person-reported downtime both produce a downtime event carrying its ingress `source`; a single seeding path turns an event into a work order. The manual path is specified to work when the broker has published nothing for that asset (FR-021) — this is the "front-end-triggered work orders, not dependent on UNS" MVP requirement, stated testably.
2. **MVP includes both the UNS/MQTT leg and real auth** — login with per-endpoint role re-checks. Dev and demo therefore need a broker with simulated messages.
3. **The work order→downtime-event link stays structurally optional (nullable), populated by both v1 origins and asserted in tests.** This resolves a real collision: the chosen "every WO traces to an event" model contradicts `architecture-facts.md`'s standing rule that a WO must never *require* a downtime event, and would foreclose the preventive-maintenance extension `user_story.md` mandates staying open. Nullable keeps a later preventive origin additive instead of a migration relaxing NOT NULL on live rows.

**Blocking the next spec:** the FS carries 4 unconfirmed assumptions (§8) and 5 open questions (§9). Two are load-bearing — **O-1** (do short UNS blips seed work orders? unbounded noise in the Planner queue if yes) and **O-2** (UNS reports a stop for an asset that already has an open manual event — the first place the two ingress paths genuinely collide). These need Senior Architect answers before the tasks they govern are specced.

**Doc edits deliberately held pending FS sign-off** (they move if the FS moves): DEC-008 (work-order origin + manual ingress — the architecture fact that currently has *no* backing decision), DEC-009 (MVP scope), an amendment to `architecture-facts.md` § Canonical data formats (its `manual` origin still describes manual *work-order* creation, but the ratified model is manual *downtime-event* creation that seeds a WO — the two now contradict), announcing the FS in `authority-docs-by-area.md`, and adding it to the instructions-mirror Tier 1.

**Also remaining:**
- The human syncs the three constitution edits into the canonical Claude Project instructions field (api-contract Tier 2, Rule 12 repoint, §3 review-agent config path). A fourth (FS in Tier 1) joins them once the FS is signed off.
- **Dangling authority doc:** `docs/design-guide.md` is cited as the UI authority in `architecture-facts.md` § Styling, in `authority-docs-by-area.md` (with no *(to author)* marker), and in instructions §5 Tier 2 (listed "live now") — **but the file does not exist.** Any UI spec would cite a doc that isn't there. Needs a call: author it, or mark it *(to author)* like `data-model.md`.
- **Environment ground truth unconfirmed:** instructions §2 records the repo at `/Users/walkerreynolds/PycharmProjects/agenticdevops-mini-cmms`, but the PM instance runs from `D:\GitHub\agenticdevops-mini-cmms` on Windows. This becomes load-bearing at T-002 (CI runner OS) and affects the handoff's own `source .venv/bin/activate` line. Rule 19 — the human's statement decides it.

## Immediate next steps

1. **Human: review `docs/functional-spec.md`** — answer §8 assumptions (A-1–A-4) and §9 open questions (O-1–O-5). O-1 and O-2 gate any work-order task.
2. **PM: on sign-off, land the five held doc edits in one turn** (DEC-008, DEC-009, the `architecture-facts.md` amendment, the authority-index announcement, the Tier-1 mirror listing).
3. **PM: spec T-002** — renderer scaffold + green CI (carries `ci.yml`; branch→PR→merge discipline resumes here). Independent of the FS review, so it can proceed in parallel — but it needs the environment ground-truth answer first, since CI runner OS depends on it.
4. Human: sync the constitution edits into the Claude Project instructions field (if still relevant while the PM runs as Claude Code).

**Note on sequencing:** the FS's MVP is materially bigger than "reactive CMMS" implied at bootstrap — it now carries the MQTT/UNS leg *and* real auth. Task breakdown after T-002 should be re-planned against `functional-spec.md` rather than extrapolated from the original scaffold split.

## Architecture authorities by area (read the one you're touching)

The full index is in `docs/authority-docs-by-area.md`. Short version: architecture constraints → `architecture-facts.md` (every spec) · **product behavior / MVP scope → `functional-spec.md` (DRAFT; not yet announced in the index — held pending sign-off)** · persistence → `data-model.md` *(to author)* · REST boundary → `api-contract.md` *(live — seeded by T-001)* · UNS/MQTT → `uns-contract.md` *(to author)* · boundary-change sync → `contract-sync.md` · auth/roles → `architecture-facts.md` § Security · UI → `design-guide.md` *(cited but **missing** — see Also remaining)* · packaging → `packaging.md` *(to author)*.

## Standing notes

- **Keep the instructions mirror in sync.** Canonical project instructions live in the Claude Project field; the git-tracked mirror is `docs/claude_project_instructions.md`. When the instructions change, rewrite the mirror in the same turn. If the two diverge, the Project copy wins. *(Three edits are currently mirror-only and need mirroring into the Project field: the `api-contract.md` Tier-2 addition, the Rule 12 repoint at `docs/contract-sync.md`, and §3's review-agent config repoint at `.cursor/rules/qa-role.mdc`. A fourth — `functional-spec.md` in Tier 1 — joins them once the FS is signed off.)*
- **No repo doc is attached to the Claude Project.** Every living doc is read on demand from the repo so it can't go stale.
- **The four foundational architecture choices** (separate-service topology, server-side role enforcement, SQLAlchemy+Alembic dual-engine persistence, live-broker UNS) are recorded in `decision-log.md` as DEC-004–007 and enforced via `architecture-facts.md`. Don't relitigate from memory.
