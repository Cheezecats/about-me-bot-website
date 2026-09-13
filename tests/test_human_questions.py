"""Behavioral contracts: the requested detail matters more than topic overlap."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend import config
from backend.api import app
from backend.generation import answer
from backend.generation.query_plan import build_query_plan
from backend.retrieval.bm25 import BM25Index, load_chunks, retrieve


@pytest.fixture(scope="module")
def runtime():
    chunks = load_chunks()
    return chunks, BM25Index.build(chunks)


def ask(question, runtime):
    chunks, index = runtime
    plan = build_query_plan(question)
    return answer.answer_or_refuse(
        question, retrieve(plan.retrieval_query, index, chunks),
        enforce_confidence_threshold=False, intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )


@pytest.mark.parametrize(("question", "expected", "absent"), [
    ("Does James still play guitar?", "Yes", "No —"),
    ("Name one non-competitive game", "千恋万花", "Apex Legends"),
    ("What is his favorite game other than Apex?", "CS:GO", "Apex Legends"),
    ("Which sports did he start after 2016?", "Tennis (2018)", "Skiing (2013)"),
    ("Did James start tennis before hockey?", "No", "sports include"),
    ("When did James start tennis?", "2018", "floorball"),
    ("What did he study before IBDP?", "IGCSE", "currently in Grade 11"),
    ("Why does he like Physics?", "hands-on", "James's projects include"),
    ("How long was his Japan trip?", "21-day", "specifically Hokkaido"),
    ("Tell me about his histology paper", "attention pooling", "James has written or researched"),
    ("What did James learn from ice hockey?", "teamwork", "sports include"),
    ("What is his guitar tuner called?", "Tune-app", "James's projects include"),
    ("hey whats he into outside class?", "hobbies", "public profile, so I won't guess"),
    ("which coding langs does he know?", "Python", "projects include"),
    ("How many projects has James built?", "9 projects", "1. React"),
])
def test_focused_answers_preserve_the_question(question, expected, absent, runtime, monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *a, **kw: pytest.fail("Known fact reached the model"))
    result = ask(question, runtime)
    assert result["status"] == "answered", result
    assert expected.lower() in result["answer"].lower(), result
    assert absent.lower() not in result["answer"].lower(), result


@pytest.mark.parametrize("question", [
    "How much did his camera cost?", "What camera settings does James use?",
    "Why does James like his camera?", "What lenses did he use before 2020?",
    "What brand of guitar does he own?", "Why did he start guitar?",
    "When was he in Italy?", "Who went to Italy with him?",
    "What sports does James not play?", "Why does James enjoy ramen?",
    "What is his favorite programming langauge?", "What hobbies does Sarah have?",
    "What did James build with Flappy Bird?",
    "What is James's father's hometown?", "Where does his mother live?",
])
def test_missing_details_refuse_instead_of_substituting_a_summary(question, runtime, monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *a, **kw: pytest.fail("Unsupported detail reached the model"))
    result = ask(question, runtime)
    assert result["status"] == "refused", result
    assert result["answer"] == config.REFUSAL_MESSAGE
    assert result["sources"] == []


@pytest.mark.parametrize("word", ["brand", "photographer", "grades", "singer", "player"])
def test_normalization_does_not_change_real_words_into_topics(word):
    plan = build_query_plan(f"What is his {word}?")
    assert word in plan.normalized_question


def test_followups_keep_specific_subjects_and_ignore_social_turns(monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *a, **kw: (config.REFUSAL_MESSAGE, False))
    with TestClient(app, base_url="http://localhost") as client:
        def send(question):
            return client.post("/api/chat", json={"question": question, "session_id": "focused-memory"}).json()
        send("Tell me about tennis")
        thanks = send("Thanks!")
        assert thanks["reason"] == "small_talk"
        start = send("When did he start?")
        assert "tennis in 2018" in start["answer"].lower(), start
        send("What projects involve AI?")
        second = send("Tell me about the second one")
        assert "hallucination" in second["answer"].lower(), second
        assert "guitar tuner" not in second["answer"].lower()


def test_ambiguous_list_reference_requests_clarification(monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *a, **kw: (config.REFUSAL_MESSAGE, False))
    with TestClient(app, base_url="http://localhost") as client:
        client.post("/api/chat", json={"question": "What sports does James play?", "session_id": "ambiguous-list"})
        body = client.post("/api/chat", json={"question": "When did he start it?", "session_id": "ambiguous-list"}).json()
        assert body["status"] == "clarification", body
        assert body["sources"] == []


@pytest.mark.parametrize(("question", "title"), [
    ("Why engineering?", "Views engineering as duality"),
    ("What about engineering appeals to him?", "Views engineering as duality"),
    ("What does he like about hardware?", "Favorite engineering topics"),
    ("How does AI help him study?", "AI/LLM usage"),
    ("Has school been challenging for James?", "Personal challenge"),
    ("What are the limitations of his histology paper?", "Histology classification research paper"),
    ("What architecture did his histology paper use?", "Histology classification research paper"),
])
def test_open_ended_and_specific_research_questions_use_the_right_evidence(question, title, runtime, monkeypatch):
    def generate(semantic_question, chunks, *args, **kwargs):
        assert chunks[0]["metadata"]["title"] == title
        return config.REFUSAL_MESSAGE, False
    monkeypatch.setattr(answer, "generate_answer", generate)
    result = ask(question, runtime)
    if "limitations" in question.lower():
        # This is a clear but undocumented relationship; the semantic
        # contract now refuses before generation instead of spending a model
        # call to obtain the same refusal.
        assert result["reason"] == "unsupported", result
    else:
        assert result["reason"] in {"model_refusal", "structured_evidence"}, result
        if result["reason"] == "structured_evidence":
            assert result["sources"][0]["title"] == title, result


def test_grade_is_explicitly_a_dated_profile_fact(runtime):
    result = ask("What grade is James in?", runtime)
    assert "Grade 11" in result["answer"]
    assert "2025–2026" in result["answer"]
    assert "currently" not in result["answer"]


def test_bulleted_ordinals_and_explicit_topic_switch(monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *a, **kw: (config.REFUSAL_MESSAGE, False))
    with TestClient(app, base_url="http://localhost") as client:
        def send(question):
            return client.post("/api/chat", json={"question": question, "session_id": "experience-followups"}).json()
        send("What sports does James play?")
        second = send("Tell me about the second one")
        assert second["status"] == "answered", second
        assert "hockey" in second["answer"].lower(), second
        send("Does he play guitar?")
        python = send("How did he learn Python?")
        assert "electric guitar" not in python["answer"].lower(), python
        assert "guitar" not in python["normalized_query"].lower(), python


def test_requested_shorter_list_keeps_facts_and_resolves_new_ordinals(monkeypatch):
    monkeypatch.setattr(answer, "generate_answer", lambda *a, **kw: (config.REFUSAL_MESSAGE, False))
    with TestClient(app, base_url="http://localhost") as client:
        def send(question):
            return client.post("/api/chat", json={"question": question, "session_id": "shorter-list"}).json()
        full = send("What projects has James built?")
        brief = send("Can you make that shorter?")
        assert brief["status"] == "answered", brief
        assert len(brief["answer"]) < len(full["answer"])
        assert "Showing 3 of 9 listed items" in brief["answer"]
        assert brief["sources"]
        assert "Flappy Bird" not in brief["answer"]
        second = send("Tell me about the second one")
        assert second["status"] == "answered", second


def test_list_shortening_preserves_surrounding_qualifications():
    from backend.generation.conversation import shorten_list_answer
    text = "Examples only:\n- A\n- B\n- C\n- D\n\nNo dates are documented."
    short = shorten_list_answer(text)
    assert short.startswith("Examples only:")
    assert short.endswith("No dates are documented.")
    assert "Showing 3 of 4" in short
