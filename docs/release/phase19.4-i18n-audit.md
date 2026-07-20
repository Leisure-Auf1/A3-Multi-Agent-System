# Phase 19.4-A — Internationalization Audit Report

**Date:** 2026-07-20
**Status:** ✅ Read-Only Audit Complete

---

## 1. Executive Summary

A3-Agent 的 Web UI 目前是**混合双语状态**——onboarding 页面和部分 v1 组件使用中文，主 app、settings、auth 使用英文。**不存
在任何 i18n/lang 基础设施**（无 gettext、无 locale 文件、无语言配置）。实现中英文切换需要建立最小 i18n 层。

---

## 2. Current Language Distribution

### 2.1 按文件统计

| 文件 | 中文行 | 英文 st.* 调用 | 主要语言 |
|------|--------|---------------|----------|
| `web/app.py` | 0 | 118 | 🇬🇧 English |
| `web/settings_tab.py` | 25 | 70 | 🇬🇧 English (混少量中文错误提示) |
| `web/onboarding_page.py` | 38 | 31 | 🇨🇳 **Chinese** |
| `web/components/auth.py` | 0 | 15 | 🇬🇧 English |
| `web/components/quiz_panel.py` | 0 | 34 | 🇬🇧 English |
| `web/v1/components.py` | 56 | 51 | 🇨🇳 **Chinese** |
| `web/app_v3.py` | 103 | 72 | 🇨🇳 **Chinese** |
| `web/dashboard/components.py` | 94 | 77 | 🇨🇳 **Chinese** |
| `web/dashboard/data_providers.py` | 26 | — | 🇨🇳 **Chinese** |
| `web/settings_tab.py` | 25 | 70 | 🇬🇧 English |

**总计：** 734 个 `st.*` 调用点，637 处中文字符串

### 2.2 主入口语言分裂

```
web/app.py                → English (tabs, dashboard, learning, errors)
web/onboarding_page.py    → Chinese (welcome, provider setup)
web/components/auth.py    → English (login, register, guest)
web/settings_tab.py       → English (AI Provider Center, 含少量中文 error hints)
```

---

## 3. User-Visible Text Inventory

### 3.1 Auth Gate (`web/components/auth.py`) — 15 处

| 类别 | 文本示例 |
|------|---------|
| 页头 | `A3 AI Learning Assistant` |
| Tab 标签 | `🔑 Login`, `📝 Register`, `👤 Guest` |
| 输入字段 | `Email`, `Password`, `Display Name`, `Your Name (optional)` |
| 按钮 | `Login`, `Create Account`, `Continue as Guest` |
| 错误 | `Login failed: ...`, `Registration failed: ...` |
| 登出 | `🚪 Logout` |

### 3.2 Onboarding (`web/onboarding_page.py`) — 31 处 (中文)

| 类别 | 文本示例 |
|------|---------|
| Hero | `A3 智能学习伙伴` / `9 个 AI 智能体协同 · 个性化学习路径` |
| Feature cards | `多智能体协同`, `个性化学习画像` |
| 按钮 | `🚀 开始配置`, `🎭 先体验 Demo` |
| 设置步骤 | `⚙️ 配置 AI 模型`, `🤖 选择提供商`, `🧩 模型版本`, `🔑 API Key` |
| 状态 | `连接成功！延迟: Xs`, `Demo 模式不需要 API Key`, `正在测试连接...` |
| 按钮 | `🔍 测试连接`, `💾 保存并开始使用`, `🎭 进入 Demo`, `← 返回` |

### 3.3 Main App (`web/app.py`) — 118 处 (英文为主)

| 类别 | 文本示例 |
|------|---------|
| Sidebar tabs | `🏠 Dashboard`, `🎓 Learning`, `📜 History`, `📂 Workspace`, `👤 Profile`, `⚙️ Settings` |
| Sidebar 状态 | `🤖 **Deepseek**`, `🎭 **Demo Mode**`, `No LLM configured` |
| Dashboard | `Your AI-powered learning command center.`, `Demo Mode`, `AI Mode`, `AI Memory`, `Try These`, `Custom Goal` |
| Learning | `🎓 Learning Pipeline`, `Learning Goal`, `🚀 Run Pipeline`, `Pipeline complete`, `📊 Pipeline Results`, `AI Engine Details`, `AI Execution Card` |
| Fallback welcome | `Welcome to A3 AI Learning Assistant`, `Get Started`, `Try Demo` |
| 错误处理 (en) | `Session expired. Please log in again.`, `Usage limit reached`, `Invalid input`, `Server error`, `Retry` |
| Demo suggestions | `🐍 Learn Python basics`, `🤖 Understand machine learning`, `📊 Master data structures` |
| Memory | `🧠 AI Memory`, `Mastered Concepts`, `Weak Areas`, `Sessions`, `Interactions`, `Focus areas` |
| Pipeline agents | `Analyzing your learning profile`, `Building learning path`, `Generating materials`, `Finding resources`, `Quality review`, `Reflecting on plan`, `Saving to memory` |

### 3.4 Settings (`web/settings_tab.py`) — 70 处 (英文为主)

| 类别 | 文本示例 |
|------|---------|
| Header | `⚙️ AI Provider Center` |
| Subtitle | `Configure your AI engine` |
| Sections | `🚀 Production Models`, `🎭 Demo & Offline Models`, `⚡ Active Provider Configuration` |
| Labels | `Select AI Provider`, `Model`, `API Key`, `Test Connection`, `Save Configuration`, `Configuration Details` |
| Status | `Connected!`, `Failed`, `Connection verified`, `Saved`, `Active` |
| Warnings | `🔔 No AI provider configured — running in Demo mode.` |
| Error hints (中) | `API Key 无效`, `请检查 API Key 是否正确`, `请检查网络连接` (mixed Chinese) |

