# Phase 11 — Desktop Application: Design

> **Version:** 1.0 | **Date:** 2026-07-17 | **Type:** Design-Only  
> **Status:** Phase 10.3 Complete | 1130 tests | Docker Hub ready  
> **Constraint:** Zero Veritas-Core modifications | Design → Implement path

---

## 1. Desktop Architecture

### 1.1 High-Level Design

```
┌──────────────────────────────────────────────────────────────┐
│                   A3 Desktop Application                      │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Electron Shell (Renderer)                 │   │
│  │                                                      │   │
│  │  ┌──────────────────┐  ┌─────────────────────────┐   │   │
│  │  │  Streamlit WebView│  │  Native UI               │   │   │
│  │  │  (localhost:8501) │  │  • Menu bar              │   │   │
│  │  │                   │  │  • System tray           │   │   │
│  │  │  ChatGPT-style    │  │  • File dialogs          │   │   │
│  │  │  learning UI      │  │  • Notifications         │   │   │
│  │  └────────┬──────────┘  │  • Auto-start            │   │   │
│  │           │             └──────────────────────────┘   │   │
│  └───────────┼──────────────────────────────────────────┘   │
│              │ HTTP (localhost)                              │
│              ▼                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Docker Engine (Host)                      │   │
│  │                                                      │   │
│  │  ┌──────────────┐    ┌──────────────┐               │   │
│  │  │ a3-api       │    │ a3-dashboard │               │   │
│  │  │ (FastAPI)    │◄───│ (Streamlit)  │               │   │
│  │  │ :8000        │    │ :8501        │               │   │
│  │  └──────┬───────┘    └──────────────┘               │   │
│  │         │                                            │   │
│  │         ▼                                            │   │
│  │  ┌──────────────┐                                    │   │
│  │  │ a3_data      │  Named volume (persistent)        │   │
│  │  │ (SQLite)     │                                    │   │
│  │  └──────────────┘                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              User Data (Host Filesystem)              │   │
│  │                                                      │   │
│  │  ~/A3/                                               │   │
│  │  ├── data/         ← Bind mount to a3_data volume    │   │
│  │  ├── config/       ← .env, settings                  │   │
│  │  └── backups/      ← Auto-backups                    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack

| Layer | Technology | Rationale |
|:------|:-----------|:----------|
| Shell | Electron 30+ | Cross-platform, native menus, system tray, auto-update |
| WebView | Streamlit (existing) | Zero rewrite — reuse entire web UI |
| Backend | Docker Compose (existing) | Container lifecycle, health checks, volumes |
| Packaging | electron-builder | Windows .exe, macOS .dmg, Linux .AppImage |
| Updates | electron-updater | Auto-download new releases from GitHub |
| Installer | NSIS (Windows) | Custom install wizard, Docker Desktop check |

### 1.3 Why Electron + Docker

```
Decision: Electron wrapper + Docker backend

Rationale:
  ✅ Reuse entire Streamlit UI — zero frontend rewrite
  ✅ Docker already production-ready (Phase 10.3)
  ✅ Cross-platform (Windows, macOS, Linux) with single codebase
  ✅ Native features: tray, notifications, file dialogs
  ✅ Auto-update via electron-updater
  ✅ User data persists outside container

Trade-offs:
  ⚠️ App size: ~200 MB (Electron ~150 + Docker image ~300 pulled separately)
  ⚠️ Requires Docker Desktop on Windows/macOS
  ⚠️ Startup: ~10s cold (Docker container start)

Alternatives considered:
  • Tauri: Smaller (~10MB) but limited WebView features, no Docker interop
  • PyWebView: Lighter but no tray/notifications/auto-update
  • Nativefier: Quick wrapper, no lifecycle management
```

---

## 2. Electron + Docker Integration

### 2.1 Lifecycle State Machine

```
                    ┌──────────┐
                    │ STOPPED  │  ← Initial state
                    └────┬─────┘
                         │ user clicks "Start"
                         ▼
                    ┌──────────┐
                    │ STARTING │  docker compose up -d
                    └────┬─────┘
                         │ health check passed
                         ▼
                    ┌──────────┐
                    │ RUNNING  │  Normal operation
                    └────┬─────┘
                         │ user clicks "Stop" / app closes
                         ▼
                    ┌──────────┐
                    │ STOPPING │  docker compose down
                    └────┬─────┘
                         │ containers exited
                         ▼
                    ┌──────────┐
                    │ STOPPED  │
                    └──────────┘

