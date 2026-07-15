from __future__ import annotations

import json

from backend import config
from backend.generation.answer import answer_or_refuse
from backend.generation.intent import detect_intent
from backend.generation.query_plan import build_query_plan
from backend.retrieval.bm25 import BM25Index, load_chunks, retrieve


def _evaluation_rows() -> list[dict]:
    return [
        json.loads(line)
        for line in (config.DATA_DIR / "evaluation_questions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _runtime():
    chunks = load_chunks()
    return chunks, BM25Index.build(chunks)


def test_evaluation_corpus_is_large_enough_and_has_all_modes():
    rows = _evaluation_rows()
    assert len(rows) >= 28
    assert {row["mode"] for row in rows} == {"structured", "policy"}


def test_structured_capabilities_answer_without_llm():
    chunks, index = _runtime()
    rows = [row for row in _evaluation_rows() if row["mode"] == "structured"]
    failures: list[str] = []
    for row in rows:
        plan = build_query_plan(row["question"])
        retrieved = retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K)
        result = answer_or_refuse(
            row["question"],
            retrieved,
            enforce_confidence_threshold=False,
            intent_question=plan.normalized_question,
        )
        if result["status"] != "answered":
            failures.append(f"{row['question']}: status={result['status']}")
            continue
        title = retrieved[0].get("metadata", {}).get("title") if retrieved else None
        if title != row["title"]:
            failures.append(f"{row['question']}: title={title!r}, expected={row['title']!r}")
        for term in row["terms"]:
            if term.lower() not in result["answer"].lower():
                failures.append(f"{row['question']}: missing {term!r}")
    assert not failures, "\n".join(failures)


def test_policy_capabilities_answer_without_retrieval():
    rows = [row for row in _evaluation_rows() if row["mode"] == "policy"]
    failures: list[str] = []
    for row in rows:
        result = answer_or_refuse(row["question"], [], enforce_confidence_threshold=False)
        if result["status"] != row["status"]:
            failures.append(f"{row['question']}: status={result['status']}")
        for term in row["terms"]:
            if term.lower() not in result["answer"].lower():
                failures.append(f"{row['question']}: missing {term!r}")
    assert not failures, "\n".join(failures)


def test_followup_can_resolve_a_previous_sports_topic():
    from backend.generation.conversation import ConversationState

    chunks, index = _runtime()
    state = ConversationState()
    first = "What sports does James play?"
    first_result = answer_or_refuse(first, retrieve(first, index, chunks, k=config.TOP_K), enforce_confidence_threshold=False)
    state.record(first, first_result["answer"], "sports")

    followup = "Which one did he start first?"
    resolved_query = state.augment_query(followup)
    result = answer_or_refuse(
        followup,
        retrieve(resolved_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=resolved_query,
    )
    assert result["status"] == "answered"
    assert "skiing first" in result["answer"].lower()


def test_intent_layer_extracts_topics_entities_and_filters():
    comparison = detect_intent("Which projects involve AI?")
    assert comparison.topic == "projects"
    assert "ai" in comparison.entities

    timeline = detect_intent("Which sports did James start before 2020?")
    assert timeline.topic == "sports"
    assert timeline.before_year == 2020
    assert timeline.comparison

    privacy = detect_intent("What is James's password?")
    assert privacy.kind == "privacy"


def test_entity_questions_use_focused_evidence_chunks():
    chunks, index = _runtime()
    cases = [
        ("What is James's highest rank in Apex Legends?", "Diamond 2"),
        ("What is James's Math IA about?", "Markov chain"),
        ("What did James film in Greece?", "8K"),
        ("What position does James play in ice hockey?", "defender"),
        ("What is James's Extended Essay about?", "Uniswap V3"),
    ]
    for question, expected in cases:
        result = answer_or_refuse(
            question,
            retrieve(question, index, chunks, k=config.TOP_K),
            enforce_confidence_threshold=False,
        )
        assert result["status"] == "answered", question
        assert expected.lower() in result["answer"].lower(), question


def test_query_planner_recovers_informal_typos_and_targets():
    chunks, index = _runtime()
    cases = [
        ("apex legends ank", "rank", "Diamond 2"),
        ("songs he like", "What songs does James like?", "君の神様になりたい"),
        ("favoriate songs", "What songs does James like?", "君の神様になりたい"),
        ("favoriate band", "What are James's favorite bands?", "Yorushika"),
        ("disliked things", "What has James explicitly said he dislikes?", "summer"),
        ("acheivements james", "achievements", "Physics Bowl"),
        ("musci james like", "What songs does James like?", "君の神様になりたい"),
        ("James最喜欢什么游戏？", "What are James's favorite games?", "Apex Legends"),
        ("James喜欢什么音乐？", "What songs does James like?", "君の神様になりたい"),
        ("他会弹什么乐器?", "Does James play an instrument?", "electric guitar"),
    ]
    for question, normalized_term, expected in cases:
        plan = build_query_plan(question)
        assert normalized_term.lower() in (
            f"{plan.normalized_question} {plan.retrieval_query}"
        ).lower(), question
        assert plan.confidence >= 0.9, question
        retrieved = retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K)
        result = answer_or_refuse(
            question,
            retrieved,
            enforce_confidence_threshold=False,
            intent_question=plan.normalized_question,
        )
        assert result["status"] == "answered", question
        assert expected.lower() in result["answer"].lower(), question


def test_query_planner_handles_new_informal_phrasing_without_guessing():
    chunks, index = _runtime()
    cases = [
        ("what does james do for fun", "hobbies", "electric guitar"),
        ("what games does james play", "favorite games", "Apex Legends"),
        ("how good is james at apex", "highest rank", "Diamond 2"),
        ("james hobies", "hobbies", "photography and videography"),
        ("what did james write", "essays", "Uniswap V3"),
        ("what is james's camera gear", "camera", "Nikon Z8"),
        ("How did James learn to code?", "programming", "middle school"),
        ("Why does James enjoy gaming?", "gaming", "friends"),
    ]
    for question, normalized_term, expected in cases:
        plan = build_query_plan(question)
        assert normalized_term.lower() in (
            f"{plan.normalized_question} {plan.retrieval_query}"
        ).lower(), question
        retrieved = retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K)
        result = answer_or_refuse(
            question,
            retrieved,
            enforce_confidence_threshold=False,
            intent_question=plan.normalized_question,
        )
        assert result["status"] == "answered", question
        assert expected.lower() in result["answer"].lower(), question


