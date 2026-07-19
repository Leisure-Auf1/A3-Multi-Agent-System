# A3-Agent v7.1.0 — Windows Installation Guide

## Requirements

| Requirement | Minimum | Notes |
|:------------|:--------|:------|
| OS | Windows 10+ (x64) | 64-bit only |
| Browser | Chrome / Edge / Firefox | For the Streamlit UI |
| Disk space | ~300 MB | Extracted bundle |
| Python | **Not required** | Everything is bundled |
| Admin rights | **Not required** | Runs as a normal user |

---

## Quick Start

### 1. Download

Get `A3-Agent-v7.1.0-win64.zip` from [GitHub Releases](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/tag/v7.1.0).

### 2. Verify (optional)

Open **PowerShell**:

```powershell
Get-FileHash -Algorithm SHA256 .\A3-Agent-v7.1.0-win64.zip
```

Expected SHA256:

```
3063ec38f82b84a0a255b319bea444d43f55668da1e032110e49107f199e8bfa
```

### 3. Extract

Right-click the zip → **Extract All...** → choose a destination folder.

Recommended locations:
- `C:\A3-Agent`
- `Desktop\A3-Agent`
- Any folder you have write access to

> **⚠️ Do NOT extract to `C:\Program Files\`.** The application needs write access to its own directory.

After extracting, you should see:

```
A3-Agent.exe      # Main launcher
_internal\        # Bundled Python runtime + dependencies
LICENSE           # MIT License
README.txt        # Quick reference
VERSION           # Version identifier
```

### 4. Launch

**Double-click `A3-Agent.exe`.**

The launcher console window shows:

```
==================================================
  A3-Agent v7.1.0 — Desktop Launcher
  Bundle root : C:\A3-Agent\_internal
  Executable  : C:\A3-Agent\A3-Agent.exe
  Internal    : C:\A3-Agent\_internal\streamlit\static\index.html
  User data   : C:\Users\<You>\AppData\Roaming\A3-Agent
  Integ check : PASS
==================================================
[1/5] Initializing user data...
[2/5] Starting AI Backend (FastAPI)...
[3/5] Waiting for API health check...
[4/5] Starting Learning Interface (Streamlit)...
[5/5] Opening browser → http://127.0.0.1:8501
```

Your browser opens automatically to the A3-Agent interface.

### 5. Verify

Open a browser tab and navigate to:

- `http://127.0.0.1:8000/health` → should show `{"status":"ok"}`
- `http://127.0.0.1:8501` → A3-Agent Streamlit UI

---

## Windows Defender / SmartScreen

Because the `.exe` is not code-signed, Windows may show a warning on first launch:

1. **SmartScreen**: Click **"More info"** → **"Run anyway"**
2. **Windows Defender**: If a "Windows protected your PC" dialog appears, click **"More info"** → **"Run anyway"**

The application:
- Only makes local network connections (`127.0.0.1`)
- Does not modify system files
- Stores all data in your user profile

---

## First Launch Wizard

On first run, you'll see the **Welcome Page**:

| Action | Description |
|:-------|:------------|
| 🎭 **先体验 Demo** | One-click demo pipeline — no API key, no network |
| 🚀 **开始配置** | Set up DeepSeek, OpenAI, or Spark provider |

### Demo Mode (recommended first)

Click "🎭 先体验 Demo" → the 6-agent pipeline runs with mock data. All 7 tabs are functional offline.

### Connect a Real AI Provider

1. Click "🚀 开始配置"
2. Select a provider (e.g., DeepSeek)
3. Enter your API key
4. Click **🔍 测试连接** (Test Connection)
5. Click **💾 保存配置** (Save)
6. Return to the main tab and start learning

API keys are stored securely in **Windows Credential Manager** — not in plaintext files.

---

## Data Locations

| Path | Contents |
|:-----|:---------|
| `%APPDATA%\A3-Agent\config\` | LLM configuration (`llm.json`) |
| `%APPDATA%\A3-Agent\storage\` | Learning database (`a3.db`) |
| `%APPDATA%\A3-Agent\logs\` | Launcher and service logs |

> `%APPDATA%` is typically `C:\Users\<YourName>\AppData\Roaming\`.

### Reset to Factory

Delete the user data directory:

```
C:\Users\<YourName>\AppData\Roaming\A3-Agent\
```

Then restart A3-Agent — it will reinitialize from the bundle seed.

---

## Uninstall

1. Delete the extracted folder (e.g., `C:\A3-Agent`)
2. (Optional) Delete `%APPDATA%\A3-Agent\` to remove all user data

No registry entries. No system modifications. Just delete the folders.

---

## Troubleshooting

| Problem | Solution |
|:--------|:---------|
| Windows Defender blocks launch | Click "More info" → "Run anyway" |
| Console window closes immediately | Check `%APPDATA%\A3-Agent\logs\launcher.log` |
| Port 8501 already in use | Close other A3-Agent windows, or run `netstat -ano \| findstr :8501` then `taskkill /PID <pid> /F` |
| Port 8000 already in use | Same — replace `8501` with `8000` |
| Browser doesn't open | Manually navigate to `http://127.0.0.1:8501` |
| "Internal Server Error" | See [Troubleshooting Guide](TROUBLESHOOTING.md#streamlit-internal-server-error) |
| API key not saving | Ensure Windows Credential Manager service is running |
| UI shows blank white page | Wait 5-10 seconds for Streamlit cold-start, then refresh |

For more detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Next Steps

- [User Guide](USER_GUIDE.md) — Learn how to use the 7-tab interface
- [Troubleshooting](TROUBLESHOOTING.md) — Fix common issues
- GitHub Issues: [Report a bug](https://github.com/Leisure-Auf1/A3-Multi-Agent-System/issues/new)
