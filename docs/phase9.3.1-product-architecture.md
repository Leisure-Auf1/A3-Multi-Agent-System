# Phase 9.3.1 — Production-Grade Architecture

> **Version:** 2.0 | **Date:** 2026-07-17 | **Type:** Architecture Design (no code)  
> **Builds on:** `docs/phase9.3-design.md` (577 lines)  
> **Constraint:** Veritas-Core V7 API frozen | Zero Runtime modifications  
> **Foundation:** A3 SQLite DB (5 tables) | ResourceGenerationAgent (508 LOC) | 1064 tests

---

## 1. Resource Artifact Lifecycle

### 1.1 State Machine

```
                    ┌─────────┐
                    │ PENDING │  ← Request received, queued
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
         ┌────────┐ ┌────────┐ ┌────────┐
         │  RULE  │ │  LLM   │ │ MEDIA  │  ← Generation path chosen
         │  GEN   │ │ ENRICH │ │  API   │
         └───┬────┘ └───┬────┘ └───┬────┘
             │          │          │
             └──────────┼──────────┘
                        ▼
                 ┌────────────┐
                 │ GENERATED  │  ← Raw content produced
                 └─────┬──────┘
                       │
                       ▼
            ┌─────────────────────┐
            │   VALIDATING        │  ← Content Validation Layer
            │                     │
            │  ┌─────────────────┐│
            │  │ Academic Check  ││
            │  ├─────────────────┤│
            │  │ Format Check    ││
            │  ├─────────────────┤│
            │  │ Security Filter ││
            │  └────────┬────────┘│
            └───────────┼────────┘
                        │
              ┌─────────┼─────────┐
              ▼                   ▼
       ┌──────────┐        ┌──────────┐
       │  VALID   │        │ REJECTED │  ← Failed validation
       └────┬─────┘        └────┬─────┘
            │                   │
            ▼                   ▼
     ┌────────────┐     ┌────────────┐
     │  STORED    │     │  FALLBACK  │  ← Generate placeholder
     └─────┬──────┘     └─────┬──────┘
           │                  │
           ▼                  ▼
     ┌────────────┐     ┌────────────┐
     │  ACTIVE    │     │  ACTIVE    │  ← Both reach active
     └─────┬──────┘     └─────┬──────┘
           │                  │
           └────────┬─────────┘
                    │
          ┌─────────┼─────────┐
          ▼                   ▼
    ┌──────────┐       ┌──────────┐
    │ EXPIRED  │       │ ARCHIVED │  ← TTL or manual
    └──────────┘       └──────────┘
```

### 1.2 State Transitions

| From | To | Trigger | Action |
|:-----|:--|:--------|:-------|
| PENDING | RULE_GEN | `enrich=False` | Generate via templates |
| PENDING | LLM_ENRICH | `enrich=True` | Call LLM provider |
| PENDING | MEDIA_API | `generate_media=True` | Call image/audio API |
| GENERATED | VALIDATING | Content produced | Enter validation pipeline |
| VALIDATING | VALID | All checks pass | Store to DB |
| VALIDATING | REJECTED | Any check fails | Log rejection reason |
| REJECTED | FALLBACK | Auto-retry policy | Generate placeholder |
| VALID | STORED | Persist to DB | `INSERT INTO resources` |
| FALLBACK | STORED | Placeholder ready | `INSERT INTO resources` |
| STORED | ACTIVE | Ready for consumption | Available to TutorAgent |
| ACTIVE | EXPIRED | TTL exceeded | Mark `expired_at = now()` |
| ACTIVE | ARCHIVED | Manual/user action | Move to archive table |

### 1.3 Caching Strategy

```
Layer 1: In-Memory (LRU, 128 entries, 5min TTL)
    ↓ miss
Layer 2: SQLite (resources table, indexed by topic+level+type)
    ↓ miss
Layer 3: Regenerate (rule-based fallback, always succeeds)

Cache Key: {student_level}:{topic}:{resource_type}:{language}
Cache Invalidation: On course KB update, on user profile change
```

### 1.4 Storage Schema (New Table)

