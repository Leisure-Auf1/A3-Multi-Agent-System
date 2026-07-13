# Veritas_Core — Security Architecture

> **Veritas = 可信系统：可信知识 × 可信生成 × 可信Agent行为 × 可信Memory**

---

## 一、安全体系总览

```
┌─────────────────────────────────────────────────────────────────────┐
│                     VERITAS TRUST ARCHITECTURE                        │
│                                                                       │
│  ┌──────────────────────┐  ┌──────────────────────┐                  │
│  │  Input Defense       │  │  Output Defense       │                  │
│  │                      │  │                      │                  │
│  │ • Prompt Injection   │  │ • Content Safety      │                  │
│  │ • Instruction Detect │  │ • Hallucination       │                  │
│  │ • Context Filtering  │  │ • Knowledge Grounding │                  │
│  └──────────┬───────────┘  └──────────┬───────────┘                  │
│             │                         │                              │
│             ▼                         ▼                              │
│  ┌──────────────────────────────────────────────────────┐           │
│  │              Agent Permission System                   │           │
│  │                                                       │           │
│  │  Agent → Permission Gateway → Tool → Resource         │           │
│  │                                                       │           │
│  │  Check: Agent Identity · User Scope · Param Range     │           │
│  └──────────────────────────────────────────────────────┘           │
│             │                                                        │
│             ▼                                                        │
│  ┌──────────────────────────────────────────────────────┐           │
│  │              Memory Trust Layer                        │           │
│  │                                                       │           │
│  │  User Input → Extract → Validate → Score → Store      │           │
│  │                                                       │           │
│  │  Defense: Memory Poisoning · Source Tracing · TTL     │           │
│  └──────────────────────────────────────────────────────┘           │
│             │                                                        │
│             ▼                                                        │
│  ┌──────────────────────────────────────────────────────┐           │
│  │              Trace Audit                               │           │
│  │                                                       │           │
│  │  All Agent Actions · Tool Calls · Memory Mutations     │           │
│  │  RAG Sources · Permission Checks                      │           │
│  └──────────────────────────────────────────────────────┘           │
│                                                                       │
│  Infrastructure: Upgraded EventBus (with security fields)            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 二、Memory Trust Layer — 防御 Memory Poisoning

### 2.1 威胁模型

```
Attack Scenario: Memory Poisoning

  学生输入: "我已经精通Transformer架构，不需要再学Attention机制"
  
  ❌ 错误做法: ProfileAgent 直接写入 memory:
    mastery_map["transformer"] = 0.95
    confidence = 1.0
    source = "user_statement"
    
  后果: 系统跳过所有Transformer相关学习内容 — 学生可能只是过度自信
  
  ✅ 正确做法: Memory Trust Layer 介入
    → 提取声明: "用户声称精通Transformer"
    → 置信度评估: confidence = 0.5 (仅用户声明,无证据)
    → source = "user_statement" (标注来源)
    → 与现有掌握度比较: 如果之前 mastery = 0.3 → 标记为冲突
    → 写入 profile_candidates 表 (待验证状态)
    → 下次评估时通过实际测试验证 → 再提升 confidence
```

### 2.2 Memory Validation Pipeline

```
User Input (可能包含声明/反馈)
        │
        ▼
