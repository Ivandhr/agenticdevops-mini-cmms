# CMMess — Functional Specification (v1 / MVP)

> **What this doc is.** The enumerated, testable behavior of the v1 product — what
> the system does, for whom, under what rules. It sits between `docs/user_story.md`
> (the story-level *why*) and the per-task specs under `docs/tasks/` (the *how*,
> one slice at a time). Task specs cite **FR-NNN** ids from this doc in their
> Acceptance Criteria; that citation is the trace from a shipped test back to a
> product requirement.
>
> **What this doc is not.** Not schema — `docs/data-model.md` *(to author)* owns
> tables and columns. Not endpoints — `docs/api-contract.md` owns the REST surface.
> Not hard technical constraints — `docs/architecture-facts.md` owns those and this
> doc **points at them rather than restating them** (one canonical home per fact).
> Where this doc names a shape, it is naming *behavior that must be representable*,
> not prescribing the storage.

**Status:** APPROVED 2026-07-22. All nine open items from the draft are resolved and
recorded in §9 with their rationale. One PM-proposed default (the seeding threshold
value, FR-035) stands until the Senior Architect says otherwise.

---

## 1. Actors

| Actor | Who | Defining capability |
|---|---|---|
| **User** | Maintenance engineer / technician | Reports downtime, executes work orders |
| **Planner** | Maintenance manager | Everything a User can do, plus planning, scheduling, and assignment |
| **UNS** | The plant's Unified Namespace, via MQTT | Publishes asset existence and up/down state |

Single shared multi-user instance. **Planner is a superset of User** — planning,
scheduling, assignment, and downtime-event correction are the Planner-exclusive
capabilities; a Planner can otherwise do anything a User can, including executing
work (§5). Roles are enforced server-side per endpoint (`architecture-facts.md`
§ Security baseline, DEC-005); the renderer's role awareness is presentation only.

## 2. Domain concepts

Described behaviorally. Storage is `data-model.md`'s call.

- **Asset** — a generic, configurable entity identified by its **UNS path**.
  Discovered from the UNS, never hand-maintained as a fixed equipment list. The
  local registry is a *cache* of discovery (DEC-007).
- **Downtime event** — a timestamped record that a specific asset stopped, and
  (once resolved) when it restarted. Carries the **ingress source** that produced
  it: `uns` (broker-detected) or `manual` (a person recorded it in the UI).
  Duration is **derived** from the timestamps, never stored
  (`architecture-facts.md` § Derived vs. authoritative state). Its description is
  an **observation record and is immutable** (FR-036).
- **Work order** — the unit of maintenance work. Seeded from a downtime event,
  then planned by a Planner and executed by a User. Carries a typed **origin**
  recording what caused it to exist, and `created_by` recording who.
- **Asset status** — `up` / `down`, **derived** from the event log: an asset is
  `down` exactly while it has an unresolved downtime event. Never stored as
  authoritative state.

## 3. The core loop

The product's distinctive move: **downtime drives the work.** v1 has two ingress
paths into one seeding path.

```
  UNS (MQTT)  ──┐                              ┌── under threshold: no seed
  asset stops   │                              │   (event still recorded)
                ├──►  DowntimeEvent  ──► gate ─┤
  User in UI  ──┘     source: uns|manual       └── seeds ──► WorkOrder ──► plan ──► execute
  logs downtime       asset_uns_path                                      (Planner)  (User)
                      started_at, ended_at?
                      created_by                    manual always seeds
```

**Both ingress paths converge before seeding.** There is exactly one piece of
seeding logic; what varies is how the event arrived. This is what makes the manual
path cost near-nothing to support and keeps asset status truthful — a manually
reported stoppage moves the asset to `down` the same way a broker-detected one
does.

**The gate is on seeding, never on recording.** A four-second UNS blip is still a
downtime event — the event log stays complete, asset status stays correctly
derived, and downtime history stays honest. What the threshold suppresses is only
the *work order* (FR-035). A manual event always seeds, because a person
deliberately asked for one.

**At most one open downtime event exists per asset** (FR-026). Asset status is
derived from the event log, so two concurrent open events on one asset would make
"is it down, and for how long?" ill-defined. A second stop signal on an
already-down asset attaches to the open event rather than creating a rival.

**The work order's link to its downtime event is optional in structure, populated
in practice.** In v1 both origins set it, and that is asserted as an invariant in
tests. It is not a NOT NULL constraint, because preventive maintenance — explicitly
in-scope-later per `user_story.md` — produces work orders with no downtime event,
and `architecture-facts.md` forbids hardcoding that a work order *requires* one.
Making it non-nullable now converts a later additive change into a migration that
must relax a constraint on live rows. (See DEC-008.)

## 4. Functional requirements

### 4.1 Authentication and authorization

- **FR-001** — A person authenticates with credentials and receives a
  backend-issued session/token. Unauthenticated requests to protected endpoints are
  rejected.
- **FR-002** — Every authenticated identity carries exactly one role: `user` or
  `planner`.
