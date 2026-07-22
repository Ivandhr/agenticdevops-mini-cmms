# CMMess

A reactive **CMMS** (computerized maintenance management system) for facility maintenance teams, where **downtime drives the work**: a downtime event on any asset seeds a work order that Planners plan and schedule and Users execute — rather than tracking and planning being separate, disconnected capabilities.

## What makes it different

- **Downtime-driven.** Work orders originate from a typed, extensible trigger — an automated downtime event detected via the UNS, or manual creation by a User or Planner. v1 is reactive-only, but the origin is a first-class field so preventive/scheduled maintenance can be added later without a redesign.
- **Process-agnostic assets.** Assets are generic, configurable entities discovered through a **Unified Namespace (UNS)** rather than a hardcoded equipment list, so any industry, plant, or facility onboards without changing the data model.
- **Two roles, one shared instance.** Users (technicians/engineers) and Planners (managers) work from a single multi-user instance with role-based access, enforced server-side.
- **Cross-platform.** Delivered as a desktop app that runs across operating systems.

## Stack

- **Renderer:** Electron + TypeScript + React
- **Backend:** Python 3.12 + FastAPI, run as a separate local service
- **Persistence:** SQLAlchemy + Alembic — SQLite by default (v1/dev), Postgres supported
- **Asset discovery:** MQTT client (paho/aiomqtt) subscribing to a UNS topic structure
- **Auth:** role-based (User / Planner), enforced in the backend

The renderer talks to the backend over HTTP (localhost) and holds no business logic, database access, or MQTT access — all domain logic lives in the backend. See `docs/architecture-facts.md` for the full set of hard constraints.

## Status

**v1, scaffolded.** The workflow and architecture are established. T-001 stood up the FastAPI backend skeleton; T-002 added the Electron/React/TypeScript renderer and the CI pipeline. The app currently has one view: it reports backend health. Domain surface starts arriving with the next tasks.

## Running locally

The backend and the renderer are **separate services** — start the backend first, then the app.

**1. Backend** (from `backend/`, Python 3.12):

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

It serves on `http://127.0.0.1:8000`. Check it with `http://127.0.0.1:8000/health`, which answers `{"status": "ok"}`.

**2. App** (from the repo root, Node 22):

```
npm install
npm run dev
```

This starts the Vite dev server and opens the Electron window.

**The backend must be running for the health view to report healthy.** If it isn't, the window shows a "Backend unreachable" state rather than failing silently — that is expected, not a crash.

Other root-level commands: `npm run build` (renderer + main), `npm run typecheck`, `npm run lint`, `npm test`. Packaging (per-OS installers) is not wired up yet.

## How this project is developed

CMMess is built with an agentic-devops loop: a human lead (architecture and behavioral testing), a PM agent (specs, verification, living docs), a coding agent, and a review agent (mechanical QA). Every change rides a spec → branch → implement → QA → read-verify → runtime-test → close-out → PR → CI loop. The governing docs live under `docs/`:

- `docs/architecture-facts.md` — the hard technical constraints every change enforces
- `docs/decision-log.md` — numbered architectural decisions with rationale
- `docs/development_workflow.md` — the branch/PR loop
- `docs/devops_pipeline.md` — what CI runs and why
- `docs/agent_handoff.md` — current state (read first)

## License

Open-source under an open license; developed from a closed repository during v1. (License file to be added.)
