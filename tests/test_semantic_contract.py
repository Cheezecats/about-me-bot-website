from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.api import app
from backend.generation import answer
from backend.generation.contracts import unavailable_profile_detail
from backend.generation.query_plan import build_query_plan
from backend.retrieval.bm25 import BM25Index, load_chunks, retrieve


@pytest.fixture(scope="module")
def runtime():
    chunks = load_chunks()
    return chunks, BM25Index.build(chunks)


def ask(question: str, runtime, monkeypatch):
    chunks, index = runtime
    plan = build_query_plan(question)
    monkeypatch.setattr(
        answer,
        "generate_answer",
        lambda *args, **kwargs: pytest.fail("unsupported or eligible deterministic case reached generation"),
    )
    return answer.answer_or_refuse(
        question,
        retrieve(plan.retrieval_query, index, chunks),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )


@pytest.mark.parametrize(
    ("question", "domain", "relation", "object_type"),
    [
        ("favorite picture", "photography", "favorite", "photograph"),
        ("what camera does he use", "photography", "uses", "camera"),
        ("football player he likes", "sports", "likes", "athlete"),
        ("which team does he support", "sports", "supports", "team"),
        ("where does he play on the pitch", "sports", "playing_position", "position"),
        ("song he likes", "music", "likes", "song"),
        ("artist he listens to", "music", "listens_to", "artist"),
        ("how did he learn coding", "projects", "learned_by", "method"),
        ("what did he build with Python", "projects", "created", "project"),
        ("what subjects does he take", "education", "studies", "school_subject"),
        ("why does he like Physics", "education", "reason", "explanation"),
        ("places he visited", "travel", "visited", "place"),
        ("where he photographed", "photography", "photographed_in", "place"),
        ("what method did his histology paper use", "writing", "method", "paper"),
        ("What role does AI play in James's learning?", "hobbies", "uses", "unresolved"),
        ("How would James make technology more accessible?", "personality", "reason", "explanation"),
        ("Does James prefer teamwork or individual work?", "personality", "likes", "unresolved"),
        ("What was hardest about being an IB student?", "education", "reason", "explanation"),
        ("How does engineering combine different skills for James?", "personality", "reason", "explanation"),
        ("What does James think failure leads to?", "personality", "result", "unresolved"),
    ],
)
def test_every_clause_has_one_shared_semantic_contract(
    question, domain, relation, object_type
):
    contract = build_query_plan(question).intent
    assert contract.original_text == question
    assert contract.subject == "james"
    assert contract.domain == domain
    assert contract.relation == relation
    assert contract.object_type == object_type
    assert contract.supporting_spans
    assert contract.provenance == "deterministic"


@pytest.mark.parametrize(
    ("question", "required", "forbidden"),
    [
        ("favorite picture", "curated photo picks", "Nikon Z8"),
        ("favoirate picture", "curated photo picks", "Nikon Z8"),
        ("places he visited", "has visited", "favorite place"),
        ("what did he build with Python", "Economics graphing tool", "personal website"),
        ("where does he play on the pitch", "defender", "Real Madrid"),
    ],
)
def test_evidence_selection_answers_the_requested_relationship(
    question, required, forbidden, runtime, monkeypatch
):
    result = ask(question, runtime, monkeypatch)
    assert result["status"] == "answered", result
    assert required.lower() in result["answer"].lower(), result
    assert forbidden.lower() not in result["answer"].lower(), result


def test_missing_favorite_athlete_is_specific_and_does_not_substitute_team(runtime, monkeypatch):
    result = ask("favorite footballer", runtime, monkeypatch)
    assert result["status"] == "refused", result
    assert result["answer"] == config.REFUSAL_MESSAGE
    assert result["sources"] == []


def test_missing_paper_limitations_do_not_become_product_metadata(runtime, monkeypatch):
    result = ask("What are the limitations of his histology paper?", runtime, monkeypatch)
    assert result["status"] == "refused", result
    assert result["reason"] == "unsupported"
    assert result["answer"] == config.REFUSAL_MESSAGE


def test_bare_favorite_picture_uses_the_same_contract_for_answer_and_navigation(monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *args, **kwargs: pytest.fail("must be deterministic"))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post(
            "/api/chat",
            json={"question": "favorite picture", "session_id": "semantic-photo-pick"},
        )
    body = response.json()
    assert body["status"] == "answered", body
    assert body["actions"] == ["authors-choice"], body
    assert "curated photo picks" in body["answer"].lower(), body


def test_ai_role_question_is_not_mistaken_for_a_different_person():
    plan = build_query_plan("What role does AI play in James's learning?")
    assert plan.intent.contract is not None
    assert plan.intent.contract.domain == "hobbies"
    assert plan.intent.contract.relation == "uses"
    assert not unavailable_profile_detail("What role does AI play in James's learning?", plan.intent)