def test_contextual_anything_else_returns_additional_hobby_evidence():
    from backend.generation.conversation import ConversationState

    chunks, index = _runtime()
    state = ConversationState()
    first = "What does James do for fun?"
    first_plan = build_query_plan(first)
    first_result = answer_or_refuse(
        first,
        retrieve(first_plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=first_plan.normalized_question,
    )
    state.record(first, first_result["answer"], first_plan.intent.topic or "hobbies", first_plan.intent.entities)

    followup = "anything else?"
    resolved = state.augment_query(followup)
    plan = build_query_plan(resolved)
    assert plan.normalized_question == "What else does James do for fun?"
    assert "additional_hobbies" in plan.intent.entities
    retrieved = retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K)
    result = answer_or_refuse(
        followup,
        retrieved,
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
    )
    assert result["status"] == "answered"
    assert "cosplay" in result["answer"].lower()
    assert "3d printer" in result["answer"].lower()
    assert len(result["sources"]) == 4


def test_anything_else_does_not_turn_a_different_topic_into_hobbies():
    plan = build_query_plan("photography camera lens anything else")
    assert plan.intent.topic == "photography"
    assert "additional_hobbies" not in plan.intent.entities


def test_common_additional_hobby_phrasings_are_normalized_consistently():
    for question in [
        "other hobbies",
        "more hobbies",
        "tell me more",
        "and?",
        "what does he do for fun besides that?",
        "what other things does James enjoy?",
    ]:
        plan = build_query_plan(f"hobbies {question}")
        assert plan.normalized_question == "What else does James do for fun?", question
        assert "additional_hobbies" in plan.intent.entities, question


def test_ia_entities_and_apex_season_followup_use_focused_answers():
    chunks, index = _runtime()
    for question, expected in [
        ("What is his Math IA about?", "Markov chain"),
        ("What is his Physics IA about?", "FFT guitar tuner"),
    ]:
        plan = build_query_plan(question)
        result = answer_or_refuse(
            question,
            retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
            enforce_confidence_threshold=False,
            intent_question=plan.normalized_question,
        )
        assert result["status"] == "answered", question
        assert expected.lower() in result["answer"].lower(), question

    from backend.generation.conversation import ConversationState

    state = ConversationState()
    first = "What is James's highest rank in Apex Legends?"
    first_plan = build_query_plan(first)
    first_result = answer_or_refuse(
        first,
        retrieve(first_plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=first_plan.normalized_question,
    )
    state.record(first, first_result["answer"], first_plan.intent.topic or "games", first_plan.intent.entities)

    followup = "What season did he reach it?"
    resolved = state.augment_query(followup)
    followup_plan = build_query_plan(resolved)
    followup_result = answer_or_refuse(
        followup,
        retrieve(followup_plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=followup_plan.normalized_question,
    )
    assert followup_result["status"] == "answered"
    assert "diamond 2" in followup_result["answer"].lower()
    assert "season 22" in followup_result["answer"].lower()


def test_second_hop_followups_keep_the_previous_topic():
    from backend.generation.conversation import ConversationState

    state = ConversationState()
    state.record(
        "What camera does James use?",
        "James's primary camera is a Nikon Z8.",
        "photography",
        ("camera",),
    )
    state.record(
        "What about his lenses?",
        "James uses a NIKKOR lens.",
        "photography",
        ("lens",),
    )
    assert "lens" in state.augment_query("What about it?").lower()

    state = ConversationState()
    state.record(
        "What sports does James play?",
        "James's sports include skiing, ice hockey, tennis, and floorball.",
        "sports",
    )
    state.record(
        "Which one did he start first?",
        "James started skiing first, in 2013.",
        "sports",
    )
    assert "skiing" in state.augment_query("Which one?").lower()


def test_unresolved_followup_asks_for_a_topic_instead_of_guessing():
    result = answer_or_refuse("What about it?", [], enforce_confidence_threshold=False)
    assert result["status"] == "clarification"
    assert "Which topic" in result["answer"]
    assert result["reason"] == "ambiguous_followup"
