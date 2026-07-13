"""
A3 v4 — Integration Guide: 集成指南与完整闭环

本文档定义 v4 新增模块与现有 Agent Pipeline 的集成方案，
遵循"保持现有稳定核心，增量式架构扩展"原则。

═══════════════════════════════════════════════════════════
                    完整闭环架构图 (ASCII)
═══════════════════════════════════════════════════════════

                         ┌──────────────────────────┐
                         │    STUDENT INPUT          │
                         │  NL + 对话 + 行为日志       │
                         └────────────┬─────────────┘
                                      │
         ┌────────────────────────────┼────────────────────────────┐
         ▼                            ▼                            ▼
┌─────────────────┐    ┌───────────────────────┐    ┌──────────────────────┐
│ ① ProfileAgent  │    │ ⑧ BehaviorTracker    │    │ ⑩ ProfileUpdateEngine│
│ (升级: 10维提取) │    │ (NEW: 行为事件采集)    │    │ (NEW: 衰减+冲突处理)   │
│ → DynamicStudent │    │ → BehaviorLog[]       │    │ → DynamicStudent      │
│   Profile        │    └───────────┬───────────┘    │   Profile (更新)      │
└────────┬─────────┘               │                 └──────────▲───────────┘
         │                         │                            │
         ▼                         │                            │
┌─────────────────┐               │                            │
│ ② KnowledgeGraph│               │                            │
│   Agent (NEW)   │               │                            │
│ → KnowledgeGap  │               │                            │
│   (缺口诊断)     │               │                            │
└────────┬────────┘               │                            │
         │                         │                            │
         ▼                         │                            │
┌──────────────────────┐          │                            │
│ ③ AgentCouncil (NEW) │          │                            │
│ Propose→Deliberate   │          │                            │
│ → CouncilDecision    │          │                            │
└──────────┬───────────┘          │                            │
           │                      │                            │
           ▼                      │                            │
┌──────────────────────┐          │                            │
│ ④ PlannerAgent        │          │                            │
│ (升级: KG路径搜索)     │          │                            │
│ → LearningPlan       │          │                            │
└──────────┬───────────┘          │                            │
           │                      │                            │
           ▼                      │                            │
┌──────────────────────────┐      │                            │
│ ⑤ MultiModalGenAgent    │      │                            │
│   (NEW: 统一协议+注册表)   │      │                            │
│ → List[LearningResource] │      │                            │
│ → ReviewGate 3层验证      │      │                            │
└──────────┬───────────────┘      │                            │
           │                      │                            │
           ▼                      │                            │
┌─────────────────────────────────┐                            │
│ ⑥ ResourceRecommendationAgent   │                            │
│ (保持: 掌握度+弱点+风格)          │                            │
│ → PersonalizedResourcePlan      │                            │
└──────────┬──────────────────────┘                            │
           │                                                   │
           ▼                                                   │
    ┌──────────────┐                                           │
    │  学生消费资源  │───────────────────────────────────────────┘
    │ (学习→练习→反馈)│
    └──────┬───────┘
           │
           ▼
┌─────────────────────┐
│ ⑦ AgentEvaluator     │
│ (保持: 4维评分)       │
│ → EvaluationResult   │
└─────────┬───────────┘
          │
     score < 0.5?
     ┌────┴────┐
     ▼         ▼
┌──────────┐ ┌──────────────────────────┐
│MetaReflector│ ⑨ StrategyInjector (NEW) │
│(保持: 根因) │→ ImprovementLoop (保持)   │
└──────────┘ │→ AgentExperienceMemory   │
             │   (NEW: 经验存储+注入)     │
             └──────────┬───────────────┘
                        │
                        └────────────────────────────────────────────→ ⑩ 画像更新

所有事件: EventBus (council.* + kg.* 扩展)
可观测: Dashboard V4 → 7 Panel (含 Council Chamber + KnowledgeGraph Viewer)
安全: ReviewGate 3 层 (AST/Pytest/Judge)

═══════════════════════════════════════════════════════════
                  Agent 调用顺序 (UML 时序)
═══════════════════════════════════════════════════════════

Student               ProfileAgent        KnowledgeGraph       AgentCouncil         Planner             MultiModalGen        Evaluator           Evolution
   │                       │                     │                    │                  │                     │                    │                   │
   │── NL Input ──────────►│                     │                    │                  │                     │                    │                   │
   │                       │─ extract() ────────►│                    │                  │                     │                    │                   │
   │                       │◄─ DynamicProfile ───│                    │                  │                     │                    │                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │                       │───── compute_gap() ─►                    │                  │                     │                    │                   │
   │                       │                     │─ KnowledgeGap      │                  │                     │                    │                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │                       │                     │─ gap>3? ──────────►│                  │                     │                    │                   │
   │                       │                     │                    │ open_session()   │                     │                    │                   │
   │                       │                     │                    │ deliberate()      │                     │                    │                   │
   │                       │                     │                    │── CouncilDecision─►                   │                    │                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │                       │                     │                    │                  │ plan(kg=KG)        │                    │                   │
   │                       │                     │                    │                  │── LearningPlan ────►                   │                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │                       │                     │                    │                  │                     │ generate_all()    │                   │
   │                       │                     │                    │                  │                     │── Resources ────►│                   │
   │                       │                     │                    │                  │                     │◄─ ReviewGate OK ──│                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │◄── Learning Resources ────────────────────────────────────────────────────────────────────────────────────────│                    │                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │── 学习+练习 ──────────────────────────────────────────────────────────────────────────────────────────────────►                   │
   │                       │                     │                    │                  │                     │                    │                   │
   │                       │                     │                    │                  │                     │ evaluate()         │                   │
   │                       │                     │                    │                  │                     │── EvalResult ──────►                   │
   │                       │                     │                    │                  │                     │                    │ score<0.5?        │
   │                       │                     │                    │                  │                     │                    │── MetaReflector   │
   │                       │                     │                    │                  │                     │                    │── store()+inject()│
   │                       │                     │                    │                  │                     │                    │                   │
   │                       │◄── Profile Update ────────────────────────────────────────────────────────────────────────────────────────────────│
   │                       │                     │                    │                  │                     │                    │                   │

═══════════════════════════════════════════════════════════
              现有文件修改列表 (最小侵入)
═══════════════════════════════════════════════════════════

保持不变 (零修改):
  src/agents/resource_recommendation_agent.py
  src/agents/resource_generation_agent.py     (被 MultiModalGenAgent 包裹, 不删除)
  src/core/content_agent.py
  src/core/review_gate.py
  src/core/sandbox.py
  src/core/quarantine.py
  src/core/feedback_loop.py
  src/core/user_simulation.py
  src/core/agent_trace.py
  src/core/decision_explainer.py
  src/core/improvement_loop.py
  src/core/meta_reflector.py
  src/core/prompt_injector.py
  src/core/llm_agent_adapter.py
  src/core/provider_factory.py
  src/memory/student_memory.py
  src/memory/experience_memory.py
  src/llm/xunfei_provider.py
  src/llm/mock_provider.py
  src/llm/provider.py

需要修改 (轻量):
  src/core/event_bus.py
    → 新增 CouncilEvent 类型支持 (emit 时 metadata 中包含 council 字段)
    → 无需修改现有方法签名, 仅新增 council 相关事件的 emit 模式

  src/agents/profile_agent.py
    → 接入 DynamicStudentProfile (from src.profile import DynamicStudentProfile)
    → 输出从旧 6-dim dataclass 改为 DynamicStudentProfile
    → 向下兼容: 保留旧 to_dict() 方法

  src/agents/planner_agent.py
    → 新增可选参数: knowledge_graph: Optional[InMemoryKnowledgeGraph]
    → 若有 KG → 使用 compute_optimal_path() 替代规则表
    → 若没有 KG → 回退到现有规则表逻辑 (完全兼容)
    → 新增可选参数: council_decision: Optional[CouncilDecision]

新增文件:
  src/council/__init__.py      (消息协议)
  src/council/council.py       (AgentCouncil 核心类)
  src/knowledge_graph/__init__.py     (KnowledgeNode/Edge/Graph/Gap/PathResult)
  src/knowledge_graph/graph_store.py  (InMemoryKnowledgeGraph + 默认图谱)
  src/profile/__init__.py             (DynamicStudentProfile + ProfileEntry)
  src/multimodal/__init__.py          (LearningResource + ResourceGeneratorRegistry)
  src/evolution/__init__.py           (AgentExperienceRecord + StrategyInjector + AgentExperienceMemory)
  designs/a3_v4_upgrade_design.md     (本文档)

═══════════════════════════════════════════════════════════
              EventBus 扩展方案 (无侵入)
═══════════════════════════════════════════════════════════

现有 AgentEventBus 通过 metadata dict 传递扩展数据, 无需修改核心签名。

新增 Council 相关事件 pattern:

  # 提案提交
  bus.emit("AgentCouncil", "proposal_submitted",
           input_summary="from=ResourceGenAgent type=difficulty_override",
           metadata={"council_event": "proposal_submitted", "proposal": {...}})

  # 评审收集
  bus.emit("AgentCouncil", "review_collected",
           input_summary="reviewer=PlannerAgent vote=approve",
           metadata={"council_event": "review", "review": {...}})

  # 决策完成
  bus.emit("AgentCouncil", "decision_finalized",
           input_summary="consensus=0.80 resolved_by=majority",
           metadata={"council_event": "decision", "decision": {...}})

新增 KG 相关事件 pattern:

  bus.emit("KnowledgeGraph", "gap_computed",
           input_summary="target=transformer",
           metadata={"kg_event": "gap", "gap": {...}})

  bus.emit("KnowledgeGraph", "path_computed",
           input_summary="total_nodes=6 total_min=120",
           metadata={"kg_event": "path", "path": {...}})

Dashboard 通过过滤 metadata 中的特定 key 渲染对应 Panel。

═══════════════════════════════════════════════════════════
              数据流说明 (10 步闭环)
═══════════════════════════════════════════════════════════

Step 1 — 画像构建
  输入: 学生 NL 输入 + 对话历史
  模块: ProfileAgent (from src.profile 接入 DynamicStudentProfile)
  输出: DynamicStudentProfile (10 dim × value+confidence+evidence+update_time)

Step 2 — 知识诊断
  输入: DynamicStudentProfile + StudentMemory.mastery_map
  模块: InMemoryKnowledgeGraph.compute_knowledge_gap()
  输出: KnowledgeGap {missing_prereqs, weak_concepts, ready_concepts, recommended_sequence}

Step 3 — Agent 协商
  触发条件: KnowledgeGap.missing_prereqs > 3 OR StrategyInjector 检测到已有经验
  模块: AgentCouncil.deliberate()
  输出: CouncilDecision {final_strategy, reasoning, consensus_score}

Step 4 — 路径规划
  输入: CouncilDecision + KnowledgeGraph + DynamicStudentProfile
  模块: PlannerAgent (KG mode: compute_optimal_path() + profile_bias)
  输出: LearningPlan (拓扑排序节点序列)

Step 5 — 多模态资源生成
  输入: LearningPlan nodes + DynamicStudentProfile.cognitive_style
  模块: ResourceGeneratorRegistry.generate_all(preferred_types)
  输出: List[LearningResource] → ReviewGate 验证

Step 6 — 资源推荐
  输入: LearningResource[] + StudentMemory
  模块: ResourceRecommendationAgent (现有)
  输出: PersonalizedResourcePlan

Step 7 — 效果评估
  输入: 学生练习结果 + LearningResource[]
  模块: AgentEvaluator (现有 4-dim)
  输出: EvaluationResult

Step 8 — 行为采集
  输入: 学习时长 + 点击流 + 暂停事件
  模块: BehaviorTracker (from EventBus 监听)
  输出: BehaviorLog[]

Step 9 — 策略优化
  触发: EvaluationResult.score < 0.5
  模块: MetaReflector → ImprovementLoop → AgentExperienceMemory.store()
        + StrategyInjector 注入预防策略
  输出: AgentExperienceRecord (新增经验)

Step 10 — 画像更新
  输入: EvaluationResult + BehaviorLog[] + 对话信号
  模块: ProfileUpdateEngine
  输出: DynamicStudentProfile (更新后) + ProfileDiff
"""