```sql
CREATE TABLE resources (
    id            TEXT PRIMARY KEY,
    topic         TEXT NOT NULL,
    resource_type TEXT NOT NULL,   -- document|mindmap|exercise|code|video|reading|slides|illustration
    student_level TEXT DEFAULT 'beginner',
    language      TEXT DEFAULT 'zh-CN',
    status        TEXT DEFAULT 'pending',  -- pending|generated|validating|valid|rejected|active|expired|archived
    data_json     TEXT NOT NULL,   -- Full resource payload as JSON
    media_urls    TEXT DEFAULT '[]',  -- JSON array of generated image/audio URLs
    fallback_used TEXT DEFAULT '[]',  -- Which fallbacks were activated
    cost_usd      REAL DEFAULT 0.0,
    tokens_used   INTEGER DEFAULT 0,
    generated_by  TEXT DEFAULT 'rule',  -- rule|llm|api
    created_at    TEXT NOT NULL,
    expires_at    TEXT,             -- NULL = never expire
    accessed_at   TEXT,
    access_count  INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}',
    
    FOREIGN KEY (topic) REFERENCES knowledge_topics(id)
);

CREATE INDEX idx_resources_topic_type ON resources(topic, resource_type);
CREATE INDEX idx_resources_status ON resources(status, created_at);
CREATE INDEX idx_resources_level_type ON resources(student_level, resource_type);
```

---

## 2. Multimodal Gateway Provider Adapter

### 2.1 Abstract Provider Interface

```python
class GatewayProvider(ABC):
    """Abstract multimodal generation provider."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is reachable. Returns False → activate fallback."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Synchronous generation."""

    @abstractmethod
    async def generate_async(self, request: GenerationRequest) -> GenerationResult:
        """Async generation for non-blocking usage."""

    @abstractmethod
    def estimate_cost(self, request: GenerationRequest) -> float:
        """Estimate cost before calling API. $0.00 = free."""


class GatewayProviderChain:
    """Ordered chain: try providers in sequence until one succeeds."""

    def __init__(self, providers: List[GatewayProvider]):
        self._chain = providers

    def generate(self, request: GenerationRequest) -> GenerationResult:
        for provider in self._chain:
            if provider.is_available():
                try:
                    return provider.generate(request)
                except Exception as e:
                    continue  # Try next provider
        # All providers failed — fallback
        return FALLBACK_PROVIDER.generate(request)
```

### 2.2 Provider Catalog

| Provider | Type | Cost Model | Max/Request | Availability |
|:---------|:-----|:-----------|:------------|:-------------|
| `DeepSeekTextProvider` | Text | $0.14/1M tokens | 8K tokens | API key required |
| `FALImageProvider` | Image | $0.005/image | 4 images | API key required |
| `OpenAIImageProvider` | Image | $0.04/image | 10 images | API key required |
| `EdgeTTSProvider` | Audio | **Free** | 10 min | No key needed |
| `RuleTextProvider` | Text | **Free** | Unlimited | Always available |
| `SVGPlaceholderProvider` | Image | **Free** | Unlimited | Always available |
| `SilenceAudioProvider` | Audio | **Free** | Unlimited | Always available |

### 2.3 Provider Selection Logic

```python
class GatewayRouter:
    """Routes generation requests to the best available provider."""

    def __init__(self, config: GatewayConfig, cost_controller: CostController):
        self.config = config
        self.cost = cost_controller

    def route(self, request: GenerationRequest) -> GatewayProviderChain:
        """
        Build provider chain based on:
          1. User tier (free/premium)
          2. Cost budget remaining
          3. Provider availability
        """

        if request.resource_type in ("document", "mindmap", "exercise", "code", "slides"):
            # Text generation
            chain = [RuleTextProvider()]
            if self.config.text_api_key and self.cost.can_afford(request):
                chain.insert(0, DeepSeekTextProvider(self.config))
            return GatewayProviderChain(chain)

        if request.resource_type == "illustration":
            # Image generation
            chain = [SVGPlaceholderProvider()]
            if self.config.image_api_key and self.cost.can_afford(request):
                chain.insert(0, FALImageProvider(self.config))
            return GatewayProviderChain(chain)

        if request.resource_type == "audio":
            chain = [SilenceAudioProvider()]
            # EdgeTTS is free — always try it
            chain.insert(0, EdgeTTSProvider())
            return GatewayProviderChain(chain)

        return GatewayProviderChain([RuleTextProvider()])
```

### 2.4 Provider Health Check

