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
| Backend | Docker (single container) | Start script runs both uvicorn + streamlit |
| Packaging | electron-builder | Windows .exe, macOS .dmg, Linux .AppImage |
| Updates | electron-updater | Auto-download new releases from GitHub |

### 1.3 Technology Evaluation — Why Electron

| Option | Size | Native Features | Docker Interop | Complexity | Verdict |
|:-------|:----:|:---------------:|:--------------:|:----------:|:-------|
| **Electron** | ~150MB | ✅ tray, menu, notifications | ✅ child_process | Medium | **Selected** |
| PyWebView | ~30MB | ❌ no tray, no notifications | ⚠️ subprocess only | Low | Too limited |
| Tauri | ~10MB | ✅ tray, menu | ❌ Rust-side only | High | No Node.js ecosystem |
| Nativefier | ~100MB | ❌ wrapper only | ❌ none | Very Low | No lifecycle control |

**Decision:** Electron — the only option that provides both native desktop features AND full control over Docker lifecycle via Node.js `child_process`.

### 1.4 Single-Container Architecture

```
Desktop uses ONE container (vs server's two):

Server (docker-compose.yml):       Desktop (docker-compose.desktop.yml):
  api container :8000                 a3-app container
  dashboard container :8501           ├── uvicorn src.api.server:app :8000
  ─ separate for scaling              ├── streamlit run app.py :8501
                                      └── both via scripts/start.sh

Why single container for desktop:
  ✅ Simpler lifecycle (start/stop ONE container)
  ✅ No Docker network needed (both on localhost)
  ✅ Lower resource usage (~300MB vs ~500MB for two)
  ✅ Matches existing start.sh (already runs both)
```

---

## 2. Electron + Docker Integration

### 1.5 docker-compose.desktop.yml

Single-container desktop deployment:

```yaml
# docker-compose.desktop.yml — Desktop single-container deployment
# Bundled with Electron app at: resources/docker-compose.desktop.yml

services:
  a3-app:
    image: leisureauf1/a3-multi-agent-system:${A3_VERSION:-latest}
    container_name: a3-desktop
    ports:
      - "${A3_API_PORT:-18000}:8000"
      - "${A3_UI_PORT:-18501}:8501"
    environment:
      - PYTHONUNBUFFERED=1
      - LLM_PROVIDER=${LLM_PROVIDER:-mock}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - FAL_KEY=${FAL_KEY:-}
      - DEFAULT_USER_TIER=${DEFAULT_USER_TIER:-free}
    volumes:
      - ${A3_DATA_DIR}:/app/storage        # Persistent user data
      - ${A3_KB_DIR:-./knowledge_base}:/app/knowledge_base:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -sf http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 15s
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
```

**Key differences from server `docker-compose.yml`:**
- Single service (not api + dashboard)
- Different default ports (18000/18501) to avoid conflicts
- `${A3_DATA_DIR}` for platform-specific path
- Security hardening (read_only, cap_drop, no-new-privileges)
- Version tag from env var for update control

### 1.6 Platform-Specific Data Paths

| Platform | Data Directory | Env Var |
|:---------|:---------------|:--------|
| Windows | `%APPDATA%/A3/data/` | `A3_DATA_DIR=C:\Users\<user>\AppData\Roaming\A3\data` |
| macOS | `~/Library/Application Support/A3/data/` | `A3_DATA_DIR=/Users/<user>/Library/Application Support/A3/data` |
| Linux | `~/.local/share/A3/data/` | `A3_DATA_DIR=/home/<user>/.local/share/A3/data` |

All platforms: auto-created on first launch. Portable between platforms (SQLite + JSON).

---

## 2. Docker Prerequisites Handling

### 2.1 Docker Detection Flow

```
App launched
     │
     ▼
┌──────────────────────────────────────────┐
│ Check: docker --version                   │
└──────────────┬───────────────────────────┘
               │
     ┌─────────┼─────────┐
     ▼         ▼         ▼
  [Found]   [Not Found]  [Error]
     │         │           │
     ▼         ▼           ▼
  Start     ┌────────────────────────────┐
  container │  Docker Not Found           │
            │                            │
            │  A3 requires Docker to run │
            │  the learning engine.       │
            │                            │
            │  [Download Docker Desktop]  │
            │  [I already have Docker]    │
            │  [Quit]                    │
            └────────────────────────────┘
                 │ user clicks download
                 ▼
            Open: https://docs.docker.com/get-docker/
```

