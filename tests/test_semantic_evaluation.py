"""Data-driven coverage for the shared JamChat semantic contract.

The JSONL fixtures intentionally keep phrasing groups and the blind holdout
labels separate from implementation code.  This suite checks interpretation,
positive evidence eligibility, deterministic answers, and approved actions;
it does not count a model timeout as an answer-quality success.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.api import app
from backend.generation import answer
from backend.generation.evidence import capability_for, eligible_evidence
from backend.generation.navigation import answer_actions
from backend.generation.query_plan import build_query_plan
from backend.retrieval.bm25 import BM25Index, load_chunks, retrieve


ROOT = Path(__file__).resolve().parents[1]
SINGLE_TURN_PATH = ROOT / "data" / "semantic_evaluation_cases.jsonl"
SEQUENCE_PATH = ROOT / "data" / "semantic_conversation_cases.jsonl"


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _single_turn_cases() -> list[tuple[dict, str]]:
    return [(row, variant) for row in _read_jsonl(SINGLE_TURN_PATH) for variant in row["variants"]]


SINGLE_TURN_CASES = _single_turn_cases()
CONVERSATION_CASES = _read_jsonl(SEQUENCE_PATH)


@pytest.fixture(scope="module")
def retrieval_runtime():
    chunks = load_chunks()
    return chunks, BM25Index.build(chunks)


def test_semantic_fixture_has_generalization_and_frozen_holdout_coverage():
    total = len(SINGLE_TURN_CASES)
    holdout = sum(len(row["variants"]) for row in _read_jsonl(SINGLE_TURN_PATH) if row.get("holdout"))
    assert total >= 200
    assert holdout / total >= 0.25
    assert len(CONVERSATION_CASES) >= 30
    assert sum(bool(row.get("holdout")) for row in CONVERSATION_CASES) >= 10


@pytest.mark.parametrize("row,question", SINGLE_TURN_CASES, ids=lambda item: item if isinstance(item, str) else None)
def test_single_turn_contract_evidence_answer_and_actions(row, question, retrieval_runtime, monkeypatch):
    chunks, index = retrieval_runtime
    plan = build_query_plan(question)
    contract = plan.intent.contract
    assert contract is not None
    assert contract.original_text == question
    assert contract.validate() == ()
    assert contract.subject == row["expected_subject"]
    assert contract.domain == row["expected_domain"]
    assert contract.relation == row["expected_relation"]
    assert contract.object_type == row["expected_object_type"]
    assert contract.supporting_spans
    assert contract.provenance == "deterministic"

    candidates = retrieve(plan.retrieval_query, index, chunks)
    capability = capability_for(contract, plan.intent)
    eligible = eligible_evidence(contract, plan.intent, candidates)
    if row["expected_status"] == "answered":
        assert capability is not None, (question, contract)
        assert eligible, (question, plan.retrieval_query, contract)
        eligible_titles = {chunk.get("metadata", {}).get("title") for chunk in eligible}
        assert eligible_titles.intersection(row["eligible_titles"]), (question, eligible_titles)
    else:
        assert row["eligible_titles"] == []
        assert capability is None

    assert answer_actions(question, plan.intent) == row["expected_actions"]

    def unexpected_generation(*args, **kwargs):
        raise AssertionError(f"deterministic evaluation case reached model generation: {question}")

    monkeypatch.setattr(answer, "generate_answer", unexpected_generation)
    result = answer.answer_or_refuse(
        question,
        candidates,
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )
    assert result["status"] == row["expected_status"], (question, result)
    answer_text = result["answer"]
    assert not any(term.lower() in answer_text.lower() for term in row["forbidden_terms"]), (question, result)
    if row["acceptable_answer_terms"]:
        assert any(term.lower() in answer_text.lower() for term in row["acceptable_answer_terms"]), (question, result)
    assert "flappy bird" not in answer_text.lower()
    assert all("flappy bird" not in source["text"].lower() for source in result["sources"])


def test_conversation_sequences_preserve_annotated_context_and_actions(monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *args, **kwargs: pytest.fail("sequence reached unplanned model generation"))
    with TestClient(app, base_url="http://localhost") as client:
        # This corpus is a semantic evaluation, so the production per-client
        # request quota should not turn a long fixture run into a rate-limit
        # result.
        monkeypatch.setattr(app.state.rate_limiter, "allow", lambda _key: True)
        for sequence in CONVERSATION_CASES:
            session_id = f"semantic-evaluation-{sequence['id']}"
            for turn in sequence["turns"]:
                body = client.post(
                    "/api/chat",
                    json={"question": turn["question"], "session_id": session_id},
                ).json()
                assert body["status"] == turn["expected_status"], (sequence["id"], turn, body)
                assert "flappy bird" not in body["answer"].lower()
                if "expected_actions" in turn:
                    assert body["actions"] == turn["expected_actions"], (sequence["id"], turn, body)
                for term in turn.get("answer_terms", ()):
                    assert term.lower() in body["answer"].lower(), (sequence["id"], turn, body)

                # Small talk intentionally leaves the prior semantic context
                # intact; its annotated unresolved fields describe the turn,
                # not a destructive state reset.
                if turn["question"].lower().rstrip(".!?") in {"thanks", "thank you", "thanks a lot"}:
                    continue
                state = app.state.conversations.get(session_id)
                assert state is not None and state.last_contract is not None, (sequence["id"], turn)
                contract = state.last_contract
                assert contract.domain == turn["domain"], (sequence["id"], turn, contract)
                assert contract.relation == turn["relation"], (sequence["id"], turn, contract)
                assert contract.object_type == turn["object_type"], (sequence["id"], turn, contract)
                assert contract.context_resolution == turn["context_resolution"], (sequence["id"], turn, contract)
