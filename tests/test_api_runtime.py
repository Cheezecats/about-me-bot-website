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


def test_api_returns_contextual_followups_and_typo_interpretation():
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/api/chat", json={"question": "james hobies"})
        body = response.json()
        assert response.status_code == 200
        assert body["status"] == "answered"
        assert body["normalization_applied"] is True
        assert "hobbies" in body["normalized_query"].lower()
        assert "What sports does James play?" in body["suggested_questions"]

        meta_response = client.post("/api/chat", json={"question": "how does this chat work"})
        meta_body = meta_response.json()
        assert meta_body["status"] == "answered"
        assert "What model powers this chat?" in meta_body["suggested_questions"]


def test_api_resolves_anything_else_using_the_previous_hobby_topic():
    with TestClient(app, base_url="http://localhost") as client:
        session_id = "anything-else-test"
        first = client.post(
            "/api/chat",
            json={"question": "What does James do for fun?", "session_id": session_id},
        )
        second = client.post(
            "/api/chat",
            json={"question": "anything else?", "session_id": session_id},
        )
        assert first.json()["status"] == "answered"
        assert "electric guitar" in first.json()["answer"].lower()
        assert second.json()["status"] == "answered"
        assert "cosplay" in second.json()["answer"].lower()
        assert "3d printer" in second.json()["answer"].lower()


def test_api_handles_user_reported_camera_and_project_phrasings():
    with TestClient(app, base_url="http://localhost") as client:
        cameras = client.post("/api/chat", json={"question": "what are his cameras"}).json()
        projects = client.post("/api/chat", json={"question": "school projects?"}).json()
        assert cameras["status"] == "answered"
        assert "nikon z8" in cameras["answer"].lower()
        assert "iphone 13 pro" in cameras["answer"].lower()
        assert projects["status"] == "answered"
        assert "ftc robotics project" in projects["answer"].lower()
        assert "flappy" not in projects["answer"].lower()


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


def test_api_preserves_concrete_subjects_for_instrument_and_travel_followups():
    with TestClient(app, base_url="http://localhost") as client:
        instrument_session = "instrument-followup-regression"
        first_instrument = client.post(
            "/api/chat",
            json={"question": "Does James play an instrument?", "session_id": instrument_session},
        ).json()
        second_instrument = client.post(
            "/api/chat",
            json={"question": "When did he start?", "session_id": instrument_session},
        ).json()
        assert first_instrument["status"] == "answered"
        assert second_instrument["status"] == "answered"
        assert second_instrument["normalized_query"].startswith("When did James start playing electric guitar")
        assert second_instrument["answer"] == "James started playing electric guitar in 2025."

        travel_session = "travel-followup-regression"
        client.post(
            "/api/chat",
            json={"question": "Where has James travelled?", "session_id": travel_session},
        )
        italy = client.post(
            "/api/chat",
            json={"question": "What about Italy?", "session_id": travel_session},
        ).json()
        assert italy["status"] == "answered"
        assert "specifically Tuscany" in italy["answer"]
        assert "James has visited" not in italy["answer"]


def test_api_preserves_destination_and_reason_context_across_followups():
    with TestClient(app, base_url="http://localhost") as client:
        travel_session = "report-travel-followup"
        client.post(
            "/api/chat",
            json={"question": "Where has James travelled?", "session_id": travel_session},
        )
        client.post(
            "/api/chat",
            json={"question": "What about Italy?", "session_id": travel_session},
        )
        photographed = client.post(
            "/api/chat",
            json={"question": "What did he photograph there?", "session_id": travel_session},
        ).json()
        greece = client.post(
            "/api/chat",
            json={"question": "And Greece?", "session_id": travel_session},
        ).json()
        assert photographed["status"] == "answered"
        assert "Tuscany" in photographed["answer"]
        assert greece["status"] == "answered"
        assert "Athens" in greece["answer"]

        gaming_session = "report-gaming-followup"
        client.post(
            "/api/chat",
            json={"question": "What games does James like?", "session_id": gaming_session},
        )
        client.post(
            "/api/chat",
            json={"question": "What is his Apex rank?", "session_id": gaming_session},
        )
        season = client.post(
            "/api/chat",
            json={"question": "When did he reach it?", "session_id": gaming_session},
        ).json()
        reason = client.post(
            "/api/chat",
            json={"question": "Why does he enjoy gaming?", "session_id": gaming_session},
        ).json()
        assert "Season 22" in season["answer"]
        assert "relax" in reason["answer"].lower()
        assert "Diamond 2" not in reason["answer"]

        guitar_session = "report-guitar-followup"
        client.post(
            "/api/chat",
            json={"question": "Does James play an instrument?", "session_id": guitar_session},
        )
        genres = client.post(
            "/api/chat",
            json={"question": "What kind of music does he play?", "session_id": guitar_session},
        ).json()
        learned = client.post(
            "/api/chat",
            json={"question": "How did he learn?", "session_id": guitar_session},
        ).json()
        assert "J-pop" in genres["answer"]
        assert "self-taught" in learned["answer"].lower()


def test_api_suppresses_sources_for_refusals_and_clarifications():
    with TestClient(app, base_url="http://localhost") as client:
        refusal = client.post(
            "/api/chat", json={"question": "What is James's Harvard degree?"}
        ).json()
        clarification = client.post(
            "/api/chat", json={"question": "What does he play?"}
        ).json()
        assert refusal["status"] == "refused"
        assert refusal["sources"] == []
        assert clarification["status"] == "clarification"
        assert clarification["sources"] == []


def test_api_resolves_dependent_clauses_inside_one_compound_question():
    with TestClient(app, base_url="http://localhost") as client:
        body = client.post(
            "/api/chat", json={"question": "Does he play guitar and when did he start?"}
        ).json()
        assert body["status"] == "answered"
        assert "electric guitar" in body["answer"].lower()
        assert "2025" in body["answer"]
        assert "Question 2" not in body["answer"]


def test_api_confidence_is_bounded_and_raw_score_remains_diagnostic():
    with TestClient(app, base_url="http://localhost") as client:
        body = client.post("/api/chat", json={"question": "What camera does James use?"}).json()
        assert 0.0 <= body["confidence"] <= 1.0
        assert body["retrieval_score"] >= 0.0
