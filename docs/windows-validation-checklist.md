# Windows Release Validation Checklist

A3-Agent v7.1.0 — Windows .exe Release Verification

## Pre-requisites

- [ ] Clean Windows environment (VM or physical, no Python installed)
- [ ] A3-Agent.exe downloaded from release
- [ ] Internet connection (for API key testing)
- [ ] Valid API key for at least one provider

---

## Phase 1: Installation

| # | Check | Expected | Actual |
|:--|:------|:---------|:-------|
| 1.1 | Double-click `A3-Agent.exe` | Application window opens | |
| 1.2 | No Python error popups | Clean launch | |
| 1.3 | `%APPDATA%/A3-Agent/` created | Directory exists | |

---

## Phase 2: First Run Wizard

| # | Check | Expected | Actual |
|:--|:------|:---------|:-------|
| 2.1 | Welcome page shown | "A3 智能学习伙伴" + 2 buttons | |
| 2.2 | Click "🎭 先体验 Demo" | Enters main UI (4 tabs) | |
| 2.3 | Close and re-open | Goes directly to main UI (no wizard) | |
| 2.4 | Delete `%APPDATA%/A3-Agent/config/llm.json` | Wizard re-appears on restart | |
| 2.5 | Click "🚀 开始配置" | Shows provider setup page | |

---

## Phase 3: API Configuration

| # | Check | Expected | Actual |
|:--|:------|:---------|:-------|
| 3.1 | Select "DeepSeek" | DeepSeek options shown | |
| 3.2 | Select model "deepseek-chat" | Model selector updates | |
| 3.3 | Enter valid API key | Input masked (••••) | |
| 3.4 | Click "🔍 测试连接" | ✅ Connection OK with latency | |
| 3.5 | Enter INVALID API key | ❌ Error with Chinese explanation | |
| 3.6 | Click "💾 保存并开始使用" | Enters main UI | |
| 3.7 | Check `llm.json` | API key is NOT in plaintext | |

---

## Phase 4: Agent Pipeline

| # | Check | Expected | Actual |
|:--|:------|:---------|:-------|
| 4.1 | Enter learning goal in Tab 1 | Text input works | |
| 4.2 | Click "🚀 开始分析" | Spinner appears, agents execute | |
| 4.3 | Check timeline | 5+ agents with timestamps | |
| 4.4 | Switch to Tab 2 (画像) | Profile data displayed | |
| 4.5 | Switch to Tab 3 (学习空间) | Learning path + resources shown | |
| 4.6 | Switch to Tab 4 (AI模型设置) | Current provider shown, can change | |
| 4.7 | Select "Mock" provider in Tab 4 | Switches to demo mode | |
| 4.8 | Pipeline still works in Mock mode | All agents execute | |

---

## Phase 5: Edge Cases

| # | Check | Expected | Actual |
|:--|:------|:---------|:-------|
| 5.1 | Close app during pipeline run | No crash, clean exit | |
| 5.2 | Invalid JSON in llm.json | App starts, falls back to mock | |
| 5.3 | Missing API key file | Wizard re-appears | |
| 5.4 | Network disconnected (mock mode) | Pipeline still works offline | |

---

## Sign-off

| Role | Name | Date | Signature |
|:-----|:-----|:-----|:----------|
| Tester | | | |
| Reviewer | | | |