Error states:
  STARTING → ERROR (Docker not installed, port conflict, pull failed)
  RUNNING  → ERROR (container crashed, health check failed)
```

### 2.2 Electron Main Process

```javascript
// main.js — Electron main process (design reference)

const { app, BrowserWindow, Tray, Menu, dialog, ipcMain } = require('electron');
const { spawn, execSync } = require('child_process');
const path = require('path');

// ── Container Manager ──────────────────────────────────
class ContainerManager {
  status: 'stopped' | 'starting' | 'running' | 'stopping' | 'error';

  async start() {
    // 1. Check Docker is installed
    this._checkDocker();

    // 2. Pull latest image (optional, configurable)
    if (config.autoUpdate) {
      await exec('docker pull leisureauf1/a3-multi-agent-system:latest');
    }

    // 3. Start containers
    this.status = 'starting';
    await exec('docker compose -f /path/to/docker-compose.yml up -d');

    // 4. Wait for health check
    await this._waitForHealth('http://localhost:8000/health', 30000);

    this.status = 'running';
  }

  async stop() {
    this.status = 'stopping';
    await exec('docker compose -f /path/to/docker-compose.yml down');
    this.status = 'stopped';
  }

  async _checkDocker() {
    try { execSync('docker --version'); }
    catch { throw new Error('Docker not installed'); }
  }
}

// ── Window Manager ─────────────────────────────────────
class WindowManager {
  createMainWindow() {
    const win = new BrowserWindow({
      width: 1280, height: 800,
      webPreferences: { nodeIntegration: false },
    });

    // Load Streamlit UI (localhost — managed by Docker)
    win.loadURL('http://localhost:8501');

    // Show loading screen until healthy
    win.webContents.on('did-fail-load', () => {
      win.loadFile('loading.html');  // "Starting A3..."
    });
  }
}
```

### 2.3 IPC Channels

```
Renderer (Streamlit)  ←──IPC──→  Main Process (Electron)
─────────────────────────────────────────────────────────
'container:status'    ←──→      Container state
'container:start'     ──→       Start Docker
'container:stop'      ──→       Stop Docker
'config:get'          ←──→      Read settings
'config:set'          ──→       Write settings
'export:data'         ──→       Open file dialog → export
'import:data'         ──→       Open file dialog → import
'app:quit'            ──→       Graceful shutdown
'update:available'    ←──       New version detected
'update:install'      ──→       Download and install
```

---

## 3. Windows Installer Flow

### 3.1 Installation Steps

```
Step 1: Prerequisites Check
  ┌────────────────────────────────────────┐
  │  A3 Desktop Setup                       │
  │                                        │
  │  Checking prerequisites...              │
  │  ✅ Docker Desktop 24+     (found)      │
  │  ✅ 2 GB free disk space   (5.2 GB)    │
  │  ✅ Windows 10/11 64-bit   (detected)  │
  └────────────────────────────────────────┘

Step 2: Installation
  ┌────────────────────────────────────────┐
  │  Installing A3 Desktop...              │
  │                                        │
  │  📁 C:\Program Files\A3\              │
  │  📁 %APPDATA%\A3\         (user data) │
  │  🔗 Start Menu shortcut               │
  │  🔗 Desktop shortcut                  │
  └────────────────────────────────────────┘

Step 3: Pull Docker Image (optional, can skip)
  ┌────────────────────────────────────────┐
  │  Pulling A3 image (~300 MB)...         │
  │  ████████████░░░░░░  65%              │
  │                                        │
  │  [Skip — will download on first launch]│
  └────────────────────────────────────────┘

Step 4: Complete
  ┌────────────────────────────────────────┐
  │  ✅ A3 Desktop is ready!               │
  │                                        │
  │  [✓] Launch A3 Desktop                 │
  │  [✓] Create desktop shortcut           │
  │                                        │
  │       [Finish]                         │
  └────────────────────────────────────────┘
