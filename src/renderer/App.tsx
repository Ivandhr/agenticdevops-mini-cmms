import { useEffect, useState } from 'react';

import { BACKEND_BASE_URL, readHealth, type HealthState } from './api/health';

function describe(health: HealthState): { label: string; detail: string; tone: string } {
  switch (health.kind) {
    case 'loading':
      return { label: 'Checking…', detail: `Asking ${BACKEND_BASE_URL} for its health.`, tone: '#6b7280' };
    case 'healthy':
      return { label: `Backend healthy — "${health.status}"`, detail: `${BACKEND_BASE_URL}/health answered.`, tone: '#15803d' };
    case 'unreachable':
      return {
        label: 'Backend unreachable',
        detail: `No answer from ${BACKEND_BASE_URL}. Start it with "uvicorn app.main:app" from backend/.`,
        tone: '#b91c1c',
      };
  }
}

export function App() {
  const [health, setHealth] = useState<HealthState>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;
    void readHealth().then((next) => {
      if (!cancelled) {
        setHealth(next);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const { label, detail, tone } = describe(health);

  return (
    <main
      style={{
        fontFamily: 'Segoe UI, system-ui, sans-serif',
        padding: '2rem',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.5rem',
      }}
    >
      <h1 style={{ fontSize: '1.25rem', margin: 0 }}>CMMess</h1>
      <p style={{ color: tone, fontWeight: 600, margin: 0 }}>{label}</p>
      <p style={{ color: '#6b7280', margin: 0 }}>{detail}</p>
    </main>
  );
}
