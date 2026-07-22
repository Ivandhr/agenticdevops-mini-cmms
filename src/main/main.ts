/**
 * Electron main process — window creation and app lifecycle ONLY.
 *
 * Per DEC-004 main is never a proxy between renderer and backend: no HTTP calls to
 * the backend, no IPC channels carrying domain data, no database, no MQTT. The
 * renderer talks to the backend directly over HTTP.
 */

import path from 'node:path';

import { app, BrowserWindow } from 'electron';

/** Set by `npm run dev`; absent when running the built renderer from disk. */
const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL;

function createWindow(): void {
  const window = new BrowserWindow({
    width: 1024,
    height: 720,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (DEV_SERVER_URL) {
    void window.loadURL(DEV_SERVER_URL);
  } else {
    void window.loadFile(path.join(__dirname, '..', 'renderer', 'index.html'));
  }
}

void app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