```python
class ProviderHealthChecker:
    """Periodic health check. Providers that fail 3x in 5min are degraded."""

    def __init__(self):
        self._failures: Dict[str, List[float]] = {}  # provider → [timestamps]
        self._degraded: Set[str] = set()

    def record_success(self, provider_name: str): ...
    def record_failure(self, provider_name: str): ...
    def is_healthy(self, provider_name: str) -> bool: ...
    def get_status(self) -> Dict[str, str]: ...
```

---

## 3. Content Validation Layer

### 3.1 Three-Stage Pipeline

```
Raw Generated Content
        │
        ▼
┌─────────────────────────────┐
│ Stage 1: Academic Validation │
│                             │
│ • Topic relevance check     │  Cosine similarity: content vs learning goal
│ • Factual consistency       │  Key concept coverage check
│ • Curriculum alignment      │  Student level appropriateness
│ • Language quality          │  Readability score (Flesch-Kincaid)
│                             │
│ Threshold: score ≥ 0.60     │
└──────────────┬──────────────┘
               │ ✓ pass
               ▼
┌─────────────────────────────┐
│ Stage 2: Format Validation   │
│                             │
│ • Structure completeness    │  Required fields present
│ • Markdown syntax           │  No broken links/images
│ • JSON schema conformance   │  Valid per resource type schema
│ • Size limits               │  < 50KB text, < 100 slides, < 50 exercises
│                             │
│ Threshold: all checks pass  │
└──────────────┬──────────────┘
               │ ✓ pass
               ▼
┌─────────────────────────────┐
│ Stage 3: Security Filter     │
│                             │
│ • PII detection             │  Regex: email, phone, ID numbers
│ • Harmful content           │  Keyword blocklist (violence, hate, NSFW)
│ • Prompt injection guard    │  Detect escaped system instructions
│ • Code safety               │  No `os.system()`, `eval()`, `rm -rf`
│ • URL validation            │  Only allowlisted domains
│                             │
│ Threshold: zero violations  │
└──────────────┬──────────────┘
               │ ✓ pass
               ▼
          VALID Content
```

### 3.2 Academic Validator Detail

```python
@dataclass
class AcademicValidationResult:
    score: float              # 0.0–1.0
    topic_relevance: float    # Cosine similarity to learning goal
    concept_coverage: float   # % of key concepts present
    level_match: float        # Student level appropriateness
    readability: float        # Flesch-Kincaid score normalized
    passed: bool              # All scores ≥ 0.60
    issues: List[str]

class AcademicValidator:
    def validate(self, content: str, topic: str, concepts: List[str],
                 student_level: str) -> AcademicValidationResult:
        """Rule-based academic validation. No LLM dependency."""
        # Check 1: Topic relevance via keyword presence
        keywords = self._extract_keywords(topic)
        relevance = sum(1 for kw in keywords if kw.lower() in content.lower()) / max(len(keywords), 1)

        # Check 2: Concept coverage
        covered = sum(1 for c in concepts if c.lower() in content.lower())
        coverage = covered / max(len(concepts), 1)

        # Check 3: Level appropriateness (vocabulary complexity)
        level_scores = {"beginner": 0.3, "intermediate": 0.5, "advanced": 1.0}
        target_complexity = level_scores.get(student_level, 0.5)
        actual_complexity = self._measure_complexity(content)
        level_match = 1.0 - abs(target_complexity - actual_complexity)

        # Check 4: Readability
        sentences = [s for s in content.split(".") if len(s) > 5]
        avg_words = sum(len(s.split()) for s in sentences) / max(len(sentences), 1)
        readability = min(1.0, 25.0 / max(avg_words, 1))

        score = (relevance * 0.3 + coverage * 0.3 + level_match * 0.2 + readability * 0.2)
        return AcademicValidationResult(
            score=round(score, 2),
            topic_relevance=relevance,
            concept_coverage=coverage,
            level_match=level_match,
            readability=readability,
            passed=score >= 0.60,
            issues=[...]
        )
```

### 3.3 Security Filter Detail

