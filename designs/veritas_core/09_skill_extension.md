# Veritas_Core — Skill System & MCP Extension Architecture

> **定位:** 扩展能力层 (Extension Capability Layer) — 不是核心模块  
> **目标:** 解决大量Skill导致的 Context污染、Tool选择困难、安全风险

---

## 一、Skill System 设计动机

### 1.1 问题

```
❌ 当前A3的问题:
  - 128+ Skills 全部可见 → Context窗口膨胀
  - Agent需要自己选择Tool → 选择困难，容易出错
  - 没有Skill生命周期 → 无法动态加载/卸载
  - 没有权限控制 → Agent可以调用任何Skill
  - Security: Skill = 隐式权限提升
```

### 1.2 解决方案

```
Agent 不做 Tool Discovery
    ↓
Skill Router 负责匹配
    ↓
只注入 Context-Relevant Skills
    ↓
用完自动卸载
```

---

## 二、Skill 架构

```
Agent Layer (6 Cognitive Agents)
    │
    │  "我需要生成一份关于RAG的PPT"
    │
    ▼
┌─────────────────────────────────────────────────────┐
│                Skill Router                           │
│                                                       │
│  ① Intent Analysis:  意图分析 → "ppt_generation"      │
│  ② Skill Matching:   从Registry匹配相关Skills          │
│  ③ Permission Check: Agent有权限调用这些Skills吗?      │
│  ④ Context Budget:   Token预算内最多加载N个Skills      │
│  ⑤ Skill Loading:    动态加载选中的Skills              │
└──────────────┬──────────────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────┐
│                Skill Registry                         │
│                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │ Core Skills │  │ Gen Skills  │  │ MCP Tools   │  │
│  │             │  │             │  │             │  │
│  │ • rag_query │  │ • doc_gen   │  │ • browser   │  │
│  │ • profile_r │  │ • ppt_gen   │  │ • terminal  │  │
│  │ • plan_gen  │  │ • quiz_gen  │  │ • file_ops  │  │
│  │ • eval_run  │  │ • code_gen  │  │ • web_search│  │
│  │             │  │ • mind_gen  │  │             │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 三、Skill Lifecycle Management

### 3.1 生命周期状态机

```
   ┌─────────┐
   │ REGISTER│  注册到Registry (含权限/分类/限制)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ DISCOVER│  Skill Router 匹配到该Skill
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  LOAD   │  加载到Agent Context (注入prompt/tools)
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ EXECUTE │  Agent 调用Skill
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │ EVALUATE│  记录: success_rate, latency, cost
   └────┬────┘
        │
        ▼
   ┌─────────┐
   │  CACHE  │  高频Skill保持热加载 (TTL可配)
   └────┬────┘
        │
        ▼ (idle timeout / context budget exceeded)
   ┌─────────┐
   │ UNLOAD  │  从Context移除, 释放Token预算
   └─────────┘
```

### 3.2 Skill Record

```python
@dataclass
class SkillRecord:
    """Skill注册信息"""
    # 标识
    skill_id: str              # "document_generator_v1"
    skill_name: str            # "Document Generator"
    category: str              # "core" | "generation" | "mcp" | "experimental"
    version: str               # "1.0.0"
    
    # 权限
    permission: str            # "read" | "generate" | "system" (技能的最低权限要求)
    min_agent_level: str       # 需要什么级别的Agent (所有Agent可调 | 特定Agent)
    allowed_agents: List[str]  # ["ResourceAgent", "PlannerAgent"]
    
    # 使用数据
    usage_count: int           # 总调用次数
    success_rate: float        # 成功率 (EMA)
    avg_latency_ms: float      # 平均延迟
    avg_token_cost: int        # 平均Token消耗
    
    # 状态
    status: str                # "active" | "deprecated" | "experimental"
    last_used: str             # ISO timestamp
    cache_priority: int        # 0-10, 越高越容易被热加载
    
    # 触发条件
    triggers: List[str]        # ["ppt", "presentation", "slides"]
    contexts: List[str]        # ["ResourceAgent", "content_generation"]