# 模块导入验证
if __name__ == "__main__":
    print("A3 v4 Integration Guide — 模块导入验证")
    print("=" * 50)

    # 验证新模块可导入
    from src.council import CouncilProposal, CouncilDecision, CouncilSession
    print(f"✅ Council 协议: {len(CouncilProposal.__annotations__)} 字段")

    from src.council.council import AgentCouncil
    print(f"✅ AgentCouncil: 就绪")

    from src.knowledge_graph import KnowledgeNode, KnowledgeGraph, KnowledgeGap
    print(f"✅ KnowledgeGraph 数据结构: 就绪")

    from src.knowledge_graph.graph_store import InMemoryKnowledgeGraph
    kg = InMemoryKnowledgeGraph.build_default_multimodal_ai_graph()
    print(f"✅ 默认知识图谱: {kg.node_count} 节点, {kg.edge_count} 边")

    from src.profile import DynamicStudentProfile, ProfileDimension
    profile = DynamicStudentProfile.create_default("test_student")
    print(f"✅ DynamicStudentProfile: {len(profile.dimensions)} 维, global_conf={profile.global_confidence}")

    from src.multimodal import LearningResource, ResourceType, ResourceGeneratorRegistry
    print(f"✅ 多模态资源协议: {len(ResourceType)} 种类型")

    from src.evolution import AgentExperienceMemory, StrategyInjector
    mem = AgentExperienceMemory(storage_path="/tmp/test_agent_exp.json")
    print(f"✅ Evolution Memory: {mem.record_count} 条预注入经验")

    # Gap 诊断测试
    gap = kg.compute_knowledge_gap(
        "kg:ch5:multi_agent_patterns",
        {"kg:ch1:ai_overview": 0.9, "kg:ch5:agent_concept": 0.6, "kg:ch5:agent_communication": 0.2},
    )
    print(f"✅ KnowledgeGap: missing={len(gap.missing_prerequisites)}, "
          f"weak={len(gap.weak_concepts)}, ready={len(gap.ready_concepts)}")
    print(f"   推荐序列: {' → '.join(gap.recommended_sequence[:5])}...")

    # 路径规划测试
    path = kg.compute_optimal_path(
        {"kg:ch1:ai_overview": 0.9, "kg:ch5:agent_concept": 0.7},
        "kg:ch5:multi_agent_patterns",
    )
    print(f"✅ 最优路径: {len(path.ordered_nodes)} 节点, {path.total_minutes}min, "
          f"skipped={len(path.skipped_nodes)}, boosted={len(path.boosted_nodes)}")

    print("\n" + "=" * 50)
    print("A3 v4 所有模块验证通过 ✅")
