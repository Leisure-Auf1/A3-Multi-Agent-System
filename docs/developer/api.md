# A3 REST API Reference

> **Base URL**: `http://localhost:8000`
> **Auth**: Bearer token in `Authorization` header

---

## Authentication

### Register

```http
POST /api/v2/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password",
  "display_name": "Alice"
}
```

**Response** `201`:
```json
{
  "token": "abc123...",
  "user_id": "a1b2c3d4e5f6",
  "display_name": "Alice"
}
```

### Login

```http
POST /api/v2/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Response** `200`:
```json
{
  "token": "abc123...",
  "user_id": "a1b2c3d4e5f6",
  "display_name": "Alice"
}
```

### Logout

```http
POST /api/v2/auth/logout
Authorization: Bearer <token>
```

**Response** `200`

### Guest Session

```http
POST /api/v2/auth/guest
Content-Type: application/json

{ "display_name": "Guest" }
```

---

## Learning Pipeline

### Run Full Pipeline

```http
POST /api/v2/learning/run
Authorization: Bearer <token>
Content-Type: application/json

{
  "goal": "Learn Python async programming",
  "depth": "normal"
}
```

**Response** `200`:
```json
{
  "run_id": "run_abc123",
  "user_id": "a1b2c3d4",
  "goal": "Learn Python async programming",
  "profile": { ... },
  "plan": { "nodes": [...], "difficulty": "beginner" },
  "resources": [ ... ],
  "evaluation": { "score": 85, "passed": true },
  "trace": [ { "agent": "ProfileAgent", "action": "extract", ... } ],
  "artifacts_saved": [ "/path/to/profile.json", ... ],
  "memory_saved": true,
  "duration_ms": 1234.5,
  "status": "success"
}
```

### Learning History

```http
GET /api/v2/learning/history?limit=20
Authorization: Bearer <token>
```

**Response** `200`: Array of learning records.

### Learning Stats

```http
GET /api/v2/learning/stats
Authorization: Bearer <token>
```

**Response** `200`:
```json
{
  "total_sessions": 5,
  "avg_score": 78.5,
  "total_duration_ms": 45678
}
```

---

## Profile

### Get Profile

```http
GET /api/v2/profile
Authorization: Bearer <token>
```

### Assess Profile

```http
POST /api/v2/profile/assess
Authorization: Bearer <token>
Content-Type: application/json

{
  "text": "I am a Python developer with 3 years experience..."
}
```

---

## Chat

### Send Message

```http
POST /api/v2/chat/message
Authorization: Bearer <token>
Content-Type: application/json

{
  "message": "What is a decorator in Python?",
  "thread_id": "optional_existing_thread_id"
}
```

### List Threads

```http
GET /api/v2/chat/threads
Authorization: Bearer <token>
```

---

## Resources

### Generate Resources

```http
POST /api/v2/resources/generate
Authorization: Bearer <token>
Content-Type: application/json

{
  "topic": "Python decorators",
  "concepts": ["closures", "wrappers", "functools"],
  "resource_types": ["document", "exercise"]
}
```

---

## Health Check

```http
GET /health
```

**Response** `200`:
```json
{ "status": "ok" }
```

---

## Error Responses

| Status | Meaning |
|:-------|:--------|
| `401` | Missing/invalid/expired token |
| `403` | Insufficient role permission |
| `409` | Email already registered |
| `422` | Invalid input (e.g., goal < 3 characters) |
| `429` | Token budget exceeded |

All errors follow the format:
```json
{ "detail": "Human-readable error message" }
```

---

## Usage Tracking

```http
GET /api/v2/usage
Authorization: Bearer <token>
```

**Response** `200`:
```json
{
  "user_id": "a1b2c3d4",
  "total_tokens_used": 15000,
  ...
}
```
