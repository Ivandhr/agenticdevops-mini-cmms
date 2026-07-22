# Data Model — CMMess

> The authority for persisted schema: entities, columns, relationships, invariants,
> and the engine-portability rules every migration obeys. Per
> `docs/contract-sync.md`, a change to a SQLAlchemy model or the persisted schema
> moves its **Alembic migration (runnable on both SQLite and Postgres) + this doc**
> in the same commit (Rule 12).
>
> **Scope.** This doc owns storage. Behavior is `docs/functional-spec.md` (FR ids);
> the REST surface is `docs/api-contract.md`; hard constraints are
> `docs/architecture-facts.md`. Where a column exists to satisfy a requirement, the
> FR id is cited — that is the trace from a column back to why it exists.

**Status:** authored 2026-07-22. **No persistence code exists yet** — the backend is
the T-001 skeleton (one `/health` endpoint, no SQLAlchemy, no Alembic). This
document is the *target* the first persistence task implements, not a description of
running code.

---

## 1. Engine-portability rules

Binding on every model and every migration (DEC-006). These are not preferences —
each is a place where SQLite and Postgres diverge in a way that produces
green-in-dev, broken-in-deployment.

### 1.1 No native database enums

**Store enumerated values as `String`, validated in the application layer.** No
`sa.Enum` with `native_enum=True`, no Postgres `CREATE TYPE`, no `CHECK` constraints
on enumerated columns.

Why this is a rule and not a style choice: Postgres native enums require
`ALTER TYPE … ADD VALUE` to extend, which is a schema migration on the type itself;
SQLite emulates enums as `VARCHAR` + `CHECK`, and altering a `CHECK` constraint on
SQLite requires a full table rebuild. **`WorkOrder.origin` is required to be
extensible** (FR-032, DEC-008) — adding a preventive-maintenance origin later must
be additive. A native enum makes that trivial addition a two-engine migration.
Validation lives in the Pydantic/domain layer where adding a member is a one-line
change.

### 1.2 UUID primary keys via SQLAlchemy's portable type

Use SQLAlchemy 2.0's `Uuid` type, which maps to native `UUID` on Postgres and
`CHAR(32)` on SQLite. Generate values in Python, never with a database default.
Avoids autoincrement/sequence divergence between the engines entirely.

### 1.3 Timestamps: UTC, timezone-aware, generated in Python

- Every timestamp column is `DateTime(timezone=True)`.
- **Every datetime handed to the ORM must be a timezone-aware UTC datetime.** The
  application is responsible for this; the database is not.
- **No server-side defaults** (`server_default=func.now()`, `CURRENT_TIMESTAMP`).
  Generate timestamps in Python so both engines produce identical values.

**This is the trap most likely to bite this project.** SQLite has no timezone-aware
storage — it silently discards the offset and hands back a *naive* datetime, while
Postgres returns an *aware* one. The same code path then computes downtime duration
successfully on one engine and raises `TypeError: can't subtract offset-naive and
offset-aware datetimes` on the other. Because SQLite is the dev default and Postgres
is the deployment target, the failure surfaces in deployment, from code that passed
every local test. The defense: never let a naive datetime reach the ORM, and assert
awareness at the boundary rather than trusting round-trip.

### 1.4 Migrations are additive-first and dialect-free

- Alembic migrations use `op.*` operations only — **no `op.execute()` with raw
  dialect SQL.**
- Additive-first: new columns are nullable or carry a default. **A new `NOT NULL`
  column with no default makes every pre-existing row invalid** — CLAUDE.md records
  this as a standing trap, and the same applies to a new required field on a
  persisted Pydantic schema.
- Every migration must run on both engines. "It ran on SQLite" is half a test.

### 1.5 Named constraints and batch mode (required for SQLite)

- The `MetaData` carries an explicit `naming_convention` for indexes, unique
  constraints, checks, foreign keys, and primary keys.
- Alembic's `env.py` sets **`render_as_batch=True`**.

SQLite cannot `ALTER` most constraints; Alembic emulates it by rebuilding the table
("batch mode"), and it can only do that if constraints have deterministic names.
Without a naming convention, the first migration that alters a constrained column
fails on SQLite with an unnamed-constraint error — typically long after the
convention would have been cheap to add.

### 1.6 Partial unique index — portable, and used

`CREATE UNIQUE INDEX … WHERE …` is supported by both SQLite (≥ 3.8.0) and Postgres.
This is what enforces the one-open-event-per-asset invariant (§4.1). It is called
out explicitly because partial indexes are *usually* a portability hazard; here they
are verified-portable and load-bearing.

### 1.7 Not used in v1

