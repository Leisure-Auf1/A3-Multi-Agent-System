# Veritas_Core — 完整设计文档索引

> **A3 → Veritas_Core 升级重构完整设计**  
> **状态: Architecture Freeze. Move to Implementation Phase.**  
> **设计日期:** 2026-07-13  
> **定位:** Trustworthy Personalized Learning Multi-Agent System

---

## 📁 设计文档清单 (12篇)

### 架构设计 (Phase: Architecture Design)

| # | 文档 | 内容 |
|:--|:-----|:-----|
| 00 | [`资产分析`](00_asset_analysis.md) | A3现有模块四分类评估 (KEEP/REFINE/REBUILD/DROP) |
| 01 | [`总体架构`](01_architecture.md) | 六层架构图、模块职责、7 Phase数据流、Agent协作时序 |
| 02 | [`Agent设计`](02_agent_design.md) | 6 Agent + **Agent+Tool架构** + 7 Generator Tools清单 |
| 03 | [`RAG设计`](03_rag_design.md) | Parser→Chunker→Embedder→ChromaDB→Retriever→ContextBuilder |
| 04 | [`Memory设计`](04_memory_design.md) | 三层记忆 (Conversation/Profile/History) + SQL Schema |
| 05 | [`Trust & 闭环`](05_trust_loop.md) | Trust Layer 4-Gate + 完整学习闭环数据流 + 画像演化 |
| 06 | [`工程化`](06_engineering.md) | 代码目录、Docker Compose、Observability |
| 07 | [`集成方案`](07_integration.md) | 6个ADR、5 Phase路线、P0-P3优先级、风险分析 |
| 08 | [`安全架构`](08_security_architecture.md) | Memory Trust Layer、Agent Permission、Prompt Injection防御 |
| 09 | [`Skill扩展`](09_skill_extension.md) | Skill Lifecycle、Skill Router、MCP Adapter定位 |

### 工程实施 (Phase: Implementation)

| # | 文档 | 内容 |
|:--|:-----|:-----|
| 10 | [`实施计划`](10_implementation_plan.md) | **Architecture Freeze**、Agent Runtime状态机、Human-in-the-loop、双Evaluation、Skill Budget、Security Testing、核心接口定义、最终代码目录、4 Phase MVP路线、A3迁移映射 |
| 11 | [`GitHub README`](11_github_readme.md) | 最终展示用README (面向GitHub/面试/评审) |

---

## 🧭 快速导航

| 问题 | 看这篇 |
|:-----|:-------|
| "Veritas_Core是什么?" | [01_architecture.md](01_architecture.md) → [02_agent_design.md](02_agent_design.md) |
| "架构定稿了吗? 可以开始写代码了吗?" | [10_implementation_plan.md](10_implementation_plan.md) §1 |
| "Agent状态怎么管理?" | [10_implementation_plan.md](10_implementation_plan.md) §3 |
| "安全怎么做?" | [08_security_architecture.md](08_security_architecture.md) |
| "需要人工确认吗?" | [10_implementation_plan.md](10_implementation_plan.md) §4 |
| "怎么评价系统质量?" | [10_implementation_plan.md](10_implementation_plan.md) §5 |
| "Skill/Tool怎么调度?" | [09_skill_extension.md](09_skill_extension.md) + [10_implementation_plan.md](10_implementation_plan.md) §6 |
| "接口长什么样?" | [10_implementation_plan.md](10_implementation_plan.md) §8 |
| "代码放哪?" | [10_implementation_plan.md](10_implementation_plan.md) §9 |
| "先做什么后做什么?" | [10_implementation_plan.md](10_implementation_plan.md) §10 |
| "A3哪些代码能用?" | [00_asset_analysis.md](00_asset_analysis.md) + [10_implementation_plan.md](10_implementation_plan.md) §11 |
| "GitHub上怎么写?" | [11_github_readme.md](11_github_readme.md) |
| "为什么这样设计?" | [07_integration.md](07_integration.md) §1 (6个ADR) |

---

## 📊 核心决策速览

| 决策 | 选择 |
|:-----|:-----|
| Agent数 | 6 Cognitive + 5 Generator Tools |
| RAG | ChromaDB, 课程知识增强 |
| Memory | 3层: Redis / PostgreSQL / ChromaDB |
| Security | Memory Trust + Permission Matrix + Injection Defense + Approval Gate |
| Skill | Lifecycle管理 + Budget限制 + Router调度 |
| Evaluation | 双评估: Learning (学生) + Agent (AI系统) |
| State | Agent状态机: IDLE→REASONING→...→COMPLETED |
| Deploy | `docker compose up` |
| MVP | 4 Phase, 22天 |

---

## 🔄 从A3到Veritas_Core

| 维度 | A3 (v2.8) | Veritas_Core |
|:-----|:----------|:-------------|
| Agent | 12 | 6 (决策) + 5 Tool (执行) |
| 生成 | 规则模板 | RAG增强LLM + Trust Layer |
| 记忆 | JSON文件 | 3层: Redis/PG/ChromaDB |
| 安全 | 无 | Memory Trust + Permission + Injection + Approval |
| 部署 | pip install | Docker Compose |
| 测试 | 241 pass | 300+ 含 security/ |
| 定位 | 竞赛Demo | 可运行、可测试、可展示的工程项目 |
