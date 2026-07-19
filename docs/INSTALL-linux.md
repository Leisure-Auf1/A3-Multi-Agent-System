# A3-Agent v7.1.0 — Linux Installation Guide

## Requirements

| Requirement | Minimum | Notes |
|:------------|:--------|:------|
| Architecture | x86_64 (amd64) | PyInstaller binary is x86-64 only |
| Kernel | Linux 3.2+ | Standard for any modern distro |
| Browser | Chrome / Firefox / Edge | For the Streamlit UI |
| Disk space | ~600 MB | Bundle includes Python runtime + all deps |
| Python | **Not required** | Bundled in the `_internal/` directory |

---

## Quick Start — Pre-built Bundle (Recommended)

### 1. Download

Get the latest release from GitHub:

```bash
curl -LO https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/download/v7.1.0/A3-Agent-v7.1.0-linux-x64.tar.gz
curl -LO https://github.com/Leisure-Auf1/A3-Multi-Agent-System/releases/download/v7.1.0/A3-Agent-v7.1.0-linux-x64.sha256
```

### 2. Verify

```bash
sha256sum -c A3-Agent-v7.1.0-linux-x64.sha256
# Expected: A3-Agent-v7.1.0-linux-x64.tar.gz: OK
```

### 3. Extract

```bash
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64
```

You should see:

```
A3-Agent          # Main launcher binary
_internal/        # Bundled Python runtime + dependencies
LICENSE           # MIT License
README.txt        # Quick reference
VERSION           # Version identifier
```

### 4. Launch

```bash
./A3-Agent
```

The launcher goes through 5 stages:

```
[1/5] Initializing user data...
[2/5] Starting AI Backend (FastAPI)...
[3/5] Waiting for API health check...
[4/5] Starting Learning Interface (Streamlit)...
[5/5] Opening browser → http://127.0.0.1:8501
```

### 5. Verify

```bash
# FastAPI health check
curl -s http://127.0.0.1:8000/health
# → {"status":"ok"}

# Streamlit UI
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8501
# → 200
```

---

## Distro-Specific Notes

### Arch Linux

No dependencies needed — the bundle is self-contained:

```bash
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64
./A3-Agent
```

If Streamlit doesn't open automatically (some window managers don't support `xdg-open`):

```bash
# Manually open the browser
xdg-open http://127.0.0.1:8501
```

### Ubuntu / Debian

No extra packages needed:

```bash
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64
./A3-Agent
```

If you get "Permission denied":

```bash
chmod +x A3-Agent
./A3-Agent
```

### Fedora / RHEL

```bash
tar xzf A3-Agent-v7.1.0-linux-x64.tar.gz
cd A3-Agent-v7.1.0-linux-x64
./A3-Agent
```

If SELinux blocks execution:

```bash
chcon -t bin_t A3-Agent
./A3-Agent
```

---

## Build from Source

For developers who want to run from source or modify the code:

### 1. Clone

```bash
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
```

### 2. Set up Python environment

```bash
# Arch
sudo pacman -S python python-pip

# Ubuntu
sudo apt install python3 python3-pip python3-venv
```

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run in dev mode

```bash
python -m desktop.launcher
```

### 5. Run tests

```bash
make test
# Expected: 1164 passed
```

### 6. Build a release bundle (optional)

```bash
pip install pyinstaller
bash scripts/build-release.sh
# Output: dist/A3-Agent/
```

---

## Data Locations

All user data is stored under `~/.a3-agent/`:

| Directory | Purpose |
|:----------|:--------|
| `~/.a3-agent/config/` | LLM provider configuration (`llm.json`) |
| `~/.a3-agent/storage/` | Learning database (`a3.db`) |
| `~/.a3-agent/logs/` | Launcher and subprocess logs |

To reset the app to factory state:

```bash
rm -rf ~/.a3-agent
```

Then restart — the launcher will reinitialize the database from the bundle seed.

---

## Uninstall

```bash
# 1. Delete the extracted bundle
rm -rf ~/A3-Agent-v7.1.0-linux-x64

# 2. (Optional) Remove all user data
rm -rf ~/.a3-agent
```

---

## First Launch

On first run, the launcher seeds a fresh database and opens the browser to the Welcome Page:

1. **Demo Mode** — Click "🎭 先体验 Demo" to explore without an API key
2. **Configure Provider** — Click "🚀 开始配置" to set up DeepSeek, OpenAI, or Spark

API keys are stored in Linux Secret Service (via `keyring`), with automatic XOR fallback if the keyring daemon is unavailable.

---

## Next Steps

- [User Guide](USER_GUIDE.md) — Learn how to use the 7-tab interface
- [Troubleshooting](TROUBLESHOOTING.md) — Fix common startup and runtime issues
- [Architecture Overview](architecture.md) — Understand the 5-layer system design
