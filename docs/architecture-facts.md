# Key Architecture Facts — CMMess (Reactive CMMS)

> The **hard technical constraints every spec must enforce.** Not preferences, not
> style — the rules that, if broken, produce architectural rot that's expensive to
> unwind. The PM cites the relevant facts in every spec; the coding agent honors
> them (they are the spine of `CLAUDE.md`); the review agent catches violations
> visible in a diff. Facts are grouped by concern; the single hardest rule is
> marked. Each fact maps to a numbered entry in `docs/decision-log.md`.

## Process / layer boundaries

**The renderer is presentation only; all domain logic lives in the FastAPI backend.**
Downtime→work-order seeding, planning/scheduling, asset discovery, and
role/authorization all live server-side. The React/TypeScript renderer holds no
business logic, no direct database access, and no MQTT/UNS access — it only calls
typed backend endpoints. **This is the hardest rule — no exceptions.** Logic in the
client can't be shared, secured, or extended to preventive maintenance later.

**The renderer talks to the backend directly over HTTP (localhost); the Electron
main process is lifecycle-only.** Main manages windows and app lifecycle, not data
or domain calls — it is never a proxy between renderer and backend. (Least-
resistance topology: a plain REST contract, not a two-hop IPC+HTTP chain.)

## Canonical data formats

**A work order is seeded from a typed, extensible trigger source, through exactly
one seeding path.** In v1, downtime reaches the system by two *ingress* routes —
detected via the UNS, or recorded in the UI by a User or Planner — and both produce
a downtime event that flows through the same seeding logic. What varies is how the
event arrived, never how a work order is made. The manual route must work when the
broker has published nothing for that asset. The work order's origin is a
first-class typed field (e.g. `uns_downtime`, `manual_downtime`, with `created_by`
recording the actual user), and **the link from a work order to its originating
downtime event is nullable** — never a schema constraint that makes a work order
*require* a downtime event. v1 populates it from both origins and asserts that in
tests; reactive-only v1 must not preclude adding a scheduled/preventive origin
later, and a NOT NULL link would turn that additive change into a migration
relaxing a constraint on live rows. The origin field is the extension point.
*(DEC-008; behavior enumerated in `docs/functional-spec.md`.)*

**Seeding is gated; recording never is.** A configurable minimum duration
suppresses the *work order* for a UNS-detected blip — it never suppresses the
downtime event itself. The event log stays complete so derived asset status and
downtime history remain honest. Manual events always seed. *(DEC-008.)*

**Every work order ties to a UNS-discoverable asset, regardless of origin.**
Seeding is not the same as planning: both roles may *create* a work order, but
planning/scheduling stays Planner-gated (see Security baseline).

**Asset identity is the UNS path.** Assets are generic, configurable entities keyed
by their Unified-Namespace address — never a hardcoded, plant-specific equipment
table. Process-agnostic onboarding is the product's distinctive move.

## Persistence & migrations

**The backend supports both SQLite and Postgres; SQLite is the default for v1/dev.**
Persistence must be portable across both — no SQLite-only or Postgres-only SQL. All
access goes through SQLAlchemy; migrations are authored with Alembic to run on both
engines, additive-first. `docs/data-model.md` is the schema authority. The
SQLite→Postgres path is a stated product requirement; a dialect shortcut now is an
expensive refactor later.

## Module-boundary contracts

**The renderer↔backend REST API is typed end to end.** Pydantic models on the
Python side, matching TypeScript types on the renderer side; the renderer never
hand-rolls a shape that bypasses the shared typed surface. Any endpoint/schema
change moves its Pydantic model, its TS type, and the API contract doc **in the same
commit** (Rule 12).

**The UNS/MQTT surface is a contract.** The UNS topic structure the backend
subscribes to for asset discovery is authoritative and documented in
`docs/uns-contract.md`. The backend is the **only** MQTT client — nothing else in the
system subscribes or publishes.

## Security baseline

**Authorization is enforced in the backend; the renderer's role is display-only and
never trusted.** Login issues a backend token/session; every protected endpoint
independently checks the authenticated identity's role (User vs. Planner) per action.
A hidden button is not an access control. This is a single shared multi-user
instance — client-side role checks are trivially bypassed.

**Secrets live in backend config/env, never in the renderer bundle** (Postgres
credentials, MQTT broker credentials). Electron baseline: context isolation on, node
integration off.

**Never read, write, or delete data outside the app's own store** — only committed
test fixtures are touched.

## Derived vs. authoritative state

**Downtime duration and asset up/down status are derived from the authoritative
event log.** Store timestamped state transitions; compute duration and current
status from them — never store a duration that can drift from its events.

**An asset has at most one open downtime event.** A stop signal arriving for an
asset that already has an open event — from either ingress route, in either order —
attaches to that open event rather than creating a rival, and seeds no additional
work order. This follows directly from deriving status from the log: two concurrent
open events on one asset make "is it down, and for how long?" ill-defined.
*(DEC-008.)*

**The local asset registry is a cache of UNS discovery, not the source of truth.**
The UNS is authoritative for what assets exist; any persisted asset table is rebuilt
from UNS discovery, never treated as the authority.

## Styling / brand (UI)

**Follow the design guide; tokens over raw values.** `docs/design-guide.md` is the
authority for tokens, type scale, and component patterns. The structural-layout
pre-flight (Rule 11) applies to any resizable-boundary or divider work.

## Testing boundaries

**Unit-test backend domain logic and pure renderer logic; exercise the boundaries
for real.** The renderer↔backend REST contract and server-side role enforcement are
covered by integration tests against a running backend, not mocked into triviality.
UNS ingestion is tested against a broker with simulated messages, since that is how
it runs.

---

*Each fact above maps to a numbered decision in `docs/decision-log.md` and is
enforced in every spec. The four foundational choices — separate-service topology,
server-side role enforcement, SQLAlchemy+Alembic dual-engine persistence, and the
live-broker UNS contract — are recorded there with rationale.*
