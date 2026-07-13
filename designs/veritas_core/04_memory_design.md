# Veritas_Core — Student Learning Memory 设计

> **三层记忆架构：** Conversation Memory · Student Profile Memory · Learning History Memory  
> **核心原则：** 每层有独立的存储策略、更新时机和查询方式

---

## 一、三层架构总览

```
┌───────────────────────────────────────────────────────────────┐
│                   MEMORY LAYER                                  │
│                                                                 │
│  ┌─────────────────────────┐                                   │
│  │ Conversation Memory      │  ← Redis                         │
│  │ (会话级, TTL=24h)        │    Key: session:{id}:messages    │
│  │                          │    Value: List<Message>           │
│  │ • 当前学习会话的对话历史   │    TTL: 86400                    │
│  │ • 短期上下文窗口           │                                   │
│  │ • 每轮对话的Agent产出      │                                   │
│  └───────────┬─────────────┘                                   │
│              │                                                  │
│              ▼                                                  │
│  ┌─────────────────────────┐                                   │
│  │ Student Profile Memory   │  ← PostgreSQL                    │
│  │ (学生级, 持久, 长期)      │    Table: student_profiles       │
│  │                          │    Table: profile_evolution      │
│  │ • 学生8维动态画像          │    Table: mastery_tracking      │
│  │ • 掌握度 (EMA α=0.5)     │    Table: weak_points           │
│  │ • 画像演化时间线           │                                   │
│  │ • 资源偏好                │                                   │
│  └───────────┬─────────────┘                                   │
│              │                                                  │
│              ▼                                                  │
│  ┌─────────────────────────┐                                   │
│  │ Learning History Memory  │  ← PostgreSQL + Vector DB        │
│  │ (课程级, 持久, 可分析)     │    Table: learning_records      │
│  │                          │    Table: exercise_errors        │
│  │ • 学习记录 (完成/跳过)     │    Table: resource_feedback     │
│  │ • 错题本                  │    Table: experience_lessons (VD)│
│  │ • 资源反馈                │                                   │
│  │ • 经验教训 (跨学生)       │                                   │
│  └─────────────────────────┘                                   │
│                                                                 │
│              MemoryManager (统一入口)                            │
└───────────────────────────────────────────────────────────────┘
```

---

## 二、Conversation Memory (会话记忆)

**存储:** Redis  
**生命周期:** 会话期间 (TTL=24h)  
**用途:** 当前学习会话的上下文窗口，供Agent推理时使用

```python
# 数据结构
@dataclass
class ConversationTurn:
    role: str               # "student" | "agent" | "resource"
    content: str
    agent_name: Optional[str]  # 哪个Agent产出的
    resource_type: Optional[str]  # 如果是资源: "notes" | "exercises" | ...
    timestamp: str
    metadata: dict

class ConversationMemory:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.max_turns = 50  # 最多保留50轮
        self.ttl = 86400     # 24小时

    def add_turn(self, session_id: str, turn: ConversationTurn):
        key = f"session:{session_id}:messages"
        self.redis.rpush(key, json.dumps(turn.__dict__))
        # FIFO: 超过max_turns截断头部
        if self.redis.llen(key) > self.max_turns:
            self.redis.lpop(key)
        self.redis.expire(key, self.ttl)

    def get_context(self, session_id: str, last_n: int = 10
                    ) -> List[ConversationTurn]:
        """获取最近N轮对话作为上下文"""
        key = f"session:{session_id}:messages"
        raw = self.redis.lrange(key, -last_n, -1)
        return [ConversationTurn(**json.loads(r)) for r in raw]

    def get_agent_outputs(self, session_id: str) -> List[ConversationTurn]:
        """获取本会话中所有Agent产出"""
        all_turns = self.get_context(session_id, last_n=50)
        return [t for t in all_turns if t.role == "agent"]
```

**更新时机:**

