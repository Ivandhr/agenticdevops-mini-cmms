# CMMess — Proposed Architecture (temp doc)

> **Temporary, and derived — not an authority.** Rendered from
> `docs/architecture-facts.md`, `docs/functional-spec.md`, `docs/data-model.md`, and
> DEC-004–010 for the Senior Architect. Not part of the living-doc set; safe to
> delete. **If this diagram disagrees with any of those documents, they are right and
> this is stale** — one area, one authority doc.
>
> Current as of 2026-07-22, after the functional spec was approved and
> `data-model.md` authored. Built so far: backend `GET /health` (T-001); the renderer
> shell + CI land with T-002. Everything else is proposed.

```mermaid
flowchart TB
    subgraph desktop["Electron Desktop App"]
        main["Electron Main Process<br/><i>lifecycle only — windows, app startup</i><br/>context isolation ON · node integration OFF"]
        renderer["Renderer — React + TypeScript (Vite)<br/><i>presentation only</i><br/>no business logic · no DB access · no MQTT<br/>role display only, never trusted"]
        main -. "creates window" .-> renderer
    end

    subgraph backend["FastAPI Backend (Python 3) — all domain logic"]
        api["Typed REST API<br/>Pydantic models ↔ TS types, end to end<br/>sync handlers (def, not async def) — DEC-010<br/>(contract: docs/api-contract.md)"]
        auth["Auth & Roles<br/>server-side enforcement per endpoint<br/>User vs. Planner (Planner ⊃ User)<br/>accounts operator-provisioned, no self-service"]
        ingress["Downtime Ingress — two routes<br/>source: uns (broker-detected)<br/>source: manual (person, in the UI)<br/><b>manual works with no broker at all</b>"]
        seeding["One Seeding Path — DEC-008<br/>both routes converge here<br/>gate: min-duration threshold suppresses the<br/><i>work order</i>, never the event record<br/>manual always seeds"]
        domain["Work-Order Domain<br/>planning / scheduling / assignment (Planner-gated)<br/>execution (assignee)<br/>origin: typed, extensible field<br/>(uns_downtime · manual_downtime · future: preventive)<br/>link to downtime event is <b>nullable</b>"]
        derived["Derived State — never stored<br/>up/down status & downtime duration<br/>computed from the timestamped event log<br/><b>≤1 open downtime event per asset</b>"]
        mqtt["MQTT Client (aiomqtt/paho)<br/><b>the only MQTT client in the system</b><br/>UNS asset discovery + downtime signals"]
        api --> auth --> ingress
        mqtt --> ingress
        ingress --> seeding --> domain
        domain --> derived
    end

    subgraph persistence["Persistence — SQLAlchemy + Alembic (sync)"]
        tables["identity · asset<br/>downtime_event · work_order<br/><i>schema authority: docs/data-model.md</i>"]
        sqlite[("SQLite<br/>v1 / dev default")]
        pg[("Postgres<br/>deployment path")]
        cache["Asset Registry<br/><i>cache of UNS discovery — never source of truth</i><br/><b>upsert by uns_path; rows never deleted</b>"]
    end

    subgraph uns["Unified Namespace (external)"]
        broker["MQTT Broker<br/><b>authoritative for assets</b><br/>asset identity = UNS path<br/>(contract: docs/uns-contract.md)"]
    end

    renderer == "HTTP (localhost) — typed REST<br/>no IPC proxy through main" ==> api
    domain --> tables
    derived --> tables
    tables --> sqlite
    tables --> pg
    sqlite -. "portable migrations<br/>no dialect-specific SQL" .- pg
    broker -- "subscribe: asset discovery,<br/>downtime signals" --> mqtt
    mqtt -- "rebuild (upsert)" --> cache
    cache --> tables

    classDef built fill:#1a7f37,color:#fff,stroke:#1a7f37
    class api built
```

**Legend:** green = exists today (T-001: `GET /health` through a typed Pydantic
model). The renderer shell and CI land with T-002; the four tables with T-003.
Everything else is proposed, constrained by `docs/architecture-facts.md`.

**The foundational decisions (DEC-004–010):** separate-service topology (Electron
shell + local FastAPI service, plain REST — no IPC data path) · server-side role
enforcement (a hidden button is not an access control) · SQLAlchemy + Alembic
dual-engine persistence (SQLite→Postgres without refactor) · live-broker UNS
(backend is the sole MQTT client; UNS authoritative for assets) · two downtime
ingress routes converging on **one** seeding path, with the work-order→event link
deliberately nullable so preventive maintenance stays additive · v1 ships both
ingress routes plus real auth · synchronous SQLAlchemy with `def` handlers.

**Three things this diagram exists to make visible**, because each is easy to build
wrong and expensive to unwind:

1. **The two ingress routes converge *before* seeding.** There is one piece of
   seeding logic; only how the event arrived varies. The manual route must work when
   the broker has published nothing.
2. **The gate is on seeding, not on recording.** A sub-threshold blip still logs its
   downtime event — the event log stays complete, so derived asset status and
   downtime history stay honest.
3. **The asset registry is rebuilt by upsert, never by truncate.** The UNS is
   authoritative for what exists *now*; it has no authority over what *happened*.