JSON/JSONB columns, array columns, materialized views, triggers, stored procedures,
database-level `CASCADE` on update. Each either diverges between engines or moves
domain logic into the database, where `architecture-facts.md` says it does not
belong.

---

## 2. Entities

Column types are given portably. Every table has a `Uuid` primary key named `id`,
generated in Python (§1.2).

### 2.1 `identity` — users and their roles

Accounts are provisioned by the instance operator (FR-005); there is no
registration, password reset, or in-app management in v1.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `username` | String | no | **unique** |
| `password_hash` | String | no | hash only — never a recoverable secret |
| `role` | String | no | `user` \| `planner` — app-validated (§1.1), FR-002 |
| `is_active` | Boolean | no | default `True`; deactivation instead of deletion, so history keeps its author |
| `created_at` | DateTime(tz) | no | |

**Rows are never hard-deleted.** Work orders and downtime events reference
identities as their author, reporter, and assignee; deleting a person would either
orphan or rewrite history. Deactivate instead.

### 2.2 `asset` — the UNS discovery cache

The UNS is authoritative for what assets exist (DEC-007); this table is a **cache**,
never the source of truth.

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK — a stable surrogate, *not* the identity |
| `uns_path` | String | no | **unique** — the real identity of an asset (`architecture-facts.md`) |
| `display_name` | String | yes | human label if discovery supplies one |
| `first_discovered_at` | DateTime(tz) | no | |
| `last_seen_at` | DateTime(tz) | no | updated on each discovery |
| `is_present` | Boolean | no | currently advertised by the UNS |

**Rebuilding the cache is an upsert by `uns_path`. It is never a delete-and-reinsert,
and rows are never removed.** An asset that disappears from the UNS has
`is_present = False`; its row and `id` survive.

This is the sharpest trap in the model. "The asset table is a cache rebuilt from the
UNS" reads like a licence to truncate and repopulate — and doing so would either
break every foreign key from `downtime_event` and `work_order`, or (worse, with
cascade delete) silently destroy the maintenance history of every asset that was
briefly absent from the broker. **The UNS is authoritative for what exists now; it
has no authority over what happened.** Surrogate `id` plus upsert-by-path is what
keeps those two facts separable.

### 2.3 `downtime_event` — the authoritative event log

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `asset_id` | Uuid FK → `asset.id` | no | correctable by a Planner (FR-027) |
| `source` | String | no | `uns` \| `manual` — the ingress route (FR-020, FR-021) |
| `started_at` | DateTime(tz) | no | |
| `ended_at` | DateTime(tz) | **yes** | `NULL` ⇒ the event is **open** and the asset is down |
| `description` | Text | yes | what was observed. **Immutable after creation** (FR-036) |
| `reported_by_id` | Uuid FK → `identity.id` | yes | the reporting person for `manual`; `NULL` for `uns` |
| `created_at` | DateTime(tz) | no | |

**Indexes:** `(asset_id, started_at)` for history queries; plus the partial unique
index in §4.1.

`description` is an observation record. The work order carries the evolving
statement of work (§2.4); editing that never rewrites what the technician actually
saw.

### 2.4 `work_order`

| Column | Type | Null | Notes |
|---|---|---|---|
| `id` | Uuid | no | PK |
| `asset_id` | Uuid FK → `asset.id` | no | follows event corrections (FR-027, §4.3) |
| `downtime_event_id` | Uuid FK → `downtime_event.id` | **yes** | **deliberately nullable — DEC-008, §4.2** |
| `origin` | String | no | `uns_downtime` \| `manual_downtime`; **extensible** (FR-032) |
| `status` | String | no | `new` \| `planned` \| `in_progress` \| `complete` (FS §6) |
| `description` | Text | yes | copied from the event at seeding, then independently editable (FR-036) |
| `priority` | String | yes | set during planning (FR-040) |
| `scheduled_start` | DateTime(tz) | yes | FR-040 |
| `scheduled_end` | DateTime(tz) | yes | FR-040 |
| `assignee_id` | Uuid FK → `identity.id` | yes | **exactly one** — no join table (FR-041, A-3) |
| `created_by_id` | Uuid FK → `identity.id` | yes | `NULL` ⇒ system-seeded; see below |
| `execution_notes` | Text | yes | FR-051 |
| `created_at` | DateTime(tz) | no | |
| `started_at` | DateTime(tz) | yes | set on → `in_progress` |
| `completed_at` | DateTime(tz) | yes | set on → `complete` |

**Indexes:** `(status)` for the Planner queue (FR-061); `(assignee_id, status)` for
"my work" (FR-062); `(asset_id)` for per-asset views.

**`created_by_id` is nullable rather than pointing at a synthetic "system" account.**
FR-031 requires the responsible identity, which for a UNS-detected event is the
system itself. A sentinel row would be a fake person that every query filtering
real users must remember to exclude. `NULL` plus `origin` as the discriminator says
the same thing without the landmine.