| 事件 | 操作 |
|:-----|:-----|
| 学生发送消息 | `add_turn("student", ...)` |
| Agent执行完成 | `add_turn("agent", agent_name=..., ...)` |
| 资源生成完成 | `add_turn("resource", resource_type=..., ...)` |
| 会话结束 | Redis TTL自动过期 (24h后清除) |

---

## 三、Student Profile Memory (学生画像记忆)

**存储:** PostgreSQL  
**生命周期:** 永久  
**用途:** 学生的长期学习画像，是所有Agent个性化的基础

### 3.1 数据库 Schema

```sql
-- 学生画像表
CREATE TABLE student_profiles (
    student_id      VARCHAR(64) PRIMARY KEY,
    display_name    VARCHAR(128),
    -- 8维画像
    knowledge_base  VARCHAR(32),        -- junior_dev | mid_level | senior
    learning_goal   TEXT,               -- 学习目标描述
    cognitive_style VARCHAR(32),        -- visual_dominant | text_linear | auditory
    learning_habit  VARCHAR(32),        -- code_sandbox | quiz_first | exploratory
    resource_pref   VARCHAR(32),        -- diagram+code | text_only | video+quiz
    learning_motivation VARCHAR(32),    -- career_advancement | academic | hobby
    time_budget     VARCHAR(32),        -- flexible | 5h | 10h | 20h/week
    frustration_threshold VARCHAR(32),  -- low | medium | high
    -- 元数据
    source          VARCHAR(16),        -- rule | llm (提取方式)
    confidence      FLOAT DEFAULT 0.7,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 画像演化时间线 (记录每次画像变化的推理)
CREATE TABLE profile_evolution (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64) REFERENCES student_profiles(student_id),
    session_id      VARCHAR(64),
    change_type     VARCHAR(32),        -- mastery_update | weak_point_add | ...
    change_detail   JSONB,
    reason          TEXT,               -- 为什么变化 (ReflectionAgent推理)
    evaluation_ref  VARCHAR(128),       -- 关联的评估记录
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 掌握度追踪 (每个概念的EMA追踪)
CREATE TABLE mastery_tracking (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64) REFERENCES student_profiles(student_id),
    concept         VARCHAR(128),       -- 概念名 (如 "async_io", "rag_retrieval")
    mastery_score   FLOAT DEFAULT 0.5,  -- EMA α=0.5
    attempts        INT DEFAULT 0,      -- 练习尝试次数
    last_practiced  TIMESTAMPTZ,
    status          VARCHAR(16) DEFAULT 'learning', -- mastered | learning | weak
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(student_id, concept)
);

-- 薄弱点记录
CREATE TABLE weak_points (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64) REFERENCES student_profiles(student_id),
    concept         VARCHAR(128),
    error_type      VARCHAR(64),        -- 错误类型分类
    occurrence_count INT DEFAULT 1,
    last_error      TIMESTAMPTZ DEFAULT NOW(),
    resolved        BOOLEAN DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mastery_student ON mastery_tracking(student_id);
CREATE INDEX idx_mastery_score ON mastery_tracking(student_id, mastery_score);
CREATE INDEX idx_weak_points_active ON weak_points(student_id) WHERE resolved = FALSE;
```

### 3.2 掌握度 EMA 追踪

```python
@dataclass
class MasteryTracker:
    """概念级掌握度追踪 — EMA α=0.5"""

    def update(self, student_id: str, concept: str,
               new_score: float) -> MasteryRecord:
        """
        EMA公式: new_mastery = old_mastery × 0.5 + new_score × 0.5

        阈值:
          ≥ 0.8 → mastered (跳过)
          0.5-0.8 → learning (标准深度)
          ≤ 0.3 → weak (加大深度 + 练习量)
        """
        old = self.db.query(
            "SELECT mastery_score FROM mastery_tracking "
            "WHERE student_id=%s AND concept=%s",
            (student_id, concept)
        )
        old_score = old["mastery_score"] if old else 0.5
        updated = old_score * 0.5 + new_score * 0.5

        self.db.execute(
            """INSERT INTO mastery_tracking (student_id, concept, mastery_score)
               VALUES (%s, %s, %s)
               ON CONFLICT (student_id, concept)
               DO UPDATE SET mastery_score=%s, updated_at=NOW()""",
            (student_id, concept, updated, updated)
        )
        return MasteryRecord(concept=concept, score=updated, ...)
```