```

---

## 四、Skill Router

### 4.1 核心逻辑

```python
class SkillRouter:
    """Agent不直接选择Skill，Router负责匹配和加载"""

    def __init__(self, registry: SkillRegistry, context_budget: int = 3000):
        self.registry = registry
        self.context_budget = context_budget  # Token budget for Skills
        self.active_skills: Dict[str, SkillRecord] = {}  # 当前加载的Skills

    def resolve(self, agent: str, intent: str,
                context: AgentContext) -> List[SkillRecord]:
        """
        为给定的Agent+意图匹配最合适的Skills。

        处理流程:
        1. Intent → 匹配Skill triggers
        2. Agent权限过滤
        3. 按 success_rate × cache_priority 排序
        4. Token预算内取Top-K
        5. 加载Skills到Context
        """
        # Step 1: Match
        candidates = self.registry.match(intent=intent)
        
        # Step 2: Filter by permission
        allowed = [s for s in candidates 
                   if agent in s.allowed_agents]
        
        # Step 3: Sort by relevance × success
        scored = sorted(allowed, 
                       key=lambda s: s.success_rate * s.cache_priority,
                       reverse=True)
        
        # Step 4: Budget-aware selection
        selected = []
        tokens_used = 0
        for skill in scored:
            skill_tokens = self._estimate_tokens(skill)
            if tokens_used + skill_tokens <= self.context_budget:
                selected.append(skill)
                tokens_used += skill_tokens
            else:
                break
        
        # Step 5: Load & track
        for skill in selected:
            self._load_skill(skill, context)
            self.active_skills[skill.skill_id] = skill
        
        return selected

    def unload_idle(self, idle_timeout_min: int = 30):
        """卸载空闲Skills，释放Token预算"""
        now = datetime.now(timezone.utc)
        for sid, skill in list(self.active_skills.items()):
            last_used = datetime.fromisoformat(skill.last_used)
            if (now - last_used).total_seconds() > idle_timeout_min * 60:
                self._unload_skill(skill)
                del self.active_skills[sid]
```

### 4.2 为什么需要 Skill Router 而不是 Agent 直接调用

| 方案 | Agent直接调用Tool | Skill Router |
|:-----|:------------------|:-------------|
| **Context** | 所有Tool descriptions占用Token | 只加载相关的Skills |
| **选择逻辑** | Agent自己推理选择(慢+不可靠) | Router确定性匹配(快+可调试) |
| **权限** | 无集中控制 | Router统一检查 |
| **成本** | Context满Token → 贵 | 预算控制 |
| **可观测** | 分散在各Agent | Router统一记录 |

---

## 五、Resource Generation Tools

### 5.1 Agent+Tool架构

```
不是:  ResourceGenerationAgent → 直接生成所有资源
而是:  ResourceGenerationAgent → Skill Router → 选择Generator Tool

ResourceGenerationAgent
    │
    │ "学生需要: 讲义 + PPT + 习题 + 思维导图 + 代码实验"
    │
    ▼
SkillRouter.resolve(
    agent="ResourceAgent",
    intent="document_generation,ppt_generation,quiz_generation,..."
)
    │
    ├── DocumentGenerator     → CourseNotes (Markdown)
    ├── PPTGenerator          → PPT (.pptx)
    ├── QuizGenerator         → Exercises (3级难度)
    ├── CodeLabGenerator      → CodeLab (Python + test stubs)
    └── MindMapGenerator      → MindMap (Mermaid)
```

### 5.2 Generator Tools 定义

```python
@dataclass
class GeneratorTool(SkillRecord):
    """生成器Tool — 每个对应一种资源类型"""
    
    # SkillRecord fields +
    tool_id: str               # "document_generator"
    tool_type: str             # "generator"
    resource_type: str         # "notes" | "ppt" | "mindmap" | "exercises" | "codelab"
    
    # 生成参数
    supports_customization: bool   # 是否支持个性化 (profile注入)
    max_output_tokens: int         # 输出Token上限
    requires_rag_context: bool     # 是否需要RAG知识上下文
    
    # Trust Layer集成
    trust_gates: List[str]         # ["source_check", "grounding", "hallucination"]
    
    category = "generation"
    permission = "generate"
    allowed_agents = ["ResourceAgent"]