### 3.5 Dashboard Components (`web/dashboard/components.py`) — 77 处 (中文为主)

| 类别 | 文本示例 |
|------|---------|
| Hero | `学生画像`, `学习进度`, `知识图谱` |
| 数据标签 | `知识掌握度`, `学习时长`, `互动次数` |

---

## 4. API Endpoint Page Text (`web/v1/components.py`) — 51 处

Contains Chinese text for API documentation page: `文本生成`, `图片生成`, `工作流`, `端点`, `请求体`, `响应` 等。

---

## 5. Settings / Config Storage

### 当前配置存储

```python
# src/config/llm_config.py → JSON file
LLMConfig:
  provider: str        # "deepseek" | "openai" | "mock" | ...
  model: str           # "deepseek-chat" | ...
  api_key: str         # masked
  is_configured: bool  # computed
```

- 存储位置：`config_path` (环境变量 `LLM_CONFIG_PATH` 或默认路径)
- 格式：JSON 单文件
- **没有 `language` / `locale` 字段**
- Streamlit `session_state` 中也没有语言状态

---

## 6. Constraints & Exclusions

### ❌ 不可修改

| 模块 | 原因 |
|------|------|
| `src/core/` | 核心逻辑 |
| `src/agents/` | Agent 实现 |
| `src/workflow/` | 工作流引擎 |
| `src/api/` | API 层 |
| `src/security/` | 安全层 |

### ✅ 可修改

| 模块 | 用途 |
|------|------|
| `web/` (所有 .py) | UI 文本提取 |
| `src/config/` | 添加语言配置到 LLMConfig |
| 新增 `web/i18n/` | locale 文件 |
| `.gitignore` | 如需要 |

---

## 7. Recommended Minimal i18n Implementation

### 方案：轻量 TOML/JSON locale + Streamlit session_state

#### 7.1 新增文件

```
web/i18n/
├── __init__.py          # t(key, lang=None) → str
├── en.toml              # English locale (~150 keys)
├── zh.toml              # Chinese locale (~150 keys)
└── keys.py              # Key constants (TAB_DASHBOARD, BTN_LOGIN, ...)
```

#### 7.2 修改文件（最小集）

| 文件 | 改动 | 行数变化 |
|------|------|----------|
| `web/app.py` | 替换 118 处硬编码文本 → `t("key")` | ~120 行 |
| `web/settings_tab.py` | 替换 70 处 → `t("key")` | ~70 行 |
| `web/onboarding_page.py` | 替换 31 处 → `t("key")` | ~31 行 |
| `web/components/auth.py` | 替换 15 处 → `t("key")` | ~15 行 |
| `src/config/llm_config.py` | 添加 `language: str = "en"` 字段 | ~3 行 |
| **新增** `web/i18n/` | locale 文件 + t() 函数 | ~400 行 |

#### 7.3 总规模

| 维度 | 估算 |
|------|------|
| 新增文件 | 4 个 (~400 行) |
| 修改文件 | 5 个 (~240 行改动) |
| locale keys | ~150 个 |
| 翻译工作量 | ~150 条中英文条目（大部分已有对应文本） |

#### 7.4 实现流程

```
1. 提取所有 st.* 硬编码文本 → en.toml / zh.toml
2. src/config/llm_config.py 添加 language 字段
3. 创建 web/i18n/__init__.py — t() 函数
4. 在 app.py main() 中设置语言:
   cfg = load_llm_config()
   lang = getattr(cfg, 'language', 'en')  # 或从 session_state 读取
   st.session_state.lang = lang
5. 替换所有硬编码文本为 t("key")
6. Settings 页添加语言选择（下拉菜单）
7. 保持 onboarding_page.py 中文为 zh.toml 的默认值
```

#### 7.5 不处理的部分

| 组件 | 原因 |
|------|------|
| `web/legacy/` (app_v3, app_v4, competition_demo) | 旧版，不纳入 |
| `web/v1/` API 文档页 | 技术文档，保持英文 |
| `src/` 中的日志/错误 | 后端文本，不在此阶段 |
| FAQ / docs 引用 | 独立于 UI |

#### 7.6 locale key 命名规范

```
格式: {section}_{element}
示例:
  tab_dashboard       = "🏠 Dashboard" / "🏠 仪表板"
  tab_learning        = "🎓 Learning" / "🎓 学习"
  btn_login           = "Login" / "登录"
  btn_run_pipeline    = "🚀 Run Pipeline" / "🚀 运行管道"
  err_session_expired = "Session expired" / "会话已过期"
  dashboard_subtitle  = "Your AI-powered learning command center."
  settings_header     = "⚙️ AI Provider Center" / "⚙️ AI 提供商中心"
```

---

## 8. Risks & Notes

| 风险 | 缓解 |
|------|------|
| `st.markdown(html_string)` 中内嵌文本 | HTML 中的文本也需要提取，但保持 HTML 结构 |
| emoji + 文本组合 | 保留 emoji 在 key 中，只翻译文本部分 |
| 动态拼接文本 (`f"✅ Connected! ({latency}s)"`) | 使用参数化：`t("connected", latency=1.2)` |
| 已有中文的 pages 翻译方向 | `onboarding_page.py` 的中文 → zh.toml，另需补充对应 en.toml |
| LLMConfig 向后兼容 | 默认 `language="en"`（字段不存在时） |

---

## 9. Conclusion

- **可行性：** ✅ 高 — 纯 UI 层改动，不涉核心模块
- **工作量：** ~400 行新增 + ~240 行修改 = ~640 行
- **风险：** 低 — 只替换文本字符串，逻辑不变
- **建议：** Phase 19.4-B 可以实施最小 i18n 层