### 3.3 更新时机

| 事件 | 操作 | 触发Agent |
|:-----|:-----|:----------|
| 初次画像提取 | INSERT into student_profiles | ProfileAgent |
| 每次答题后 | mastery_tracking EMA更新 | EvaluationAgent |
| 薄弱点发现 | INSERT/UPDATE weak_points | EvaluationAgent |
| 薄弱点解决 | UPDATE weak_points SET resolved=true | ReflectionAgent |
| 画像维度变化 | INSERT into profile_evolution | ReflectionAgent |
| 偏好微调 | UPDATE student_profiles.resource_pref | ReflectionAgent |

---

## 四、Learning History Memory (学习历史记忆)

**存储:** PostgreSQL (结构化) + ChromaDB (语义/经验教训)  
**生命周期:** 永久  
**用途:** 学习记录、错题分析、资源反馈、跨学生经验

### 4.1 数据库 Schema

```sql
-- 学习记录
CREATE TABLE learning_records (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64),
    session_id      VARCHAR(64),
    plan_node_id    VARCHAR(128),       -- 对应的学习节点
    concept         VARCHAR(128),
    resource_types  TEXT[],             -- 使用的资源类型 ['notes', 'code_lab']
    action          VARCHAR(32),        -- started | completed | skipped | retried
    time_spent_sec  INT,
    behavior_data   JSONB,              -- 学习行为 (停留/滚动/复制/重试)
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 错题本
CREATE TABLE exercise_errors (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64),
    exercise_id     VARCHAR(128),
    concept         VARCHAR(128),
    question_text   TEXT,
    student_answer  TEXT,
    correct_answer  TEXT,
    error_type      VARCHAR(64),        -- 概念错误/语法错误/理解偏差
    attempt_count   INT DEFAULT 1,
    resolved        BOOLEAN DEFAULT FALSE,
    resolved_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 资源反馈
CREATE TABLE resource_feedback (
    id              BIGSERIAL PRIMARY KEY,
    student_id      VARCHAR(64),
    resource_id     VARCHAR(128),
    resource_type   VARCHAR(32),        -- notes | ppt | mindmap | exercise | codelab
    difficulty_rating INT,              -- 1-5 (学生自评难度)
    quality_rating  INT,                -- 1-5 (质量评分)
    helpfulness     INT,                -- 1-5 (是否有帮助)
    comment         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 指标
CREATE INDEX idx_records_student ON learning_records(student_id, created_at DESC);
CREATE INDEX idx_errors_active ON exercise_errors(student_id) WHERE resolved = FALSE;
CREATE INDEX idx_feedback_resource ON resource_feedback(resource_type);
```

### 4.2 经验教训记忆 (Vector DB)

从 A3 的 `ExperienceMemory` 升级，使用 ChromaDB 语义搜索替代关键词匹配。