```

### 5.3 ResourceAgent → 不再是上帝Agent

```python
class ResourceAgent(BaseAgent):
    """核心资源生成Agent — 通过Skill Router调度Generator Tools"""

    agent_name = "ResourceAgent"

    def generate_resources(self, plan_node: PlanNode,
                           profile: DynamicProfile,
                           knowledge_context: KnowledgeContext
                           ) -> List[Resource]:
        """
        生成流程:
        1. 根据plan_node确定需要哪些资源类型
        2. 通过SkillRouter匹配对应的Generator Tools
        3. Trust Layer检查每个生成结果
        4. 返回可信资源
        """
        resources = []
        for resource_type in plan_node.resource_types:
            # Router匹配
            tool = self.skill_router.resolve(
                agent="ResourceAgent",
                intent=f"{resource_type}_generation",
                context=self.ctx
            )[0]  # 每种类型只有一个Generator
            
            # 执行生成
            result = tool.execute(
                profile=profile,
                knowledge_context=knowledge_context,
                plan_node=plan_node,
            )
            
            # Trust检查
            trust_report = self.trust_pipeline.check(result, knowledge_context)
            if trust_report.overall_trust_score < 0.7:
                result = self._regenerate(tool, ...)
            
            resources.append(result)
            self.record_event("generate", ...)
        
        return resources
```

---

## 六、MCP Extension (可选)

### 6.1 定位

MCP 不是核心模块。只在需要外部工具时使用。

```
Agent
    │
    ▼
Skill Router
    │
    ├── Core Skills (直接可用)
    │   └── DocumentGenerator, QuizGenerator, ...
    │
    └── MCP Adapter (按需启用) ← Extension Layer
        │
        ├── browser-use    (浏览器自动化)
        ├── file-system    (文件操作)
        ├── web-search     (网页搜索)
        └── ...            (其他MCP Servers)
```

### 6.2 MCP Adapter

```python
class MCPAdapter:
    """
    MCP工具适配器 — 将MCP Servers的工具注册到Skill Registry。
    
    设计原则:
    - MCP Tools作为 "external" category skills
    - 所有MCP调用经过ToolCallGateway (权限检查)
    - MCP Tools默认不加载 (按需enable)
    """
    
    def register_mcp_server(self, server_config: dict):
        """
        连接MCP Server → 获取工具列表 → 注册到Skill Registry
        每个MCP Tool作为一个Skill Record, category="mcp"
        """
        client = MCPClient(server_config)
        tools = client.list_tools()
        for tool in tools:
            self.registry.register(SkillRecord(
                skill_id=f"mcp:{tool.name}",
                category="mcp",
                permission="read",  # MCP工具默认只读
                allowed_agents=[],  # 需要显式授权
                ...
            ))
```

---

## 七、Skill System 总结

| 问题 | 传统方案 | Veritas_Core 方案 |
|:-----|:---------|:------------------|
| **Context污染** | 所有Skill描述塞进Context | Skill Router按需加载，Token预算控制 |
| **Tool选择** | Agent自己推理选择 | Router确定性匹配 (intent → triggers) |
| **权限** | Agent可以调任何Tool | Agent-Capability Matrix + Permission Check |
| **生命周期** | 无管理 | REGISTER→DISCOVER→LOAD→EXECUTE→EVALUATE→CACHE→UNLOAD |
| **可观测** | 分散 | Router统一记录 skill usage/success_rate/cost |
| **安全** | MCP Tool = 潜在后门 | 所有MCP Tool经过ToolCallGateway |
| **成本** | 固定Context → 贵 | 用多少加载多少 → 省Token |

**核心原则: Agent代表决策能力，Tool代表执行能力。不要让Agent永久拥有全部Tool — 按需加载，用过即卸。**