```

### 3.2 Installer Technology

| Platform | Tool | Output |
|:---------|:-----|:-------|
| Windows | NSIS (via electron-builder) | `A3-Setup-1.0.0.exe` |
| macOS | DMG (via electron-builder) | `A3-1.0.0.dmg` |
| Linux | AppImage | `A3-1.0.0.AppImage` |

### 3.3 File Layout (Windows)

```
C:\Program Files\A3\
├── A3.exe                    # Electron executable
├── resources\
│   ├── app/                  # Electron app code
│   ├── docker-compose.yml   # Container config
│   └── docker-compose.desktop.yml  # Desktop-specific overrides
└── uninstall.exe

%APPDATA%\A3\
├── data\                     # SQLite DB (bind-mounted to container)
│   └── a3.db
├── config\
│   └── settings.json         # User preferences
├── backups\                  # Auto-backups
└── logs\
    └── a3.log
```

---

## 4. First Launch Experience

### 4.1 Onboarding Flow

```
App Launched
     │
     ▼
┌──────────────────────────────────────────┐
│         🦊 Welcome to A3 Desktop          │
│                                          │
│    Your personal AI learning assistant   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  We're starting the A3 engine...  │   │
│  │  ████████░░░░░░░░  50%           │   │
│  │  Pulling Docker image...          │   │
│  └──────────────────────────────────┘   │
│                                          │
│  First launch may take 2-5 minutes       │
│  while we download the learning engine.  │
│  Subsequent launches: <10 seconds.       │
└──────────────────────────────────────────┘
     │ (image pulled + container healthy)
     ▼