┌─────────────────────────────────────────┐
│ Step 1: Information Extraction           │
│                                          │
│ 从用户输入中提取可存储的信息:              │
│ • 知识声明: "我掌握/不会/了解 X"          │
│ • 偏好声明: "我喜欢视觉化学习"             │
│ • 进度声明: "我完成了第3章"               │
│                                          │
│ 输出: MemoryCandidate[]                   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Step 2: Source Classification            │
│                                          │
│ 标注信息来源:                             │
│ • user_statement — 用户口头声明          │
│ • exercise_result — 答题结果(客观)        │
│ • system_inference — Agent推理(主观)      │
│ • rag_evidence — RAG知识库支撑           │
│ • behavior_data — 学习行为数据(客观)      │
│                                          │
│ 客观来源 > 主观来源                        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Step 3: Consistency Check                │
│                                          │
│ 检查新数据是否与现有记忆冲突:              │
│ • 同概念掌握度冲突检测                     │
│ • 偏好突变检测 (频繁跳变 = 可疑)          │
│ • 进度跳跃检测 (跳过章节 = 可疑)           │
│                                          │
│ 冲突 → 不直接覆盖, 进入仲裁队列             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Step 4: Confidence Scoring               │
│                                          │
│ 基础分 + 来源加权:                         │
│                                          │
│ 来源            │ 权重  │ 基础 confidence  │
│ exercise_result │ 0.35  │ 0.90            │
│ behavior_data   │ 0.25  │ 0.80            │
│ rag_evidence    │ 0.20  │ 0.85            │
│ system_inference│ 0.15  │ 0.60            │
│ user_statement  │ 0.05  │ 0.50            │
│                                          │
│ confidence = Σ(source_weight × base_conf) │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Step 5: TTL Decision                     │
│                                          │
│ 根据 confidence 决定有效期:               │
│                                          │
│ confidence ≥ 0.8 → 永久 (仍需定期复核)     │
│ 0.6 ≤ conf < 0.8 → 30天 (到期重新验证)    │
│ 0.4 ≤ conf < 0.6 → 7天  → 存入 candidates│
│ conf < 0.4       → 不存入 → 提示验证      │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Step 6: Dual-State Storage               │
│                                          │
│ 每条Memory记录有两种状态:                 │
│                                          │
│ ① status = "confirmed"                   │
│    → 可用于Agent决策                      │
│    → 有足够证据支撑 (confidence ≥ 0.8)    │
│                                          │
│ ② status = "candidate"                   │
│    → 不用于Agent决策                      │
│    → 等待更多证据验证                      │
│    → 下次评估时触发验证                    │
│    → 验证通过 → confirmed                │
│    → 验证失败 → rejected + 记录原因        │
└─────────────────────────────────────────┘
```

### 2.3 Memory Record Schema

```python
@dataclass
class MemoryRecord:
    """所有Memory写入的标准化格式"""
    record_id: str            # UUID
    student_id: str
    memory_type: str          # "profile" | "mastery" | "preference" | "weak_point"
    
    # 内容
    content: Dict[str, Any]   # 实际存储的数据
    
    # 安全元数据 (每条必填)
    source: str               # "user_statement" | "exercise_result" | ...
    confidence: float         # 0.0-1.0
    evidence: List[str]       # 证据引用 (如 exercise_id, rag_chunk_id)
    created_at: str           # ISO timestamp
    created_by: str           # 哪个Agent创建
    session_id: str           # 来源会话
    
    # 验证状态
    status: str               # "candidate" | "confirmed" | "rejected"
    verification_count: int   # 被验证次数
    last_verified: str        # 最后验证时间
    verified_by: str          # 验证方 (EvaluationAgent | ReflectionAgent)
    
    # TTL
    expires_at: Optional[str] # 过期时间 (低confidence记录)
    
    # 冲突
    conflicts_with: List[str] # 与哪些记录冲突 (record_id列表)
    resolution: str           # "merged" | "replaced" | "kept_both"
```

### 2.4 Database Schema

```sql
-- 扩展 mastery_tracking 表: 每条记录必须带安全元数据
CREATE TABLE mastery_tracking_v2 (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64) NOT NULL,
    concept         VARCHAR(128) NOT NULL,
    mastery_score   FLOAT DEFAULT 0.5,
    
    -- 安全字段
    source          VARCHAR(32) NOT NULL,        -- 信息来源
    confidence      FLOAT NOT NULL DEFAULT 0.5,  -- 置信度
    evidence        JSONB DEFAULT '[]',          -- 证据引用
    status          VARCHAR(16) DEFAULT 'candidate', -- candidate | confirmed
    last_verified   TIMESTAMPTZ,
    verification_count INT DEFAULT 0,
    created_by      VARCHAR(64),                 -- Agent名称
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(student_id, concept)
);

-- Memory候选记录表 (未经验证的数据)
CREATE TABLE memory_candidates (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64) NOT NULL,
    memory_type     VARCHAR(32) NOT NULL,
    content         JSONB NOT NULL,
    source          VARCHAR(32) NOT NULL,
    confidence      FLOAT NOT NULL,
    evidence        JSONB DEFAULT '[]',
    session_id      VARCHAR(64),
    
    -- 验证
    status          VARCHAR(16) DEFAULT 'pending', -- pending | verified | rejected
    verified_by     VARCHAR(64),
    verified_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    
    -- 冲突
    conflicts_with  JSONB DEFAULT '[]',
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,  -- TTL: 低confidence候选记录自动过期
    
    INDEX idx_candidates_status (student_id, status),
    INDEX idx_candidates_expiry (expires_at)
);