```python
class SecurityFilter:
    """Content security scanner. Zero false-negative tolerance on PII."""

    PII_PATTERNS = [
        (r'\b\d{17}[\dXx]\b', 'CN_ID_NUMBER'),        # 中国身份证号
        (r'\b1[3-9]\d{9}\b', 'CN_PHONE'),             # 中国手机号
        (r'\b[\w.-]+@[\w.-]+\.\w+\b', 'EMAIL'),        # Email address
        (r'\b\d{3}-\d{4}-\d{4}\b', 'PHONE_FORMAT'),    # Phone format
    ]

    HARMFUL_KEYWORDS = {
        "violence", "hate_speech", "self_harm",
        "illegal_activity", "nsfw", "gambling",
    }

    CODE_UNSAFE_PATTERNS = [
        r'\bos\.system\(', r'\beval\(', r'\bexec\(',
        r'\brm\s+-rf\b', r'\b__import__\(', r'\bsubprocess\.',
    ]

    PROMPT_INJECTION_MARKERS = [
        "ignore previous instructions",
        "system prompt:",
        "<<SYS>>", "</SYS>",
        "you are now",
    ]

    def scan(self, content: str) -> SecurityResult:
        """Scan content. Returns list of violations."""
        violations = []
        for pattern, label in self.PII_PATTERNS:
            if re.search(pattern, content):
                violations.append(SecurityViolation(
                    type="PII_LEAK", detail=label, severity="CRITICAL"))

        lower = content.lower()
        for kw in self.HARMFUL_KEYWORDS:
            if kw in lower:
                violations.append(SecurityViolation(
                    type="HARMFUL", detail=kw, severity="HIGH"))

        for pattern in self.CODE_UNSAFE_PATTERNS:
            if re.search(pattern, content):
                violations.append(SecurityViolation(
                    type="UNSAFE_CODE", detail=pattern, severity="HIGH"))

        for marker in self.PROMPT_INJECTION_MARKERS:
            if marker in lower:
                violations.append(SecurityViolation(
                    type="PROMPT_INJECTION", detail=marker, severity="CRITICAL"))

        return SecurityResult(
            passed=len(violations) == 0,
            violations=violations,
        )
```

### 3.4 Validation Pipeline

```python
class ValidationPipeline:
    """Orchestrate the three-stage validation."""

    def __init__(self, academic: AcademicValidator, security: SecurityFilter):
        self.academic = academic
        self.security = security
        self.schemas = self._load_resource_schemas()  # JSON Schema per type

    def validate(self, content: str, resource_type: str,
                 topic: str, concepts: List[str],
                 student_level: str) -> ValidationResult:
        """
        Run all three stages. Stop at first critical failure.
        """
        issues = []
        warnings = []

        # Stage 1: Academic
        academic_result = self.academic.validate(content, topic, concepts, student_level)
        if not academic_result.passed:
            issues.append(f"Academic validation failed (score: {academic_result.score:.2f})")
            if academic_result.score < 0.30:
                return ValidationResult(passed=False, issues=issues, stage="academic")

        # Stage 2: Format
        schema = self.schemas.get(resource_type)
        if schema:
            format_issues = self._validate_schema(content, schema)
            if format_issues:
                issues.extend(format_issues)

        # Stage 3: Security (always runs — never skipped)
        security_result = self.security.scan(content)
        if not security_result.passed:
            for v in security_result.violations:
                if v.severity == "CRITICAL":
                    issues.append(f"SECURITY: {v.type} — {v.detail}")
            if any(v.severity == "CRITICAL" for v in security_result.violations):
                return ValidationResult(passed=False, issues=issues, stage="security")

        return ValidationResult(
            passed=len(issues) == 0,
            issues=issues,
            warnings=warnings,
            stage="complete",
            academic_score=academic_result.score,
        )
```

---

## 4. Cost Controller

### 4.1 Budget Model

```
┌─────────────────────────────────────────────────────┐
│                    Cost Controller                   │
│                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐ │
│  │ Token Budget │  │ API Budget  │  │ Time Budget │ │
│  │              │  │             │  │             │ │
│  │ Daily: 100K  │  │ Images: 20  │  │ Per-req:    │ │
│  │ Per-req: 8K  │  │ Audio: 10m  │  │  30s max    │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘ │
│         │                │                │         │
│         └────────────────┼────────────────┘         │
│                          │                          │
│                   ┌──────┴──────┐                   │
│                   │ Budget Pool  │                   │
│                   └──────┬──────┘                   │
└──────────────────────────┼──────────────────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         ┌────────┐  ┌────────┐  ┌────────┐
         │  Free  │  │  Pro   │  │  Team  │
         │ Tier   │  │ Tier   │  │ Tier   │
         ├────────┤  ├────────┤  ├────────┤
         │Tokens: │  │Tokens: │  │Tokens: │
         │ 50K/d  │  │ 500K/d │  │ 2M/d   │
         │Images: │  │Images: │  │Images: │
         │  0     │  │  50/d  │  │ 200/d  │
         │Audio:  │  │Audio:  │  │Audio:  │
         │  5m/d  │  │  60m/d │  │ 300m/d │
         │Cost:   │  │Cost:   │  │Cost:   │
         │  $0    │  │ $10/mo │  │ $50/mo │
         └────────┘  └────────┘  └────────┘
```

