# A3-Agent v7.1.0 — Troubleshooting Guide

This guide covers common startup and runtime issues for the A3-Agent desktop application.

---

## Streamlit Internal Server Error

### Symptom

Browser shows "Internal Server Error" when visiting `http://127.0.0.1:8501`. The launcher console shows no error, but the Streamlit page refuses to load.

### Cause

**The application bundle was moved or deleted while A3-Agent was running.** The PyInstaller onedir bundle relies on files staying at their original location. If the directory is renamed, moved, or cleaned up (e.g., `/tmp` auto-cleanup on Linux), the Streamlit child process loses access to its static assets.

This can happen when:

- You extract the `.tar.gz`/`.zip` to `/tmp`, launch it, then the system cleans `/tmp`
- You move the extracted folder to a new location while the launcher is running
- You delete `_internal/` files manually

### Diagnosis

Check `~/.a3-agent/logs/subprocess.log` (Linux) or `%APPDATA%\A3-Agent\logs\subprocess.log` (Windows). Look for:

```
FileNotFoundError: .../A3-Agent-v7.1.0-linux-x64/_internal/streamlit/static/index.html
SystemExit: ...appears to have been moved or deleted
FileNotFoundError: pathlib.Path.cwd() — No such file or directory
```

### Solution

1. **Stop all A3-Agent processes:**

   **Linux:**
   ```bash
   pkill -f A3-Agent
   ```

   **Windows:**
   ```cmd
   taskkill /F /IM A3-Agent.exe
   ```

2. **Re-extract the bundle** from the original `.tar.gz` or `.zip` to a permanent directory.

3. **Do not put it in `/tmp`** — use a stable location:

   | OS | Recommended path |
   |:---|:-----------------|
   | Linux | `~/Applications/A3-Agent-v7.1.0-linux-x64/` |
   | Windows | `C:\A3-Agent\` or `Desktop\A3-Agent\` |

4. **Start from the new location:**

   ```bash
   cd ~/Applications/A3-Agent-v7.1.0-linux-x64
   ./A3-Agent
   ```

### Prevention

- v7.1.0+ includes bundle integrity validation at startup. The launcher checks that `_internal/streamlit/static/index.html` exists before launching any services.
- If the launcher detects a corrupted bundle, it prints a clear error and exits before starting FastAPI or Streamlit.

---

## Bundle Integrity Failure (New in v7.1.0+)

### Symptom

Launcher exits immediately with:

```
Integ check : FAILED — N missing
  Missing: Streamlit static assets: /path/to/_internal/streamlit/static/index.html

A3-Agent installation appears corrupted.
Please re-download from the official release:
  https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases
```

### Cause

Critical bundle files are missing or the bundle directory was moved. The launcher's integrity check prevents startup when:

- `_internal/streamlit/static/index.html` is missing
- The `A3-Agent` executable itself cannot be found
- The `_internal/` directory was deleted

### Solution

1. Delete the corrupted bundle directory
2. Re-download the `.tar.gz` or `.zip` from the [official release page](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0)
3. Extract to a permanent location and restart

---

## Port Conflicts

### Symptom

Launcher fails with:

```
Port 8501 is not available
ERROR: [Errno 98] address already in use
```

### Cause

Another instance of A3-Agent (or another application) is already using port 8000 or 8501.

### Solution

**Linux — find and kill the process:**

```bash
# Find what's using port 8501
ss -tlnp | grep 8501
# or
lsof -i :8501

# Kill by PID
kill <PID>

# Or kill all A3-Agent processes
pkill -f A3-Agent
```

**Linux — change ports (alternative):**

Set environment variables before launching:

```bash
A3_API_PORT=8001 A3_UI_PORT=8502 ./A3-Agent
```

**Windows:**

```cmd
REM Find the process using port 8501
netstat -ano | findstr :8501

REM Kill by PID (replace <PID> with the actual PID)
taskkill /PID <PID> /F
```

Then restart A3-Agent.

---

## LLM API Key Configuration Failure

### Symptom

In the **AI模型设置** (Settings) tab:

- "Test Connection" button shows no result
- "Save" button remains disabled even after entering an API key
- After saving, the key appears to be lost on next launch

### Cause

Several possible causes:

1. **Keyring service unavailable** — The OS credential store (Windows Credential Manager, Linux Secret Service) is not running, and the XOR fallback is also failing.
2. **Network proxy issues** — The provider API is unreachable behind a proxy/firewall.
3. **Streamlit rerun clears password field** — On older versions, the password input field clears on page refresh.

### Diagnosis

Check the secret manager status:

**Linux:**
```bash
# Check if Secret Service (gnome-keyring) is running
ps aux | grep gnome-keyring

