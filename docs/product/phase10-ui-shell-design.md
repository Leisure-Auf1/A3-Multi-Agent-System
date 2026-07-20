# Phase 10.1 — Unified Product UI Shell Design

> **Status**: DESIGN ONLY — 等待 Human Gate 审批  
> **Date**: 2026-07-20  
> **Baseline**: 2375 tests, 0 failures  
> **Phase**: Post-9.6-B audit → Phase 10 planning

---

## 1. Current UI Architecture

### 1.1 入口点矩阵

| 文件 | 行数 | 用途 | 启动方式 |
|------|:---:|------|----------|
| `web/app.py` | 16 | 委托到 app_v4 | `streamlit run app.py` |
| `web/app_v3.py` | 610 | 7-tab Pipeline UI | `make run` |
| `web/app_v4.py` | 83 | Auth + Chat UI | `streamlit run web/app_v4.py` |

### 1.2 app_v3.py — 完整 Pipeline UI

**导入链 (所有 `src/` 直连, 无 API 桥)**:

```
web/app_v3.py
  ├── src.workflow.A3Workflow          ← 直连 Pipeline
  ├── src.core.provider_factory        ← 直连 LLM Provider
  ├── src.config.onboarding            ← 直连 onboarding
  ├── src.config.llm_config            ← 直连 LLM config
  ├── web.settings_tab                 ← 609行 AI模型设置
  ├── web.onboarding_page              ← 354行 首次配置引导
  ├── web.architecture_overview        ← 197行 架构图
  ├── web.demo_dashboard               ← 173行 仪表盘
  ├── web.competition_demo             ← 154行 比赛演示
  ├── web.components.quiz_panel        ← Quiz 面板
  └── web.components.material_panel    ← AI 教材面板
```

**7个Tab**:

| Tab | 名称 | 功能 | 认证 |
|-----|------|------|:---:|
| 1 | 🏠 学习助手 | Pipeline 执行: 输入目标 → 12 Agent → 结果 | ❌ |
| 2 | 👤 学习画像 | 6维雷达 + 维度详情 + 反思 | ❌ |
| 3 | 📚 学习空间 | 学习路径 + 资源推荐 + 质量评估 + 可信度 | ❌ |
| 4 | ⚙️ AI模型设置 | Provider/Model/Key 配置 | ❌ |
| 5 | 🏆 比赛演示 | One-click 竞赛演示 | ❌ |
| 6 | 🎯 仪表盘 | Agent timeline + 评估分数 | ❌ |
| 7 | 🏗️ 架构概览 | 5-layer architecture diagram | ❌ |

**关键常量**:
- `student_id = "app_v3_user"` (硬编码, 无用户隔离) — Line 138
- `session_id = "app_v3_demo"` (硬编码) — Line 378

### 1.3 app_v4.py — Auth + Chat UI

**导入链 (零 `src/` 直连, 全 API 桥)**:

```
web/app_v4.py
  ├── web.utils.api.A3APIClient        ← urllib → FastAPI:8000
  ├── web.components.auth              ← 登录/注册/Guest 表单
  └── web.components.chat              ← Chat sidebar + main
```

**功能**:
- ✅ Auth gate (Login / Register / Guest)
- ✅ Sidebar (user info + thread list + logout)
- ✅ Chat UI (threads + messages)
- ❌ 无 Pipeline
- ❌ 无 Profile
- ❌ 无 Learning Space
- ❌ 无 Settings
- ❌ 无 Dashboard

### 1.4 web/utils/api.py — REST API Client

**特点**: 零 `src/` 导入，stdlib `urllib.request` 通信  
**覆盖端点**:

| 模块 | 方法 |
|------|------|
| Auth | register, login, guest, logout, me |
| Chat | create_thread, get_threads, get_messages, send_message, rename_thread |
| Profile | get_profile, assess_profile |
| Learning | get_learning_stats, get_learning_history |
| Resources | generate_resource |
| Evaluation | generate_quiz, score_quiz, get_evaluation_results |

**缺失**:
- ❌ 无 `create_learning_plan()` — v2 `/api/v2/learning/plan`
- ❌ 无 User management 端点 (v2 `/api/v2/users/*`)
- ❌ 无 Settings 端点 (v2 `/api/v2/settings/*`)
- ❌ 无 Usage 查询 (v2 `/api/v2/usage`)

---

## 2. 核心问题

### P0 🔴 — UI 功能分裂

```
app_v3:  [Pipeline ✅] [Profile ✅] [Learning ✅] [Settings ✅] [Auth ❌]
app_v4:  [Auth ✅]     [Chat ✅]    [Pipeline ❌] [Profile ❌]  [Settings ❌]
```

**没有一个入口同时拥有认证 + 完整学习流水线**。

