import { describe, expect, it } from 'vitest';

import { BACKEND_BASE_URL, readHealth } from './health';

/**
 * These tests cover renderer logic only. They never contact the backend, so they are
 * NOT evidence that the renderer and backend agree on the shape of `GET /health` —
 * that boundary is proven by exercising a running backend, not here.
 */
describe('readHealth', () => {
  it('reports healthy when the backend answers with a well-formed response', async () => {
    const state = await readHealth(async (url) => {
      expect(url).toBe(`${BACKEND_BASE_URL}/health`);
      return new Response(JSON.stringify({ status: 'ok' }), { status: 200 });
    });

    expect(state).toEqual({ kind: 'healthy', status: 'ok' });
  });

  it('reports unreachable when the request fails', async () => {
    const state = await readHealth(() => Promise.reject(new Error('connect ECONNREFUSED')));

    expect(state).toEqual({ kind: 'unreachable' });
  });

  it('reports unreachable when the backend answers with a non-2xx status', async () => {
    const state = await readHealth(async () => new Response('', { status: 503 }));

    expect(state).toEqual({ kind: 'unreachable' });
  });
});
