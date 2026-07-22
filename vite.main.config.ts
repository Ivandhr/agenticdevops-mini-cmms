import { defineConfig } from 'vite';

/** Electron main-process build. Emits CommonJS, which is what Electron loads. */
export default defineConfig({
  build: {
    outDir: 'dist/main',
    emptyOutDir: true,
    target: 'node20',
    lib: {
      entry: 'src/main/main.ts',
      formats: ['cjs'],
      fileName: () => 'main.js',
    },
    rollupOptions: {
      external: ['electron', 'node:path'],
    },
  },
});
