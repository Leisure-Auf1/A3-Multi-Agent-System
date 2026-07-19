# A3-Agent v7.1.0 — Windows Release Validation

## Pre-requisites

- [x] Source: `feat/deploy-final` branch, commit `fec0f7e`
- [x] `desktop/build.bat` verified (23 hidden-imports, 10 add-data)
- [x] Linux PyInstaller build validated (FastAPI ✅, Streamlit ✅, 185 MB)
- [ ] Windows 10/11 machine with Python 3.10+ installed

---

## Build

```batch
REM 1. Clone and checkout
git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
cd A3-Multi-Agent-System
git checkout feat/deploy-final

REM 2. Install dependencies
pip install -r requirements.txt
pip install pyinstaller

REM 3. Build
desktop\build.bat
```

**Expected output**: `dist\A3-Agent\A3-Agent.exe` (~200-250 MB)

> **Note**: Windows build will be larger than Linux (185 MB) because:
> - Windows bundles more DLLs
> - Keyring Windows backend (win32ctypes, pywin32) adds ~5-10 MB
> - Streamlit frontend assets are larger on Windows

---

## Clean-Machine E2E

Test on a Windows machine with **no Python installed**:

| # | Check | Expected | Result |
|:--|:------|:---------|:-------|
| 1 | Copy `dist\A3-Agent\` to Desktop | Folder contains `A3-Agent.exe` + `_internal\` | ⬜ |
| 2 | Double-click `A3-Agent.exe` | No error popups, terminal window appears | ⬜ |
| 3 | Terminal shows `[1/5] Initializing...` | 5 stages displayed sequentially | ⬜ |
| 4 | `[3/5] API is healthy ✓` | Within 5 seconds | ⬜ |
| 5 | Browser opens automatically | `http://127.0.0.1:8501` loads | ⬜ |
| 6 | Streamlit UI renders | 7 tabs visible | ⬜ |
| 7 | Click "🏆 Competition Demo" | Page loads with Run button | ⬜ |
| 8 | Click "Run Pipeline" | 6 agents execute, timeline shows | ⬜ |
| 9 | Click "🎯 Dashboard" | KPI cards + agent timeline visible | ⬜ |
| 10 | Click "⚙️ AI Model Settings" | Provider selector works | ⬜ |
| 11 | Close browser, Ctrl+C in terminal | "A3 Agent shut down cleanly" | ⬜ |

---

## Keyring Verification

| # | Check | Expected | Result |
|:--|:------|:---------|:-------|
| 1 | Open "⚙️ AI Model Settings" tab | Provider selector visible | ⬜ |
| 2 | Select DeepSeek, enter fake key `sk-test-verify` | Key input masked | ⬜ |
| 3 | Click "Save Configuration" | "Configuration saved" message | ⬜ |
| 4 | Open Windows Credential Manager | `cmdkey /list` shows `A3-Agent` entry | ⬜ |
| 5 | Check `%APPDATA%\A3-Agent\config\llm.json` | API key field is `keyring://deepseek` (not plaintext) | ⬜ |
| 6 | Restart A3-Agent | Settings page shows "DeepSeek" as configured | ⬜ |

---

## llm.json Verification

| # | Check | Expected | Result |
|:--|:------|:---------|:-------|
| 1 | `%APPDATA%\A3-Agent\config\` exists | Directory created on first run | ⬜ |
| 2 | `llm.json` permissions | Only current user can read (check Properties → Security) | ⬜ |
| 3 | Delete `llm.json` | First-run wizard appears on restart | ⬜ |
| 4 | `%APPDATA%\A3-Agent\logs\` exists | `launcher.log` and `subprocess.log` present | ⬜ |
| 5 | `%APPDATA%\A3-Agent\storage\a3.db` | Seeded from bundle on first run | ⬜ |

---

## Demo Fixtures

| # | Check | Expected | Result |
|:--|:------|:---------|:-------|
| 1 | Competition Demo loads fixtures | `sample_profile.json` data displayed | ⬜ |
| 2 | Dashboard shows trace | 6 agent events with bars | ⬜ |
| 3 | Architecture page renders | 5-layer diagram visible | ⬜ |

---

## Release Packaging

After all checks pass:

```batch
REM Create release zip
mkdir release
xcopy /E /I dist\A3-Agent release\A3-Agent-v7.1.0-win64\
copy LICENSE release\A3-Agent-v7.1.0-win64\
copy README.md release\A3-Agent-v7.1.0-win64\README.txt
echo A3-Agent v7.1.0 > release\A3-Agent-v7.1.0-win64\VERSION

REM Zip it
powershell Compress-Archive -Path release\A3-Agent-v7.1.0-win64 -DestinationPath release\A3-Agent-v7.1.0-win64.zip
```

**Deliverable**: `release/A3-Agent-v7.1.0-win64.zip`

---

## Sign-off

| Role | Date | Signature |
|:-----|:-----|:----------|
| Builder | | |
| Tester (clean machine) | | |
| Release Manager | | |