### P0 🔴 — 用户流程断裂

用户期望的流程:
```
注册 → 配置 API Key → 输入学习目标 → Pipeline → 查看结果 → 下载产出
```

实际:
- app_v4: 注册 → Chat (停)  
- app_v3: 输入目标 → Pipeline → 结果 (无用户身份)

### P1 🟡 — 硬编码用户隔离

`app_v3.py` 使用 `student_id="app_v3_user"` 和 `session_id="app_v3_demo"` 硬编码。所有用户共享同一身份。Phase 9.5-B 的 User/Workspace/Session 层完全未被 UI 使用。

### P1 🟡 — v3 绕过全部安全层

`app_v3` 的调用链:
```
Streamlit UI → A3Workflow.run() → Agent Pipeline
                                    ↓ (绕过)
                                 OrchestratorRuntime ❌
                                 PermissionManager ❌
                                 TokenBudgetManager ❌
                                 AuditLogger ❌
                                 RequestContext ❌
```

### P2 🟢 — 竞赛演示未去耦合

Tab 5 (比赛演示) 和 `competition_demo.py` 仍然为比赛场景设计，包含 `mock` 固定数据和比赛相关语言。

---

## 3. 目标架构

```
web/app.py  ←── 新的统一入口 (替换 app_v3 + app_v4)
│
├── [Auth Gate] ←── 复用 app_v4 的 render_auth_gate
│   ├── Login
│   ├── Register
│   └── Guest
│
├── [Sidebar] ←── 用户信息 + 导航 + Logout
│   ├── User Info (name, role, plan)
│   ├── Navigation tabs
│   │   ├── 🏠 Dashboard (home)
│   │   ├── 💬 Chat
│   │   ├── 👤 Profile
│   │   ├── 📚 Learning Space
│   │   └── ⚙️ Settings
│   └── Logout
│
├── [Main Content Area]
│   ├── Home/Dashboard Tab
│   │   ├── Pipeline Input (复用 app_v3 输入 + provider)
│   │   ├── Pipeline Execution (通过 API → OrchestratorRuntime)
│   │   ├── Results Summary
│   │   └── Quick Stats
│   │
│   ├── Chat Tab
│   │   └── 复用 app_v4 chat components
│   │
│   ├── Profile Tab
│   │   └── 复用 app_v3 profile rendering (API 驱动)
│   │
│   ├── Learning Space Tab
│   │   ├── 复用 app_v3 学习路径 + 资源 + 评估
│   │   └── Teaching Material Panel
│   │
│   └── Settings Tab
│       └── 复用 web/settings_tab.py (LLM config)
│
└── [API Client] ←── A3APIClient (已有)
    └── 扩展: 添加缺失端点 (plan, users, usage, settings)
```

### 3.1 文件结构

```
web/
  app.py                    ← 统一入口 (替换 app_v3 + app_v4)
  
  components/
    auth.py                 ← 已有 (Login/Register/Guest)
    chat.py                 ← 已有 (Thread list + message UI)
    pipeline.py             ← 新建: Pipeline 输入+执行+结果显示
    profile.py              ← 新建: 学习画像渲染
    learning_space.py       ← 新建: 学习路径+资源+评估
    dashboard.py            ← 新建: 首页仪表盘
    quiz_panel.py           ← 已有
    material_panel.py       ← 已有
  
  services/                 ← 新建: 服务层
    api_client.py           ← 搬迁: web/utils/api.py
    auth_service.py         ← 新建: 认证流封装
    pipeline_service.py     ← 新建: Pipeline API 封装
  
  settings_tab.py           ← 已有
  onboarding_page.py        ← 已有
  
  legacy/                   ← 保留: 向后兼容
    app_v3.py               ← 原样保留
    app_v4.py               ← 原样保留
    competition_demo.py     ← 原样保留
    architecture_overview.py← 原样保留
```

### 3.2 依赖方向 (严格约束)

```
web/app.py
    │
    ├── web/services/api_client.py    ← urllib → FastAPI:8000
    │       ↓
    │   REST API (/api/v2/*)
    │       ↓
    │   src/api/v2/* 路由
    │       ↓
    │   Auth → RequestContext → OrchestratorRuntime → Agent Pipeline
    │
    └── web/components/*              ← Streamlit render only
    
❌ 禁止: web/ → src/ 直连 (绕过 API)
❌ 禁止: web/ → src/orchestration/ 直连
❌ 禁止: web/ → src/workflow/ 直连
```

---

## 4. 认证流设计

### 4.1 认证门控 (复用 app_v4)

