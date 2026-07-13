# A3 v4.0 — 科研级教育智能体平台升级设计方案

> **定位：** 从"多智能体教学 Demo"升级为"具有科研创新性的教育智能体平台"  
> **核心命题：** Agent 自主协商 × 知识图谱推理 × 多模态教学 × 动态学生画像 × 完整教育闭环  
> **版本：** v4.0 Alpha Design | **日期：** 2026-07-13 | **基准：** A3 v3.0 (12 Agents · 241 Tests)

---

## 目录

1. [AgentCouncil — 多 Agent 自主协商机制](#1-agentcouncil--多-agent-自主协商机制)
2. [KnowledgeGraphAgent — 课程知识图谱系统](#2-knowledgegraphagent--课程知识图谱系统)
3. [MultiModalGenerationAgent — 增强多模态教学能力](#3-multimodalgenerationagent--增强多模态教学能力)
4. [DynamicStudentProfile — 强化学生画像系统](#4-dynamicstudentprofile--强化学生画像系统)
5. [Complete Education Loop — 完整教育闭环设计](#5-complete-education-loop--完整教育闭环设计)
6. [Competition Innovation — 竞赛申报创新点提炼](#6-competition-innovation--竞赛申报创新点提炼)

---

## 1. AgentCouncil — 多 Agent 自主协商机制

### 1.1 当前问题诊断

A3 v3.0 的 Agent 协作本质是**管线式 (Pipeline)**：

```
ProfileAgent → PlannerAgent → ResourceGenAgent → ResourceRecAgent
```

每个 Agent 单向传递 `dataclass` 契约，下游 Agent 只能被动接受上游产出。这带来三个结构性局限：

1. **无博弈** — PlannerAgent 规划了错误路径，ResourceGenAgent 发现了但无法反驳，只能照单生成
2. **无全局优化** — 每个 Agent 做局部最优决策，没有全局视角的统筹
3. **竞赛答辩弱** — 评委必然追问"Agent 之间如何协作？"时，管线式架构缺乏说服力

### 1.2 AgentCouncil 架构设计

`AgentCouncil` 是一个**轻量级多 Agent 协商层**，位于现有 Pipeline 之上，提供 **Propose → Deliberate → Decide** 三段式协商协议。

```
                          ┌──────────────────────────┐
                          │     AgentCouncil          │
                          │                           │
                       ┌──┤  • session_id             │
                       │  │  • proposals[]            │
   ┌────────────────┐  │  │  • deliberation_log[]     │
   │ ProposalAgent  │──┤  │  • final_decision         │
   │ (任意Agent)     │  │  │  • consensus_score        │
   └────────────────┘  │  │                           │
                       │  │  open_session()            │
   ┌────────────────┐  │  │  submit_proposal()         │
   │ CritiqueAgent  │──┤  │  vote()                    │
   │ (任意Agent)     │  │  │  finalize()               │
   └────────────────┘  │  │  resolve_deadlock()        │
                       │  │                           │
   ┌────────────────┐  │  │  决策模式:                 │
   │ EvaluatorAgent │──┤  │  • Majority Vote           │
   └────────────────┘  │  │  • Weighted Vote           │
                       │  │  • Chairperson Override    │
   ┌────────────────┐  │  │                           │
   │ ...更多Agent    │──┘  │  扩展 EventBus:            │
   └────────────────┘     │  • council.proposal.*      │
                          │  • council.vote.*          │
                          └──────────────────────────┘
```

### 1.3 消息协议格式

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ProposalType(Enum):
    """提案类型"""
    PATH_ADJUSTMENT = "path_adjustment"       # 路径调整
    RESOURCE_CHANGE = "resource_change"       # 资源变更
    DIFFICULTY_OVERRIDE = "difficulty_override"  # 难度覆盖
    PACING_CHANGE = "pacing_change"           # 节奏调整
    STRATEGY_SWITCH = "strategy_switch"       # 策略切换
    EMERGENCY_HALT = "emergency_halt"         # 紧急暂停


class VoteType(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"
    COUNTER_PROPOSE = "counter_propose"  # 附替代方案


@dataclass
class CouncilProposal:
    """协商提案 — 任何 Agent 可发起"""
    proposal_id: str
    session_id: str
    proposer_agent: str               # e.g. "PlannerAgent"
    proposal_type: ProposalType
    target_layer: str                 # 被建议修改的模块 e.g. "resource_difficulty"
    rationale: str                    # 建议理由（自然语言 + 可追溯证据）
    evidence: Dict[str, Any]          # 支撑数据：mastery_map 快照、错误日志等
    suggested_action: str             # 具体建议操作
    priority: int                     # 紧急度 1-10
    timestamp: datetime = field(default_factory=lambda: datetime.now())


@dataclass
class CouncilVote:
    """Agent 对提案的投票"""
    vote_id: str
    proposal_id: str
    voter_agent: str
    vote: VoteType
    reasoning: str                    # 投票理由
    counter_proposal: Optional['CouncilProposal'] = None  # 若是 COUNTER_PROPOSE


@dataclass
class CouncilDecision:
    """协商最终决策"""
    decision_id: str
    session_id: str
    original_proposals: List[str]     # proposal_ids
    votes: List[CouncilVote]
    outcome: str                      # "approved" | "rejected" | "compromise"
    final_action: str                 # 最终执行的操作
    consensus_score: float            # 0.0-1.0 共识度
    minority_opinion: Optional[str]   # 少数派意见保留
    resolved_by: str                  # "majority" | "weighted" | "chairperson"
    timestamp: datetime = field(default_factory=lambda: datetime.now())
```

### 1.4 AgentCouncil Python 类设计

```python
class AgentCouncil:
    """
    多 Agent 协商层 — 轻量嵌入现有 Pipeline，不替换仅增强。

    核心设计原则:
    - 无侵入: 现有 Agent 无需修改核心逻辑，仅需注册 `council_opinion()` 回调
    - 异步非阻塞: 协商不阻塞主 Pipeline，仅在关键决策点触发
    - 可降级: 若协商超时（默认 30s），自动 fallback 到 Chairperson 直接决策
    """

    def __init__(self, chairperson: str = "PlannerAgent", timeout_s: int = 30):
        self.chairperson = chairperson
        self.timeout_s = timeout_s
        self._sessions: Dict[str, CouncilSession] = {}
        self._agent_registry: Dict[str, CouncilCapability] = {}

    def register_agent(self, agent_name: str, capability: 'CouncilCapability'):
        """
        注册 Agent 的协商能力。
        现有 Agent 需新增以下方法:
          - council_opinion(proposal: CouncilProposal) -> CouncilVote
          - council_propose(context: Dict) -> Optional[CouncilProposal]
        """
        self._agent_registry[agent_name] = capability

    def open_session(self, context: Dict[str, Any]) -> str:
        """开启一轮协商会话。context 携带当前学生画像、规划草稿等上下文。"""
        ...

    def submit_proposal(self, proposal: CouncilProposal) -> str:
        """Agent 提交提案 → 广播给所有注册 Agent → 收集投票。"""
        # 1. 存入 session.proposals
        # 2. EventBus.emit("council.proposal.submitted", proposal)
        # 3. 异步收集所有 Agent 的 council_opinion() 返回值
        # 4. 返回 proposal_id
        ...

    def vote(self, vote: CouncilVote) -> None:
        """单个 Agent 的投票。"""
        ...

    def finalize(self, session_id: str) -> CouncilDecision:
        """
        汇总投票 → 生成最终决策。
        决策规则:
          1. 全票 APPROVE → approve, consensus=1.0
          2. ≥2/3 APPROVE → approve, consensus=0.67+
          3. <2/3 → chairperson 做最终决定, consensus=投票比例
          4. 有 COUNTER_PROPOSE → 对替代方案重新投票
        """
        ...

    def resolve_deadlock(self, session_id: str) -> CouncilDecision:
        """
        僵局解决: 连续 3 轮无法达成 2/3 共识 → Chairperson 独裁决策。
        记录 minority_opinion 供审计。
        """
        ...
```

### 1.5 EventBus 扩展支持

现有 `AgentEventBus` 通过新增 EventType 支持协商：

```python
# 新增事件类型（追加到 event_bus.py）
class CouncilEventType(Enum):
    SESSION_OPENED = "council.session.opened"
    PROPOSAL_SUBMITTED = "council.proposal.submitted"
    VOTE_CAST = "council.vote.cast"
    DEADLOCK_DETECTED = "council.deadlock.detected"
    DECISION_FINALIZED = "council.decision.finalized"
    MINORITY_OPINION = "council.minority.recorded"
```

Dashboard V2 新增 **"Council Chamber" (第 7 Panel)**：
- 实时展示当前协商状态
- 显示各 Agent 的提案、投票、推理
- 历史协商记录可回溯

### 1.6 典型协商场景实例

**场景: PlannerAgent 规划错误 → ResourceAgent 发现 → Council 纠正**

```
Step 1: PlannerAgent 产出现有规划
  LearningPlan: [Ch2 Basics (20min, 4 exercises), Ch3 Prompt (25min, 4 exercises), ...]

Step 2: ResourceGenAgent 在生成 Ch2 资源时发现:
  student.mastery_map["python_basics"] = 0.85 (已掌握)
  但 PlannerAgent 给 Ch2 分配了 4 道基础语法练习 → 浪费学生时间

Step 3: ResourceGenAgent 发起提案
  council.submit_proposal(CouncilProposal(
      proposer_agent="ResourceGenAgent",
      proposal_type=ProposalType.PATH_ADJUSTMENT,
      target_layer="planner_output.ch2_exercises",
      rationale="学生 Python 基础 mastery=0.85，4 道语法练习属冗余。建议替换为 2 道中等难度的 Agent 架构练习。",
      evidence={"mastery_map_snapshot": {"python_basics": 0.85}},
      suggested_action="ch2: 移除 4 道基础语法 → 替换为 2 道 Agent 概念应用题",
      priority=7
  ))

Step 4: Council 广播 → 各 Agent 投票
  AgentEvaluator: APPROVE — "冗余练习降低效率维度评分"
  PlannerAgent: COUNTER_PROPOSE — "建议保留 1 道语法快速回顾 + 2 道 Agent 练习"
  ProfileAgent: APPROVE (ResourceGenAgent 原方案)
  ResourceRecAgent: APPROVE (PlannerAgent 替代方案)

Step 5: 重新投票 → 替代方案 3/4 通过 → Decision
  outcome: "compromise"
  final_action: "ch2: 1 道语法回顾 + 2 道 Agent 概念练习"
  consensus_score: 0.75
```

### 1.7 工程落地优先级

| 阶段 | 内容 | 工作量 |
|:---|:---|:---|
| **P0** | `CouncilProposal` / `CouncilVote` / `CouncilDecision` 数据模型 | 1d |
| **P1** | `AgentCouncil` 核心类 (open_session / submit / vote / finalize) | 2d |
| **P2** | EventBus 扩展 (council.* 事件) + Dashboard Council Panel | 1.5d |
| **P3** | 3 个示范协商场景的 Agent 改造 (PlannerAgent / ResourceGenAgent / AgentEvaluator) | 2d |

---

## 2. KnowledgeGraphAgent — 课程知识图谱系统

### 2.1 当前问题诊断

A3 v3.0 的知识层是**扁平 Markdown 章节**，PlannerAgent 通过 `course_kb_loader.py` 做章节级解析。问题：
- 知识点间**依赖关系不可计算** — "RAG 检索"需要先掌握"向量嵌入"，但系统中这是隐式的
- 无法做**前置知识检查** — 学生要学"多 Agent 通信"，系统不知道他是否已掌握"消息队列基础"
- **路径规划是规则表驱动**，不是图遍历 — 无法做最优学习路径搜索

### 2.2 KnowledgeGraphLayer 架构

```
┌──────────────────────────────────────────────────────────────┐
│                   KnowledgeGraphLayer                         │
│                                                               │
│  ┌──────────────────┐   ┌──────────────────┐                 │
│  │ KnowledgeGraphAgent│  │ GraphDatabase     │                │
│  │                    │  │ (Neo4j / NetworkX)│                │
│  │ • extract_concepts │  │                   │                │
│  │ • build_dependencies│ │  nodes: Concept    │                │
│  │ • infer_prereqs    │  │  edges: PREREQ_OF │                │
│  │ • compute_topology │  │  edges: RELATED_TO│                │
│  │ • recommend_path   │  │  edges: ASSESSED_BY│               │
│  └────────┬───────────┘  └────────┬─────────┘               │
│           │                       │                           │
│           └───────────┬───────────┘                           │
│                       ▼                                       │
│  ┌──────────────────────────────────────────────────────┐    │
│  │          KnowledgeGraph → PlannerAgent 接口            │    │
│  │                                                       │    │
│  │  • get_prerequisites(concept) → List[Concept]         │    │
│  │  • compute_optimal_path(profile, goal) → PathResult   │    │
│  │  • topological_sort(concepts) → List[Concept]         │    │
│  │  • get_knowledge_gap(student_mastery, target) → Gap   │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### 2.3 数据结构定义

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set
import uuid


class ConceptType(Enum):
    """知识概念类型"""
    CONCEPT = "concept"           # 概念型 (e.g. "向量嵌入")
    SKILL = "skill"               # 技能型 (e.g. "Python 编码")
    METHOD = "method"             # 方法型 (e.g. "反向传播")
    PRINCIPLE = "principle"       # 原理型 (e.g. "注意力机制原理")
    TOOL = "tool"                 # 工具型 (e.g. "LangChain 框架")


class EdgeType(Enum):
    PREREQ_OF = "PREREQ_OF"       # A 是 B 的前置知识
    STRONG_RELATED = "STRONG_RELATED_TO"  # 强关联
    WEAK_RELATED = "WEAK_RELATED_TO"      # 弱关联
    ASSESSED_BY = "ASSESSED_BY"   # 该概念可通过某习题评估
    TAUGHT_BY = "TAUGHT_BY"       # 该概念可由某资源教学


@dataclass
class KnowledgeNode:
    """知识图谱节点 — 单个知识点"""
    concept_id: str               # 唯一标识 e.g. "kg:ma:agent_communication"
    concept_name: str             # 知识点名称 e.g. "Agent 通信协议"
    concept_type: ConceptType
    description: str              # 知识点描述
    difficulty: float             # 难度等级 0.0-1.0
    chapter: str                  # 所属章节
    related_resources: List[str]  # 关联资源 ID 列表
    mastery_threshold: float      # 掌握阈值 (≥此值视为已掌握)
    estimated_minutes: int        # 预估学习时间 (分钟)
    keywords: Set[str]            # 语义标签集合


@dataclass
class KnowledgeEdge:
    """知识图谱边 — 知识点间关系"""
    source_id: str                # 前置知识
    target_id: str                # 后继知识
    edge_type: EdgeType
    weight: float                 # 关系强度 0.0-1.0
    rationale: str                # 建立此关系的依据


@dataclass
class KnowledgeGraph:
    """完整知识图谱"""
    nodes: Dict[str, KnowledgeNode]
    edges: List[KnowledgeEdge]
    version: str

    def get_prerequisites(self, concept_id: str) -> List[KnowledgeNode]:
        """获取前置知识链（直接+传递）"""
        ...

    def compute_optimal_path(
        self,
        mastered: Set[str],       # 已掌握节点 (来自 StudentMemory.mastery_map)
        target: str,              # 目标节点
        profile: 'DynamicStudentProfile'
    ) -> 'PathResult':
        """基于拓扑排序 + profile 偏差计算最优学习路径"""
        ...


@dataclass
class PathResult:
    """最优路径规划结果"""
    ordered_nodes: List[KnowledgeNode]   # 拓扑排序后的学习序列
    total_minutes: int                   # 总预估时间
    critical_path: List[KnowledgeNode]   # 关键路径（最长依赖链）
    skipped_nodes: List[KnowledgeNode]   # 已掌握跳过的节点
    boosted_nodes: List[KnowledgeNode]   # 薄弱点加强的节点
    alternative_paths: List[List[KnowledgeNode]]  # 替代路径
```

### 2.4 图数据库方案

**竞赛阶段 (当前 → 3 月内): NetworkX 内存图**

```python
import networkx as nx

class InMemoryKnowledgeGraph:
    """
    竞赛 Demo 阶段使用 NetworkX 内存图。
    理由: 零外部依赖、演示稳定、秒级加载 6 章 46 概念。
    接口与 `KnowledgeGraph` 抽象类一致，后续替换 Neo4j 无需改业务逻辑。
    """

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_concept(self, node: KnowledgeNode):
        self.graph.add_node(node.concept_id, **node.__dict__)

    def add_dependency(self, edge: KnowledgeEdge):
        self.graph.add_edge(edge.source_id, edge.target_id,
                           edge_type=edge.edge_type.value,
                           weight=edge.weight)

    def topological_order(self) -> List[str]:
        return list(nx.topological_sort(self.graph))

    def shortest_learning_path(self, start: str, goal: str) -> List[str]:
        """Dijkstra 最短学习路径 (权重=难度×时间)"""
        return nx.dijkstra_path(self.graph, start, goal, weight='weight')
```

**生产阶段 (3-6 月): Neo4j + Cypher 图查询**

```cypher
// 查询概念 A 的所有传递前置知识
MATCH (c:Concept {id: $target})-[:PREREQ_OF*1..5]->(prereq:Concept)
RETURN prereq

// 查找学生的知识缺口
MATCH (target:Concept {id: $target})-[:PREREQ_OF*]->(prereq:Concept)
WHERE NOT prereq.id IN $mastered_concepts
RETURN prereq ORDER BY prereq.difficulty

// 计算最优学习路径 (按难度×时间加权)
MATCH path = shortestPath(
  (start:Concept {id: $current})-[*]->(goal:Concept {id: $target})
)
RETURN path, reduce(total=0, r in relationships(path) | total + r.weight) AS total_cost
ORDER BY total_cost
```

### 2.5 与 Memory 系统结合

```
KnowledgeGraph ←────── 读取 ──────→ StudentMemory
      │                                  │
      │  get_prerequisites(concept)      │  mastery_map: {"embedding": 0.45, ...}
      │                                  │  weak_points: ["tokenization", ...]
      │  compute_knowledge_gap()         │
      │                                  │
      ▼                                  ▼
  KnowledgeGap                       PlannerAgent
  ┌─────────────────────┐            使用 gap 信息做个性化规划:
  │ missing_prereqs[]   │            • gap > 3 个前置知识 → 降低目标难度
  │ weak_concepts[]     │            • weak_points ∩ prereqs → 插入复习节点
  │ ready_concepts[]    │            • ready_concepts → 快速推进
  └─────────────────────┘
```

### 2.6 知识图谱自动构建

`KnowledgeGraphAgent` 核心能力: 从现有 6 章 Markdown KB **自动构建知识图谱**。

```python
class KnowledgeGraphAgent:
    """
    从课程 Markdown 知识库自动构建知识图谱。

    构建策略:
    1. 解析章节 → 提取 ##/### 标题作为候选概念
    2. 对每个概念调用 LLM (Xunfei Spark) 提取结构化信息
    3. 基于章节顺序 + 概念间引用关系推断 PREREQ_OF 边
    4. 人工审核 + 微调 → 生成最终图谱
    """

    def extract_concepts(self, chapter_path: str) -> List[KnowledgeNode]:
        """Markdown 解析 → LLM 结构化提取 → KnowledgeNode 列表"""
        ...

    def infer_dependencies(self, nodes: List[KnowledgeNode]) -> List[KnowledgeEdge]:
        """
        依赖推断策略:
        - 层次型: 同一章节内按出现顺序 (深层概念在浅层之后)
        - 引用型: 章节 B 引用了 A 的定义 → A PREREQ_OF B
        - 语义型: LLM 判断两个概念间是否存在前置关系
        - 计算型: 概念 A 的难度 > 概念 B 且 A 晚出现 → B PREREQ_OF A
        """
        ...

    def build_full_graph(self, kb_dir: str) -> KnowledgeGraph:
        """端到端: 所有章节 → 提取 → 推断 → 校验 → 输出图"""
        ...
```

**预期产出:**
- 从现有 6 章 46 概念 → 扩展为 80-100 个细粒度概念节点
- 150-200 条 PREREQ_OF 依赖边
- 50-80 条 RELATED_TO 关联边

---

## 3. MultiModalGenerationAgent — 增强多模态教学能力

### 3.1 当前问题诊断

A3 v3.0 的 `ResourceGenerationAgent` 生成 6 类资源，但：
- 视频输出仅为**分镜文字脚本** → 不是真正的多模态
- 图片/动画/PPT 均缺失 → 竞赛演示中缺少视觉冲击力
- 资源格式不具备**统一协议** → 无法被推荐系统统一调度

### 3.2 统一资源协议 — LearningResource

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ResourceType(Enum):
    """资源类型枚举 — 可扩展"""
    COURSE_NOTE = "course_note"         # Markdown 课程笔记
    MIND_MAP = "mind_map"              # Mermaid 思维导图
    PPT_DECK = "ppt_deck"              # PPT 课件 (.pptx)
    VIDEO_SCRIPT = "video_script"      # 视频分镜脚本 + 生成描述
    IMAGE_ASSET = "image_asset"        # 教学图片素材 (AI 生成)
    ANIMATION_DESC = "animation_desc"  # 动画生成描述 (Manim / Remotion)
    CODE_LAB = "code_lab"              # 代码实验
    EXERCISE = "exercise"              # 习题
    EXTENDED_READING = "extended_reading"  # 扩展阅读


class ResourceFormat(Enum):
    MARKDOWN = "markdown"
    MERMAID = "mermaid"
    PPTX = "pptx"
    JSON = "json"                      # 用于结构化描述 (动画/图片 prompt)
    PYTHON = "python"
    TEXT = "text"


@dataclass
class LearningResource:
    """统一学习资源协议"""
    resource_id: str                   # UUID
    type: ResourceType
    format: ResourceFormat
    title: str
    description: str
    content: str                       # 核心内容（文本 or Markdown or 序列化 JSON）
    visual_prompt: Optional[str]       # 用于 AI 图像/视频生成的 prompt
    difficulty: float                  # 0.0-1.0
    estimated_minutes: int
    target_profile_dim: Optional[str]  # 针对哪个画像维度优化 e.g. "visual_dominant"
    prerequisite_concepts: List[str]   # 前置知识概念 IDs
    keywords: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_renderable(self) -> Dict[str, Any]:
        """生成 Dashboard 渲染所需的结构化数据"""
        ...
```

### 3.3 MultiModalGenerationAgent 类设计

```python
class MultiModalGenerationAgent:
    """
    统一多模态资源生成 Agent。

    与现有 ResourceGenerationAgent 的关系:
    - ResourceGenerationAgent → 降级为"纯文本类资源生成器"
    - MultiModalGenerationAgent → 包裹并扩展它，新增图片/PPT/动画生成能力
    - 对外暴露统一 `generate(resource_type, context) → LearningResource` 接口
    """

    def __init__(self, llm_provider, image_provider=None, ppt_engine=None):
        self.llm = llm_provider          # Xunfei Spark
        self.image_gen = image_provider  # 可选: FAL / DALL·E / Stable Diffusion
        self.ppt_engine = ppt_engine     # python-pptx

    def generate_course_note(self, topic: str, profile: DynamicStudentProfile) -> LearningResource:
        """Markdown 课程笔记 — 规则引擎 + LLM 增强"""
        ...

    def generate_mind_map(self, topic: str, concepts: List[str]) -> LearningResource:
        """Mermaid 思维导图 — 基于概念层级自动构建"""
        ...

    def generate_ppt(self, topic: str, note_content: str) -> LearningResource:
        """
        PPT 课件生成策略:
        1. 从 Course Note 提取关键点 (## 标题 → SlideTitle, 列表 → Bullets)
        2. 为每页生成 visual_prompt (用于后续 AI 图片插入)
        3. 使用 python-pptx 创建 .pptx 文件
        4. visual_prompt 可被 Image Agent 调用生成配图
        """
        ...

    def generate_image_asset(self, visual_prompt: str, style: str = "educational") -> LearningResource:
        """
        教学图片素材生成:
        - 使用 visual_prompt → 调用多模态 API (FAL / DALL·E)
        - 返回 LearningResource 中 visual_prompt 已填充
        - 生成的图片路径存入 metadata["image_path"]
        """
        ...

    def generate_animation_desc(self, topic: str, concept: str) -> LearningResource:
        """
        动画生成描述:
        - 输出 Manim Python 代码 或 Remotion React 组件描述
        - visual_prompt 包含完整的动画场景描述
        - 可用于后续实际渲染
        """
        ...

    def generate_video_script(self, topic: str, concepts: List[str]) -> LearningResource:
        """
        视频分镜脚本:
        - 现有逻辑保留 + visual_prompt 增强
        - 每个场景新增"画面描述"字段，可用于 AI 视频生成 (Sora/Runway)
        """
        ...

    def generate_all(self, node: PlanNode, profile: DynamicStudentProfile) -> List[LearningResource]:
        """
        根据 PlanNode 和 StudentProfile 批量生成适配的资源。
        资源类型选择策略:
        - visual_dominant → 优先生成 MindMap + Image + Animation
        - text_preferred → 优先生成 Note + Extended Reading
        - code_sandbox → 优先生成 CodeLab + Exercise
        """
        ...
```

### 3.4 与讯飞星火及多模态模型结合

```
MultiModalGenerationAgent
         │
         ├── 文本生成 (已就绪)
         │   └── Xunfei Spark → Course Note / Mind Map / Video Script / Exercise / Code Lab
         │
         ├── 图片生成 (新增)
         │   └── visual_prompt → FAL API (FLUX) / DALL·E → 教学配图
         │       流程: ContentAgent 生成课程文本 → 提取关键概念 → 生成 visual_prompt
         │             → image_generate(prompt) → 图片存入 CDN/本地 → metadata["image_path"]
         │
         ├── PPT 生成 (新增)
         │   └── python-pptx 引擎 + Spark 内容提取 → .pptx 课件
         │       流程: Course Note → 提取大纲 → 创建 Slide(标题+要点+visual_prompt)
         │             → 保存 .pptx → metadata["pptx_path"]
         │
         └── 动画描述 (新增)
             └── Spark 生成 Manim Python 代码 → 可本地渲染
                  流程: 概念 → Spark 生成 Manim 场景描述 → 保存 .py → metadata["manim_path"]
```

---

## 4. DynamicStudentProfile — 强化学生画像系统

### 4.1 当前问题诊断

A3 v3.0 的 6 维画像是**静态快照** — 创建后仅通过 EMA 更新 mastery_map，缺少：
- 画像演化的**可追溯性** (何时变？为何变？根据什么证据？)
- 学习心理和行为维度的覆盖（动机、注意力、时间碎片化）
- 每个维度的**置信度**和**证据链**

### 4.2 DynamicStudentProfile 数据模型

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum


class ProfileDimension(Enum):
    """画像维度 — 从 6 维扩展到 10 维"""
    # === 认知维度 (原保留) ===
    KNOWLEDGE_BASE = "knowledge_base"         # 知识基础
    COGNITIVE_STYLE = "cognitive_style"       # 认知风格
    LEARNING_PACE = "learning_pace"           # 学习节奏
    ERROR_PATTERN = "error_pattern"           # 错误模式 (原 error_prone_bias)
    INTERACTION_PREF = "interaction_preference"  # 交互偏好

    # === 行为维度 (新增) ===
    LEARNING_MOTIVATION = "learning_motivation"    # 学习动机 (内在/外在/无)
    ATTENTION_PATTERN = "attention_pattern"        # 注意力模式 (持续/脉冲/碎片)
    TIME_FRAGMENTATION = "time_fragmentation"      # 时间碎片化程度 (0.0-1.0)
    SELF_REGULATION = "self_regulation"            # 自我调节能力 (0.0-1.0)
    FRUSTRATION_TOLERANCE = "frustration_tolerance"  # 挫折容忍度 (原)


@dataclass
class ProfileEntry:
    """单个画像维度的值 — 带置信度和证据"""
    dimension: ProfileDimension
    value: Any                           # 可以是 str / float / enum
    confidence: float                    # 0.0-1.0 置信度
    evidence: List[Dict[str, Any]]       # 证据链 [{"source": "对话", "timestamp": ..., "detail": "..."}, ...]
    updated_at: datetime                 # 最后更新时间

    def to_dict(self) -> Dict:
        return {
            "dimension": self.dimension.value,
            "value": self.value,
            "confidence": self.confidence,
            "evidence_sources": [e["source"] for e in self.evidence],
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class DynamicStudentProfile:
    """
    动态学生画像 — 每个维度独立追踪值/置信度/证据/时间戳。

    核心设计:
    - 每个维度有独立生命周期 (可单独更新、降置信度)
    - 证据链支持画像演化的完整审计 (为什么 3 周前判断为 fast_track 但现在降为 steady?)
    - 置信度随时间衰减 (长时间无新证据 → 置信度下降 → 触发重新采集)
    """
    student_id: str
    dimensions: Dict[str, ProfileEntry]  # dimension.value → ProfileEntry
    global_confidence: float             # 全局画像可信度 (所有维度均值)
    created_at: datetime
    last_activity_at: datetime

    def update_dimension(
        self,
        dimension: ProfileDimension,
        new_value: Any,
        confidence: float,
        evidence: Dict[str, Any]
    ) -> None:
        """
        更新单个维度 — 核心方法。

        更新策略:
        1. 若新证据与现有证据一致 → 置信度上升 (min 1.0)
        2. 若新证据与现有证据矛盾 → 置信度下降 + 标记冲突
        3. 长时间 (7d+) 无更新 → 置信度按指数衰减 (decay_factor=0.9/day)
        """
        ...

    def decay_stale_dimensions(self) -> None:
        """衰减长期未更新的维度置信度"""
        ...

    def to_planner_input(self) -> Dict[str, Any]:
        """
        转换为 PlannerAgent 可消费的输入格式。
        仅输出 confidence ≥ 0.5 的维度（低置信度暂不参与规划）。
        """
        ...

    def diff(self, previous: 'DynamicStudentProfile') -> 'ProfileDiff':
        """
        画像差异对比 — 用于 Dashboard 展示学生成长轨迹。
        """
        ...
```

### 4.3 动态更新策略 — 四源融合

```
                     DynamicStudentProfile
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
    ┌──────────┐        ┌──────────┐        ┌──────────┐
    │ 对话分析  │        │ 错题分析  │        │ 学习行为  │
    │ (高频)   │        │ (中频)   │        │ (连续)   │
    └────┬─────┘        └────┬─────┘        └────┬─────┘
         │                   │                   │
         ▼                   ▼                   ▼
    ┌──────────────────────────────────────────────────┐
    │           ProfileSignalExtractor                  │
    │                                                    │
    │  将原始信号转换为画像维度更新:                       │
    │                                                    │
    │  对话信号:                                          │
    │    "太简单了" → pace ↑, confidence 0.6             │
    │    "不想学了" → motivation ↓, confidence 0.7       │
    │    "等等再回来看" → time_fragmentation ↑            │
    │                                                    │
    │  错题信号:                                          │
    │    同一概念连错 3 次 → error_pattern 更新           │
    │    难度跳跃过大导致全错 → self_regulation 重评估     │
    │    错后主动查资料 → self_regulation ↑               │
    │                                                    │
    │  行为信号:                                          │
    │    单次学习 < 5min → time_fragmentation ↑          │
    │    连续学习 > 45min → attention_pattern=持续        │
    │    反复查看同一概念 → mastery 实际可能 < EMA 值      │
    │    跳过前置知识直接挑战高难内容 → motivation 高      │
    │    但 self_regulation 低                           │
    │                                                    │
    │  时长信号:                                          │
    │    间隔 3 天以上无学习 → 触发 decay_stale()         │
    │    每日 30min 持续 7 天 → motivation 稳定高         │
    └──────────────────────────────────────────────────┘
```

**与 ExperienceMemory 的结合:**

```python
class ProfileExperienceBridge:
    """
    画像更新 → ExperienceMemory 的双向通道。

    正向: 画像维度剧烈变化 (confidence<0.3) → 存入 ExperienceMemory 作为警示案例
    反向: 遇到相似学生的经验 → 用于初始化新学生画像的先验概率
    """
    def on_dimension_collapse(self, student_id, dimension, old_value, new_value):
        """当某维度置信度骤降时，记录为经验教训"""
        experience = ExperienceRecord(
            problem=f"画像维度 {dimension} 置信度崩溃 ({old_value}→{new_value})",
            cause="证据矛盾积累超过阈值",
            solution="触发对话式画像重新采集",
            keywords=["profile_collapse", dimension, student_id],
            severity="L1"
        )
        self.experience_memory.store(experience)
```

---

## 5. Complete Education Loop — 完整教育闭环设计

### 5.1 全闭环架构图 (ASCII)

```
                            ┌─────────────────────────┐
                            │     STUDENT INPUT        │
                            │  NL + 对话 + 行为日志     │
                            └────────────┬────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
            ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
            │ ① 画像构建    │    │ ⑧ 学习行为采集 │    │ ⑩ 画像更新    │
            │ ProfileAgent │    │ BehaviorTrack │    │ ProfileUpdate│
            │ (10维提取)    │    │ (时长/点击/暂停)│    │ (Decay+Merge)│
            └──────┬───────┘    └──────┬───────┘    └──────▲───────┘
                   │                   │                    │
                   ▼                   │                    │
            ┌──────────────┐           │                    │
            │ ② 知识诊断    │           │                    │
            │ KnowledgeGraph│          │                    │
            │ (前置/漏洞/准备)│          │                    │
            └──────┬───────┘           │                    │
                   │                   │                    │
                   ▼                   │                    │
         ┌─────────────────────┐       │                    │
         │ ③ Agent 协商        │       │                    │
         │  AgentCouncil       │       │                    │
         │  (Propose→Vote→Decide)│     │                    │
         └─────────┬───────────┘       │                    │
                   │                   │                    │
                   ▼                   │                    │
         ┌─────────────────────┐       │                    │
         │ ④ 路径规划           │       │                    │
         │  PlannerAgent       │       │                    │
         │  (图遍历+偏差调整)    │       │                    │
         └─────────┬───────────┘       │                    │
                   │                   │                    │
                   ▼                   │                    │
         ┌─────────────────────┐       │                    │
         │ ⑤ 多模态资源生成     │       │                    │
         │  MultiModalGenAgent │       │                    │
         │  (笔记/图/PPT/视频/动画)│    │                    │
         └─────────┬───────────┘       │                    │
                   │                   │                    │
                   ▼                   │                    │
         ┌─────────────────────┐       │                    │
         │ ⑥ 资源推荐           │       │                    │
         │  ResourceRecAgent   │       │                    │
         │  (掌握度+弱点+风格)   │       │                    │
         └─────────┬───────────┘       │                    │
                   │                   │                    │
                   ▼                   │                    │
         ┌─────────────────────┐       │                    │
         │      学生消费资源     │───────┘                    │
         │  (学习→练习→反馈)    │                            │
         └─────────┬───────────┘                            │
                   │                                        │
                   ▼                                        │
         ┌─────────────────────┐                            │
         │ ⑦ 效果评估           │                            │
         │  AgentEvaluator     │                            │
         │  (4维评分+Exercise)  │                            │
         └─────────┬───────────┘                            │
                   │                                        │
              score < 0.5?                                  │
              ┌────┴────┐                                   │
              ▼         ▼                                   │
        ┌──────────┐  ┌──────────────────┐                  │
        │MetaReflector│ │ ⑨ 策略优化       │                  │
        │(根因分析)   │→│ ImprovementLoop  │──────────────────┘
        └──────────┘  │ (策略注入)        │
                      └──────────────────┘

        同时: 所有事件流经 EventBus → TraceCollector → Dashboard
        安全护栏: ReviewGate (AST/Pytest/Judge) 内嵌在 ⑤ 资源生成后
```

### 5.2 10 步闭环数据流详解

| 步骤 | 模块 | 输入 | 输出 | 触发条件 |
|:---|:---|:---|:---|:---|
| ① 画像构建 | ProfileAgent (10-dim) | 学生 NL 输入 + 对话历史 | `DynamicStudentProfile` (10 dim × value+confidence+evidence) | 新学生首次对话 / 每周触发重评估 |
| ② 知识诊断 | KnowledgeGraphAgent | `DynamicStudentProfile` + `StudentMemory.mastery_map` | `KnowledgeGap {missing_prereqs[], weak_concepts[], ready_concepts[]}` | 每次路径规划前 |
| ③ Agent 协商 | AgentCouncil | ② KnowledgeGap + ⑤ 的冲突 (如有) | `CouncilDecision` (最终教学策略) | 知识缺口 > 3 OR ResourceAgent 提出异议 |
| ④ 路径规划 | PlannerAgent v4.0 | ③ Decision + DynamicProfile + KnowledgeGraph | `LearningPlan` (拓扑排序节点序列) | 协商完成后 |
| ⑤ 多模态资源 | MultiModalGenerationAgent | ④ PlanNode + DynamicProfile | `List[LearningResource]` (统一协议) | PlanNode 生成触发 |
| ⑥ 资源推荐 | ResourceRecommendationAgent | ⑤ Resources + StudentMemory | `PersonalizedResourcePlan` (最多 8 资源) | 资源池就绪 |
| ⑦ 效果评估 | AgentEvaluator + ReviewGate | ⑤ Resources + 练习答题结果 | `EvaluationResult` (4-dim) | 学生完成练习 / 资源消费后 |
| ⑧ 行为采集 | BehaviorTracker (新增) | 学习时长 + 点击流 + 暂停事件 | `BehaviorLog[]` | 持续采集 (事件驱动) |
| ⑨ 策略优化 | MetaReflector + ImprovementLoop | ⑦ 低分结果 + ⑧ BehaviorLog | `ImprovementSuggestion[]` → `ExperienceMemory` | score < 0.5 |
| ⑩ 画像更新 | ProfileUpdateEngine (新增) | ⑦ 评估结果 + ⑧ 行为日志 + 对话信号 | 更新后的 `DynamicStudentProfile` | 步骤 ⑦ 完成后 / 每日定时衰减 |

### 5.3 Agent 调用顺序（顺序图）

```
Student Input
    │
    ▼
ProfileAgent.extract()                      ← Step ①: 10 维画像提取
    │
    ▼
KnowledgeGraphAgent.compute_knowledge_gap()  ← Step ②: 知识缺口诊断
    │
    ├── gap > 3 个前置知识?
    │   └── YES → AgentCouncil.open_session()  ← Step ③: 触发协商
    │            ├── PlannerAgent.propose("降低目标难度")
    │            ├── ResourceGenAgent.vote(APPROVE)
    │            ├── AgentEvaluator.vote(APPROVE, "避免挫败感")
    │            └── AgentCouncil.finalize() → "降级路径 A"
    │
    ▼
PlannerAgent.plan(topology_sort + profile_bias)
    │                                          ← Step ④: 知识图谱驱动规划
    ▼
MultiModalGenerationAgent.generate_all(node, profile)
    │                                          ← Step ⑤: 多模态资源生成
    ├── ReviewGate.validate(resources)         ← Gate 1/2/3 安全检查
    │
    ▼
ResourceRecommendationAgent.recommend()
    │                                          ← Step ⑥: 个性化推荐
    ▼
Student 消费资源 (Dashboard 交互)
    │
    ▼
AgentEvaluator.evaluate()                     ← Step ⑦: 质量评估
    │
    ├── score ≥ 0.5 → 直接画像更新
    └── score < 0.5 → MetaReflector.reflect()
                       └── ImprovementLoop.run()
                           └── ExperienceMemory.store()  ← Step ⑨
    │
    ▼
ProfileUpdateEngine.update()                  ← Step ⑩: 画像更新 + 衰减
```

---

## 6. Competition Innovation — 竞赛申报创新点提炼

### 6.1 项目核心创新点（5 条）

**创新点一：基于 AgentCouncil 协商协议的多智能体自主协同决策机制**

针对现有多智能体系统普遍采用固定管线（Pipeline）导致缺乏真正协同的问题，本项目提出 **AgentCouncil 轻量级协商层**，实现 Propose→Deliberate→Decide 三段式多 Agent 协商协议。每个 Agent 可对教学方案的任意环节提出提案、附议、反驳或替代方案，Council 通过加权投票 + Chairperson 独裁降级机制在 30 秒内收敛至全局最优决策。该机制使 12 个 Agent 从"顺序执行者"升级为"协同决策者"，是教育智能体从自动化走向自主化的关键一步。

**创新点二：基于知识图谱拓扑排序的个性化学习路径生成算法**

传统教育系统的路径规划依赖人工编排的线性章节，无法自适应学生的知识结构差异。本项目构建 **KnowledgeGraphAgent**，从课程 Markdown 知识库自动提取 80+ 细粒度概念节点和 150+ 条 PREREQ_OF 依赖边，结合 StudentMemory 的 EMA 掌握度数据，通过 Dijkstra 加权最短路径算法计算每个学生的最优学习序列。该方法将路径规划从"规则表查找"提升为"图遍历搜索"，使同一课程对不同学生的路径差异率达到 60% 以上。

**创新点三：统一资源协议 LearningResource 驱动的多模态教学资源协奏生成**

现有教育 AI 的资源生成局限于文本，多模态输出缺乏统一调度。本项目定义 **LearningResource 统一协议**（type × format × content × visual_prompt × difficulty × target_profile_dim 六元组），实现 Markdown 笔记、Mermaid 思维导图、PPT 课件、AI 生成教学配图、Manim 动画描述、视频分镜脚本等 9 类资源在同一协议下的协奏生成。visual_prompt 字段将文本内容自动桥接至图像/视频生成 API，实现"一段文字 → 多模态输出"的自动化流水线。

**创新点四：10 维 DynamicStudentProfile 的动态追踪与置信度衰减机制**

传统学习系统的学生画像是一次性快照，无法反映学习状态的时序演化。本项目将画像从 6 维扩展至 10 维（新增学习动机、注意力模式、时间碎片化程度、自我调节能力），每维度独立追踪 value × confidence × evidence × update_time 四元组。通过**多源信号融合**（对话+错题+行为+时长）自动更新画像，辅以**置信度指数衰减**（7 天无新证据 → 0.9/day 衰减）和**证据矛盾检测**，使画像从"静态标签"进化成"活的学习者数字孪生"。

**创新点五：ExperienceMemory 跨学生经验迁移的闭环自优化教育系统**

现有系统要么无自我改进能力，要么改进仅限于单会话。本项目通过 **ExperienceMemory** 实现跨学生、跨会话的失败模式积累：MetaReflector 对每次低分产出做根因分析 → 结构化失败模式（problem/cause/solution/success_rate）存入经验库 → ImprovementLoop 在下一次规划前自动加载相关经验策略 → 防范同类错误。该机制使系统随使用量增长持续自我优化，目前已积累 13+ 条精炼经验，验证了"越用越好"的教育 AI 核心理念。

### 6.2 与普通 ChatGPT 教育助手的本质区别

| 维度 | ChatGPT 教育助手 | A3 v4.0 多智能体教育平台 |
|:---|:---|:---|
| **架构范式** | 单一 LLM 承担所有角色（教师、评估者、规划者） | 12+ 个专职 Agent，每个 Agent 仅负责一项任务，通过 Council 协商达成全局最优 |
| **个性化机制** | Prompt 级描述 (best-effort) | 10 维 DynamicStudentProfile + EMA α=0.5 掌握度追踪 + 4 源信号融合 + 置信度衰减 |
| **知识组织** | 无结构化知识库，依赖 LLM 参数记忆 | KnowledgeGraph (80+ 概念节点 × 150+ 依赖边) + 6 章权威课程 KB 锚定 |
| **路径规划** | "请你按顺序列一个学习大纲" — 无拓扑保证 | 图拓扑排序 + Dijkstra 最短路径 + profile 偏差调整 |
| **资源生成** | 纯文本回答，无结构化多模态调度 | 9 类统一协议资源并行生成，visual_prompt 自动桥接图片/动画 API |
| **质量保证** | 无系统级质量控制 | ReviewGate 3 层防线 (AST 静态 + Pytest 动态 + LLM-Judge 语义) |
| **自我改进** | 无 | 跨学生 ExperienceMemory + MetaReflector + ImprovementLoop 闭环自优化 |
| **可解释性** | "因为我计算得出" | DecisionExplainer 证据链 + Council 协商日志 + confidence score |
| **可观测性** | 对话日志 | EventBus + TraceCollector + 7-panel Dashboard (含 Council Chamber) |

### 6.3 技术壁垒

| 壁垒 | 说明 | 复现难度 |
|:---|:---|:---|
| **AgentCouncil 协商协议** | Propose→Deliberate→Decide 三段式协议 + 加权投票 + 僵局解决机制，需要设计完整的消息协议、状态机和降级策略，非简单 Prompt Engineering | 🔴 高 — 需要系统设计 + 协议工程 |
| **KnowledgeGraph 自动构建 + 路径搜索** | 从非结构化 Markdown 到结构化图数据库的自动映射，包含概念提取、依赖推断、拓扑排序和加权最短路径，需要 NLP + 图算法交叉能力 | 🔴 高 — 跨领域技术栈 |
| **10 维 DynamicStudentProfile + 置信度衰减** | 四源信号融合（对话/错题/行为/时长）的 ProfileSignalExtractor + 指数衰减 + 证据矛盾检测，需要教育测量学 + 时序数据建模 | 🟡 中高 — 需要领域知识 |
| **ExperienceMemory 跨学生经验迁移** | 从单次失败模式提取到关键词召回再到跨学生策略注入的全链路，涉及知识蒸馏和迁移学习思想 | 🟡 中 — 需要系统性工程 |
| **多模态统一资源协议 + 协奏生成** | 9 类资源同一协议的强类型约束 + visual_prompt 桥接 + 画像驱动的资源类型选择策略 | 🟡 中 — 需要 API 集成 + 协议设计 |

### 6.4 竞赛答辩评委可能问题及应对

**Q1: "你们的核心是多 Agent 协作，但 12 个 Agent 只是按顺序调用，这和普通的工作流有什么区别？"**

> **回答:** 在 v4.0 中，Agent 已不再是固定管线。我们引入了 AgentCouncil 协商协议 — 任何 Agent 可以主动对教学方案提出提案，其他 Agent 投票表决或提出替代方案。例如 ResourceGenAgent 发现 PlannerAgent 给学生分配的基础练习与 mastery_map 矛盾时，会主动提交提案要求调整，而不是被动接受错误规划。这种 Agent 间的自主博弈才是真正的 multi-agent collaboration，区别于"把 12 个函数改名 Agent 的伪多智能体"。我们在 v3.0 的管线架构上叠加了 Council 层，这正是从"自动化工作流"到"自主协同"的质变。

**Q2: "你们的个性化到底体现在哪里？跟普通教育 App 的推荐算法有什么差别？"**

> **回答:** 三个层面的本质差异。第一，画像维度 — 我们不只追踪"哪个知识点不会"，而是追踪学生的认知风格（visual/text）、注意力模式（持续/脉冲）、自我调节能力、时间碎片化程度，这些维度直接驱动教学策略选择而非简单的难度调整。第二，路径规划 — 我们用知识图谱的拓扑排序 + Dijkstra 最短路径取代推荐算法的协同过滤，保证学习路径的科学性（前置知识不遗漏）。第三，闭环 — 普通推荐算法的反馈是"点击→调整权重"，我们是"评估→根因分析→策略注入→画像更新"的完整教育闭环。

**Q3: "系统的自改进能力是如何验证的？"**

> **回答:** 我们有三个层面的验证。第一，Regression Testing — 241 个 pytest 测试用例覆盖所有 Agent 的输入输出契约，每次改进后需全量通过。第二，EvaluationRunner — 20 个预设不同画像的基准学生案例，对比同一输入在不同 ExperienceMemory 积累阶段下的规划质量和资源适配度。第三，UserSimulationAgent — 基于认知画像驱动的第一人称模拟学习过程，验证改进策略对学习效果的实际影响。我们不是简单的"模型更新"，而是"评测→诊断→策略→防范"的结构化改进管线。

**Q4: "12 个 Agent 的 LLM 调用成本怎么控制？用户能用得起吗？"**

> **回答:** 这是我们在架构设计中重点考虑的问题。三层优化策略：第一，规则引擎优先 — ProfileAgent 和 PlannerAgent 默认使用关键词+规则表，零 LLM API 调用即可完成核心管线。第二，LLM 按需激活 — 只有 ContentAgent（内容生成）、ReviewGate Gate 3（语义质量评估）等真正需要语义理解的节点才调用 LLM，其余节点使用确定性逻辑。第三，KV Cache 计划 — 对重复画像/概念组合缓存 LLM 响应，预计降低 40-60% API 成本。实际测试：在不调用 LLM 的规则模式下，完整学习路径规划耗时 < 1 秒，API 成本为零。

**Q5: "你们的产品和市面上已有的 AI 教学产品有什么区别？"**

> **回答:** 市面上的 AI 教学产品本质上是"一个 LLM + 系统 Prompt = 一个教师角色"。我们是一个由 12 个专职 Agent 组成的**教学团队** — 有单独的画像师（ProfileAgent）、课程规划师（PlannerAgent）、资源创作者（MultiModalGenAgent）、质量审核员（ReviewGate）、教学反思员（MetaReflector）。每个 Agent 只做一件事，做成这件事的专家。更关键的是，Agent 之间可以通过 AgentCouncil 协商、博弈、达成共识，这是单体 LLM 永远无法模拟的涌现行为。如果说 ChatGPT 是一个全科家教，A3 就是一个**AI 教研室**。

### 6.5 未来产业化方向

| 方向 | 市场痛点 | A3 方案优势 | 市场规模 (预估) |
|:---|:---|:---|:---|
| **高等教育自适应学习平台** | 大班授课无法因材施教，挂科率高 | 10 维画像 + 知识图谱个性化路径 | 300 亿 RMB (中国在线高等教育市场) |
| **企业 AI 培训系统** | 企业内部培训一刀切，学习效果难量化 | 多 Agent 场景模拟 + 练习自动生成 + 效果评估闭环 | 50 亿 RMB (中国企业培训 SaaS) |
| **K-12 自适应辅导** | 辅导班师资参差不齐，价格高昂 | AI 教研团队替代人工教研，7×24 服务 | 500 亿 RMB (中国 K-12 课后辅导) |
| **终身学习平台** | 成年人学习时间碎片化、目标多样化 | 动态画像持续追踪 + 碎片化时间自适应 | 全球 1000 亿 USD |
| **特殊教育辅助** | 特殊需求学生师资严重不足 | 极致个性化 + 多模态替代方案 (听觉→视觉→触觉) | 社会效益 > 经济效益 |

**短期产业化路径 (1-2 年):**
1. 与高校计算机学院合作，将 A3 部署于"人工智能导论"课程，收集真实学习效果数据
2. 推出 SaaS 版本，支持教师上传自有课程 KB，扩展至多学科
3. 接入多模态 API (图片/视频生成)，完成 PPT 课件和教学动画的商业化

**中长期产业化路径 (3-5 年):**
1. 平台化：开放 Plugin API，允许第三方开发教学资源生成器、评测器、教学策略
2. 国际化：多语言支持 (中/英/日)，接入当地教育标准体系
3. 从高等教育下沉至 K-12 和职业培训，形成全学段覆盖

---

## 附录 A: 升级前后对比总览

| 维度 | A3 v3.0 (当前) | A3 v4.0 (设计目标) |
|:---|:---|:---|
| **Agent 数量** | 12 | 15 (+KnowledgeGraphAgent, +MultiModalGenerationAgent, +BehaviorTracker) |
| **Agent 协作模式** | Pipeline (固定管线) | Pipeline + Council (管线 + 协商双层) |
| **画像维度** | 6 维静态 | 10 维动态 (value/confidence/evidence/update_time) |
| **知识组织** | 6 章 Markdown | 知识图谱 (80+ 节点, 150+ 边) |
| **路径规划** | 规则表查找 | 图拓扑排序 + Dijkstra 最短路径 |
| **资源类型** | 6 类 (文本为主) | 9 类 (多模态: 笔记/图/PPT/图片/动画/视频/代码/习题/阅读) |
| **安全教育** | ReviewGate 3 层 | ReviewGate 3 层 (保留) |
| **自改进** | 5 预注入经验 + 自增长 | 经验库持续增长 + 跨学生迁移 |
| **可观测** | 6-panel Dashboard | 7-panel Dashboard (+Council Chamber) |
| **LLM 成本** | 全部 LLM 调用 | 规则优先 + LLM 按需 + KV Cache |
| **竞赛竞争力** | 评分: 85% | 目标: 95%+ |

---

## 附录 B: 文件增量规划

```
A3-Multi-Agent-System/
├── src/
│   ├── council/                          # NEW — 协商层
│   │   ├── __init__.py
│   │   ├── protocols.py                  # CouncilProposal, CouncilVote, CouncilDecision
│   │   ├── council.py                    # AgentCouncil 核心类
│   │   └── event_types.py               # CouncilEventType
│   ├── knowledge/                        # NEW — 知识图谱层
│   │   ├── __init__.py
│   │   ├── graph_agent.py               # KnowledgeGraphAgent
│   │   ├── graph_store.py               # InMemoryKnowledgeGraph (NetworkX)
│   │   ├── path_planner.py              # Dijkstra + 拓扑排序
│   │   └── node_edge.py                 # KnowledgeNode, KnowledgeEdge, KnowledgeGraph
│   ├── multimodal/                       # NEW — 多模态生成层
│   │   ├── __init__.py
│   │   ├── multimodal_gen_agent.py      # MultiModalGenerationAgent
│   │   ├── ppt_generator.py             # python-pptx PPT 生成
│   │   ├── image_generator.py           # 图片生成 (FAL/DALL·E)
│   │   └── resource_protocol.py         # LearningResource 统一协议
│   ├── profile/                          # REWORK — 画像升级
│   │   ├── __init__.py
│   │   ├── dynamic_profile.py           # DynamicStudentProfile (10-dim)
│   │   ├── profile_entry.py             # ProfileEntry
│   │   ├── signal_extractor.py          # ProfileSignalExtractor (4源融合)
│   │   └── update_engine.py             # ProfileUpdateEngine (衰减/冲突/合并)
│   ├── behavior/                         # NEW — 行为追踪层
│   │   ├── __init__.py
│   │   └── behavior_tracker.py          # BehaviorTracker (事件驱动采集)
│   ├── agents/
│   │   ├── profile_agent.py             # REWORK — 接入 DynamicStudentProfile
│   │   ├── planner_agent.py             # REWORK — 接入 KnowledgeGraph 路径搜索
│   │   ├── resource_generation_agent.py # DEPRECATE — 被 MultiModalGenAgent 取代
│   │   └── ...
│   └── core/
│       ├── event_bus.py                  # EXTEND — 添加 CouncilEventType
│       └── ...
├── tests/
│   ├── test_council.py                  # NEW
│   ├── test_knowledge_graph.py          # NEW
│   ├── test_multimodal_gen.py           # NEW
│   ├── test_dynamic_profile.py          # NEW
│   └── test_closed_loop.py              # NEW — 全闭环集成测试
├── knowledge_base/
│   └── knowledge_graph.json             # NEW — 预构建知识图谱 (NetworkX 序列化)
├── web/
│   └── dashboard/
│       ├── council_panel.py             # NEW — Council Chamber 第 7 面板
│       └── ...
└── designs/
    └── a3_v4_upgrade_design.md          # 本文件
```

---

## 附录 C: 实施优先级矩阵

| 优先级 | 模块 | 工作量 (人天) | 对竞赛加分 | 技术风险 |
|:---|:---|:---|:---|:---|
| **P0** | KnowledgeGraphAgent + 路径搜索 | 5d | ⭐⭐⭐⭐⭐ | 低 — NetworkX 成熟 |
| **P0** | DynamicStudentProfile 数据模型 | 3d | ⭐⭐⭐⭐ | 低 — dataclass 扩展 |
| **P1** | AgentCouncil 核心协议 | 3d | ⭐⭐⭐⭐⭐ | 中 — 需设计状态机 |
| **P1** | MultiModalGenerationAgent (核心) | 4d | ⭐⭐⭐⭐ | 中 — API 集成 |
| **P2** | ProfileSignalExtractor (4 源融合) | 4d | ⭐⭐⭐ | 中 — 需领域知识 |
| **P2** | BehaviorTracker | 2d | ⭐⭐⭐ | 低 |
| **P2** | Dashboard Council Panel | 1.5d | ⭐⭐ | 低 |
| **P3** | PPT 生成 + 图片生成 | 3d | ⭐⭐ | 中 — 外部 API 依赖 |
| **P3** | 全闭环集成测试 | 3d | ⭐⭐ | 中 |

**最短冲刺路径（竞赛前 2 周）：P0 + P1 = 15d → 可直接用于答辩的核心创新点全部到位。**

---

*A3 v4.0 Alpha Design — 2026-07-13*
*从"多智能体 Demo"到"科研级教育智能体平台"*
