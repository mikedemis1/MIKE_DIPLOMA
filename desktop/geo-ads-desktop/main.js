const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const http = require("http");
const net = require("net");
const { spawn } = require("child_process");
const treeKill = require("tree-kill");

const BACKEND_HOST = process.env.GEO_ADS_BACKEND_HOST || "127.0.0.1";
const BACKEND_PORT = Number(process.env.GEO_ADS_BACKEND_PORT || "8000");
const HEALTH_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}/health`;

let mainWindow = null;
let backendProcess = null;
let backendPidFile = null;
let backendLogFile = null;

let isQuitting = false;
let isStopping = false;

// 1) Single instance (αποφεύγει διπλό backend spawn + cache issues)
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) app.quit();
app.on("second-instance", () => {
  if (!mainWindow) return;
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.focus();
});

// 2) userData σε καθαρό path
const userDataDir = path.join(app.getPath("appData"), "GEO-ADS-Desktop");
try { fs.mkdirSync(userDataDir, { recursive: true }); } catch {}
app.setPath("userData", userDataDir);

function appendLog(line) {
  const msg = `[${new Date().toISOString()}] ${line}\n`;
  try { if (backendLogFile) fs.appendFileSync(backendLogFile, msg, "utf8"); } catch {}
}

function httpGetStatus(url) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, (res) => {
      const { statusCode } = res;
      res.resume();
      resolve(statusCode);
    });
    req.on("error", reject);
    req.setTimeout(1000, () => req.destroy(new Error("timeout")));
  });
}

function isTcpPortInUse(host, port, timeoutMs = 250) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    const done = (result) => {
      try { socket.removeAllListeners(); } catch {}
      try { socket.destroy(); } catch {}
      resolve(result);
    };
    socket.setTimeout(timeoutMs);
    socket.once("connect", () => done(true));
    socket.once("timeout", () => done(false));
    socket.once("error", () => done(false));
    socket.connect(port, host);
  });
}

async function waitForBackendHealthy(timeoutMs = 15000) {
  const start = Date.now();
  while (true) {
    if (backendProcess && backendProcess.exitCode !== null) {
      throw new Error(`Backend exited early (exitCode=${backendProcess.exitCode}). Check backend.log.`);
    }
    try {
      const status = await httpGetStatus(HEALTH_URL);
      if (status === 200) return;
    } catch {}

    if (Date.now() - start > timeoutMs) {
      throw new Error(`Backend did not become healthy at ${HEALTH_URL}`);
    }
    await new Promise((r) => setTimeout(r, 300));
  }
}

async function killProcessTree(pid, timeoutMs = 5000) {
  if (!pid || pid <= 0) return;

  await new Promise((resolve) => {
    let finished = false;
    const finish = () => { if (!finished) { finished = true; resolve(); } };

    treeKill(pid, "SIGTERM", () => finish());
    setTimeout(() => {
      if (finished) return;
      treeKill(pid, "SIGKILL", () => finish());
    }, timeoutMs);
  });
}

async function killStaleBackendIfAny() {
  if (!backendPidFile) return;
  if (!fs.existsSync(backendPidFile)) return;

  const raw = fs.readFileSync(backendPidFile, "utf8").trim();
  const pid = Number(raw);

  try {
    if (pid > 0) {
      await killProcessTree(pid, 3000);
      appendLog(`Killed stale backend pid=${pid}`);
    }
  } catch {} finally {
    try { fs.unlinkSync(backendPidFile); } catch {}
  }
}

async function preflightPortOrFail() {
  const inUse = await isTcpPortInUse(BACKEND_HOST, BACKEND_PORT);
  if (!inUse) return;

  let health = null;
  try { health = await httpGetStatus(HEALTH_URL); } catch {}

  const hint =
    health === 200
      ? `Υπάρχει ήδη service που απαντάει /health=200 στο ${HEALTH_URL}.`
      : `Το port ${BACKEND_PORT} είναι πιασμένο αλλά δεν απαντάει /health.`;

  const msg =
    `${hint}\n\n` +
    `Κλείσε το process που κρατάει το port και ξανάτρεξε.\n` +
    `Windows: netstat -ano | findstr :${BACKEND_PORT}\n` +
    `        taskkill /PID <PID> /F`;

  appendLog(msg);
  dialog.showErrorBox("GEO-ADS: Port collision", msg);
  throw new Error(msg);
}

function resolvePythonExecutable(backendDir) {
  const candidates = [
    process.env.GEO_ADS_PYTHON,
    path.join(backendDir, ".venv", "Scripts", "python.exe"),
    path.join(backendDir, "venv", "Scripts", "python.exe"),
    "python",
  ].filter(Boolean);

  for (const p of candidates) {
    if (p && (p === "python" || fs.existsSync(p))) return p;
  }
  return "python";
}

function startBackend() {
  const backendDir = path.join(__dirname, "..", "..", "backend");
  const py = resolvePythonExecutable(backendDir);

  backendProcess = spawn(
    py,
    ["-m", "uvicorn", "app.main:app", "--host", BACKEND_HOST, "--port", String(BACKEND_PORT)],
    { cwd: backendDir, env: { ...process.env, PYTHONUNBUFFERED: "1" }, windowsHide: true, shell: false }
  );

  fs.writeFileSync(backendPidFile, String(backendProcess.pid), "utf8");
  appendLog(`Spawned backend pid=${backendProcess.pid} (py=${py})`);

  backendProcess.stdout.on("data", (data) => {
    const s = data.toString();
    process.stdout.write(`[backend] ${s}`);
    appendLog(`[stdout] ${s.trimEnd()}`);
  });

  backendProcess.stderr.on("data", (data) => {
    const s = data.toString();
    process.stderr.write(`[backend:err] ${s}`);
    appendLog(`[stderr] ${s.trimEnd()}`);
  });

  backendProcess.on("error", (err) => {
    appendLog(`Backend spawn error: ${String(err)}`);
    if (!isQuitting) {
      dialog.showErrorBox("GEO-ADS: Backend failed to start",
        `Backend spawn error:\n${String(err)}\n\nΔες backend.log για λεπτομέρειες.`
      );
    }
    app.quit();
  });

  backendProcess.on("exit", (code, signal) => {
    appendLog(`Backend exited code=${code} signal=${signal}`);
    if (!isQuitting && !isStopping) {
      dialog.showErrorBox("GEO-ADS: Backend exited",
        `Backend exited unexpectedly (code=${code}, signal=${signal}).\n\nΔες backend.log.`
      );
      app.quit();
    }
  });
}

async function stopBackend() {
  if (!backendProcess) return;
  if (isStopping) return;

  isStopping = true;
  const pid = backendProcess.pid;
  backendProcess = null;

  try {
    await killProcessTree(pid, 5000);
    appendLog(`Stopped backend pid=${pid}`);
  } finally {
    isStopping = false;
    try { fs.unlinkSync(backendPidFile); } catch {}
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: { nodeIntegration: false, contextIsolation: true },
  });

  const indexPath = path.join(__dirname, "..", "..", "frontend", "geo-ads-frontend", "build", "index.html");

  if (!fs.existsSync(indexPath)) {
    dialog.showErrorBox("GEO-ADS: UI build missing",
      `Δεν βρέθηκε:\n${indexPath}\n\nΤρέξε build (npm run build) ή npm run desktop.`
    );
    app.quit();
    return;
  }

  mainWindow.loadFile(indexPath);
  mainWindow.on("closed", () => (mainWindow = null));
}

app.whenReady().then(async () => {
  backendPidFile = path.join(app.getPath("userData"), "backend.pid");
  backendLogFile = path.join(app.getPath("userData"), "backend.log");

  try {
    await killStaleBackendIfAny();
    await preflightPortOrFail();

    startBackend();
    await waitForBackendHealthy();

    createWindow();
  } catch (err) {
    appendLog(`Startup failed: ${String(err)}`);
    try { await stopBackend(); } catch {}
    if (!isQuitting) dialog.showErrorBox("GEO-ADS: Startup failed", String(err));
    app.quit();
  }
});

app.on("before-quit", async (e) => {
  isQuitting = true;
  if (backendProcess && !isStopping) {
    e.preventDefault();
    try { await stopBackend(); } finally { app.quit(); }
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
