/**
 * Rokan — Electron Main Process
 * 
 * 1. Spawns the Python Flask backend
 * 2. Opens a native window
 * 3. Connects window to the backend
 * 
 * This is a real desktop app. Not a browser wrapper.
 */

const { app, BrowserWindow, Tray, Menu, nativeImage, shell } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');
const fs = require('fs');
const net = require('net');

const PORT = 18991;
const isDev = process.argv.includes('--dev');

let mainWindow = null;
let tray = null;
let pythonProcess = null;

// ── Paths ───────────────────────────────────────────────────────

function getPythonDir() {
  if (isDev) {
    return path.join(__dirname, '..');
  }
  return path.join(process.resourcesPath, 'python');
}

function getVenvDir() {
  return path.join(app.getPath('userData'), 'venv');
}

function getDataDir() {
  const home = app.getPath('home');
  return path.join(home, '.rokan');
}

function getEnvFile() {
  return path.join(getDataDir(), '.env');
}

// ── Python Backend ──────────────────────────────────────────────

function loadEnvFile() {
  const envPath = getEnvFile();
  const env = { ...process.env };

  if (fs.existsSync(envPath)) {
    const lines = fs.readFileSync(envPath, 'utf-8').split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx > 0) {
          const key = trimmed.slice(0, eqIdx).trim();
          const val = trimmed.slice(eqIdx + 1).trim();
          if (val) env[key] = val;
        }
      }
    }
  }

  return env;
}

function findPython() {
  const venvPython = path.join(getVenvDir(), 'bin', 'python');
  if (fs.existsSync(venvPython)) return venvPython;

  // Fallback to system python
  for (const cmd of ['python3', 'python']) {
    try {
      execSync(`${cmd} --version`, { stdio: 'ignore' });
      return cmd;
    } catch (e) { /* skip */ }
  }
  return null;
}

async function ensureVenv() {
  const venvDir = getVenvDir();
  const venvPython = path.join(venvDir, 'bin', 'python');

  if (fs.existsSync(venvPython)) {
    console.log('[ROKAN] Venv exists:', venvDir);
    return;
  }

  console.log('[ROKAN] Creating venv...');
  const pythonDir = getPythonDir();

  execSync(`python3 -m venv --system-site-packages "${venvDir}"`, { stdio: 'inherit' });
  execSync(`"${venvPython}" -m pip install --upgrade pip -q`, { stdio: 'inherit' });
  execSync(`"${venvPython}" -m pip install -e "${pythonDir}" -q`, { stdio: 'inherit' });

  // Optional search
  try {
    execSync(`"${venvPython}" -m pip install duckduckgo-search -q`, { stdio: 'ignore' });
  } catch (e) { /* optional */ }

  console.log('[ROKAN] Venv ready.');
}

function ensureDataDir() {
  const dataDir = getDataDir();
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  const envFile = getEnvFile();
  if (!fs.existsSync(envFile)) {
    fs.writeFileSync(envFile, [
      '# Rokan — API Keys',
      '# Get a free key at https://build.nvidia.com',
      '',
      'NVIDIA_API_KEY=',
      '',
      '# Optional',
      '# TAVILY_API_KEY=',
      '',
    ].join('\n'));
  }
}

function startPythonBackend() {
  return new Promise((resolve, reject) => {
    const python = findPython();
    if (!python) {
      reject(new Error('Python not found'));
      return;
    }

    const env = loadEnvFile();
    const pythonDir = getPythonDir();

    // Add python source to PYTHONPATH
    env.PYTHONPATH = pythonDir + (env.PYTHONPATH ? ':' + env.PYTHONPATH : '');

    console.log(`[ROKAN] Starting backend: ${python} -m rokan_gui.server`);

    pythonProcess = spawn(python, ['-m', 'rokan_gui.server'], {
      env,
      cwd: pythonDir,
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    pythonProcess.stdout.on('data', (d) => console.log('[PY]', d.toString().trim()));
    pythonProcess.stderr.on('data', (d) => console.error('[PY]', d.toString().trim()));

    pythonProcess.on('error', (err) => {
      console.error('[ROKAN] Python failed:', err);
      reject(err);
    });

    pythonProcess.on('exit', (code) => {
      console.log(`[ROKAN] Python exited: ${code}`);
      pythonProcess = null;
    });

    // Wait for server to be ready
    const maxWait = 15000;
    const start = Date.now();

    const check = () => {
      const sock = new net.Socket();
      sock.setTimeout(500);
      sock.on('connect', () => {
        sock.destroy();
        console.log('[ROKAN] Backend ready');
        resolve();
      });
      sock.on('error', () => {
        sock.destroy();
        if (Date.now() - start > maxWait) {
          reject(new Error('Backend timeout'));
        } else {
          setTimeout(check, 300);
        }
      });
      sock.on('timeout', () => {
        sock.destroy();
        setTimeout(check, 300);
      });
      sock.connect(PORT, '127.0.0.1');
    };

    setTimeout(check, 500);
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    console.log('[ROKAN] Stopping backend...');
    pythonProcess.kill('SIGTERM');
    pythonProcess = null;
  }
}

// ── Window ──────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 900,
    minHeight: 600,
    title: 'Rokan',
    backgroundColor: '#08080f',
    icon: getIcon(),
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  mainWindow.loadURL(`http://127.0.0.1:${PORT}`);

  // Open external links in system browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('close', (e) => {
    // Minimize to tray instead of quitting
    if (tray && !app.isQuitting) {
      e.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  if (isDev) {
    mainWindow.webContents.openDevTools();
  }
}

function getIcon() {
  const iconPath = path.join(__dirname, 'build', 'icon.png');
  if (fs.existsSync(iconPath)) {
    return nativeImage.createFromPath(iconPath);
  }
  return undefined;
}

// ── Tray ────────────────────────────────────────────────────────

function createTray() {
  const icon = getIcon();
  if (!icon) return;

  tray = new Tray(icon);
  tray.setToolTip('Rokan — The System');

  const contextMenu = Menu.buildFromTemplate([
    { label: 'Open Rokan', click: () => { mainWindow?.show(); } },
    { type: 'separator' },
    { label: 'Quit', click: () => { app.isQuitting = true; app.quit(); } },
  ]);

  tray.setContextMenu(contextMenu);
  tray.on('click', () => mainWindow?.show());
}

// ── App Lifecycle ───────────────────────────────────────────────

app.whenReady().then(async () => {
  console.log('[ROKAN] Starting...');

  ensureDataDir();

  try {
    await ensureVenv();
  } catch (e) {
    console.error('[ROKAN] Venv setup failed:', e.message);
    // Continue anyway — might work with system python
  }

  try {
    await startPythonBackend();
  } catch (e) {
    console.error('[ROKAN] Backend failed:', e.message);
    // Show error window
    createWindow();
    mainWindow.loadURL(`data:text/html,
      <body style="background:#08080f;color:#f87171;font-family:monospace;padding:40px">
        <h2>Rokan — Backend Failed</h2>
        <p>${e.message}</p>
        <p style="color:#5a6080">Check that Python 3.10+ is installed and NVIDIA_API_KEY is set in ~/.rokan/.env</p>
      </body>
    `);
    return;
  }

  createWindow();
  createTray();
});

app.on('window-all-closed', () => {
  // On Linux, quit when all windows are closed
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  } else {
    mainWindow.show();
  }
});

app.on('before-quit', () => {
  app.isQuitting = true;
  stopPythonBackend();
});
