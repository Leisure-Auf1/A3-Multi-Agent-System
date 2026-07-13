# Veritas_Core — Trust Layer 可信生成 & 学习闭环设计

> **Veritas = 学习内容可靠、生成过程可解释**

---

## 一、Trust Layer — 可信生成机制

### 1.1 定位

Trust Layer 不是评估 LLM 模型本身，而是保证 **给学生的学习内容可靠、可溯源、可验证**。

```
                    学生最终看到的内容
                            ▲
                            │ 只有通过Trust Layer的内容才能发布
                    ┌───────┴───────┐
                    │  TRUST LAYER   │
                    │                │
Agent生成 ──────────►                │
                    │ ① 知识来源检查   │
                    │ ② RAG引用验证    │
                    │ ③ 内容质量评估   │
                    │ ④ 幻觉检测      │
                    │ ⑤ 安全过滤      │
                    │                │
                    └───────┬───────┘
                            │
                    未通过 → 自动修正 (最多3轮)
                            → 人工标记 (超限)
```

### 1.2 Trust Pipeline

```
ResourceAgent 生成的资源
        │
        ▼
┌──────────────────────────────┐
│ Gate 1: 知识来源检查           │  A3 ReviewGate Gate 1+
│                               │
│ ① Source Check:               │
│    生成内容是否引用了RAG知识库？ │
│    是否有明确的知识来源标注？    │
│    PASS: ≥70%的关键断言有溯源   │
│                               │
│ ② Structural Check (AST):     │
│    代码示例是否语法有效？        │
│    Markdown/mermaid结构是否合规？│
│    PASS: 无语法错误             │
└──────────┬───────────────────┘
           │ PASS
           ▼
┌──────────────────────────────┐
│ Gate 2: RAG 引用验证           │
│                               │
│ 对比生成内容 vs RAG检索到的原文  │
│                               │
│ ③ Fact Grounding:              │
│    生成内容中的事实断言是否      │
│    可在RAG检索到的chunk中找到？  │
│    使用 NLI (自然语言推理) 判断  │
│    断言是否被上下文"蕴含"        │
│    PASS: ≥80%的断言有事实支撑   │
│                               │
│ ④ Consistency Check:          │
│    同一概念在多个资源中是否一致？ │
│    讲义 vs PPT vs 思维导图      │
│    PASS: 无矛盾                 │
└──────────┬───────────────────┘
           │ PASS
           ▼
┌──────────────────────────────┐
│ Gate 3: 幻觉检测               │
│                               │
│ ⑤ LLM-as-Judge:               │
│    逐句检查: "这句话在知识库     │
│    中有证据吗？"                │
│    标注每句的 confidence level  │
│    PASS: ≥85分 (rubric score)  │
│                               │
│ ⑥ Self-Consistency:           │
│    同一知识点多次采样             │
│    答案不一致的断言 = 高风险幻觉  │
│    PASS: 核心概念一致           │
└──────────┬───────────────────┘
           │ PASS
           ▼
┌──────────────────────────────┐
│ Gate 4: 安全教育过滤           │
│                               │
│ ⑦ Content Safety:             │
│    无不当内容/偏见/歧视          │
│    代码安全: 无恶意代码          │
│    PASS: 全部安全              │
│                               │
│ ⑧ Difficulty Appropriateness:│
│    内容难度是否匹配学生水平？     │
│    PASS: 难度偏差 ≤±1 level    │
└──────────┬───────────────────┘
           │
           ▼
      ┌─────────┐
      │  PASS   │ → 发布给学生
      │  FAIL   │ → 记录问题 → 重新生成 (≤3轮) → 标记人工审核
      └─────────┘
```

### 1.3 Trust Report

