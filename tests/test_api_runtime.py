from __future__ import annotations

from backend.api import _RateLimiter
from backend.api import app
from backend import config
from backend.generation.conversation import ConversationState, ConversationStore
from fastapi.testclient import TestClient


def test_rate_limiter_blocks_only_after_configured_limit():
    limiter = _RateLimiter(limit=2)
    assert limiter.allow("client")
    assert limiter.allow("client")
    assert not limiter.allow("client")
    assert limiter.allow("other-client")


def test_conversation_store_is_bounded_and_returns_state():
    store = ConversationStore(max_conversations=1, ttl_seconds=3600)
    first = store.get("first")
    assert isinstance(first, ConversationState)
    store.get("second")
    assert len(store) == 1
    assert store.get("second") is not first


def test_api_uses_planner_and_exposes_rollback_diagnostics():
    with TestClient(app, base_url="http://localhost") as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["query_planner_enabled"] is True

        response = client.post("/api/chat", json={"question": "apex legends ank"})
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "answered"
        assert body["planner_used"] is True
        assert "highest rank" in body["normalized_query"].lower()
        assert "diamond 2" in body["answer"].lower()


def test_api_can_disable_planner_without_changing_legacy_answer_path(monkeypatch):
    monkeypatch.setattr(config, "QUERY_PLANNER_ENABLED", False)
    with TestClient(app, base_url="http://localhost") as client:
        health = client.get("/api/health")
        assert health.json()["query_planner_enabled"] is False

        response = client.post("/api/chat", json={"question": "favorite game"})
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "answered"
        assert body["planner_used"] is False
        assert body["normalized_query"] == "favorite game"


def test_api_preserves_entities_across_second_hop_followups():
    with TestClient(app, base_url="http://localhost") as client:
        session_id = "followup-test"
        first = client.post(
            "/api/chat",
            json={"question": "What camera does James use?", "session_id": session_id},
        )
        second = client.post(
            "/api/chat",
            json={"question": "What about his lenses?", "session_id": session_id},
        )
        third = client.post(
            "/api/chat",
            json={"question": "What about it?", "session_id": session_id},
        )
        assert first.json()["status"] == "answered"
        assert second.json()["status"] == "answered"
        assert third.json()["status"] == "answered"
        assert "nikkor" in third.json()["answer"].lower()
