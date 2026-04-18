/**
 * Rokan — Preload script
 * Runs in renderer context before page loads.
 * Exposes safe APIs to the frontend.
 */

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('rokan', {
  platform: process.platform,
  version: '2.0.0',
});
