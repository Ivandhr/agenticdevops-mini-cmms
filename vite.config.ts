import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

/** Renderer build + vitest. The main-process build lives in `vite.main.config.ts`. */
export default defineConfig({
  // Relative asset URLs so the built renderer loads over file:// in Electron.
  base: './',
  plugins: [react()],
  build: {
    outDir: 'dist/renderer',
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