-- Memory变更审计日志
CREATE TABLE memory_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64) NOT NULL,
    record_id       VARCHAR(128),
    action          VARCHAR(32),   -- create | update | verify | reject | delete
    actor           VARCHAR(64),   -- Agent或用户
    old_value       JSONB,
    new_value       JSONB,
    reason          TEXT,
    trace_id        VARCHAR(128),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 三、Agent Permission System

### 3.1 Agent-Capability Matrix

```
                    ┌──────────────┬──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
                    │ ProfileAgent │KnowledgeAgent│ PlannerAgent │ResourceAgent │EvaluationAgt │ReflectionAgt │
┌───────────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ READ  profile     │     ✅       │     ✅       │     ✅       │     ✅       │     ✅       │     ✅       │
│ READ  history     │     ✅       │     ✅       │     ✅       │     -       │     ✅       │     ✅       │
│ READ  knowledge   │     -       │     ✅       │     ✅       │     ✅       │     -       │     -       │
│ READ  exercises   │     -       │     -       │     -       │     ✅       │     ✅       │     -       │
├───────────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ WRITE profile     │  candidate   │     -       │     -       │     -       │     -       │  confirmed   │
│ WRITE history     │     -       │     -       │     -       │     -       │     ✅       │     ✅       │
│ WRITE mastery     │  candidate   │     -       │     -       │     -       │  candidate   │  confirmed   │
│ WRITE weak_point  │  candidate   │     -       │     -       │     -       │  candidate   │  confirmed   │
├───────────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ LLM CALL          │     ✅       │     -       │     ✅       │     ✅       │     ✅       │     ✅       │
│ RAG QUERY         │     -       │     ✅       │     ✅       │     ✅       │     -       │     -       │
│ GEN RESOURCE      │     -       │     -       │     -       │     ✅       │     -       │     -       │
│ RUN EVALUATION    │     -       │     -       │     -       │     -       │     ✅       │     -       │
├───────────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┼──────────────┤
│ DELETE memory     │     ❌       │     ❌       │     ❌       │     ❌       │     ❌       │     ❌       │
│ ADMIN db          │     ❌       │     ❌       │     ❌       │     ❌       │     ❌       │     ❌       │
│ MODIFY system     │     ❌       │     ❌       │     ❌       │     ❌       │     ❌       │     ❌       │
└───────────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘

图例:
  ✅      = 直接允许
  ❌      = 禁止 (拒绝 + 记录审计)
  candidate = 允许写入 Memory Candidates (需验证)
  confirmed = 允许直接写入 Confirmed Memory
  -        = 不可用 (该Agent不需要此能力)
```

关键点:
- **ProfileAgent 只能写 candidate** — 用户输入不可直接进入长期画像
- **ReflectionAgent 可以写 confirmed** — 基于评估证据（客观数据），confidence高
- **EvaluationAgent 写 mastery candidate** — 评估结果仍需验证
- **没有任何 Agent 有 DELETE/ADMIN 权限**

### 3.2 Tool Call Gateway

```
Agent调用工具流程:

  ResourceAgent.generate("笔记", topic="Attention机制")
        │
        ▼
  ┌────────────────────────────────────────────┐
  │          Tool Call Gateway                   │
  │                                              │
  │  ① Identity Check                            │
  │     当前调用者: ResourceAgent                 │
  │     → 查找 Agent Permission Matrix            │
  │     → ResourceAgent 有 GEN_RESOURCE 权限?    │
  │     → ✅                                     │
  │                                              │
  │  ② Parameter Check                           │
  │    参数: topic="Attention机制"               │
  │    → topic 在允许范围内吗?                    │
  │    → 是否有注入标记 (特殊分隔符/指令)?        │
  │    → ✅                                     │
  │                                              │
  │  ③ Scope Check                               │
  │    → 该学生的 learning_goal 包含此 topic?     │
  │    → 该 course 的 knowledge_base 有此内容?    │
  │    → ✅                                     │
  │                                              │
  │  ④ Audit Record                              │
  │    记录: agent=ResourceAgent                  │
  │          action=GEN_RESOURCE                 │
  │          params={topic, type}                │
  │          trace_id=xxx                        │
  │          timestamp=...                       │
  │                                              │
  │  ⑤ Forward to Tool                           │
  │    → DocumentGenerator.generate(...)         │
  └────────────────────────────────────────────┘
```