┌──────────────────────────────────────────┐
│         👤 Create Your Profile            │
│                                          │
│  How would you like to get started?      │
│                                          │
│  [🎓 I'm a student]  [👨‍🏫 I'm a teacher] │
│  [💻 I'm a developer] [🚀 Just exploring]│
│                                          │
│  Or describe yourself:                   │
│  ┌──────────────────────────────────┐   │
│  │ I know Python basics and want    │   │
│  │ to learn machine learning...     │   │
│  └──────────────────────────────────┘   │
│                                          │
│  [Skip — use as guest]                   │
└──────────────────────────────────────────┘
     │
     ▼
┌──────────────────────────────────────────┐
│         🎯 Your Learning Dashboard        │
│                                          │
│  [Dashboard loads — ready to learn]      │
└──────────────────────────────────────────┘
```

### 4.2 Loading States

| State | UI | Duration |
|:------|:---|:---------|
| Docker check | "Checking Docker..." spinner | <1s |
| Image pull (first time) | Progress bar "Downloading A3 engine..." | 2-5 min |
| Image pull (update) | Progress bar "Updating to v1.1.0..." | 1-3 min |
| Container start | "Starting learning engine..." spinner | 5-15s |
| Health check | "Connecting..." dots | 2-5s |
| Dashboard ready | Full UI | <1s after health |

---

## 5. Container Lifecycle Management

### 5.1 System Tray Menu

```
┌─────────────────────┐
│ 🦊 A3 Desktop       │
├─────────────────────┤
│ Open Dashboard      │
│ ───────────────     │
│ Status: ● Running   │
│ ───────────────     │
│ ▶ Start Engine      │  (disabled when running)
│ ⏸️  Stop Engine      │
│ 🔄 Restart Engine   │
│ ───────────────     │
│ 📊 Show Logs        │
│ ⚙️  Settings         │
│ ───────────────     │
│ ❌ Quit A3          │
└─────────────────────┘
```

### 5.2 Auto-Start Options

```
Settings → General:
  [✓] Start A3 when Windows starts
  [✓] Start engine automatically (skip manual start)
  [ ] Minimize to tray on close
  [✓] Show notifications for updates
```

### 5.3 Health Monitoring

```javascript
// Health check loop — runs every 30s
setInterval(async () => {
  try {
    const resp = await fetch('http://localhost:8000/health');
    if (resp.ok) {
      updateTrayStatus('running');
    } else {
      updateTrayStatus('degraded');
    }
  } catch {
    updateTrayStatus('error');
    // Auto-restart if configured
    if (config.autoRestart) {
      await containerManager.restart();
    }
  }
}, 30000);
```

---

## 6. Auto Update Strategy

### 6.1 Update Flow

```
GitHub Release (new tag)
        │
        ▼
electron-updater checks on app start + every 4 hours
        │
        ▼
┌──────────────────────────────────────────┐
│  🔄 Update Available                     │
│                                          │
│  A3 Desktop v1.1.0 is available.         │
│                                          │
│  What's new:                             │
│  • New EvaluationAgent v2               │
│  • Faster resource generation            │
│  • Bug fixes                             │
│                                          │
│  [Update Now]  [Remind Later]  [Skip]    │
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│  ⬇️ Downloading Update...                 │
│  ████████████░░░░  75%  (45 MB / 60 MB)  │
└──────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────┐
│  ✅ Update ready. Restart to apply.       │
│  [Restart Now]  [Later]                  │
└──────────────────────────────────────────┘
```

### 6.2 Version Sources

| Component | Update Method | Frequency |
|:----------|:--------------|:----------|
| Electron shell | electron-updater → GitHub Releases | On app start + periodic |
| Docker image | `docker pull` on restart | On app start |
| Course content | Git pull knowledge_base/ | Weekly |
| Veritas-Core | Baked into Docker image | With image update |

### 6.3 Rollback

```
If update fails:
  1. Electron: Keep previous version in `%LOCALAPPDATA%/a3-updater/pending/`
  2. Docker: Keep previous image tag; `docker tag ... :previous`
  3. Data: Never roll back user data (always forward-compatible)
```

---

## 7. User Data Persistence

### 7.1 Data Map

| Data | Location | Container Path | Backup |
|:-----|:---------|:---------------|:-------|
| SQLite DB | `%APPDATA%/A3/data/a3.db` | `/app/storage/a3.db` | Daily auto |
| Student profiles | SQLite → student_profiles table | Same | With DB |
| Learning records | SQLite → learning_records table | Same | With DB |
| Generated resources | SQLite → resources table | Same | With DB |
| Chat threads | SQLite → chat_threads/messages | Same | With DB |
| User settings | `%APPDATA%/A3/config/settings.json` | Not containerized | Manual |
| Course KB | `%APPDATA%/A3/knowledge_base/` | `/app/knowledge_base` (ro) | Git |

### 7.2 Backup Strategy

```
Automatic (daily, on app close):
  %APPDATA%/A3/backups/
  ├── a3-2026-07-17.db
  ├── a3-2026-07-16.db
  └── ... (keeps last 7)

Manual (user triggered):
  File → Export Data → Choose location → .zip with all data

Restore:
  File → Import Data → Select backup → Replace current data
```

### 7.3 Data Portability

```
Export format: A3-Export-YYYY-MM-DD.zip
  ├── a3.db               # Full SQLite database
  ├── settings.json        # User preferences
  └── manifest.json        # Version, timestamp, checksum

Cross-platform:
  Windows → macOS → Linux: compatible (SQLite + JSON)
```

---

## 8. Offline Mode

### 8.1 Capability Matrix

| Feature | Online | Offline |
|:--------|:------:|:-------:|
| Rule-based resource generation | ✅ | ✅ |
| TutorAgent (rule fallback) | ✅ | ✅ |
| EvaluationAgent | ✅ | ✅ |
| ProfileAgent | ✅ | ✅ |
| PlannerAgent | ✅ | ✅ |
| Quiz generation | ✅ | ✅ |
| Progress tracking | ✅ | ✅ |
| Chat history | ✅ | ✅ |
| LLM-enriched generation | ✅ | ❌ (needs API) |
| Image generation (API) | ✅ | ❌ (SVG placeholder works) |
| Course KB updates | ✅ | ❌ (static snapshot) |
| Docker image updates | ✅ | ❌ |

### 8.2 Offline Detection

```javascript
// Electron detects network status
window.addEventListener('online', () => {
  trayMenu.updateStatus('online');
  // Optionally enable LLM features
});

window.addEventListener('offline', () => {
  trayMenu.updateStatus('offline');
  // Show "Offline Mode" banner in dashboard
  mainWindow.webContents.send('network:offline');
});
```

### 8.3 Graceful Degradation

```
Network lost:
  1. Show "Offline Mode" toast notification
  2. Gray out LLM-dependent buttons (with tooltip: "Requires internet")
  3. All rule-based features continue working
  4. Queue API-dependent requests for when back online

Network restored:
  1. Show "Back Online" toast
  2. Re-enable LLM features
  3. Process queued requests
```

---

## 9. Security Considerations

### 9.1 Threat Model

| Threat | Risk | Mitigation |
|:-------|:-----|:-----------|
| Malicious course content | Medium | KB is read-only bind mount; validate on import |
| Container escape | Low | Docker default seccomp/AppArmor; non-root user in container |
| API key exposure | High | Stored in host env, never in image; encrypted at rest (DPAPI on Windows) |
| SQLite injection | Low | Parameterized queries in data layer |
| Supply chain (Docker image) | Medium | Image signing (Docker Content Trust); build from verified Dockerfile |
| Local file access | Low | Electron `contextIsolation: true`, `nodeIntegration: false` |
| Prompt injection in chat | Medium | Existing SecurityFilter in validator.py |
| Data theft (lost laptop) | Medium | Optional: encrypt SQLite with SQLCipher |

### 9.2 API Key Storage

```
Windows:
  Credential Manager (DPAPI encrypted)
  → electron-store with safeStorage

macOS:
  Keychain Access
  → electron-store with safeStorage

Linux:
  libsecret (gnome-keyring / kwallet)
  → electron-store with safeStorage

Never:
  ❌ Hardcode in source
  ❌ Store in plaintext .env
  ❌ Include in Docker image
```

### 9.3 Docker Security

```yaml
# docker-compose.desktop.yml — Security hardening
services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true              # Immutable filesystem
    tmpfs:
      - /tmp                      # Writable temp only
    volumes:
      - a3_data:/app/storage:rw   # Only data dir writable
      - a3_kb:/app/knowledge_base:ro
    cap_drop:
      - ALL                       # Drop all capabilities
    cap_add:
      - NET_BIND_SERVICE          # Only need to bind port
```

---

## 10. Implementation Plan

### Phase 11.1 — Electron Shell (3-4 days)
```
desktop/
├── package.json              # Electron + dependencies
├── main.js                   # Main process: window, tray, container mgr
├── preload.js                # Secure IPC bridge
├── renderer/
│   ├── loading.html          # Startup loading screen
│   └── loading.js
├── assets/
│   ├── icon.ico              # Windows icon
│   ├── icon.icns             # macOS icon
│   └── icon.png              # Linux icon
├── docker-compose.desktop.yml # Desktop-specific overrides
└── electron-builder.yml      # Build configuration
```

### Phase 11.2 — Container Manager (1-2 days)
- Start/stop/restart Docker containers
- Health check loop
- Pull updates
- Error recovery (auto-restart)

### Phase 11.3 — Onboarding + Settings (1-2 days)
- First-launch wizard
- Profile creation
- Settings page (API keys, tier, auto-start)

### Phase 11.4 — Auto Update (1 day)
- electron-updater integration
- GitHub Release checking
- Update download + install

### Phase 11.5 — Installer + Packaging (1-2 days)
- electron-builder config
- NSIS installer script (Windows)
- DMG config (macOS)
- AppImage config (Linux)

### Phase 11.6 — Testing + Polish (2 days)
- Windows 10/11 test
- macOS test
- Docker Desktop prerequisite handling
- Offline mode verification
- Data backup/restore test

---

## 11. Constraints Compliance

| Constraint | Compliance |
|:-----------|:-----------|
| Zero Veritas-Core modifications | ✅ VC runs unchanged in Docker container |
| 1130 tests must pass | ✅ No code changes to A3 source |
| Design before implementation | ✅ This document is the design |
| B→C→A workflow | ✅ Only A3 repo modified; VC read-only |
| Existing Docker infrastructure | ✅ Desktop reuses docker-compose, Dockerfile, CI |
