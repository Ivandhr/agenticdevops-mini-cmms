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

**Status:** DRAFT — pending Senior Architect review. Assumptions in §9 and open
questions in §10 are unresolved and must be closed before the tasks they govern are
specced.

---

## 1. Actors

| Actor | Who | Defining capability |
|---|---|---|
| **User** | Maintenance engineer / technician | Reports downtime, executes work orders |
| **Planner** | Maintenance manager | Plans, schedules, and assigns work orders |
| **UNS** | The plant's Unified Namespace, via MQTT | Publishes asset existence and up/down state |

Single shared multi-user instance. Roles are enforced server-side per endpoint
(`architecture-facts.md` § Security baseline, DEC-005); the renderer's role
awareness is presentation only.

## 2. Domain concepts

Described behaviorally. Storage is `data-model.md`'s call.

- **Asset** — a generic, configurable entity identified by its **UNS path**.
  Discovered from the UNS, never hand-maintained as a fixed equipment list. The
  local registry is a *cache* of discovery (DEC-007).
- **Downtime event** — a timestamped record that a specific asset stopped, and
  (once resolved) when it restarted. Carries the **ingress source** that produced
  it: `uns` (broker-detected) or `manual` (a person recorded it in the UI).
  Duration is **derived** from the timestamps, never stored
  (`architecture-facts.md` § Derived vs. authoritative state).
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
  UNS (MQTT)  ──┐
  asset stops   │
                ├──►  DowntimeEvent  ──►  seed  ──►  WorkOrder  ──►  plan   ──►  execute
  User in UI  ──┘     source: uns|manual                            (Planner)    (User)
  logs downtime       asset_uns_path
                      started_at, ended_at?
                      created_by
```

**Both ingress paths converge before seeding.** There is exactly one piece of
seeding logic; what varies is how the event arrived. This is what makes the manual
path cost near-nothing to support and keeps asset status truthful — a manually
reported stoppage moves the asset to `down` the same way a broker-detected one
does.

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

### 4.4 Work-order seeding

- **FR-030** — Creating a downtime event seeds exactly one work order, through a
  single seeding path shared by both ingress sources.
- **FR-031** — The seeded work order records a typed `origin` distinguishing what
  produced it (broker-detected vs. person-reported) and a `created_by` identifying
  the responsible identity — the reporting user for manual events, the system for
  UNS-detected ones.
- **FR-032** — The origin field is an extensible enumeration. Adding a future
  origin (e.g. preventive/scheduled) must not require changing the seeding path's
  callers or the work-order schema's shape.
- **FR-033** — A seeded work order is tied to the asset the downtime event names.
- **FR-034** — A seeded work order enters the lifecycle unplanned and unassigned.

### 4.5 Work-order planning *(Planner-gated)*

- **FR-040** — A Planner can set a work order's scheduled window and priority.
- **FR-041** — A Planner can assign a work order to a User.
- **FR-042** — A Planner can amend a work order's description and planning fields
  after seeding.
- **FR-043** — Planning actions are rejected server-side for a `user` identity
  (FR-003).

### 4.6 Work-order execution *(User)*

- **FR-050** — An assigned User can move a work order to in-progress and then to
  complete.
- **FR-051** — A User can record execution notes describing the work performed.
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
| View work orders | ✅ | ✅ |
| Schedule / prioritize a work order | ❌ | ✅ |
| Assign a work order | ❌ | ✅ |
| Move assigned work order to in-progress / complete | ✅ | ✅ *(A-1)* |
| Record execution notes | ✅ | ✅ |

## 6. State models

**Downtime event:** `open` → `resolved`. Open means `ended_at` is unset. An asset
is `down` exactly while it holds an open event.

**Work order:** `new` → `planned` → `in_progress` → `complete`.

- `new` — seeded, not yet planned. This is the Planner's queue (FR-061).
- `planned` — scheduled and/or assigned by a Planner.
- `in_progress` — execution started.
- `complete` — execution finished.

A terminal `closed` state (Planner verifies and signs off completed work) is
**deliberately deferred** — see O-3.

## 7. Explicitly out of scope for v1

Named here so they are recognizable as *deferred*, not *forgotten*, and so no task
spec quietly adopts one:

- Preventive / scheduled maintenance — the architecture must not preclude it
  (`user_story.md`), but v1 ships no preventive origin.
- Parts, inventory, stores, purchasing.
- Reporting, analytics, dashboards, MTBF/MTTR metrics.
- Attachments, photos, file uploads.
- Notifications — email, push, or in-app.
- Multi-site / multi-tenant separation.
- Offline operation and conflict resolution.
- Mobile-native clients.
- Audit trail beyond `created_by` and lifecycle timestamps.
- Self-service account management (registration, password reset, role changes).

## 8. Assumptions pending confirmation

Written down because acting on an unconfirmed assumption is how a wrong build gets
verified as correct. Each needs a yes/no before the task it governs is specced.

- **A-1 — A Planner can also execute work orders.** The matrix above grants it on
  the reasoning that Planner is a superset of User for everything except that
  planning is exclusive. If Planner is a *distinct* role rather than a superset,
  the matrix changes.
- **A-2 — One work order per downtime event, always, automatically.** No
  deduplication, no batching, no operator confirmation step before a work order
  exists.
- **A-3 — Assignment is to exactly one User.** No crews, no multi-assignee work.
- **A-4 — A work order's asset is fixed at seeding** and not reassignable to a
  different asset afterwards.

## 9. Open questions

- **O-1 — Should short downtime blips seed a work order?** A UNS-detected stop of
  four seconds producing a work order will bury the Planner queue in noise. Options:
  a minimum-duration threshold before seeding; seed-then-auto-void; or seed
  everything and let the Planner dismiss. Affects FR-030 and the Planner queue's
  usability. **Needs a product decision.**
- **O-2 — What happens when the UNS reports a stop for an asset that already has
  an open manual event** (and the reverse)? Options: suppress the duplicate and
  attach to the open event; create both and let them coexist; merge. Affects FR-020
  and FR-021 and is the first place the two ingress paths can genuinely collide.
- **O-3 — Does v1 need a terminal `closed` state** where a Planner verifies
  completed work, or is `complete` the end? Adds a Planner-gated transition and a
  fifth status. §6 currently defers it.
- **O-4 — How are User accounts created for v1** given self-service is out of
  scope? Seeded fixtures, a Planner-only creation surface, or config-file
  provisioning.
- **O-5 — Is there a work-order description distinct from the downtime event's
  description,** or does the seeded work order inherit and share the event's text?

## 10. Constraints this document inherits

Not restated here — read them where they live, and enforce them in every spec that
cites this document:

- `docs/architecture-facts.md` — all hard technical constraints, in particular the
  renderer-holds-no-business-logic rule, server-side authorization, derived-not-
  stored downtime state, and UNS-as-authoritative-for-assets.
- `docs/decision-log.md` — DEC-004 (topology), DEC-005 (server-side auth),
  DEC-006 (dual-engine persistence), DEC-007 (UNS over live broker),
  DEC-008 (work-order origin and manual downtime ingress).
- `docs/api-contract.md` — the typed REST surface; any FR here that crosses the
  boundary lands there in the same commit (Rule 12, `docs/contract-sync.md`).
