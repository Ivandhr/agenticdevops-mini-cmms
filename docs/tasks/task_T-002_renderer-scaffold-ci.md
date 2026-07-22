# Task T-002 — Renderer scaffold (Electron + React + TS) + green CI

## 1. Background

Second code task, and the other half of the original repo-scaffold item that T-001
sliced the backend off. It stands up the Electron/Vite/React/TypeScript renderer
skeleton and the CI workflow, so both toolchains have something real to run and
**Step 4 of the loop ("CI green") becomes true for the first time**. Branch→PR→merge
discipline resumes with this task — T-001's direct-to-`main` commit was tolerated
only because no CI existed to gate a PR.

This task also closes the Rule 12 loop left open by T-001: `docs/api-contract.md`
records `GET /health` with its TypeScript leg marked *N/A — no renderer exists yet*.
A renderer now exists, so the TypeScript type and the contract doc's TS leg land in
this same commit.

**This task implements no FR from `docs/functional-spec.md`.** It is infrastructure.
Stated plainly rather than citing a requirement it doesn't satisfy — the first task
to cite FR ids will be the one that builds real domain surface.

Authority docs consulted: `docs/architecture-facts.md` (every spec — in particular
§ Process/layer boundaries for the lifecycle-only main process per DEC-004, and
§ Security baseline for the Electron hardening flags); `docs/devops_pipeline.md`
(the authority for what CI runs, its runtime pins, and the soft/hard split);
`docs/contract-sync.md` (a typed boundary surface lands here — Rule 12).

## 2. What Already Exists (Do Not Rewrite)

**The backend is built and working — do not modify it.** T-001 shipped
`backend/app/main.py` with `GET /health` returning `{"status": "ok"}` through a
Pydantic `HealthResponse` (`status: Literal["ok"]`), one passing pytest in
`backend/tests/`, plus `backend/requirements.txt` and `backend/pyproject.toml`
(ruff + mypy strict, clean from `backend/`). **No backend source changes are in
scope for this task.**

Also already present — **edit, do not recreate**:

- `docs/api-contract.md` — exists with the `GET /health` entry. Fill in its
  TypeScript leg; do not rewrite the file or restructure the existing entry.
- `docs/devops_pipeline.md` — exists and is the CI authority. One stale sentence is
  corrected (see What to Build item 8); leave the rest alone.
- `.gitignore` (root) — exists with Python + Node ignores. Extend only if something
  genuinely new needs ignoring; do not recreate.
- `README.md` — exists. Add a "Running locally" section; do not rewrite it.

**Do not modify:** anything under `docs/` other than the two files named above,
anything under `checklists/`, `CLAUDE.md`, or `.cursor/`.

**Does not exist yet:** `package.json`, any renderer or Electron source, any
TypeScript config, any CI workflow. This task creates them.

## 3. What to Build

### 3.1 Node/Electron project root

1. **`package.json`** (repo root) — Electron + Vite + React + TypeScript. Scripts,
   at minimum:
   - `dev` — Vite dev server + Electron (the renderer + main dev loop).
   - `build` — builds **both** renderer and main. This is CLAUDE.md's stated build
     gate; `npm run build` must succeed from a clean checkout.
   - `typecheck` — `tsc --noEmit`.
   - `lint` — eslint over the TS/TSX sources.
   - `test` — `vitest run`.

   **`package-lock.json` must be committed.** CI runs `npm ci`, which fails without
   a lockfile. This is the single most likely way this task ships a red CI.

2. **Electron main process** — window creation and app lifecycle **only**. Per
   DEC-004 the main process is never a proxy between renderer and backend: no IPC
   channels carrying domain data, no HTTP calls to the backend, no database, no
   MQTT. Per `architecture-facts.md` § Security baseline the `BrowserWindow` sets
   **`contextIsolation: true` and `nodeIntegration: false`**.

3. **Renderer** — React + TypeScript, one view. It calls the backend's
   `GET /health` and displays the result: the reported status when the backend
   answers, and a clearly distinguishable "backend unreachable" state when it does
   not. The unreachable path is not an edge case here — the backend will frequently
   not be running during renderer development, and a renderer that blanks, hangs, or
   throws an unhandled rejection in that situation is a defect, not a rough edge.

   **Backend base URL:** hardcode `http://127.0.0.1:8000` as a single named constant
   in one module. No env-var plumbing, no config file, no service discovery — those
   arrive when there is a reason for them.

   **Use `127.0.0.1`, not `localhost`.** On Windows `localhost` may resolve to the
   IPv6 loopback `::1` while `uvicorn` binds IPv4 `127.0.0.1` by default, producing
   a connection failure that looks like a dead backend. This is a spec decision, not
   a preference.

### 3.2 The typed boundary (Rule 12)

4. **A TypeScript `HealthResponse` type** mirroring the Pydantic model
   (`status: "ok"`), living in a module that is the renderer's single source of
   truth for boundary types. The renderer must not hand-roll an inline shape for
   the response anywhere else.

