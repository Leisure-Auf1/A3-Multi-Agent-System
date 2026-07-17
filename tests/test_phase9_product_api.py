"""
Phase 9.4 — Product API Tests

Tests for v2 API: chat, profile, learning, resources, evaluation.
"""
from __future__ import annotations

import sys, os, uuid, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from src.api.server import app
    return TestClient(app)


def _auth_headers(client) -> dict:
    """Helper: register a user and return auth headers."""
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"
    client.post("/api/v2/auth/register", json={
        "email": email, "password": "testpass", "display_name": "Test"})
    resp = client.post("/api/v2/auth/login", json={
        "email": email, "password": "testpass"})
    return {"Authorization": f"Bearer {resp.json()['token']}"}


# ── Chat API Tests ────────────────────────────────────────

class TestChatAPI:
    def test_chat_message_creates_thread(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/chat/message", json={
            "message": "What is Python?", "topic": "python"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "thread_id" in data
        assert "content" in data
        assert len(data["content"]) > 0

    def test_list_threads(self, client):
        headers = _auth_headers(client)
        # Create a thread first
        client.post("/api/v2/chat/message", json={
            "message": "Test message"}, headers=headers)
        resp = client.get("/api/v2/chat/threads", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_create_and_rename_thread(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/chat/threads", json={
            "title": "My Thread"}, headers=headers)
        assert resp.status_code == 201
        tid = resp.json()["id"]
        resp2 = client.patch(f"/api/v2/chat/threads/{tid}", json={
            "title": "Renamed"}, headers=headers)
        assert resp2.status_code == 200

    def test_get_thread_messages(self, client):
        headers = _auth_headers(client)
        msg = client.post("/api/v2/chat/message", json={
            "message": "Test"}, headers=headers)
        tid = msg.json()["thread_id"]
        resp = client.get(f"/api/v2/chat/threads/{tid}/messages", headers=headers)
        assert resp.status_code == 200
        msgs = resp.json()
        assert len(msgs) >= 2  # user + assistant

    def test_chat_requires_auth(self, client):
        resp = client.post("/api/v2/chat/message", json={"message": "Hi"})
        assert resp.status_code == 401


# ── Profile API Tests ─────────────────────────────────────

class TestProfileAPI:
    def test_get_empty_profile(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v2/profile", headers=headers)
        assert resp.status_code == 200
        assert "profile" in resp.json()

    def test_update_and_get_profile(self, client):
        headers = _auth_headers(client)
        data = {"knowledge_base": "intermediate", "cognitive_style": "code_sandbox"}
        resp = client.put("/api/v2/profile", json={"profile": data}, headers=headers)
        assert resp.status_code == 200
        resp2 = client.get("/api/v2/profile", headers=headers)
        assert resp2.json()["profile"]["knowledge_base"] == "intermediate"

    def test_assess_profile(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/profile/assess", json={
            "text": "I am a senior developer with 5 years Python experience"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "profile" in data

    def test_profile_requires_auth(self, client):
        resp = client.get("/api/v2/profile")
        assert resp.status_code == 401


# ── Learning API Tests ────────────────────────────────────

class TestLearningAPI:
    def test_generate_plan(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/learning/plan", json={
            "goal": "Learn Python OOP"}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "topic" in data
        assert isinstance(data.get("nodes"), list)

    def test_get_history_empty(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v2/learning/history", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_stats(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v2/learning/stats", headers=headers)
        assert resp.status_code == 200
        assert "total_sessions" in resp.json()

    def test_learning_requires_auth(self, client):
        resp = client.post("/api/v2/learning/plan", json={"goal": "test"})
        assert resp.status_code == 401


# ── Resources API Tests ───────────────────────────────────

class TestResourcesAPI:
    def test_generate_resources(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/resources/generate", json={
            "topic": "Python basics", "concepts": ["variables", "loops"],
            "resource_types": ["document", "mindmap"]}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_generate_single_resource(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/resources/generate/document", json={
            "topic": "Python", "concepts": ["variables"]}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["resource_type"] == "document"

    def test_generate_unknown_type(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/resources/generate/unknown", json={
            "topic": "test"}, headers=headers)
        assert resp.status_code == 400

    def test_list_courses(self, client):
        resp = client.get("/api/v2/resources/courses")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_search_resources(self, client):
        resp = client.get("/api/v2/resources/search?q=agent")
        assert resp.status_code == 200

    def test_resources_requires_auth_for_generate(self, client):
        resp = client.post("/api/v2/resources/generate", json={"topic": "test"})
        assert resp.status_code == 401


# ── Evaluation API Tests ──────────────────────────────────

class TestEvaluationAPI:
    def test_generate_quiz(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/evaluation/quiz/generate", json={
            "topic": "Python", "num_questions": 3}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "quiz_id" in data
        assert len(data["questions"]) == 3

    def test_score_quiz(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/evaluation/quiz/score", json={
            "topic": "Python",
            "answers": [
                {"question_id": "q1", "selected_index": 0,
                 "options": ["A", "B", "C", "D"], "correct_index": 0},
                {"question_id": "q2", "selected_index": 1,
                 "options": ["A", "B", "C", "D"], "correct_index": 1},
            ]}, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "score_percent" in data
        assert data["score_percent"] == 100.0

    def test_assess_open_answer(self, client):
        headers = _auth_headers(client)
        resp = client.post("/api/v2/evaluation/open/assess", json={
            "question": "Explain OOP", "answer": "Object-oriented programming",
            "topic": "Python"}, headers=headers)
        assert resp.status_code == 200
        assert "score" in resp.json()

    def test_evaluation_results(self, client):
        headers = _auth_headers(client)
        resp = client.get("/api/v2/evaluation/results", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_evaluation_requires_auth(self, client):
        resp = client.post("/api/v2/evaluation/quiz/generate", json={"topic": "test"})
        assert resp.status_code == 401


# ── Integration: Full User Flow ───────────────────────────

class TestFullUserFlow:
    def test_complete_learning_cycle(self, client):
        """Register → Profile → Plan → Chat → Quiz → Results"""
        headers = _auth_headers(client)

        # 2. Assess profile
        profile = client.post("/api/v2/profile/assess", json={
            "text": "I'm a beginner wanting to learn Python"}, headers=headers)
        assert profile.status_code == 200

        # 3. Generate learning plan
        plan = client.post("/api/v2/learning/plan", json={
            "goal": "Learn Python basics"}, headers=headers)
        assert plan.status_code == 200
        assert len(plan.json()["nodes"]) > 0

        # 4. Chat with tutor
        chat = client.post("/api/v2/chat/message", json={
            "message": "What is a variable?", "topic": "Python"}, headers=headers)
        assert chat.status_code == 200
        assert len(chat.json()["content"]) > 0

        # 5. Generate resources
        resources = client.post("/api/v2/resources/generate", json={
            "topic": "Python basics", "concepts": ["variables"],
            "resource_types": ["document"]}, headers=headers)
        assert resources.status_code == 200

        # 6. Take a quiz
        quiz = client.post("/api/v2/evaluation/quiz/score", json={
            "topic": "Python", "answers": [
                {"question_id": "q1", "selected_index": 0,
                 "options": ["A","B","C","D"], "correct_index": 0},
            ]}, headers=headers)
        assert quiz.status_code == 200
        assert quiz.json()["score_percent"] == 100.0

        # 7. Check learning stats
        stats = client.get("/api/v2/learning/stats", headers=headers)
        assert stats.status_code == 200
        assert stats.json()["total_sessions"] >= 1
