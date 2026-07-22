# CMMess — Project Management

> Holds the workflow specifics and the **task index**. The task-spec *format* lives in the spec-authoring checklist; this doc holds the index of tasks and the row format for it.

## Task-spec format

Every task gets a spec at `docs/tasks/task_<ID>_<slug>.md`, six sections, before any coding-agent command. See `checklists/spec-authoring.checklist.md`.

## Coding-agent command format

The command is handed to the human to paste into Claude Code:

```
To Claude Code — "Read docs/tasks/task_<ID>_<slug>.md in full before writing any code.
[2–4 sentence summary of what to implement, which files, key constraints.]
Standing invariants: honor docs/architecture-facts.md and CLAUDE.md; keep contract
docs (Rule 12) and user-docs (Rule 18) in the same commit; migrations run on both
SQLite and Postgres; never read/write/delete data outside the app's own store."
```

## The task index

**Row format — enforce it, because a readable index is a usable index:**

- One row per task **for its whole lifecycle**. Status transitions **edit the existing row in place** — never append a duplicate.
- Leading status symbol from a fixed set: ✅ complete · 🟡 in progress · 🔴 not started · ❄️ deferred.
- Title: soft target ≤8 words, hard cap ≤12 words; single em-dash separator; no bold annotations in the title cell.
- Date in the Verified column when complete.

| Status | ID | Title | Verified |
|---|---|---|---|
| ✅ | T-001 | Backend skeleton — FastAPI /health + tooling | 2026-07-22 |
| 🔴 | T-002 | Renderer scaffold — Electron/React/TS + green CI | |

## Queued / not-yet-specced items

Re-planned against `docs/functional-spec.md` (approved 2026-07-22) rather than
extrapolated from the original scaffold split. Two authority docs gate most of it:

- **`docs/data-model.md` *(to author — PM)*** — gates every persistence task. Must
  cover assets (cache keyed by UNS path), downtime events (with ingress `source`,
  the at-most-one-open invariant per FR-026), work orders (typed `origin`, the
  **nullable** downtime-event link per DEC-008), and identities/roles.
- **`docs/uns-contract.md` *(to author — PM)*** — gates FR-010–FR-014 and FR-020.
  Topic structure, discovery semantics, and the dev broker with simulated messages.
- **`docs/design-guide.md` *(to author — decision pending)*** — gates the first real
  UI task.

Candidate task shape after T-002, in dependency order — **not yet specced**:
persistence foundation (SQLAlchemy + Alembic, dual-engine) → auth and roles
(FR-001–FR-005, including operator account provisioning) → downtime events with the
manual ingress path (FR-021–FR-027) → work-order seeding through the single seeding
path with the duration gate (FR-030–FR-036) → UNS/MQTT discovery (FR-010–FR-014,
FR-020) → planning and execution (FR-040–FR-052) → views (FR-060–FR-063).

Sequencing note: the manual ingress path is specced to work with no broker
(FR-021), so it can land and be runtime-tested before the MQTT leg exists — which
keeps the UNS work from blocking the first genuinely usable slice.