5. **`docs/api-contract.md`** — fill in the TypeScript leg of the existing
   `GET /health` entry (name the TS type and its file path) and remove the
   now-false header note that no renderer exists. Same commit as the type itself.

### 3.3 Tooling

6. **`tsconfig.json`** (plus per-target configs if the renderer/main split needs
   them), **eslint config**, and **vitest config** — configured so `npm run
   typecheck`, `npm run lint`, and `npm run test` each exit clean from the repo
   root.

7. **At least one passing vitest test.** Test the renderer's health-response
   handling as pure logic — given a well-formed response it yields the healthy
   state; given a failed request it yields the unreachable state. **Do not attempt
   to launch Electron in a test.**

   Be clear-eyed about what this test does *not* do: it does not prove the renderer
   and backend agree, because it never contacts the backend. Per CLAUDE.md's
   recorded trap, two independently green typechecks are not evidence the two sides
   of a REST contract match. The boundary is proven in this task by the **human's
   runtime test** (Acceptance Criteria), and an automated integration test against a
   running backend is a named follow-up for the first task with real domain surface.

### 3.4 CI

8. **`.github/workflows/ci.yml`**, matching `docs/devops_pipeline.md`:

   - **Triggers:** push to `main`, and every pull request.
   - **Permissions:** `contents: read`. The workflow requests **no write token** —
     the pipeline is a checker, not a writer.
   - **Runner: `windows-latest`.** Spec decision, per the runbook's own principle of
     keeping CI on what the human actually runs; Windows is confirmed ground truth
     for this project.
   - **Runtimes:** Node **22**, Python **3.12** — pinned exactly, per the runbook.
   - **Two jobs** (the split-service topology, DEC-004):

   | Job | Step | Command | Gate |
   |---|---|---|---|
   | backend | install | `pip install -r requirements.txt` (in `backend/`) | hard |
   | backend | lint | `ruff check .` | **soft** |
   | backend | typecheck | `mypy .` | **soft** |
   | backend | test | `pytest` | hard |
   | renderer | install | `npm ci` | hard |
   | renderer | typecheck | `tsc --noEmit` | hard |
   | renderer | lint | `eslint` | hard |
   | renderer | test | `vitest run` | hard |

   **Soft means the step reports failure without failing the build** (e.g.
   `continue-on-error`). The runbook's promotion criterion governs when these become
   hard; do not promote them in this task, and do not silently make them hard by
   omitting the flag.

   **Do not add an Electron launch, packaging, or `npm run make` step.** Electron
   needs a display; launching it in CI is a known way to produce a hang or a
   confusing red. Packaging is `docs/packaging.md`'s area and that doc is unwritten.

9. **`docs/devops_pipeline.md` § First green build** — correct the stale claim. It
   currently reads that "Task T-001 (repo scaffold + green CI)" creates the minimum
   on both sides. T-001 shipped the **backend only**; T-002 (this task) adds the
   renderer and the workflow. Update that paragraph to say so, and record the
   `windows-latest` runner choice and its rationale alongside the existing runtime
   pins.

10. **`README.md`** — add a short "Running locally" section: how to start the
    backend (`uvicorn app.main:app` from `backend/`, with the venv activated using
    the **Windows** invocation `.venv\Scripts\activate`) and how to start the app
    (`npm run dev`), noting the backend must be running for the health view to
    report healthy.

## 4. Acceptance Criteria

Verifiable properties. "From a clean checkout" means a fresh clone with no
`node_modules` and no build output.

- [ ] From a clean checkout, `npm ci` succeeds — i.e. `package-lock.json` is
      committed and consistent with `package.json`.
- [ ] `npm run build` succeeds and produces build output for **both** the renderer
      and the main process.
- [ ] `npm run typecheck`, `npm run lint`, and `npm run test` each exit 0.
- [ ] At least one vitest test passes, and it exercises the renderer's health-
      response handling for both the success and the request-failure path.
- [ ] `npm run dev` launches an Electron window showing the renderer.
- [ ] **With the backend running**, the renderer displays the backend's reported
      health status. *(Human runtime test — this is what actually proves the
      boundary.)*
- [ ] **With the backend not running**, the renderer displays a clearly
      distinguishable unreachable state. It does not hang, blank, crash, or emit an
      unhandled promise rejection. *(Human runtime test.)*
- [ ] The response is consumed through the shared `HealthResponse` TypeScript type;
      no inline hand-rolled response shape exists anywhere in the renderer.
- [ ] The Electron `BrowserWindow` is created with `contextIsolation: true` and
      `nodeIntegration: false`.
- [ ] The main process contains no HTTP call to the backend, no IPC channel
      carrying domain data, no database access, and no MQTT access.