# Check existing config
cat ~/.a3-agent/config/llm.json
```

**Windows:**
```cmd
REM Check Credential Manager service
sc query VaultSvc

REM Check logs
type %APPDATA%\A3-Agent\logs\subprocess.log
```

### Solution

1. **Ensure keyring daemon is running:**

   **Arch Linux (gnome-keyring):**
   ```bash
   # Install if missing
   sudo pacman -S gnome-keyring

   # Start the daemon (add to ~/.xinitrc or autostart)
   gnome-keyring-daemon --start --components=secrets
   ```

   **Ubuntu:**
   ```bash
   sudo apt install gnome-keyring
   gnome-keyring-daemon --start --components=secrets
   ```

2. **Test network connectivity:**
   ```bash
   curl -s https://api.deepseek.com/v1/models \
     -H "Authorization: Bearer $DEEPSEEK_API_KEY"
   ```

3. **If behind a proxy:**
   ```bash
   export https_proxy=http://127.0.0.1:7897
   ./A3-Agent
   ```

4. **Manual config file (last resort):**

   Create/edit `~/.a3-agent/config/llm.json`:
   ```json
   {
     "provider": "deepseek",
     "model": "deepseek-chat",
     "api_key": "your-key-here",
     "base_url": "https://api.deepseek.com"
   }
   ```

---

## Browser Doesn't Open Automatically

### Symptom

Launcher reports `[5/5] Opening browser → http://127.0.0.1:8501` but no browser window appears.

### Cause

The `webbrowser` module couldn't find a default browser, or the `BROWSER_OPEN_DELAY` was too short and the browser opened before Streamlit was ready.

### Solution

1. Wait a few seconds, then manually navigate to `http://127.0.0.1:8501`
2. Refresh the page if you see a connection error

If this happens every time, set your default browser:

**Linux:**
```bash
xdg-settings set default-web-browser firefox.desktop
```

**Windows:**
Set Chrome/Edge as default in Settings → Apps → Default Apps.

---

## Streamlit Shows Blank White Page

### Symptom

Browser opens to `http://127.0.0.1:8501` but the page is completely white with no content.

### Cause

Streamlit is still starting up (cold-start takes ~7 seconds on first run). The `BROWSER_OPEN_DELAY` of 1.5 seconds may be too short for some machines.

### Solution

1. Wait 5-10 seconds
2. Refresh the browser page
3. If still blank, check the logs:

   ```bash
   cat ~/.a3-agent/logs/subprocess.log
   ```

   Look for `Local URL: http://localhost:8501` — when this line appears, Streamlit is ready.

---

## FastAPI Fails to Start

### Symptom

Launcher shows:

```
STARTUP FAILED — Backend did not become healthy
```

### Cause

FastAPI (`uvicorn`) couldn't start. Common causes:
- Port 8000 already in use (see [Port Conflicts](#port-conflicts))
- Missing `src/` directory (incomplete bundle extraction)
- Python dependency conflict (source build only)

### Diagnosis

Check the subprocess log:

```bash
cat ~/.a3-agent/logs/subprocess.log | grep -A 5 "FastAPI started"
```

### Solution

1. Ensure port 8000 is free (see [Port Conflicts](#port-conflicts))
2. Verify bundle extraction is complete — `_internal/src/api/server.py` must exist
3. For source builds, ensure all dependencies are installed:

   ```bash
   pip install -r requirements.txt
   ```

---

## Where to Find Logs

| OS | Path |
|:---|:-----|
| Linux | `~/.a3-agent/logs/launcher.log` |
| Linux | `~/.a3-agent/logs/subprocess.log` |
| Windows | `%APPDATA%\A3-Agent\logs\launcher.log` |
| Windows | `%APPDATA%\A3-Agent\logs\subprocess.log` |

The `launcher.log` contains launcher-level messages (startup stages, health checks).
The `subprocess.log` contains FastAPI and Streamlit output (errors, tracebacks, URLs).

---

## Still Stuck?

1. Check the [GitHub Issues](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues) for existing reports
2. Open a new issue with:
   - Your OS and version
   - The full content of `launcher.log` and `subprocess.log`
   - The exact error message you see
3. Include the output of:
   ```bash
   ls -la _internal/streamlit/static/index.html
   ```