```python
# web/app.py
def main():
    api = A3APIClient()
    
    # Gate 1: Authentication
    if not render_auth_gate(api):  # ← 复用已有组件
        st.stop()
    
    # Gate 2: Onboarding (首次配置)
    if not is_configured(api):
        render_onboarding_page(api)
        return
    
    # Authenticated + Configured → Render main UI
    render_main_ui(api)
```

### 4.2 RequestContext 注入

所有 API 调用自动携带 `Authorization: Bearer <token>`:

```
Streamlit UI
    │
    │  api.send_message(msg, thread_id)
    ▼
A3APIClient._request("POST", "/api/v2/chat/message", ...)
    │  Header: Authorization: Bearer <token>
    ▼
FastAPI:8000
    │  Depends(require_auth) → AuthUser
    │  Depends(security_middleware) → RequestContext
    ▼
Route Handler → OrchestratorRuntime.execute()
```

### 4.3 Session State 最小集

```python
st.session_state = {
    "token": str,           # Bearer token
    "user_id": str,         # e.g. "usr_abc123"
    "display_name": str,    # e.g. "Alice"
    "role": str,            # free/student/pro
    "plan": str,            # free/student/pro
    "api": A3APIClient,     # Cached client
}
```

---

## 5. API 集成映射

### 5.1 已有 → 直接使用

| UI Component | A3APIClient method | API Endpoint | Auth |
|-------------|-------------------|-------------|:---:|
| Auth Gate | `login/register/guest` | `/api/v2/auth/*` | ✅ |
| Logout | `logout` | `/api/v2/auth/logout` | ✅ |
| Chat Sidebar | `get_threads/create_thread` | `/api/v2/chat/threads` | ✅ |
| Chat Main | `get_messages/send_message` | `/api/v2/chat/threads/{id}/messages` | ✅ |
| Profile | `get_profile/assess_profile` | `/api/v2/profile` | ✅ |

### 5.2 需添加到 A3APIClient

| 方法 | 端点 | 用途 |
|------|------|------|
| `create_learning_plan(user_goal, profile)` | `POST /api/v2/learning/plan` | Pipeline入口 |
| `get_usage()` | `GET /api/v2/usage` | 用户用量 |
| `get_llm_config()` | `GET /api/v2/settings/llm` | LLM设置 |
| `save_llm_config(cfg)` | `POST /api/v2/settings/llm` | LLM设置 |
| `create_user(...)` | `POST /api/v2/users` | 用户管理 |
| `get_full_profile(user_id)` | `GET /api/v2/profile/{uid}` | 完整画像 |
| `get_workspace_info()` | (需新增端点) | 工作空间 |

### 5.3 需新增 API 端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `/api/v2/workspace/info` | GET | 当前用户workspace信息 |
| `/api/v2/pipeline/run` | POST | 触发Agent Pipeline (通过Orchestrator) |

---

## 6. 组件所有权

### 6.1 保留 (原样搬迁)

| 来源 | 组件 | 新位置 |
|------|------|--------|
| `web/components/auth.py` | `render_auth_gate`, `render_logout` | `web/components/auth.py` |
| `web/components/chat.py` | `render_chat_sidebar`, `render_chat_main` | `web/components/chat.py` |
| `web/settings_tab.py` | `render_settings_tab` | `web/settings_tab.py` |
| `web/onboarding_page.py` | `render_onboarding_page` | `web/onboarding_page.py` |
| `web/components/quiz_panel.py` | Quiz rendering | `web/components/quiz_panel.py` |
| `web/components/material_panel.py` | Material rendering | `web/components/material_panel.py` |

### 6.2 重构 (从 app_v3 提取)

| 来源 | 函数 | 新组件 |
|------|------|--------|
| L275-433 | Tab1 学习助手 | `web/components/pipeline.py` → `render_pipeline_input()` + `render_pipeline_results()` |
| L440-502 | Tab2 学习画像 | `web/components/profile.py` → `render_learning_profile()` |
| L508-573 | Tab3 学习空间 | `web/components/learning_space.py` → `render_learning_space()` |
| L217-235 | `_render_timeline()` | → `web/components/dashboard.py` |
| L238-269 | `_render_trust_panel()` | → `web/components/dashboard.py` |
| L156-166 | `_radar_values()` | → 移到 service 层 |
| L168-175 | `_get_profile_dims()` | → 移到 service 层 |

### 6.3 移除/降级

| 组件 | 处理 |
|------|------|
| `web/competition_demo.py` → Tab5 | → `web/legacy/competition_demo.py` |
| `web/architecture_overview.py` → Tab7 | → `web/legacy/architecture_overview.py` |
| Tab6 仪表盘 (`demo_dashboard`) | → 合并到 Home Dashboard |

### 6.4 新增

| 组件 | 用途 |
|------|------|
| `web/components/pipeline.py` | Pipeline 输入+执行+结果显示 |
| `web/services/pipeline_service.py` | Pipeline API 封装 (调用 learning/plan + profile/assess) |
| `web/services/auth_service.py` | 认证流封装 (token refresh, guest upgrade) |