- [ ] `docs/api-contract.md` names the TypeScript type and its path for
      `GET /health`, and no longer claims the renderer does not exist — **in this
      same commit** (Rule 12).
- [ ] `.github/workflows/ci.yml` exists, runs on `windows-latest` with Node 22 and
      Python 3.12, declares `contents: read`, and runs all eight steps in the table
      above with `ruff` and `mypy` non-blocking and everything else blocking.
- [ ] CI is green on the pull request for this task.
- [ ] No backend source file is modified.
- [ ] No file outside the Files to Modify list is created or changed.

## 5. Files to Modify

**New:**

- `package.json`
- `package-lock.json`
- `tsconfig.json` (plus any per-target configs the renderer/main split requires)
- eslint config (project's chosen filename)
- vitest config (or vitest configuration inside the Vite config)
- Vite config
- Electron main-process source (e.g. `src/main/…`)
- Electron preload script, if the chosen setup requires one
- Renderer source: React entry, root component, the health view, the boundary-types
  module, and the health-fetch logic (e.g. `src/renderer/…`)
- Renderer index HTML
- At least one vitest test file
- `.github/workflows/ci.yml`

**Edited (existing — do not recreate):**

- `docs/api-contract.md` — TypeScript leg of `GET /health`; drop the "no renderer
  exists yet" note
- `docs/devops_pipeline.md` — § First green build correction + runner-OS record
- `README.md` — "Running locally" section
- `.gitignore` — only if something genuinely new needs ignoring

**Explicitly not touched:** anything under `backend/`, anything else under `docs/`,
anything under `checklists/`, `CLAUDE.md`, `.cursor/`.

The exact renderer/main directory layout is the agent's call, provided it is
conventional for Electron + Vite and the split between main and renderer is
obvious from the paths.

## 6. Coding-Agent Instructions

Read this spec file (`docs/tasks/task_T-002_renderer-scaffold-ci.md`) in full before
writing any code.

Stand up the Electron + Vite + React + TypeScript renderer skeleton at the repo
root and the CI workflow at `.github/workflows/ci.yml`. The renderer shows one view
that calls the existing backend `GET /health` at `http://127.0.0.1:8000` and
displays either the reported status or a clear "backend unreachable" state; it
consumes the response through a shared TypeScript `HealthResponse` type mirroring
the backend's Pydantic model, and `docs/api-contract.md` gains that type's name and
path in the same commit (Rule 12). The Electron main process is lifecycle-only —
window and app lifecycle, `contextIsolation: true`, `nodeIntegration: false`, and no
backend calls, IPC data channels, database, or MQTT. CI runs on `windows-latest`
with Node 22 and Python 3.12, two jobs, `contents: read` permissions, with `ruff`
and `mypy` non-blocking and installs, `tsc`, `eslint`, `pytest`, and `vitest`
blocking.

Hard constraints decided by this spec — do not re-decide these:

- **Silencer decision:** no kept-but-unused symbols are expected. If you believe you
  need to retain an unused import, export, or function, **stop and flag it to the
  PM** — do not pick a silencer and do not delete the symbol to make the build pass.
- **Backend base URL:** the literal `http://127.0.0.1:8000`, as a single named
  constant in one module. **Not `localhost`** — on Windows it can resolve to `::1`
  while uvicorn binds IPv4, which presents as a dead backend. No env-var or config
  plumbing in this task.
- **`package-lock.json` is committed.** CI runs `npm ci` and fails without it.
- **Soft CI steps stay soft.** `ruff` and `mypy` report without failing the build.
  Do not promote them; do not drop the flag that makes them non-blocking.
- **No Electron launch, packaging, or `npm run make` step in CI.**
- **Do not modify anything under `backend/`.**
- **Contract-sync (Rule 12), same commit:** the TypeScript `HealthResponse` type
  **+** `docs/api-contract.md`. The Pydantic side already exists and does not
  change.
- **User-facing impact — this task has one.** It is the first user-visible surface
  in the project: an application window that reports backend health. Per Rule 18 the
  user-doc change ships in the same commit — that is the `README.md` "Running
  locally" section, using the Windows venv activation `.venv\Scripts\activate`.
- **Structural-layout pre-flight (Rule 11): N/A.** This is a single static view with
  no panels, splits, dividers, or resizable boundaries. If you find yourself adding
  one, stop — it is out of scope.
- **The vitest test must not claim to prove the boundary.** It tests renderer logic
  with no backend contact. Do not add a mocked "integration" test that asserts the
  contract holds; a mocked boundary proves nothing about the real one, and the
  project's recorded trap is exactly this false confidence.

Standing invariants: honor docs/architecture-facts.md and CLAUDE.md; the renderer
holds no business logic, DB, or MQTT/UNS access; authorization is enforced
server-side; keep contract docs (Rule 12) and user-docs (Rule 18) in the same
commit; migrations run on both SQLite and Postgres; never read/write/delete data
outside the app's own store; build with npm run build when done.