```python
@dataclass
class TrustReport:
    """每次资源生成的Trust评估报告"""
    resource_id: str
    overall_trust_score: float       # 0-1

    # 各Gate分数
    source_gate: SourceGateResult    # Gate 1: 来源检查
    grounding_gate: GroundingResult  # Gate 2: 引用验证
    hallucination_gate: HallucinationResult  # Gate 3: 幻觉检测
    safety_gate: SafetyResult        # Gate 4: 安全过滤

    issues_found: List[str]          # 发现的问题
    regenerated: bool                # 是否已重新生成
    regeneration_attempts: int       # 重新生成次数
    requires_human_review: bool      # 是否需要人工审核

@dataclass
class GroundingResult:
    """RAG引用验证结果"""
    total_claims: int                # 生成内容中的断言总数
    grounded_claims: int             # 有知识库支撑的断言数
    ungrounded_claims: int           # 无法验证的断言数
    grounding_score: float           # grounded/total
    problematic_claims: List[Dict]   # 问题断言详单

@dataclass
class HallucinationResult:
    """幻觉检测结果"""
    hallucination_detected: bool
    confidence: float                # 内容整体置信度
    sentence_scores: List[float]     # 逐句置信度
    flagged_sentences: List[str]     # 被标记的句子
```

---

## 二、学习闭环设计

### 2.1 闭环全流程

```
═══════════════════════════════════════════════════════════════════
                    VERITAS_CORE 学习闭环
═══════════════════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ① ProfileAgent: 学生画像构建                             │
  │     "我是谁？我想学什么？我怎么学？"                        │
  │     Input: 自然语言 → Output: DynamicProfile (8维)       │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │ DynamicProfile
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ② KnowledgeAgent: 知识诊断                               │
  │     "我缺什么知识？该从哪开始？"                            │
  │     Input: Profile + Course → Output: KnowledgeGap      │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │ KnowledgeGap
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ③ PlannerAgent: 学习路径规划                              │
  │     "应该按什么顺序学？每个环节深度多少？"                    │
  │     Input: Profile + Gap → Output: LearningPlan        │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │ LearningPlan
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ④ ResourceAgent: 资源生成                                │
  │     "生成讲义/PPT/思维导图/练习题/代码实验"                  │
  │     Input: PlanNode + Profile + RAG → Output: Resources │
  │     ┌─────────────────────────────────────┐             │
  │     │ Trust Layer 检查 (4-Gate)            │             │
  │     │ PASS → 发布 | FAIL → 重新生成          │             │
  │     └─────────────────────────────────────┘             │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │ Resources (可信)
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  学生学习 (人机交互)                                       │
  │  - 阅读讲义                                               │
  │  - 查看思维导图                                            │
  │  - 完成练习题                                              │
  │  - 运行代码实验                                            │
  │  - 给资源打分反馈                                          │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │ 答题结果 + 学习行为 + 资源反馈
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ⑤ EvaluationAgent: 学习效果评估                           │
  │     "学得怎么样？掌握了多少？哪里还薄弱？"                    │
  │     Input: 答题+行为+反馈 → Output: EvaluationResult     │
  │                                                         │
  │     评估维度:                                              │
  │     • 正确性 (答题准确率)                                   │
  │     • 知识掌握度 (EMA更新)                                  │
  │     • 学习投入度 (行为分析)                                  │
  │     • 资源质量 (反馈分析)                                   │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │ EvaluationResult
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  ⑥ ReflectionAgent: 闭环优化                               │
  │     "如何改进画像？如何调整路径？以后怎么做得更好？"           │
  │     Input: Evaluation + Profile + Plan                  │
  │     Output: UpdatedProfile + AdjustedPlan               │
  │                                                         │
  │     ┌─────────────────────────────────────┐             │
  │     │ 画像更新:                             │             │
  │     │  • mastery_map EMA更新               │             │
  │     │  • weak_points 增删                  │             │
  │     │  • 资源偏好微调                       │             │
  │     │  • 写入画像演化时间线                  │             │
  │     ├─────────────────────────────────────┤             │
  │     │ 路径调整:                             │             │
  │     │  • 已掌握节点 → 标记完成               │             │
  │     │  • 薄弱节点 → 增加练习                 │             │
  │     │  • 节奏调整 → 根据投入度              │             │
  │     ├─────────────────────────────────────┤             │
  │     │ 经验积累:                             │             │
  │     │  • 成功/失败模式 → ExperienceMemory   │             │
  │     │  • 教学策略有效性记录                   │             │
  │     └─────────────────────────────────────┘             │
  │                                                         │
  └────────────────────────┬────────────────────────────────┘
                           │
        ┌──────────────────┘
        │ UpdatedProfile + AdjustedPlan
        ▼
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │  循环: 回到第②步 (KnowledgeAgent)                          │
  │    用更新后的画像重新诊断 → 调整学习路径 → 生成新资源         │
  │    直到所有学习节点完成                                     │
  │                                                         │
  └─────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
  每次循环 = 一次"画像→生成→学习→评估→调整"的完整闭环
  数据持久化: ProfileMemory + HistoryMemory 全程记录
═══════════════════════════════════════════════════════════════════
```

