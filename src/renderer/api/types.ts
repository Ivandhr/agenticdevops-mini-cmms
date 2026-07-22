/**
 * Renderer's single source of truth for renderer↔backend boundary types.
 *
 * Every type here mirrors a Pydantic model in the backend. Changing one moves the
 * Pydantic model, the type below, and `docs/api-contract.md` in the same commit
 * (Rule 12 / `docs/contract-sync.md`).
 */

/** Mirrors `HealthResponse` in `backend/app/main.py` — `status: Literal["ok"]`. */
export interface HealthResponse {
  status: 'ok';
}