### 4.2 Token Budget (Text Generation)

```python
@dataclass
class TokenBudget:
    daily_limit: int      # Tokens per day
    per_request_limit: int # Max tokens per generation
    used_today: int = 0
    last_reset: str = ""

    def can_afford(self, estimated_tokens: int) -> bool:
        if estimated_tokens > self.per_request_limit:
            return False
        return (self.used_today + estimated_tokens) <= self.daily_limit

    def spend(self, tokens: int):
        self.used_today += tokens

    def reset_daily(self): ...


class CostController:
    def __init__(self, user_tier: str = "free"):
        self.tier = TIER_CONFIGS[user_tier]
        self.token_budget = TokenBudget(
            daily_limit=self.tier["tokens_per_day"],
            per_request_limit=8000,
        )
        self.image_quota = DailyQuota(self.tier["images_per_day"])
        self.audio_quota = DailyQuota(self.tier["audio_minutes_per_day"])
        self.total_cost_usd = 0.0

    def can_afford(self, request: GenerationRequest) -> bool:
        """Pre-flight check: can we afford this generation?"""
        estimates = self._estimate(request)
        if request.resource_type in TEXT_TYPES:
            return self.token_budget.can_afford(estimates["tokens"])
        if request.resource_type == "illustration":
            return self.image_quota.can_spend(1)
        if request.resource_type == "audio":
            return self.audio_quota.can_spend(estimates["minutes"])
        return True  # Rule-based generation is always free

    def record_usage(self, result: GenerationResult):
        """After generation: record what was actually spent."""
        self.token_budget.spend(result.tokens_used)
        self.total_cost_usd += result.cost_estimate_usd


TIER_CONFIGS = {
    "free": {
        "tokens_per_day": 50_000,
        "images_per_day": 0,        # No image generation on free tier
        "audio_minutes_per_day": 5,  # EdgeTTS is free, limited for fairness
        "max_concurrent": 1,
        "priority": "low",
    },
    "pro": {
        "tokens_per_day": 500_000,
        "images_per_day": 50,
        "audio_minutes_per_day": 60,
        "max_concurrent": 3,
        "priority": "normal",
    },
    "team": {
        "tokens_per_day": 2_000_000,
        "images_per_day": 200,
        "audio_minutes_per_day": 300,
        "max_concurrent": 10,
        "priority": "high",
    },
}
```

### 4.3 API Rate Limiting

```python
class RateLimiter:
    """Token bucket algorithm for API call rate limiting."""

    def __init__(self, max_calls_per_minute: int = 30):
        self._bucket = max_calls_per_minute
        self._max = max_calls_per_minute
        self._last_refill = time.monotonic()

    def acquire(self) -> bool:
        """Try to acquire a token. Returns False if rate limited."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._bucket = min(self._max, self._bucket + elapsed * (self._max / 60))
        self._last_refill = now
        if self._bucket >= 1:
            self._bucket -= 1
            return True
        return False
```

---

## 5. Deployment Architecture

### 5.1 Windows Client + Linux Server