---

## 3. Derived values — never stored

Per `architecture-facts.md` § Derived vs. authoritative state. Storing any of these
creates a value that can drift from the events that define it.

| Value | Derived from |
|---|---|
| Downtime duration | `ended_at - started_at`, or `now - started_at` while open |
| Asset up/down status | `down` ⟺ the asset has a `downtime_event` with `ended_at IS NULL` |
| "How long has this been down" | `now - started_at` of the open event |

No `duration`, `is_down`, or `current_status` column exists on any table. If one
appears in a diff, that is the defect.

---

## 4. Invariants and where each is enforced

The enforcement point matters as much as the rule. Some are database constraints;
some deliberately are not.

### 4.1 At most one open downtime event per asset — **enforced in the database**

> FR-026, `architecture-facts.md` § Derived vs. authoritative state.

A **partial unique index** on `downtime_event (asset_id) WHERE ended_at IS NULL`.
Portable to both engines (§1.6).

This one belongs in the database because it is what makes derived asset status
well-defined. Two concurrent open events would make "is it down, and for how long?"
ambiguous, and the two ingress routes (UNS and manual) can race — a broker message
and a technician's tap can arrive in the same instant. Application-level checking
alone has a read-then-write window; the index closes it. The seeding path must
handle the resulting integrity error as the expected "already down" outcome, not as
a crash.

### 4.2 Every v1 work order has a downtime event — **enforced in tests, not the schema**

> DEC-008.

`downtime_event_id` is **nullable**, and both v1 origins populate it. The guarantee
is asserted by tests, deliberately not by a `NOT NULL` constraint.

Preventive maintenance is explicitly in-scope-later (`user_story.md`) and produces
work orders with no downtime event; `architecture-facts.md` forbids a schema that
makes a work order *require* one. A `NOT NULL` column today turns that additive
change into a migration relaxing a constraint on live rows — on two engines, with
SQLite needing a batch table rebuild. The invariant is real; the schema is simply
not where it is enforced.

### 4.3 Asset correction cascades to the work order — **enforced in the domain layer**

> FR-027.

When a Planner corrects `downtime_event.asset_id`, the seeded work order's
`asset_id` is updated **in the same transaction**.

This is not a database cascade. `ON UPDATE CASCADE` propagates changes to a
referenced *key*, and `work_order.asset_id` is its own foreign key, not a copy of
the event's. Nothing at the database level will keep them aligned — a single
domain-layer operation must update both, and a test must assert they never diverge.

### 4.4 Seeding is gated by duration — **application logic, not schema**

> FR-035, DEC-008.

The minimum-duration threshold suppresses *work-order creation*; the downtime event
is always recorded in full. The threshold is **application configuration, not a
database row** — no settings table in v1. Proposed default 5 minutes (PM-set,
tunable).

### 4.5 Event description immutability — **enforced in the domain layer**

> FR-036.

`downtime_event.description` is not updatable after creation. No database mechanism
enforces this (a trigger would put domain logic in the database, §1.7); the domain
layer exposes no update path for the column, and a test asserts it.

---

## 5. Relationships

```
identity ──< work_order.created_by_id
identity ──< work_order.assignee_id          (exactly one assignee)
identity ──< downtime_event.reported_by_id   (NULL for uns-sourced)

asset ──< downtime_event.asset_id
asset ──< work_order.asset_id

downtime_event ──< work_order.downtime_event_id   (NULLABLE — DEC-008)
```

**No cascade deletes anywhere.** Assets and identities are never hard-deleted
(§2.1, §2.2); downtime events and work orders are the historical record. A cascade
would be a mechanism for silently destroying it.

---

## 6. Out of the schema in v1

Named so no task quietly adds one: preventive/scheduled maintenance origin and its
recurrence rules; parts, inventory, purchasing; attachments; notifications; a
settings/config table; multi-site or tenant columns; crew/multi-assignee join
tables (A-3); a Planner sign-off state (O-3); audit tables beyond the `created_by`
and lifecycle timestamps already present.

---

## 7. Open items

- **Password hashing algorithm** is unspecified here — it belongs with the auth
  task, which must also add the hashing dependency to `backend/requirements.txt`.
  This doc fixes only that the column stores a hash.
- **`priority` is typed as a free `String`.** If it should be an ordered set
  (`low`/`normal`/`high`/`urgent`) with sorting semantics in the Planner queue, that
  is a product decision not yet taken — FR-040 says only that a Planner can set it.
- **No `updated_at` column is specified** on any table. Add one only when something
  actually consumes it; a column maintained by every write and read by nothing is
  drift waiting to happen.
