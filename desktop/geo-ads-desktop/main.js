// desktop/geo-ads-desktop/main.js
const { app, BrowserWindow } = require("electron");
const path = require("path");
const { spawn } = require("child_process");

let mainWindow = null;
let backendProcess = null;

/**
 * Ξεκινάει το backend (FastAPI / uvicorn)
 * από τον φάκελο DIPLOMA.MIKE/backend
 */
function startBackend() {
  const backendDir = path.join(__dirname, "..", "..", "backend");

  // Η ίδια εντολή που τρέχεις στο PowerShell:
  // uvicorn app.main:app --reload
  backendProcess = spawn("uvicorn", ["app.main:app", "--reload"], {
    cwd: backendDir,
    shell: true
  });

  // Logs για να βλέπεις τι γίνεται στο backend
  backendProcess.stdout.on("data", (data) => {
    console.log("[backend]", data.toString());
  });

  backendProcess.stderr.on("data", (data) => {
    console.error("[backend error]", data.toString());
  });

  backendProcess.on("close", (code) => {
    console.log(`[backend] exited with code ${code}`);
  });
}

/**
 * Δημιουργεί το Electron παράθυρο
 * και φορτώνει το React build.
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Δείχνει το build του React:
  // DIPLOMA.MIKE/frontend/geo-ads-frontend/build/index.html
  const indexPath = path.join(
    __dirname,
    "..",
    "..",
    "frontend",
    "geo-ads-frontend",
    "build",
    "index.html"
  );

  mainWindow.loadFile(indexPath);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

/**
 * Όταν είναι έτοιμη η Electron:
 * 1) ξεκινάμε backend
 * 2) ανοίγουμε παράθυρο
 */
app.whenReady().then(() => {
  startBackend();
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

/**
 * Όταν κλείνει η εφαρμογή:
 * σκοτώνουμε το backend process.
 */
app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
