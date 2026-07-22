# CMMess — Proposed Architecture (temp doc)

> **Temporary** — pulled from `docs/architecture-facts.md` / DEC-004–007 for the Senior
> Architect. Not part of the living-doc set; safe to delete. As of 2026-07-22
> (post-T-001: backend `GET /health` exists; everything else is proposed).

```mermaid
flowchart TB
    subgraph desktop["Electron Desktop App"]
        main["Electron Main Process<br/><i>lifecycle only — windows, app startup</i><br/>context isolation ON · node integration OFF"]
        renderer["Renderer — React + TypeScript (Vite)<br/><i>presentation only</i><br/>no business logic · no DB access · no MQTT<br/>role display only, never trusted"]
        main -. "creates window" .-> renderer
    end

    subgraph backend["FastAPI Backend (Python 3) — all domain logic"]
        api["Typed REST API<br/>Pydantic models ↔ TS types, end to end<br/>(contract: docs/api-contract.md)"]
        auth["Auth & Roles<br/>server-side enforcement per endpoint<br/>User vs. Planner"]
        domain["Domain Logic<br/>downtime → work-order seeding<br/>planning / scheduling (Planner-gated)<br/>WO origin: typed extensible field<br/>(uns_downtime · manual · future: preventive)"]
        derived["Derived State<br/>up/down status & downtime duration<br/>computed from timestamped event log,<br/>never stored as drifting totals"]
        mqtt["MQTT Client (aiomqtt/paho)<br/><b>the only MQTT client in the system</b><br/>UNS asset discovery"]
        api --> auth --> domain
        domain --> derived
        mqtt --> domain
    end

    subgraph persistence["Persistence — SQLAlchemy + Alembic"]
        sqlite[("SQLite<br/>v1 / dev default")]
        pg[("Postgres<br/>deployment path")]
        cache["Asset Registry<br/><i>cache rebuilt from UNS discovery<br/>— never source of truth</i>"]
    end

    subgraph uns["Unified Namespace (external)"]
        broker["MQTT Broker<br/><b>authoritative for assets</b><br/>asset identity = UNS path<br/>(contract: docs/uns-contract.md)"]
    end

    renderer == "HTTP (localhost) — typed REST<br/>no IPC proxy through main" ==> api
    domain --> persistence
    sqlite -. "clean migration path<br/>no dialect-specific SQL" .- pg
    broker -- "subscribe: asset discovery,<br/>downtime signals" --> mqtt
    mqtt -- "rebuild" --> cache

    classDef built fill:#1a7f37,color:#fff,stroke:#1a7f37
    class api built
```

**Legend:** green = exists today (T-001: `GET /health` through a typed Pydantic model). Everything else is proposed, constrained by `docs/architecture-facts.md`.

**The four foundational decisions (DEC-004–007):** separate-service topology (Electron shell + local FastAPI service, plain REST — no IPC data path) · server-side role enforcement (a hidden button is not an access control) · SQLAlchemy + Alembic dual-engine persistence (SQLite→Postgres without refactor) · live-broker UNS (backend is the sole MQTT client; UNS authoritative for assets).
