# A3-Agent v7.1.0 — Resume Entry

STAR-format project descriptions for internship applications, in both Chinese and English.

---

## 项目概述 / Project Overview

| Field | Value |
|:------|:------|
| **项目名称** | A3 — 多智能体个性化学习助手 |
| **Project** | A3 — Multi-Agent Personalized Learning Assistant |
| **Role** | 全栈开发者 + 架构设计师 / Full-Stack Developer + Architect |
| **Tech Stack** | Python, FastAPI, Streamlit, PyInstaller, SQLite, keyring, LLM (DeepSeek/OpenAI/Spark) |
| **Duration** | 2026 (4 months, 12+ phases) |
| **Links** | [GitHub](https://github.com/Leisure-Auf1/A3-Multi-Agent-System) · [Live Demo](https://a3-agent.streamlit.app) |

---

## 中文简历版本 / Chinese Resume

### 项目经历

**A3 — 多智能体个性化学习助手**
*全栈开发者 · 独立完成*

- **项目描述**：设计并实现了基于 12 个 AI Agent 协作的个性化学习系统，支持 DeepSeek/OpenAI/Spark 等多种大语言模型，通过 EventBus 实现 Agent 间通信与协作。
- **核心贡献**：
  - 设计 5 层系统架构（展示层 → Agent 管道 → 智能层 → 信任层 → 数据层），实现模块间松耦合
  - 开发 7 标签页 Streamlit 产品 UI，包含学习助手、学生画像、比赛演示、仪表盘等功能
  - 实现可插拔 LLM Provider Factory，支持运行时切换模型供应商，适配 3 种不同 API 协议
  - 集成 OS 级密钥环加密（Windows Credential Manager / Linux Secret Service），确保 API Key 零明文存储
  - 使用 PyInstaller 打包为 Windows .exe 单文件应用（54 MB），实现零依赖双击运行
  - 编写 1154 个自动化测试用例，覆盖率 100%，零失败
- **技术亮点**：
  - 多智能体协作：12 Agent 通过 EventBus 解耦通信，支持异步并发
  - TF-IDF 知识检索：零向量数据库依赖，46K 课程文档 <100ms 检索
  - ReviewGate 3 级质量门：结构 → 内容 → 质量，逐级校验
  - 首次运行引导：API Key 测试 → 加密存储 → 自动配置 LLM

---

### STAR 格式 / STAR Format

**S — Situation（情境）**：
现有的 AI 学习工具多为单一 LLM 调用，无法实现个性化学习路径规划、资源生成、教学辅导和效果评估的完整闭环。同时部署门槛高，需要 Python 环境、API Key 配置等专业知识。

**T — Task（任务）**：
独立设计并开发一个可离线部署的多智能体学习助手，实现从学生画像分析 → 学习计划生成 → 资源创建 → 交互辅导 → 能力评估的完整流程，并支持 Windows/Linux/Docker 多平台一键部署。

**A — Action（行动）**：
1. 架构设计：设计 5 层可测试架构，将 Agent 管道、LLM 集成、安全加密、数据持久化分层解耦
2. Agent 实现：基于 Veritas-Core 框架开发 12 个专业 Agent，通过 EventBus 实现事件驱动协作
3. LLM 集成：实现 Provider Factory 模式，统一 DeepSeek/OpenAI/Spark 的 API 差异
4. 安全设计：集成 keyring 库实现 OS 级密钥存储，自动降级 XOR 加密
5. 测试驱动：编写 1154 个 pytest 测试用例，覆盖所有 Agent、API、数据库迁移场景
6. 分发部署：PyInstaller 打包 Windows .exe（54 MB），Docker 镜像 + Streamlit Cloud 部署

**R — Result（结果）**：
- ✅ 1154/1154 测试通过，零失败
- ✅ Windows .exe 发布（54 MB，零依赖双击运行）
- ✅ Linux tar.gz 发布（76 MB）
- ✅ Docker 镜像 + Streamlit Cloud 在线 Demo
- ✅ 7 标签页产品 UI（学习助手、学习画像、学习空间、AI模型设置、比赛演示、仪表盘、架构概览）
- ✅ 支持 4 种 LLM Provider（含 Mock 离线模式）
- ✅ GitHub Release v7.1.0 已发布

---

## English Resume

### Project Experience

**A3 — Multi-Agent Personalized Learning Assistant**
*Full-Stack Developer · Independent Project*

- **Description**: Designed and implemented a personalized learning system powered by 12 collaborating AI agents, with pluggable LLM provider support (DeepSeek/OpenAI/Spark) and cross-platform distribution.
- **Key Contributions**:
  - Architected a 5-layer system (Presentation → Agent Pipeline → Intelligence → Trust → Data) with clean separation of concerns
  - Built a 7-tab Streamlit product UI: Learning Assistant, Student Profile, Learning Space, AI Settings, Competition Demo, Dashboard, Architecture Overview
  - Implemented pluggable LLM Provider Factory supporting runtime provider switching across 3 API protocols
  - Integrated OS-level keyring encryption (Windows Credential Manager / Linux Secret Service) for zero-plaintext API key storage
  - Packaged as a single Windows .exe (54 MB) using PyInstaller — zero dependencies, double-click to run
  - Wrote 1154 automated tests with 100% pass rate (pytest, async test client, DB migration tests)
- **Technical Highlights**:
  - Multi-agent orchestration: 12 agents communicate via EventBus with async concurrency
  - TF-IDF knowledge retrieval: zero vector DB dependency, <100ms over 46K documents
  - ReviewGate 3-tier quality gate: structure → content → quality validation
  - First-run onboarding: API key testing → encrypted storage → automatic LLM configuration

---

### STAR Format

**S — Situation**:
Existing AI learning tools rely on single LLM calls, lacking the full pipeline of personalized profiling, learning plan generation, resource creation, interactive tutoring, and competency evaluation. Deployment requires Python, API keys, and technical expertise.

**T — Task**:
Independently design and develop a deployable multi-agent learning assistant covering the full pipeline: student profiling → plan generation → resource creation → tutoring → evaluation, with one-click cross-platform deployment (Windows/Linux/Docker).

**A — Action**:
1. **Architecture**: Designed a 5-layer testable architecture decoupling agent pipeline, LLM integration, security, and data persistence
2. **Agents**: Developed 12 specialized agents on Veritas-Core framework with EventBus-driven collaboration
3. **LLM Integration**: Implemented Provider Factory pattern unifying DeepSeek/OpenAI/Spark API differences
4. **Security**: Integrated OS-level keyring with automatic XOR fallback for headless environments
5. **Testing**: Wrote 1154 pytest cases covering all agents, APIs, and database migration scenarios
6. **Distribution**: PyInstaller-packaged Windows .exe (54 MB), Docker image, Streamlit Cloud deployment

**R — Result**:
- ✅ 1154/1154 tests passing, zero failures
- ✅ Windows .exe release (54 MB, double-click, zero deps)
- ✅ Linux tar.gz release (76 MB)
- ✅ Docker image + Streamlit Cloud live demo
- ✅ 7-tab product UI with competition demo and dashboard
- ✅ 4 LLM providers supported (including offline Mock mode)
- ✅ GitHub Release v7.1.0 published

---

## Key Metrics for Resume

| Metric | Value |
|:-------|:------|
| Agents | 12 (Profile, Planner, Resource, Tutor, Evaluation, Reflection + 6 support) |
| Tests | 1154 passed, 0 failed |
| Code Coverage | Full agent/API/DB layer |
| Platforms | Windows (.exe), Linux (tar.gz), Docker, Streamlit Cloud |
| LLM Providers | DeepSeek, OpenAI, Spark, Mock (offline) |
| UI Tabs | 7 (学习助手, 学习画像, 学习空间, AI模型设置, 比赛演示, 仪表盘, 架构概览) |
| Architecture | 5-layer (Presentation → Agent → Intelligence → Trust → Data) |
| Binary Size | 54 MB (Windows), 76 MB (Linux) |

---

## Skills Demonstrated

| Category | Skills |
|:---------|:-------|
| **System Design** | Multi-agent architecture, EventBus pattern, factory pattern, 5-layer separation |
| **Backend** | FastAPI, REST API, SSE streaming, async concurrency, SQLite (WAL mode) |
| **Frontend** | Streamlit, 7-tab product UI, onboarding wizard, settings management |
| **Security** | OS keyring integration, XOR fallback encryption, JWT auth, zero-plaintext keys |
| **Testing** | pytest, TestClient, async testing, 1154 test cases, DB migration testing |
| **DevOps** | PyInstaller, Docker, GitHub Releases, cross-platform distribution |
| **AI/ML** | LLM integration, prompt engineering, TF-IDF retrieval, RAG pipeline |
