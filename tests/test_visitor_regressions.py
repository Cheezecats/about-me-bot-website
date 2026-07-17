from __future__ import annotations

import pytest

from backend import config
from backend.generation import answer as answer_module
from backend.generation.answer import answer_or_refuse
from backend.generation.conversation import ConversationState
from backend.generation.query_plan import build_query_plan
from backend.generation.suggestions import build_follow_up_questions
from backend.retrieval.bm25 import BM25Index, load_chunks, retrieve


@pytest.fixture(scope="module")
def runtime():
    chunks = load_chunks()
    return chunks, BM25Index.build(chunks)


def ask(question: str, runtime: tuple[list[dict], BM25Index]) -> dict:
    chunks, index = runtime
    plan = build_query_plan(question)
    return answer_or_refuse(
        question,
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
    )


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Tell me about James", "17-year-old student"),
        ("What is James like as a person?", "nice, outgoing self-learner"),
        ("What subjects does he study?", "Computer Science"),
        ("When will he graduate?", "2027"),
        ("What videos has James made?", "Japan Winter"),
        ("Does James draw?", "digital drawing"),
        ("What did he publish?", "Curieux Academic Journal"),
        ("What is his YouTube channel?", "youtube.com/@cheezecats"),
        ("What does James want to study?", "semiconductors"),
        ("How has anime influenced him?", "visual styles"),
    ],
)
def test_common_visitor_questions_use_supported_evidence(question: str, expected: str, runtime):
    result = ask(question, runtime)
    assert result["status"] == "answered", result
    assert expected.lower() in result["answer"].lower(), result


def test_camera_and_lens_starter_question_answers_both_parts(runtime):
    result = ask("What camera and lenses does James use?", runtime)
    assert result["status"] == "answered"
    assert "Nikon Z8" in result["answer"]
    assert "NIKKOR 24-120mm F4 S" in result["answer"]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("gaming", "Apex Legends"),
        ("game", "Apex Legends"),
        ("videogames", "Apex Legends"),
        ("What are James's future academic interests?", "semiconductors"),
        ("What lenses does James use?", "NIKKOR 24-120mm F4 S"),
        ("Where has James photographed?", "Tuscany, Italy"),
        ("What places has James photographed?", "Athens, Greece"),
    ],
)
def test_reported_meta_bare_and_focused_questions_are_answered(question, expected, runtime):
    result = ask(question, runtime)
    assert result["status"] == "answered", result
    assert expected.lower() in result["answer"].lower(), result


def test_bare_gaming_does_not_use_a_secondary_social_gaming_chunk(runtime):
    result = ask("gaming", runtime)
    assert result["status"] == "answered"
    assert "favorite games are" in result["answer"].lower()
    assert "gaming connects with peers" not in result["answer"].lower()


@pytest.mark.parametrize(
    "seed",
    [
        "How does this chat work?",
        "What are James's favorite games?",
        "What camera does James use?",
        "What are James's hobbies?",
        "What songs does James like?",
        "Where has James travelled?",
        "What are James's future academic interests?",
    ],
)
def test_suggested_questions_are_answerable(seed, runtime):
    plan = build_query_plan(seed)
    for question in build_follow_up_questions(plan.intent, "answered"):
        result = ask(question, runtime)
        assert result["status"] == "answered", (seed, question, result)
        assert result["answer"] != config.REFUSAL_MESSAGE, (seed, question, result)


def test_best_sport_does_not_invent_a_ranking(runtime):
    result = ask("What sport is James best at?", runtime)
    assert result["status"] == "answered"
    assert "does not identify one" in result["answer"]


def test_jamchat_brand_is_recognized_for_meta_questions():
    result = answer_or_refuse("How does JamChat work?", [], enforce_confidence_threshold=False)
    assert result["status"] == "answered"
    assert "RAG" in result["answer"]


def test_direct_contact_question_is_not_mistaken_for_an_unresolved_followup(runtime):
    result = ask("What is his YouTube channel?", runtime)
    assert result["reason"] != "ambiguous_followup"


def test_favorite_followup_inherits_topic_context(runtime):
    chunks, index = runtime
    state = ConversationState()
    first = ask("What is James's favorite anime?", runtime)
    state.record("What is James's favorite anime?", first["answer"], "favorites", ("anime",))
    followup = "Tell me more"
    resolved = state.augment_query(followup)
    plan = build_query_plan(resolved)
    result = answer_or_refuse(
        followup,
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
    )
    assert result["status"] == "answered"
    assert "Bang Dream Mygo" in result["answer"]


def test_grounding_rejects_a_hallucinated_anime_genre_claim():
    from backend.generation.formatting import check_grounding

    context = [{"text": "Anime deeply influenced James's taste for visual styles in a Japanese fashion."}]
    assert not check_grounding("James's favorite anime genres are action and drama.", context)


def test_instrument_temporal_followup_keeps_the_guitar_subject(runtime):
    chunks, index = runtime
    state = ConversationState()
    first_plan = build_query_plan("Does James play an instrument?")
    first = answer_or_refuse(
        "Does James play an instrument?",
        retrieve(first_plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=first_plan.normalized_question,
    )
    state.record(
        "Does James play an instrument?",
        first["answer"],
        first_plan.intent.topic or "unknown",
        first_plan.intent.entities,
        normalized_question=first_plan.normalized_question,
    )
    resolved = state.augment_query("When did he start?")
    assert resolved == "When did James start playing electric guitar?"
    plan = build_query_plan(resolved)
    result = answer_or_refuse(
        "When did he start?",
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
    )
    assert result["status"] == "answered"
    assert result["answer"] == "James started playing electric guitar in 2025."


def test_named_travel_followup_selects_the_destination_chunk(runtime):
    chunks, index = runtime
    state = ConversationState()
    first_plan = build_query_plan("Where has James travelled?")
    first = answer_or_refuse(
        "Where has James travelled?",
        retrieve(first_plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=first_plan.normalized_question,
    )
    state.record(
        "Where has James travelled?",
        first["answer"],
        first_plan.intent.topic or "unknown",
        first_plan.intent.entities,
        normalized_question=first_plan.normalized_question,
    )
    resolved = state.augment_query("What about Italy?")
    plan = build_query_plan(resolved)
    result = answer_or_refuse(
        "What about Italy?",
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
    )
    assert result["status"] == "answered"
    assert "specifically Tuscany" in result["answer"]
    assert "black and orange" in result["answer"]
    assert "James has visited" not in result["answer"]


def test_polished_answers_remove_first_person_and_duplicate_video_metadata(runtime):
    anime = ask("How has anime influenced James?", runtime)
    videos = ask("What videos has James made?", runtime)
    assert "my favorite" not in anime["answer"].lower()
    assert "my experience" not in videos["answer"].lower()
    assert "Filmed 2024, captured 4K." not in videos["answer"]


def test_ollama_timeout_is_passed_to_http_client(monkeypatch):
    captured: dict[str, object] = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "ok"}}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(answer_module.httpx, "post", fake_post)
    assert answer_module._call_ollama([], timeout=2.5) == "ok"
    assert captured["timeout"] == 2.5