```python
@dataclass
class ExperienceRecord:
    """跨学生经验教训"""
    problem: str            # 失败模式描述
    cause: str              # 根因分析
    solution: str           # 修复方案
    source: str             # ReflectionAgent | Manual
    success_count: int      # 此方案成功次数
    failure_count: int      # 此方案失败次数
    keywords: List[str]     # 关键词标签
    severity: str           # LOW | MEDIUM | HIGH
    embedding: Optional[List[float]]  # 语义向量

class ExperienceMemoryStore:
    """经验教训存储 — ChromaDB"""

    def __init__(self):
        self.collection = chromadb.PersistentClient(
            path="./storage/chroma"
        ).get_or_create_collection("experience_lessons")

    def search(self, query: str, limit: int = 5) -> List[ExperienceRecord]:
        """语义搜索相关经验 — 替代A3的关键词匹配"""
        results = self.collection.query(
            query_texts=[query],
            n_results=limit,
        )
        return [self._to_record(r) for r in results]

    def add(self, record: ExperienceRecord):
        self.collection.add(
            ids=[uuid4().hex],
            documents=[f"{record.problem}\n{record.cause}\n{record.solution}"],
            metadatas=[{"severity": record.severity, "source": record.source}],
        )

    def update_success_rate(self, record_id: str, successful: bool):
        """EMA更新成功率 — ReflectionAgent调用"""
        ...
```

### 4.3 更新时机

| 事件 | 操作 | 触发 |
|:-----|:-----|:-----|
| 学生开始/完成学习节点 | INSERT learning_records | Orchestrator |
| 学生提交错误答案 | INSERT exercise_errors | EvaluationAgent |
| 学生后续答对薄弱概念 | UPDATE exercise_errors SET resolved=true | ReflectionAgent |
| 学生评价资源 | INSERT resource_feedback | API Layer |
| 反思发现失败模式 | INSERT experience_lessons (ChromaDB) | ReflectionAgent |
| 策略被成功应用 | UPDATE experience_lessons.success_count | ReflectionAgent |

---

## 五、MemoryManager 统一入口

```python
class MemoryManager:
    """三层记忆的统一入口 — 所有Agent通过此接口访问Memory"""

    def __init__(self):
        self.conversation = ConversationMemory(redis_client)
        self.profile = ProfileMemoryStore(pg_pool)
        self.history = HistoryMemoryStore(pg_pool, chroma_client)

    # ── Conversation ──
    def add_conversation_turn(self, session_id, role, content, ...): ...
    def get_session_context(self, session_id, last_n=10): ...

    # ── Profile ──
    def get_student_profile(self, student_id) -> DynamicProfile: ...
    def save_profile(self, student_id, profile: DynamicProfile): ...
    def update_mastery(self, student_id, concept, score): ...
    def add_weak_point(self, student_id, concept, error_type): ...
    def resolve_weak_point(self, student_id, concept): ...
    def record_profile_evolution(self, student_id, change, reason): ...

    # ── History ──
    def record_learning(self, student_id, plan_node, action, ...): ...
    def add_exercise_error(self, student_id, exercise, answer, ...): ...
    def add_resource_feedback(self, student_id, resource_id, ratings): ...
    def recall_experience(self, query, limit=5): ...
    def store_experience(self, problem, cause, solution): ...

    # ── Queries ──
    def get_weak_concepts(self, student_id) -> List[str]: ...
    def get_mastery_summary(self, student_id) -> Dict[str, float]: ...
    def get_recent_errors(self, student_id, days=7): ...
    def get_resource_preference_stats(self, student_id): ...
```

---

## 六、三层对比总结

| 维度 | Conversation | Profile | History |
|:-----|:------------|:--------|:--------|
| **存储** | Redis | PostgreSQL | PostgreSQL + ChromaDB |
| **生命周期** | 24h (TTL) | 永久 | 永久 |
| **更新频率** | 实时 (每轮对话) | 按需 (评估后) | 每步操作 |
| **数据量级** | ~KB (50轮对话) | ~KB (画像+掌握度) | ~MB (长期积累) |
| **查询方式** | Key-Value (session_id) | SQL (student_id) | SQL + 语义搜索 |
| **用途** | 短期上下文注入 | 个性化参数 | 分析+优化+经验复用 |
| **A3继承** | 新增 (A3无Redis) | A3 StudentMemory→PostgreSQL | A3 ExperienceMemory→PG+ChromaDB |