### 2.2 闭环关键数据流

```
第0次: StudentInput → Profile → Gap → Plan → Resources → Study

第1次循环:
  Study Results → Evaluate → Reflect → UpdatedProfile
  UpdatedProfile → KnowledgeAgent → UpdatedGap
  UpdatedGap → PlannerAgent → AdjustedPlan
  AdjustedPlan → ResourceAgent → NewResources → Study

第2次循环:
  Study Results → Evaluate → Reflect → UpdatedProfile
  → ... (直到 LearningPlan 所有节点完成)

每次循环写入:
  ProfileMemory: mastery_map更新, profile_evolution追加
  HistoryMemory: learning_record, exercise_error, resource_feedback
  ExperienceMemory: 新增经验教训 (如果有)
```

### 2.3 画像演化示例

```
初始画像 (第0次):
  knowledge_base: mid_level
  weak_points: [async_io, decorators]
  mastery_map: {async_io: 0.3, prompt_eng: 0.5}

──学习 Node 1: LLM基础回顾──

  ReflectionAgent 分析:
    async_io掌握度: 0.3 → 0.65 (显著提升)
    prompt_eng: 无变化 (节点不涉及)

──学习 Node 2: Prompt Engineering──

  ReflectionAgent 分析:
    prompt_eng掌握度: 0.5 → 0.8 (已掌握)
    weak_points: decorators 已解决 → 移除

──学习 Node 3: RAG系统原理──

  ReflectionAgent 分析:
    发现新薄弱点: embedding_dimension
    resource_preference: diagram评分高 → 偏好权重+1

最终画像 (第N次):
  knowledge_base: mid_level (认知基础未变)
  weak_points: [embedding_dimension, message_queue]
  mastery_map: {async_io: 0.65, prompt_eng: 0.8,
                rag_retrieval: 0.72, embedding_dimension: 0.25}
  resource_preference: diagram+code (权重更新)
  profile_evolution: 6条记录 (每次变化的reason)
```

---

## 三、闭环 vs A3 的改进

| 维度 | A3 (v2.8) | Veritas_Core |
|:-----|:----------|:-------------|
| **画像维度** | 6维 | 8维 (新增动机+时间) |
| **画像更新** | 仅在ProfileAgent提取时 | 每次学习后ReflectionAgent自动更新 |
| **掌握度追踪** | JSON文件, EMA α=0.5 | PostgreSQL表, EMA α=0.5, 支持历史查询 |
| **路径调整** | 规划时一次性完成 | 每次学习后可根据评估动态调整 |
| **经验积累** | 关键词匹配召回 | 语义向量搜索 (ChromaDB) |
| **资源生成** | 规则模板填充 | RAG增强LLM生成 + Trust Layer |
| **闭环证据** | 无系统记录 | profile_evolution表 + learning_records表 |
| **可视化** | 6-panel Dashboard | 画像演化时间线 + 学习进度 + Trust报告 |
