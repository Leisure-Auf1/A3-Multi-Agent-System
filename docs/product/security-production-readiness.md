# Security Production Readiness — A3-Agent v7.1.1

> **Date**: 2026-07-20
> **Phase**: 10.4-B
> **Baseline**: 2512 tests, 0 failures

---

## 1. Authentication Flow

```
Client Request (Bearer Token)
    │
    ▼
Authorization Header Parser
    │ src/auth/middleware.py:20  require_auth()
    │ └─ Extracts "Bearer <token>" from header
    │
    ▼
JWT Token Validation
    │ src/auth/auth_manager.py  get_current_user()
    │ └─ Verifies signature + expiry → AuthUser or None
    │
    ▼
User Resolution (401 if invalid)
    │ Returns AuthUser(id, email, display_name, role, is_guest)
    │
    ▼
Request Context → FastAPI Dependency Injection
```

**Auth Endpoints:**

| Endpoint | Method | Auth Required | Description |
|:---------|:-------|:------------:|:------------|
| `/api/v2/auth/register` | POST | ❌ | Create account |
| `/api/v2/auth/login` | POST | ❌ | Get JWT token |
| `/api/v2/auth/guest` | POST | ❌ | Guest session |
| `/api/v2/auth/logout` | POST | ✅ | Invalidate token |
| `/api/v2/auth/me` | GET | ✅ | Current user info |

---

## 2. Permission Model

```
Role Hierarchy:
  free < pro < teacher < admin

Permission Matrix:
```

| Capability | FREE | PRO | TEACHER | ADMIN |
|:-----------|:----:|:---:|:-------:|:-----:|
| Pipeline run (rule-only) | ✅ | ✅ | ✅ | ✅ |
| Pipeline run (LLM) | ❌ | ✅ | ✅ | ✅ |
| Learning history | ✅ | ✅ | ✅ | ✅ |
| Profile view | ✅ | ✅ | ✅ | ✅ |
| Model access (openai) | ❌ | ✅ | ✅ | ✅ |
| Multimodal access | ❌ | ✅ | ✅ | ✅ |
| Admin panel | ❌ | ❌ | ❌ | ✅ |
| User management | ❌ | ❌ | ✅ | ✅ |

**Implementation**: `src/user/permission.py` → `PermissionManager`, `src/auth/middleware.py` → `require_role()`, `require_pro()`, `require_admin()`

---

## 3. API Protection Matrix

### v2 Endpoints (Production)

All v2 endpoints require `require_auth` (Bearer token).

| Endpoint | Auth | Permission | TokenBudget | Service Layer |
|:---------|:----:|:----------:|:-----------:|:--------------|
| `POST /api/v2/learning/run` | ✅ | ✅ Role | ✅ | LearningPipelineService → A3Workflow |
| `POST /api/v2/learning/plan` | ✅ | ✅ | ❌ | Direct (legacy, deprecated) |
| `GET /api/v2/learning/history` | ✅ | ✅ | ❌ | Data layer |
| `GET /api/v2/learning/stats` | ✅ | ✅ | ❌ | Data layer |
| `GET /api/v2/profile` | ✅ | ✅ | ❌ | Profile service |
| `PUT /api/v2/profile` | ✅ | ✅ | ❌ | Profile service |
| `POST /api/v2/profile/assess` | ✅ | ✅ | ❌ | Direct (legacy, deprecated) |
| `POST /api/v2/chat/message` | ✅ | ✅ | ✅ | Chat service |
| `GET /api/v2/resources/*` | ✅ | ✅ | ❌ | Resource service |
| `POST /api/v2/evaluation/*` | ✅ | ✅ | ❌ | Evaluation service |
| `POST /api/v2/users` | ✅ | admin | ❌ | User management |
| `GET /api/v2/settings/llm` | ✅ | ✅ | ❌ | Settings service |

### v1 Endpoints (Deprecated — auth retrofitted)

| Endpoint | Auth | Deprecation | Sunset |
|:---------|:----:|:-----------:|:------:|
| `POST /api/v1/learning/plan` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |
| `GET /api/v1/runtime/snapshot` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |
| `GET /api/v1/runtime/metrics` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |
| `GET /api/v1/runtime/timeline` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |
| `GET /api/v1/runtime/events` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |
| `GET /api/v1/runtime/state` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |
| `POST /api/v1/runtime/reset` | ✅ (new) | `X-Deprecated-API: true` | 2026-09-01 |

---

## 4. Audit Architecture

```
API Request
    │
    ▼
Auth → Permission → Pipeline → Response
    │                    │
    ▼                    ▼
AuditLogger.log()   AuditLogger.log()
    │                    │
    ▼                    ▼
workspace/{user_id}/security/audit.jsonl
```

**Audit Entry Fields**: `event_id`, `user_id`, `role`, `timestamp`, `endpoint`, `method`, `status_code`, `provider`, `model_id`, `tokens_used`, `estimated_cost_usd`, `success`, `error_message`, `duration_ms`

**Audited Paths**:
- ✅ Login / Logout
- ✅ Learning pipeline run
- ✅ Resource generation
- ✅ Settings changes
- ⚠️ Profile assess (not yet wired)
- ⚠️ Chat messages (not yet wired)

**AuditLogger Capabilities**:
- `log()` — write audit entry (fire-and-forget, never blocks)
- `query()` — query entries by user/time/endpoint
- `get_user_stats()` — aggregate usage statistics
- `get_suspicious_activity()` — detect abuse patterns

---

## 5. Security Test Coverage

### Existing Tests (pre-Phase 10.4-B)

| Test File | Focus |
|:----------|:------|
| `test_auth_layer.py` | JWT, password hashing, role guards |
| `test_security_layer.py` | Security middleware |
| `test_security_hardening.py` | Hardening patterns |
| `test_chat_security.py` | Chat endpoint security |
| `test_resources_security.py` | Resource endpoint security |
| `test_product_flow_e2e.py` | End-to-end flow with auth |

### New Tests (Phase 10.4-B) — `test_security_production.py`

33 tests covering:
- Unauthorized requests (10 tests)
- Permission denied (3 tests)
- Token budget (2 tests)
- Multi-user isolation (3 tests)
- Audit log (6 tests)
- v1 deprecated auth (4 tests)
- v2 pipeline auth (4 tests)
- Logout invalidation (1 test)

---

## 6. Known Limitations

1. **Logout token invalidation**: Tokens are stateless JWT — logout doesn't truly revoke. A token remains valid until it expires.
2. **Token budget at v1 endpoints**: v1 runtime routes don't check token budget (read-only operations).
3. **Rate limiting**: No per-user request rate limiting is implemented yet.
4. **Audit log wiring**: `profile/assess` and `chat/message` endpoints not yet wired to AuditLogger.
5. **CORS**: Currently allows all origins (`*`) — should be restricted in production.
6. **v1 sunset**: v1 endpoints scheduled for removal by 2026-09-01. Migration path: use `/api/v2/learning/run` instead.

---

*End of Phase 10.4-B — Security Production Readiness*