```
┌──────────────────────────────────────────────────────────────┐
│                   Linux Server (Render / VPS)                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              FastAPI (uvicorn, port 8000)              │   │
│  │                                                      │   │
│  │  /api/v1/learning     ← A3Workflow                    │   │
│  │  /api/v1/runtime      ← RuntimeBus (Veritas-Core)     │   │
│  │  /api/v2/auth/*       ← User auth (Phase 9.1)        │   │
│  │  /api/v2/resources/*  ← Resource generation (9.3)    │   │
│  │  /api/v2/tutor/stream ← SSE streaming (9.4)          │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┼───────────────────────────────┐   │
│  │              Data Layer                               │   │
│  │  SQLite (a3.db)     │  Knowledge Base (JSON files)   │   │
│  │  - users             │  - course content              │   │
│  │  - resources         │  - exercises                   │   │
│  │  - learning_records  │  - references                  │   │
│  └──────────────────────┴───────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Veritas-Core 7.0.0                        │   │
│  │  RuntimeEngine │ SDK │ Recovery │ Lifecycle │ ...     │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  External APIs:                                              │
│  • DeepSeek (LLM)         ← DEEPSEEK_API_KEY                │
│  • FAL.ai (Image Gen)     ← FAL_KEY                         │
│  • Edge TTS (Audio)       ← Free, no key                    │
└──────────────────────────┬───────────────────────────────────┘
                           │ HTTP/HTTPS
                           │
┌──────────────────────────┼───────────────────────────────────┐
│                Windows Client                                │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Streamlit Desktop (localhost:8501)           │   │
│  │                                                      │   │
│  │  • ChatGPT-style chat UI (streaming)                 │   │
│  │  • Learning dashboard                                │   │
│  │  • Resource viewer (Markdown, cards, code)           │   │
│  │  • Quiz interface                                    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                   │
│  ┌──────────────────────┼───────────────────────────────┐   │
│  │          A3 Client SDK (Lightweight)                  │   │
│  │  • API client (httpx)                                │   │
│  │  • Local cache (SQLite)                              │   │
│  │  • Offline mode (cached resources)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 5.2 Windows Client Details

```
Windows Client Installation:

  1. Install Python 3.10+: 
     winget install Python.Python.3.12
  
  2. Clone + setup:
     git clone https://github.com/Leisure-Auf1/A3-Multi-Agent-System.git
     cd A3-Multi-Agent-System
     python -m venv .venv
     .venv\Scripts\activate
     pip install -r requirements-client.txt
  
  3. Configure server:
     set A3_API_URL=https://your-server.onrender.com
     set A3_API_KEY=your_api_key
  
  4. Launch:
     streamlit run client.py --server.port 8501

Client requirements (minimal):
  streamlit>=1.28.0
  httpx>=0.25.0
  # NO: veritas-core, fastapi, uvicorn (server-side only)
```

### 5.3 Client-Server Split

| Component | Client (Windows) | Server (Linux) |
|:----------|:----------------:|:--------------:|
| Streamlit UI | ✅ | ❌ |
| Veritas-Core Runtime | ❌ | ✅ |
| Agent execution | ❌ | ✅ |
| Resource generation | ❌ | ✅ |
| LLM calls | ❌ | ✅ |
| Image/Audio generation | ❌ | ✅ |
| SQLite (local cache) | ✅ | ❌ |
| SQLite (master DB) | ❌ | ✅ |
| Authentication | Token stored | Token issued |
| Knowledge Base | Cached copy | Master copy |

### 5.4 Offline Client Mode

```
When server is unreachable:
  1. Load cached resources from local SQLite
  2. Local Markdown viewer for previously generated content
  3. Offline quiz mode (pre-loaded questions)
  4. Queue actions for sync when back online
  5. Gray out features that require server (tutor chat, new generation)
```

---

## 6. Data Model Design (Complete)

### 6.1 Database Schema (Full)

```sql
-- ═══ Users & Auth ═══
CREATE TABLE users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  TEXT DEFAULT '',
    tier          TEXT DEFAULT 'free',   -- free | pro | team
    created_at    TEXT NOT NULL,
    last_login_at TEXT
);