### 2.2 Docker Not Running Recovery

```
Container start fails (docker daemon not running)
     │
     ▼
┌──────────────────────────────────────────┐
│  Docker Engine Not Running                │
│                                          │
│  The Docker engine needs to be started   │
│  before A3 can launch.                   │
│                                          │
│  • Windows: Docker Desktop should start  │
│    automatically. If not, open it from   │
│    the Start Menu.                       │
│  • macOS: Check the Docker icon in the   │
│    menu bar.                             │
│  • Linux: Run `sudo systemctl start      │
│    docker`                               │
│                                          │
│  [Retry]  [Open Docker Desktop]  [Quit]  │
└──────────────────────────────────────────┘
```

### 2.3 Port Conflict Handling

```
Port 18000 or 18501 already in use
     │
     ▼
┌──────────────────────────────────────────┐
│  Port Conflict                           │
│                                          │
│  Port 18000 is already in use.           │
│                                          │
│  A3 can use alternative ports:           │
│  [Use 18001/18502]  [Let me choose]      │
│                                          │
│  (Settings are saved for next launch)    │
└──────────────────────────────────────────┘
```

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

### 3.1 Electron Main Process (Interface Description)

```
Main Process Responsibilities:

1. ContainerManager
   - checkDockerInstalled() → bool
   - startContainer(composeFile) → Promise<void>
   - stopContainer() → Promise<void>
   - getStatus() → 'stopped' | 'starting' | 'running' | 'error'
   - pullImage(version) → Promise<void>
   Implementation: child_process.exec('docker compose ...')

2. WindowManager
   - createMainWindow() → loads localhost:18501
   - showLoadingScreen() → while container starting
   - showErrorScreen(message) → Docker/prereq errors

3. TrayManager
   - createTray() → system tray icon + menu
   - updateStatus(status)
   - showNotification(title, body)

4. UpdateManager
   - checkForUpdates() → GitHub Releases API
   - downloadUpdate(version) → Promise<void>
   - applyUpdate() → restart app
   Implementation: electron-updater
```

### 3.2 IPC Channels (Interface)

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

### 6.1 Unified Update Model

A3 Desktop has ONE release artifact: the GitHub Release. When a new release is published:

```
GitHub Release v1.1.0
  ├── A3-Setup-1.1.0.exe        (Electron shell, ~80 MB)
  ├── A3-1.1.0.dmg              (macOS)
  ├── A3-1.1.0.AppImage         (Linux)
  └── Release notes → changelog
```

**Key principle:** The Docker image tag is EMBEDDED in the Electron release. When the Electron shell updates, it knows which Docker image version to use.

### 6.2 Version Compatibility

```
Electron v1.1.0  ──requires──▶  Docker image v1.1.0
Electron v1.0.0  ──requires──▶  Docker image v1.0.0

Defined in: electron-builder.yml → extraMetadata.version
Docker tag:   A3_VERSION env var in docker-compose.desktop.yml
```

### 6.3 Update Flow

```
App starts
    │
    ▼
Check GitHub Releases API for latest version
    │
    ├─ Same version → skip
    │
    ▼ New version available
┌──────────────────────────────────────────┐
│  🔄 Update Available: v1.1.0             │
│  [Update Now]  [Remind Later]            │
└──────────────────────────────────────────┘
    │
    ▼ Update Now
1. Stop Docker container
2. Download new Electron .exe (electron-updater)
3. Pull new Docker image: docker pull leisureauf1/a3:1.1.0
4. Install Electron update (auto-replace on restart)
5. Restart app
    │
    ▼ App restarts
6. Start Docker container with A3_VERSION=1.1.0
7. Health check → Dashboard ready
```

### 6.4 Rollback

```
If v1.1.0 fails (container won't start, health check fails):
  1. Electron: electron-updater keeps v1.0.0 backup → auto-restore
  2. Docker: docker tag leisureauf1/a3:1.0.0 leisureauf1/a3:latest
  3. User data: NEVER rolled back (forward-compatible SQLite schema)
  4. Notification: "Update failed. Reverted to v1.0.0."
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