---

## 7. 迁移计划

### Step 1: 准备 API Client 扩展

- 向 `web/utils/api.py` 添加缺失方法: `create_learning_plan`, `get_usage`, `get_llm_config`, `save_llm_config`
- 添加新 API 端点 (若需): `GET /api/v2/workspace/info`, `POST /api/v2/pipeline/run`
- 测试: 现有 `test_streamlit_ui.py` 必须通过

### Step 2: 提取 v3 Pipeline 组件

- 从 `web/app_v3.py` 提取 Tab1/Tab2/Tab3 到独立组件
- 所有 `src/` 直连改为 API 调用 (通过 A3APIClient)
- Pipeline 执行通过 `POST /api/v2/learning/plan` → OrchestratorRuntime
- 测试: 新组件单元测试

### Step 3: 创建统一入口 `web/app.py`

- Auth gate (复用 v4)
- Sidebar navigation (5 tabs)
- 集成 Step 2 提取的组件
- Session state 管理 user_id/token/role

### Step 4: 向后兼容

- `web/app_v3.py` → `web/legacy/app_v3.py` (原样保留)
- `web/app_v4.py` → `web/legacy/app_v4.py` (原样保留)
- `web/app.py` → 新统一入口
- `make run` → 指向新 `web/app.py`
- 旧入口通过 `streamlit run web/legacy/app_v3.py` 仍可访问

### Step 5: 验证

- 全量回归: `make test` (期望 ≥2375)
- 手动 E2E: 注册 → 配置 → Pipeline → 查看结果
- API 响应验证: `curl` 每个端点

---

## 8. 风险

| 风险 | 概率 | 影响 | 缓解 |
|------|:---:|:---:|------|
| `settings_tab.py` 重度依赖 `src/` 直连，难以通过 API 调用 | 中 | 高 | Phase 10.1 保持 `settings_tab.py` 通过 `src/` 直连（设置类操作与 auth 隔离较低） |
| Pipeline 执行时间 >30s，API 超时 | 中 | 中 | 使用异步任务 + 轮询; Phase 10.1 先用同步 |
| app_v3 大量内联 CSS/HTML 重构时引入渲染差异 | 高 | 低 | 逐Tab对比截图 |
| `competition_demo.py` 移除影响现有用户 | 低 | 低 | 保留在 legacy/ 目录 |

---

## 9. 测试策略

### 9.1 单元测试 (新增)

- `test_pipeline_component.py`: Pipeline 输入组件渲染 + 状态管理
- `test_profile_component.py`: 学习画像组件
- `test_learning_space_component.py`: 学习空间组件
- `test_api_client_extended.py`: 新增 API 客户端方法

### 9.2 集成测试

- `test_unified_ui_flow.py`: 模拟认证 → Pipeline → 结果完整流程
- `test_api_auth_flow.py`: FastAPI TestClient end-to-end auth

### 9.3 回归测试

- 现有 77 个测试文件, 2375 tests 必须保持 0 failure
- `test_streamlit_ui.py`: API client 测试必须通过
- `test_phase9_product_api.py`: API 端点测试必须通过

---

## 10. 输出检查清单

- [ ] `web/app.py` — 统一产品入口
- [ ] `web/components/pipeline.py` — Pipeline 组件
- [ ] `web/components/profile.py` — 学习画像组件  
- [ ] `web/components/learning_space.py` — 学习空间组件
- [ ] `web/components/dashboard.py` — 仪表盘组件
- [ ] `web/services/pipeline_service.py` — Pipeline API 封装
- [ ] `web/utils/api.py` — 扩展 API 方法
- [ ] `web/legacy/` — app_v3, app_v4 保留
- [ ] Tests ≥ 2440+
- [ ] 0 regression

---

## 11. 架构合规核查

| 规则 | 状态 |
|------|:---:|
| 不绕过 OrchestratorRuntime | ✅ Pipeline 通过 API → Orbit → Agent |
| 不绕过 Auth Layer | ✅ 所有 API 调用 require_auth |
| 不绕过 Permission Layer | ✅ security_middleware → RequestContext |
| 不修改 src/core/ | ✅ Web 层不接触 |
| 不修改 Veritas-Core | ✅ 不涉及 |
| 不删除 app_v3/app_v4 | ✅ 移入 legacy/ |
| 向后兼容 Zero src/ imports (web→API) | ⚠️ settings_tab 例外 |

---

> **审批状态**: ⏳ 等待 Human Gate  
> **预计 Phase 10.1 范围**: ~8 文件, +16 tests, 不修改任何 src/ 或 Veritas-Core