-- ═══ Student Profiles ═══
CREATE TABLE student_profiles (
    id            TEXT PRIMARY KEY,
    user_id       TEXT UNIQUE NOT NULL,
    profile_json  TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ═══ Learning Records ═══
CREATE TABLE learning_records (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    course_id     TEXT DEFAULT '',
    agent         TEXT NOT NULL,
    action        TEXT NOT NULL,
    result_json   TEXT DEFAULT '{}',
    score         REAL DEFAULT 0.0,
    duration_ms   INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ═══ Chat Threads ═══
CREATE TABLE chat_threads (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    title         TEXT DEFAULT 'New Chat',
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ═══ Chat Messages ═══
CREATE TABLE chat_messages (
    id            TEXT PRIMARY KEY,
    thread_id     TEXT NOT NULL,
    role          TEXT NOT NULL CHECK(role IN ('user','assistant','system')),
    content       TEXT DEFAULT '',
    metadata_json TEXT DEFAULT '{}',
    created_at    TEXT NOT NULL,
    FOREIGN KEY (thread_id) REFERENCES chat_threads(id)
);

-- ═══ Resources (NEW) ═══
CREATE TABLE resources (
    id            TEXT PRIMARY KEY,
    topic         TEXT NOT NULL,
    resource_type TEXT NOT NULL,
    student_level TEXT DEFAULT 'beginner',
    language      TEXT DEFAULT 'zh-CN',
    status        TEXT DEFAULT 'pending',
    data_json     TEXT NOT NULL,
    media_urls    TEXT DEFAULT '[]',
    fallback_used TEXT DEFAULT '[]',
    cost_usd      REAL DEFAULT 0.0,
    tokens_used   INTEGER DEFAULT 0,
    generated_by  TEXT DEFAULT 'rule',
    created_at    TEXT NOT NULL,
    expires_at    TEXT,
    accessed_at   TEXT,
    access_count  INTEGER DEFAULT 0,
    metadata_json TEXT DEFAULT '{}'
);

-- ═══ Usage Tracking (NEW) ═══
CREATE TABLE usage_log (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    date          TEXT NOT NULL,       -- YYYY-MM-DD
    tokens_used   INTEGER DEFAULT 0,
    images_used   INTEGER DEFAULT 0,
    audio_seconds INTEGER DEFAULT 0,
    cost_usd      REAL DEFAULT 0.0,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ═══ Cost Ledger (NEW) ═══
CREATE TABLE cost_ledger (
    id            TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    resource_id   TEXT,
    provider      TEXT NOT NULL,
    api_call      TEXT NOT NULL,
    tokens_in     INTEGER DEFAULT 0,
    tokens_out    INTEGER DEFAULT 0,
    cost_usd      REAL DEFAULT 0.0,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 6.2 Python Dataclasses (Contracts)

```python
@dataclass
class ResourceArtifact:
    """Complete resource artifact as stored in DB."""
    id: str
    topic: str
    resource_type: str
    student_level: str = "beginner"
    language: str = "zh-CN"
    status: str = "pending"
    data: Any = None                    # Resource-specific dataclass
    media_urls: List[str] = field(default_factory=list)
    fallback_used: List[str] = field(default_factory=list)
    cost_usd: float = 0.0
    tokens_used: int = 0
    generated_by: str = "rule"
    created_at: str = ""
    expires_at: Optional[str] = None
    accessed_at: Optional[str] = None
    access_count: int = 0

@dataclass
class ValidationResult:
    passed: bool
    issues: List[str]
    warnings: List[str] = field(default_factory=list)
    stage: str = "pending"              # academic | format | security | complete
    academic_score: float = 0.0

@dataclass
class SecurityViolation:
    type: str                           # PII_LEAK | HARMFUL | UNSAFE_CODE | PROMPT_INJECTION
    detail: str
    severity: str                       # CRITICAL | HIGH | MEDIUM | LOW

@dataclass
class CostEstimate:
    tokens_estimated: int = 0
    images_estimated: int = 0
    audio_minutes_estimated: float = 0.0
    cost_usd_estimated: float = 0.0
    affordable: bool = True
    reason: str = ""
```

---

## 7. Veritas-Core Boundary

### 7.1 What Lives in Veritas-Core (Read-Only)

```
Veritas-Core 7.0.0 (FROZEN for Phase 9)
├── veritas/runtime/         RuntimeEngine, hooks, events, state machine
├── veritas/sdk/             RuntimeClient, TaskRequest, TaskResult
├── veritas/llm/             LLMProvider, create_provider, MockLLMProvider
├── veritas/memory/          MemoryManager, StudentMemory, ExperienceMemory
├── veritas/security/        PermissionMatrix, ToolGateway, AuditLogger
├── veritas/plugins/         Plugin system, PluginManager
├── veritas/recovery/        RecoveryManager, RecoveryStrategy
├── veritas/lifecycle/       AgentLifecycle, LifecycleManager
├── veritas/benchmark/       BenchmarkRunner, FailureInjector
└── veritas/distributed/     DistributedEventBus, NodeRegistry
```

### 7.2 What Lives in A3 (Phase 9 Development)

```
A3-Multi-Agent-System (Application Layer)
├── src/agents/              ← All 9 agents (Profile, Planner, Resource, etc.)
│   ├── resource_generation_agent.py   ← Enhanced in 9.3
│   ├── tutor_agent.py                 ← Phase 9.2
│   └── evaluation_agent.py            ← Phase 9.2
├── src/auth/                ← User auth (Phase 9.1)
├── src/data/                ← SQLite, stores, KB manager (Phase 9.1)
├── src/multimodal/          ← Gateway abstraction (Phase 9.3 NEW)
│   ├── gateway.py           ← GatewayRouter, GatewayConfig
│   ├── text_gateway.py      ← TextGateway (LLM adapter)
│   ├── image_gateway.py     ← ImageGateway (FAL/DALL-E)
│   ├── audio_gateway.py     ← AudioGateway (Edge TTS)
│   └── fallback.py          ← Placeholder generators
├── src/validation/          ← Content validation (Phase 9.3.1 NEW)
│   ├── academic.py          ← AcademicValidator
│   ├── format.py            ← FormatValidator (JSON Schema)
│   └── security.py          ← SecurityFilter
├── src/cost/                ← Cost control (Phase 9.3.1 NEW)
│   ├── controller.py        ← CostController, TokenBudget, RateLimiter
│   └── ledger.py            ← CostLedger (usage tracking)
├── src/api/routes/          ← REST API endpoints
│   ├── auth.py              ← Phase 9.1
│   └── resources.py         ← Phase 9.3 NEW
├── src/workflow/            ← A3Workflow (orchestrates agents via RuntimeEngine)
├── web/                     ← Streamlit UI
│   ├── app_v4.py            ← Phase 9.4 ChatGPT-style UI
│   └── components/          ← UI components
├── client.py                ← Windows client launcher (Phase 9.3.1 NEW)
└── requirements-client.txt  ← Client-only dependencies (Phase 9.3.1 NEW)
```

### 7.3 Cross-Boundary Call Rules

```
✅ ALLOWED (A3 → Veritas-Core):
   from veritas.llm import LLMProvider, create_provider
   from veritas.memory import MemoryManager
   from veritas.runtime import RuntimeEngine, AgentState
   from veritas.sdk import RuntimeClient, TaskRequest
   from veritas.security import AuditLogger

❌ FORBIDDEN (Veritas-Core → A3):
   Veritas-Core must NEVER import from src.*
   Veritas-Core must NEVER know about A3 agents

❌ FORBIDDEN (Mutations):
   A3 must NEVER modify Veritas-Core files
   A3 must NEVER add Runtime states
   A3 must NEVER change Veritas hook behavior
```

### 7.4 Why the Boundary Matters

```
Veritas-Core = Agent Runtime Framework
  → Generic, reusable, zero domain knowledge
  → npm install veritas-core (future)
  → Used by: A3, CodingAgent, ResearchAgent, any agent app

A3 = Learning Application
  → Domain-specific: students, courses, quizzes, tutoring
  → Consumes Veritas-Core as a library
  → All education logic lives HERE
```

---

## 8. Summary

### 8.1 New Modules (Design Only — Not Implemented)

| Module | Files | Purpose |
|:-------|:------|:--------|
| `src/multimodal/` | 5 files | Gateway abstraction + provider adapters |
| `src/validation/` | 3 files | Academic + Format + Security validation |
| `src/cost/` | 2 files | Cost controller + usage ledger |
| `src/api/routes/resources.py` | 1 file | Resource generation REST API |
| `client.py` | 1 file | Windows client launcher |
| `requirements-client.txt` | 1 file | Client-only deps |
| **Total** | **13 files** | |

### 8.2 Database Changes

| Table | Status | Purpose |
|:------|:------:|:--------|
| `users` | ✅ exists | Add `tier` column |
| `resources` | **NEW** | Resource artifact storage |
| `usage_log` | **NEW** | Daily usage tracking |
| `cost_ledger` | **NEW** | Per-API-call cost audit |

### 8.3 Constraints Compliance

| Constraint | Compliance |
|:-----------|:-----------|
| Veritas-Core V7 frozen | ✅ All new code in A3, imports `veritas.*` only |
| Zero Runtime modifications | ✅ No RuntimeEngine changes |
| 1064 tests must pass | ✅ All new modules are additive |
| Backward compatible | ✅ Existing ResourceGenerationAgent API unchanged |
| Offline fallback always available | ✅ SVG placeholders + rule-based generation |