- **FR-003** — Every protected endpoint independently re-checks the authenticated
  identity's role for the action requested. A renderer that hides a control is
  never the enforcement point.
- **FR-004** — A rejected action returns an authorization failure the renderer can
  present intelligibly; it does not silently no-op.
- **FR-005** — Accounts are provisioned by whoever operates the instance, via a
  backend command or configuration — not self-service and not managed in-app. v1
  ships no registration, password-reset, or account-management UI. The provisioning
  path must be sufficient to onboard a real team, not just seed demo fixtures.

### 4.2 Assets and UNS discovery

- **FR-010** — The backend subscribes to the UNS over MQTT and discovers assets
  from the topic structure. It is the sole MQTT client in the system.
- **FR-011** — Discovered assets populate a local cache keyed by UNS path. The
  cache is rebuildable from discovery and is never the source of truth for what
  assets exist.
- **FR-012** — Both roles can browse and search the discovered asset list.
- **FR-013** — Each asset displays its current derived status (`up` / `down`) and,
  when down, how long it has been down.
- **FR-014** — An asset new to the UNS appears without any code, schema, or config
  change. Onboarding a new plant or process is a UNS concern, not a product
  concern.

### 4.3 Downtime events

- **FR-020** — A downtime state change published on the UNS creates a downtime
  event with source `uns`.
- **FR-021** — A User or Planner can record a downtime event from the UI against
  any discovered asset, producing a downtime event with source `manual`. **This
  path does not depend on the UNS having reported anything** and must work when the
  broker has published no state change for that asset.
- **FR-022** — A downtime event captures the asset, start time, ingress source,
  and — for manual events — the reporting identity and a free-text description of
  what was observed.
- **FR-023** — An open downtime event can be resolved, recording the restart time.
  Resolution is available to both roles.
- **FR-024** — Downtime duration is computed from the event's timestamps on read.
  No stored duration field.
- **FR-025** — Both roles can view an asset's downtime history.
- **FR-026** — **An asset has at most one open downtime event.** A stop signal
  arriving for an asset that already has an open event — from either ingress
  source, in either order — attaches to that open event rather than creating a
  second. It does not seed an additional work order.
- **FR-027** — A Planner can correct the asset on a downtime event that was logged
  against the wrong one. The correction cascades: the seeded work order's asset
  follows, so event and work order never disagree. Correcting the asset is
  Planner-gated (FR-003).

### 4.4 Work-order seeding

- **FR-030** — Creating a seeding-eligible downtime event (FR-035) seeds exactly
  one work order, through a single seeding path shared by both ingress sources.
- **FR-031** — The seeded work order records a typed `origin` distinguishing what
  produced it (broker-detected vs. person-reported) and a `created_by` identifying
  the responsible identity — the reporting user for manual events, the system for
  UNS-detected ones.
- **FR-032** — The origin field is an extensible enumeration. Adding a future
  origin (e.g. preventive/scheduled) must not require changing the seeding path's
  callers or the work-order schema's shape.
- **FR-033** — A seeded work order is tied to the asset the downtime event names.
- **FR-034** — A seeded work order enters the lifecycle unplanned and unassigned.
- **FR-035** — **Seeding is gated by a configurable minimum duration.** A
  UNS-sourced event whose asset returns to service inside the threshold does not
  seed a work order; the event itself is still recorded in full. A `manual` event
  always seeds regardless of duration. The threshold is operator-configurable
  without a code change; **proposed default: 5 minutes** (PM-set, tunable).
- **FR-036** — The work order's description is **copied from the downtime event at
  seeding** and is independently editable thereafter. The event's description is an
  immutable record of what was observed; the work order's is the evolving statement
  of work to be done. Editing one never rewrites the other.

### 4.5 Work-order planning *(Planner-gated)*

- **FR-040** — A Planner can set a work order's scheduled window and priority.
- **FR-041** — A Planner can assign a work order to exactly one User. v1 has no
  crews or multi-assignee work orders.
- **FR-042** — A Planner can amend a work order's description and planning fields
  after seeding.
- **FR-043** — Planning actions are rejected server-side for a `user` identity
  (FR-003).

### 4.6 Work-order execution

- **FR-050** — The assigned User can move a work order to in-progress and then to
  complete. A Planner may also execute (§1, §5).
- **FR-051** — The executing identity can record execution notes describing the
  work performed.
- **FR-052** — Completing a work order does **not** resolve the asset's downtime
  event, and resolving downtime does **not** complete the work order. The asset may
  return to service before the maintenance work is finished, and work may remain
  after restart. The two lifecycles are independent.

### 4.7 Views

- **FR-060** — A work-order list, filterable by status and by asset, visible to
  both roles.
- **FR-061** — A Planner sees an unplanned-work queue — seeded work orders awaiting
  planning.
- **FR-062** — A User sees the work orders assigned to them.
- **FR-063** — A work-order detail view showing origin, originating downtime event,
  asset, planning fields, assignment, and execution notes.

## 5. Role permission matrix