### 3.3 Gateway Implementation

```python
@dataclass
class PermissionRule:
    agent: str           # Agent名称
    action: str          # 操作类型
    resource: str        # 资源类型 (profile/mastery/history/...)
    access_level: str    # "read" | "candidate" | "confirmed" | "denied"

class ToolCallGateway:
    """Agent工具调用网关 — 所有Agent调用必须经过此处"""

    # Agent权限矩阵
    PERMISSIONS: List[PermissionRule] = [...]

    def authorize(self, agent: str, action: str, params: dict,
                  context: AgentContext) -> AuthorizationResult:
        """
        检查顺序:
          1. Agent身份 → 是否有此action权限
          2. 参数范围 → params是否合法
          3. 用户作用域 → 是否在该学生的数据范围内
          4. 审计记录 → 无论通过与否都记录
        """
        # Step 1: Permission check
        rule = self._find_rule(agent, action)
        if not rule:
            return AuthorizationResult(
                allowed=False,
                reason=f"Agent '{agent}' has no permission for '{action}'",
                audit_id=self._audit(agent, action, False, reason)
            )

        # Step 2: Parameter sanitization
        safe_params = self._sanitize_params(params)
        if safe_params is None:
            return AuthorizationResult(
                allowed=False,
                reason="Parameters contain injection patterns",
                audit_id=self._audit(agent, action, False, "injection_detected")
            )

        # Step 3: Scope check
        if not self._in_scope(agent, action, safe_params, context):
            return AuthorizationResult(
                allowed=False,
                reason="Action out of student scope",
                audit_id=self._audit(agent, action, False, "out_of_scope")
            )

        # Step 4: Audit + Forward
        audit_id = self._audit(agent, action, True, safe_params)
        return AuthorizationResult(allowed=True, audit_id=audit_id)

    def _sanitize_params(self, params: dict) -> Optional[dict]:
        """参数清洗 — 防止注入"""
        for key, value in params.items():
            if isinstance(value, str):
                # 检测指令注入模式
                if any(pattern in value.lower() for pattern in [
                    "ignore previous",
                    "system prompt",
                    "<|im_start|>",
                    "you are now",
                    "new instructions:",
                    "forget everything",
                ]):
                    return None
                # 截断超长输入
                if len(value) > 5000:
                    value = value[:5000]
        return params
```

---

## 四、Prompt Injection Defense

### 4.1 多层防御

```
学生输入
    │
    ▼
┌────────────────────────────────────────────┐
│ Layer 1: Input Sanitization                 │
│                                              │
│ • 移除特殊控制字符                            │
│ • 规范化 Unicode                             │
│ • 检测分隔符注入 (如 "---SYSTEM---")         │
│ • 长度限制 (≤2000 chars)                     │
└──────────────────┬─────────────────────────┘
                   │ cleaned_text
                   ▼
┌────────────────────────────────────────────┐
│ Layer 2: Instruction Detection              │
│                                              │
│ 检测模式:                                    │
│ • "忽略之前的指令"                            │
│ • "你的新任务是..."                           │
│ • "忘记你的系统prompt"                       │
│ • "你现在是..." (角色劫持)                    │
│ • 特殊token注入 (<|im_start|>等)             │
│                                              │
│ 使用: 规则匹配 + LLM-as-Judge (轻量)         │
└──────────────────┬─────────────────────────┘
                   │ suspicious?
                   ▼
┌────────────────────────────────────────────┐
│ Layer 3: Context Isolation                   │
│                                              │
│ 构建LLM Prompt时:                            │
│ • 学生输入 = user_content (独立字段)         │
│ • 系统指令 = system_prompt (不可覆盖)        │
│ • RAG上下文 = knowledge_context (分离)       │
│                                              │
│ Template:                                    │
│ ┌──────────────────────────────────┐        │
│ │ [SYSTEM] 你是教学Agent...         │        │
│ │ (不可被用户输入修改)               │        │
│ ├──────────────────────────────────┤        │
│ │ [KNOWLEDGE] RAG检索到的知识...     │        │
│ │ (课程知识,不可污染)                │        │
│ ├──────────────────────────────────┤        │
│ │ [STUDENT] 用户输入: {text}        │        │
│ │ (隔离在独立字段)                   │        │
│ └──────────────────────────────────┘        │
└──────────────────┬─────────────────────────┘
                   │
                   ▼
┌────────────────────────────────────────────┐
│ Layer 4: Output Validation                   │
│                                              │
│ 检查LLM输出:                                 │
│ • 是否偏离了教学任务?                         │
│ • 是否执行了用户注入的指令?                    │
│ • 是否泄露了系统prompt/内部信息?               │
│                                              │
│ 使用: Trust Layer 幻觉检测 + 内容审核         │
└────────────────────────────────────────────┘
```

