# API Contract — CMMess

> The authority for the renderer↔backend REST surface. Per `docs/contract-sync.md`,
> any endpoint/schema change moves its Pydantic model, its TypeScript type, and this
> doc **in the same commit** (Rule 12).

## Endpoints

### GET /health

- **Path:** `/health`
- **Method:** `GET`
- **Auth:** none
- **Response model:** `HealthResponse` (`backend/app/main.py`) — `status: Literal["ok"]`
- **TypeScript type:** `HealthResponse` (`src/renderer/api/types.ts`) — `status: 'ok'`
- **Example response (200):**

  ```json
  {"status": "ok"}
  ```