| Capability | User | Planner |
|---|---|---|
| Authenticate | ✅ | ✅ |
| Browse assets / view asset status | ✅ | ✅ |
| Record a manual downtime event | ✅ | ✅ |
| Resolve a downtime event | ✅ | ✅ |
| View downtime history | ✅ | ✅ |
| **Correct a downtime event's asset** | ❌ | ✅ |
| View work orders | ✅ | ✅ |
| **Schedule / prioritize a work order** | ❌ | ✅ |
| **Assign a work order** | ❌ | ✅ |
| Move assigned work order to in-progress / complete | ✅ | ✅ |
| Record execution notes | ✅ | ✅ |

Bold rows are the Planner-exclusive capabilities. Everything else is shared —
Planner is a superset of User (A-1).

Account provisioning is **not** in this matrix: it happens outside the application
via operator tooling (FR-005), so no in-app role grants it.

## 6. State models

**Downtime event:** `open` → `resolved`. Open means `ended_at` is unset. An asset
is `down` exactly while it holds an open event, and holds at most one (FR-026).

**Work order:** `new` → `planned` → `in_progress` → `complete`.

- `new` — seeded, not yet planned. This is the Planner's queue (FR-061).
- `planned` — scheduled and/or assigned by a Planner.
- `in_progress` — execution started.
- `complete` — execution finished. **Terminal in v1.**

No Planner sign-off/verification state in v1 (O-3). Adding a fifth status later is
additive and carries no migration cost.

## 7. Explicitly out of scope for v1

Named here so they are recognizable as *deferred*, not *forgotten*, and so no task
spec quietly adopts one:

- Preventive / scheduled maintenance — the architecture must not preclude it
  (`user_story.md`), but v1 ships no preventive origin.
- Planner sign-off / verification of completed work (O-3).
- In-app account management, registration, password reset, role changes (FR-005).
- Multi-assignee work orders and crews (A-3).
- Parts, inventory, stores, purchasing.
- Reporting, analytics, dashboards, MTBF/MTTR metrics.
- Attachments, photos, file uploads.
- Notifications — email, push, or in-app.
- Multi-site / multi-tenant separation.
- Offline operation and conflict resolution.
- Mobile-native clients.
- Audit trail beyond `created_by` and lifecycle timestamps.

## 8. Constraints this document inherits

Not restated here — read them where they live, and enforce them in every spec that
cites this document:

- `docs/architecture-facts.md` — all hard technical constraints, in particular the
  renderer-holds-no-business-logic rule, server-side authorization, derived-not-
  stored downtime state, and UNS-as-authoritative-for-assets.
- `docs/decision-log.md` — DEC-004 (topology), DEC-005 (server-side auth),
  DEC-006 (dual-engine persistence), DEC-007 (UNS over live broker),
  DEC-008 (work-order origin and manual downtime ingress), DEC-009 (v1 scope).
- `docs/api-contract.md` — the typed REST surface; any FR here that crosses the
  boundary lands there in the same commit (Rule 12, `docs/contract-sync.md`).

## 9. Resolved product decisions

The draft's assumptions (A-N) and open questions (O-N) and how they closed. Kept so
a future reader finds *why* rather than relitigating from memory. All resolved by
the Senior Architect on 2026-07-22.

| Id | Question | Resolution | Lands in |
|---|---|---|---|
| **A-1** | Can a Planner execute work orders? | **Yes — Planner is a superset of User.** Planning, assignment, and event correction are the only exclusives. Matches how small maintenance teams actually run. | §1, §5, FR-050 |
| **A-2** | One work order per event, automatically? | **Yes, automatic, no confirmation step** — resolved as a consequence of O-1, since the threshold is the noise control rather than an operator gate. | FR-030 |
| **A-3** | Multi-assignee work orders? | **No — exactly one assignee.** Keeps "my work" unambiguous; additive later if real use demands it. | FR-041 |
| **A-4** | Correction path for a mis-logged asset? | **Planner corrects the event; the work order's asset follows.** Correcting at the source keeps event and work order consistent. Without it a mis-log is permanent — v1 has no void status, so the asset's downtime history would stay corrupted with no remedy. | FR-027 |
| **O-1** | Do short UNS blips seed work orders? | **A configurable minimum duration gates seeding only, never recording.** Sub-threshold events are still logged in full; only the work order is suppressed. Manual events always seed. | FR-035, §3 |
| **O-2** | UNS stop on an asset with an open manual event? | **At most one open event per asset** — the later signal attaches to the open one. Two concurrent open events would make derived asset status and duration ill-defined. | FR-026 |
| **O-3** | Terminal `closed` / sign-off state? | **No — `complete` is terminal in v1.** MVP already carries the UNS leg and real auth; a fifth status is additive later at no migration cost. | §6, §7 |
| **O-4** | How are accounts created? | **Operator provisioning via backend command/config.** Enough to onboard a real team without spending MVP scope on an admin UI; in-app management is the natural follow-on. | FR-005 |
| **O-5** | Separate work-order description? | **Copied from the event at seeding, editable thereafter; the event's text is immutable.** The observation and the statement of work are different artifacts and both matter. | FR-036 |