### 4.2 Input Sanitizer

```python
class InputSanitizer:
    """用户输入清洗"""

    DANGEROUS_PATTERNS = [
        # 指令注入
        r"ignore\s+(previous|all|above)\s+(instructions?|prompt)",
        r"you\s+are\s+now\s+(a\s+)?",
        r"forget\s+(everything|your|the)",
        r"new\s+(instructions?|system\s+prompt)",
        r"your\s+new\s+task\s+is",
        r"disregard\s+(previous|all)",
        
        # Token注入
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<\|system\|>",
        r"<s>",
        r"\[INST\]",
        
        # 分隔符注入
        r"^---+SYSTEM---+$",
        r"^---+USER---+$",
        r"^---+ASSISTANT---+$",
    ]

    def sanitize(self, text: str) -> SanitizationResult:
        """清洗用户输入"""
        alerts = []

        # Length limit
        if len(text) > 2000:
            text = text[:2000]
            alerts.append("input_truncated")

        # Unicode normalization
        text = unicodedata.normalize("NFKC", text)

        # Pattern detection
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                alerts.append(f"injection_pattern:{pattern}")

        return SanitizationResult(
            text=text,
            safe=len(alerts) == 0,
            alerts=alerts
        )
```

---

## 五、EventBus 安全升级

### 5.1 升级后的 Event Schema

```python
@dataclass
class SecureAgentEvent:
    """安全增强的Agent事件"""
    # 基本信息
    event_id: str               # UUID
    event_type: str             # "agent_action" | "tool_call" | "memory_mutation"
    timestamp: str
    
    # Agent信息
    source_agent: str           # 发起Agent
    target_agent: Optional[str] # 目标Agent (如果有)
    
    # 操作信息
    action: str                 # 操作类型
    status: str                 # "success" | "error" | "unauthorized"
    duration_ms: float
    
    # 安全字段 (新增)
    trace_id: str               # 全链路追踪ID
    session_id: str             # 会话ID
    permission_level: str       # "read" | "candidate" | "confirmed"
    authorization: str          # "granted" | "denied" | "partial"
    audit_id: str               # 审计记录ID
    
    # 内容摘要
    input_summary: str
    output_summary: str
    
    # 证据
    evidence_refs: List[str]    # RAG chunk IDs, exercise IDs等
    
    # 元数据
    metadata: dict
```

---

## 六、Trace Audit — 完整审计链

### 6.1 审计记录内容

| 审计项 | 记录什么 | 存储 |
|:-------|:---------|:-----|
| **Agent Action** | 哪个Agent, 什么操作, 输入/输出摘要, 耗时 | memory_audit_log |
| **Tool Call** | 哪个Agent调用, 什么工具, 参数, 结果 | memory_audit_log |
| **Memory Mutation** | 修改了什么记录, 旧值→新值, 原因, Agent | memory_audit_log |
| **Permission Check** | 请求者, 请求操作, 是否通过, 原因 | memory_audit_log |
| **RAG Query** | 谁查询, 查询内容, 返回的source IDs | TraceSpan.metadata |
| **LLM Call** | 完整prompt, response, token数, 模型 | prompt_log表 |
| **Injection Alert** | 检测到的模式, 来源输入, 是否阻断 | security_alerts表 |

---

## 七、安全总结

| 安全领域 | 机制 | 保护目标 |
|:---------|:-----|:---------|
| **Memory Poisoning** | 6步Validation Pipeline + Dual-State Storage | 用户声明不直接进入长期画像 |
| **Agent权限** | Agent-Capability Matrix + Tool Call Gateway | 每个Agent只能访问授权能力 |
| **Prompt Injection** | 4层防御: Sanitize→Detect→Isolate→Validate | 学生输入不能操控Agent行为 |
| **EventBus安全** | 每个事件含 trace_id + permission + audit_id | 所有Agent行为可追溯 |
| **审计** | memory_audit_log + TraceSpan + security_alerts | 系统行为完整记录 |
