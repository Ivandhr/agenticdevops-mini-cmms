import type { HealthResponse } from './types';

/**
 * The backend's local base URL.
 *
 * `127.0.0.1`, never `localhost`: on Windows `localhost` can resolve to the IPv6
 * loopback `::1` while uvicorn binds IPv4, which presents as a dead backend.
 */
export const BACKEND_BASE_URL = 'http://127.0.0.1:8000';

/** What the renderer knows about backend health at a point in time. */
export type HealthState =
  | { kind: 'loading' }
  | { kind: 'healthy'; status: HealthResponse['status'] }
  | { kind: 'unreachable' };

/** The slice of `fetch` this module uses; lets tests drive the logic directly. */
export type FetchLike = (url: string) => Promise<Response>;

/**
 * Ask the backend for its health and reduce the outcome to a `HealthState`.
 *
 * Every failure mode — connection refused, non-2xx, unparseable body — collapses to
 * `unreachable`, because the backend not running is the routine case during renderer
 * development and must never surface as an unhandled rejection.
 */
export async function readHealth(
  fetchImpl: FetchLike = (url) => fetch(url),
): Promise<HealthState> {
  try {
    const response = await fetchImpl(`${BACKEND_BASE_URL}/health`);
    if (!response.ok) {
      return { kind: 'unreachable' };
    }
    const body = (await response.json()) as HealthResponse;
    return { kind: 'healthy', status: body.status };
  } catch {
    return { kind: 'unreachable' };
  }
}
