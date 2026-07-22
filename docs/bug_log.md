# CMMess — Bug Log

> Active and fixed bugs, **plus the traps log.** Consult before touching any previously-buggy area — patterns that caused a bug once tend to recur.

## Bug entries

Each bug gets an entry **before** its fix task runs; flip it to Fixed only **after** verification.

**Entry format:**
```
### BUG-NNN — <one-line symptom>   [Active | Fixed <date>]

**Reported:** <how it surfaced>
**Root cause:** <the actual cause, once known — not the symptom>
**Fix:** <what changed; link the spec/task>
**Trap (if any):** <pointer to a TRAP-NNN below if this bug revealed a reusable trap>
```

## Active

*(none)*

## Fixed

### BUG-001 — Renderer reports "backend unreachable" while the backend is running   [Fixed 2026-07-22]

**Reported:** Flagged by the coding agent in T-002's commit (`1417c5e`) and confirmed
by PM read-verification of the actual files before merge — not found at runtime,
because T-002 has not been runtime-tested yet.

**Root cause:** The renderer fetches `http://127.0.0.1:8000/health` from a page
served at `http://127.0.0.1:5173` (dev, `loadURL`) or `file://` (packaged,
`loadFile`). Both are cross-origin — a different port in dev, and `Origin: null`
from `file://`. `backend/app/main.py` installed no `CORSMiddleware`, so Chromium
blocked the response. `readHealth()` collapses every failure mode to `unreachable`,
so a CORS rejection is indistinguishable from a dead backend.

**Not a coding-agent error — a spec error.** `docs/tasks/task_T-002_renderer-scaffold-ci.md`
required the renderer to display live backend health (two human-runtime acceptance
criteria) while simultaneously forbidding any backend change. Those two constraints
cannot both be satisfied: the boundary needs a backend-side CORS allowlist. The
agent surfaced the conflict rather than quietly violating the no-backend-changes
constraint, which is the correct behavior.

**Note on attribution:** the T-002 commit message states the gap was shipped "by PM
decision." No such decision was made or communicated — the PM first learned of the
gap by reading that commit message. Recorded so the trail is accurate.

**Fix:** `CORSMiddleware` added to `backend/app/main.py` (commit `f6fa20b`), per
`docs/tasks/task_T-002_renderer-scaffold-ci.md` § 3.4 — the amendment that permits
exactly one backend change. `allow_origins` is exactly `["http://127.0.0.1:5173"]`,
with `allow_methods`/`allow_headers` narrowed to what the renderer actually uses.
**No wildcard** — auth lands next (DEC-005) and wildcard-plus-credentials is a real
vulnerability, so the allowlist is tight while it is still free. **The literal
`"null"` origin is deliberately not allowlisted**; the packaged `file://` case is out
of scope here and is recorded as a blocker in
`checklists/packaging-preflight.checklist.md`, which is where it will be read at the
moment it matters.

Three tests in `backend/tests/test_health.py`: the header is emitted for the
allowlisted origin, and **absent** for an unlisted origin and for `"null"`. The
negative cases are the load-bearing ones — they are what fails if a future CORS
complaint is "fixed" with `["*"]`.

**Verified 2026-07-22, at runtime, in the real app** — the only check that means
anything here (see TRAP-001). The Electron window, against a running backend, went
from "Backend unreachable" (red) to **"Backend healthy — ok"** (green), with the two
`blocked by CORS policy` console errors gone. Confirmed by the human. Backend
`pytest`/`ruff`/`mypy` clean and CI green on `main` (run `29941029152`), but note
that none of those gates could have caught the bug in the first place.

**Trap:** TRAP-001.

## Traps

A **trap** is a failure mode that will fool a future agent — most often the "**green everywhere, broken where nobody looks**" kind, where the type-checker, linter, tests, and build all pass but the thing is still wrong. The traps log is where these are recorded once, canonically, so a close-out entry can *point* to a trap instead of restating it.

**How to write a trap:** give it an id (`TRAP-NNN`) and a one-line description of the deceptive failure, then two things — **why every guard misses it** (walk typecheck → lint → tests → build and name where it actually surfaces, usually only when the real artifact runs) and **the tell** (the concrete check that *does* catch it, since the automated guards won't). Keep the traps themselves here in this doc.

### TRAP-001 — A renderer test with an injected `fetch` cannot see a browser-enforced boundary failure

**The deceptive failure:** the renderer's HTTP call to the backend is blocked by the
browser (CORS, mixed content, a blocked scheme) and the app shows its error state,
while every automated gate reports success.

**Why every guard misses it.** *Typecheck:* both sides are correctly typed and agree
— the TypeScript type genuinely mirrors the Pydantic model, and `tsc` has no concept
of an origin. *Lint:* nothing is stylistically wrong. *Unit tests:* the fetch
function is injected so the logic can be driven directly, which is good design — and
it means the test never performs a real cross-origin request, so the browser's
security layer is never involved. *Backend tests:* `TestClient` calls the ASGI app
in-process, where no browser and no `Origin` header exist; the endpoint answers 200
in every backend test while being unreadable from the actual renderer. *Build/CI:*
green, because CI never launches Electron. The failure surfaces **only when the real
renderer, in a real Chromium, requests the real backend.**

**Made worse by correct defensive code.** A well-written client collapses connection
refused, non-2xx, and parse failure into one "unavailable" state. That is right — and
it means a security-layer rejection is indistinguishable from a backend that simply
is not running, which is the routine case during development. The failure hides
inside the state you expect to see.

**The tell.** Run the real app against a *known-running* backend and confirm the
success path renders — never infer health from the error state's plausibility. Then
check the browser devtools console/network panel, which names the blocked request
explicitly where the application code cannot. For CI, the only real check is an
integration test that performs an actual cross-origin request against a running
backend; a test with an injected transport proves the logic, never the boundary.
(This is the concrete instance of CLAUDE.md's standing warning that two green
typechecks are not proof the two sides of the REST contract agree.)

*First observed:* BUG-001 (T-002).

*(Earlier general trap worth keeping in mind: a grep that returns nothing is evidence
about the grep, not the code — validate it against a string you know is present
before trusting its silence.)*
