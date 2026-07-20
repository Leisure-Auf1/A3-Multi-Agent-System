"""
PR #3 — A3 REST API Client

Zero src/ imports. All communication through FastAPI on port 8000.
Authorization: Bearer <token> injected on every request.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List, Iterator
from dataclasses import dataclass, field


@dataclass
class AuthResult:
    token: str
    user_id: str
    display_name: str


@dataclass
class ChatResult:
    thread_id: str
    content: str
    follow_up_questions: List[str] = field(default_factory=list)


class A3APIError(Exception):
    """Raised on non-2xx API responses."""
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"{status}: {detail}")


class A3APIClient:
    """REST client for A3 Multi-Agent System APIs.

    All methods inject Authorization: Bearer <token> when a token is provided.

    For testing, set _test_client to a FastAPI TestClient instance — all
    HTTP calls will route through it instead of real sockets.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._token: Optional[str] = None
        self._test_client: Any = None  # FastAPI TestClient for testing

    def set_token(self, token: str):
        self._token = token

    def clear_token(self):
        self._token = None

    # ── internal helpers ──────────────────────────────────

    def _request(self, method: str, path: str,
                 body: Optional[dict] = None,
                 token: Optional[str] = None) -> Any:
        """Make an HTTP request, return parsed JSON. Raises A3APIError on failure."""
        if self._test_client is not None:
            return self._request_via_testclient(method, path, body, token)

        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode() if body else None
        headers = {"Content-Type": "application/json"}
        if token or self._token:
            headers["Authorization"] = f"Bearer {token or self._token}"

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = json.loads(e.read().decode()).get("detail", e.reason)
            except Exception:
                detail = e.reason
            raise A3APIError(e.code, detail)

    def _request_via_testclient(self, method: str, path: str,
                                 body: Optional[dict] = None,
                                 token: Optional[str] = None) -> Any:
        """Route request through FastAPI TestClient (for testing)."""
        tc = self._test_client
        headers = {}
        if token or self._token:
            headers["Authorization"] = f"Bearer {token or self._token}"
        kwargs = {"headers": headers}
        if body is not None:
            kwargs["json"] = body
        fn = getattr(tc, method.lower())  # tc.get, tc.post, tc.patch
        resp = fn(path, **kwargs)
        if resp.status_code >= 400:
            detail = resp.json().get("detail", "") if resp.text else ""
            raise A3APIError(resp.status_code, detail)
        return resp.json() if resp.text else {}

    def _get(self, path: str, token: Optional[str] = None) -> Any:
        return self._request("GET", path, token=token)

    def _post(self, path: str, body: Optional[dict] = None,
              token: Optional[str] = None) -> Any:
        return self._request("POST", path, body=body, token=token)

    def _patch(self, path: str, body: Optional[dict] = None,
               token: Optional[str] = None) -> Any:
        return self._request("PATCH", path, body=body, token=token)

    # ── Auth ──────────────────────────────────────────────

    def register(self, email: str, password: str,
                 display_name: str = "") -> AuthResult:
        data = self._post("/api/v2/auth/register", {
            "email": email, "password": password,
            "display_name": display_name,
        })
        return AuthResult(
            token=data["token"],
            user_id=data["user_id"],
            display_name=data["display_name"],
        )

    def login(self, email: str, password: str) -> AuthResult:
        data = self._post("/api/v2/auth/login", {
            "email": email, "password": password,
        })
        return AuthResult(
            token=data["token"],
            user_id=data["user_id"],
            display_name=data["display_name"],
        )

    def guest(self, display_name: str = "Guest") -> AuthResult:
        data = self._post("/api/v2/auth/guest", {
            "display_name": display_name,
        })
        return AuthResult(
            token=data["token"],
            user_id=data["user_id"],
            display_name=data["display_name"],
        )

    def logout(self, token: Optional[str] = None):
        self._post("/api/v2/auth/logout", token=token)
        self.clear_token()

    def me(self, token: Optional[str] = None) -> dict:
        return self._get("/api/v2/auth/me", token=token)

    # ── Chat ──────────────────────────────────────────────

    def create_thread(self, title: str = "New Chat",
                      token: Optional[str] = None) -> dict:
        return self._post("/api/v2/chat/threads",
                          {"title": title}, token=token)

    def get_threads(self, token: Optional[str] = None) -> list:
        return self._get("/api/v2/chat/threads", token=token)

    def get_messages(self, thread_id: str,
                     token: Optional[str] = None) -> list:
        return self._get(f"/api/v2/chat/threads/{thread_id}/messages",
                         token=token)

    def send_message(self, message: str, thread_id: Optional[str] = None,
                     topic: str = "", token: Optional[str] = None) -> dict:
        body = {"message": message, "topic": topic}
        if thread_id:
            body["thread_id"] = thread_id
        return self._post("/api/v2/chat/message", body, token=token)

    def rename_thread(self, thread_id: str, title: str,
                      token: Optional[str] = None) -> dict:
        return self._patch(f"/api/v2/chat/threads/{thread_id}",
                           {"title": title}, token=token)

    # ── Profile ───────────────────────────────────────────

    def get_profile(self, token: Optional[str] = None) -> dict:
        return self._get("/api/v2/profile", token=token)

    def assess_profile(self, student_text: str,
                       token: Optional[str] = None) -> dict:
        return self._post("/api/v2/profile/assess",
                          {"text": student_text}, token=token)

    # ── Learning ──────────────────────────────────────────

    def get_learning_stats(self, token: Optional[str] = None) -> dict:
        return self._get("/api/v2/learning/stats", token=token)

    def get_learning_history(self, limit: int = 20,
                             token: Optional[str] = None) -> list:
        return self._get(f"/api/v2/learning/history?limit={limit}", token=token)

    # ── Resources ─────────────────────────────────────────

    def generate_resource(self, topic: str, concepts: list,
                          resource_types: Optional[list] = None,
                          token: Optional[str] = None) -> dict:
        return self._post("/api/v2/resources/generate", {
            "topic": topic,
            "concepts": concepts,
            "resource_types": resource_types
            or ["document", "mindmap", "exercise"],
        }, token=token)

    # ── Evaluation ────────────────────────────────────────

    def generate_quiz(self, topic: str = "",
                      token: Optional[str] = None) -> dict:
        return self._post("/api/v2/evaluation/quiz/generate",
                          {"topic": topic}, token=token)

    def score_quiz(self, quiz_id: str, answers: list,
                   token: Optional[str] = None) -> dict:
        return self._post("/api/v2/evaluation/quiz/score", {
            "quiz_id": quiz_id, "answers": answers,
        }, token=token)

    def get_evaluation_results(self, limit: int = 20,
                               token: Optional[str] = None) -> list:
        return self._get(f"/api/v2/evaluation/results?limit={limit}", token=token)

    # ── Learning Plan (Phase 10.1) ────────────────────────

    def create_learning_plan(
        self, goal: str, profile: Optional[dict] = None,
        knowledge_gaps: Optional[list] = None,
        token: Optional[str] = None,
    ) -> dict:
        return self._post("/api/v2/learning/plan", {
            "goal": goal,
            "profile": profile or {},
            "knowledge_gaps": knowledge_gaps or [],
        }, token=token)

    # ── Settings (Phase 10.1) ─────────────────────────────

    def get_llm_settings(self, token: Optional[str] = None) -> dict:
        return self._get("/api/v2/settings/llm", token=token)

    def save_llm_settings(self, provider: str, model: str,
                          api_key: str = "",
                          token: Optional[str] = None) -> dict:
        return self._post("/api/v2/settings/llm", {
            "provider": provider, "model": model, "api_key": api_key,
        }, token=token)

    def test_llm_connection(self, provider: str, model: str,
                            api_key: str = "",
                            token: Optional[str] = None) -> dict:
        return self._post("/api/v2/settings/test", {
            "provider": provider, "model": model, "api_key": api_key,
        }, token=token)

    # ── User / Usage (Phase 10.1) ─────────────────────────

    def get_usage(self, token: Optional[str] = None) -> dict:
        return self._get("/api/v2/usage", token=token)

    # ── Unified Pipeline (Phase 10.2) ───────────────────

    def run_pipeline(self, goal: str, depth: str = "normal",
                     token: Optional[str] = None) -> dict:
        return self._post("/api/v2/learning/run", {
            "goal": goal, "depth": depth,
        }, token=token)
