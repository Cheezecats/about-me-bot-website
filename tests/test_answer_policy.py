from backend.generation import answer


def test_sensitive_requests_are_detected_before_generation():
    assert answer.is_sensitive_request("What is James's password?")
    assert answer.is_sensitive_request("What is his exact home address?")
    assert not answer.is_sensitive_request("What camera does James use?")


def test_small_talk_gets_a_direct_response_without_retrieval(monkeypatch):
    def fail_generation(*args, **kwargs):
        raise AssertionError("small talk must not reach generation")

    monkeypatch.setattr(answer, "generate_answer", fail_generation)
    result = answer.answer_or_refuse("hi", [], enforce_confidence_threshold=False)

    assert result["status"] == "answered"
    assert "Ask me about James" in result["answer"]


def test_product_identity_questions_are_not_sent_to_the_james_kb():
    result = answer.answer_or_refuse("what model are you", [], enforce_confidence_threshold=False)
    assert result["status"] == "answered"
    assert "qwen2.5:3b" in result["answer"]
    assert result["sources"] == []


def test_small_talk_detection_is_narrow():
    assert answer.is_small_talk("hello!")
    assert answer.is_small_talk("hey there")
    assert answer.is_small_talk("how are you")
    assert not answer.is_small_talk("What are James's hobbies?")


def test_ambiguous_family_request_does_not_guess_from_a_related_chunk():
    result = answer.answer_or_refuse("family", [], enforce_confidence_threshold=False)
    assert result["status"] == "refused"
    assert result["answer"] == answer.config.REFUSAL_MESSAGE


def test_non_profile_game_recommendation_does_not_answer_about_james():
    result = answer.answer_or_refuse("nice games", [], enforce_confidence_threshold=False)
    assert result["status"] == "refused"
    assert result["answer"] == answer.config.REFUSAL_MESSAGE


def test_unsupported_favorite_detail_does_not_silently_substitute_music():
    result = answer.answer_or_refuse(
        "What is James's favorite restaurant?",
        [{
            "chunk_id": "music",
            "text": "## Favorite music Current favorite song: a song. Favorite bands: Yorushika.",
            "score": 10.0,
            "metadata": {"title": "Favorite music", "category": "favorites"},
        }],
        enforce_confidence_threshold=False,
    )
    assert result["status"] == "refused"
    assert "restaurant" not in result["answer"].lower() or "don't have" in result["answer"].lower()


def test_refusal_variants_are_canonicalized():
    assert answer.normalize_refusal("The provided context does not contain that information.") == answer.config.REFUSAL_MESSAGE


def test_favorite_programming_language_is_not_inferred():
    result = answer.answer_or_refuse(
        "What is James's favorite programming language?",
        [],
        enforce_confidence_threshold=False,
    )
    assert result["status"] == "refused"
    assert result["answer"] == answer.config.REFUSAL_MESSAGE


def test_numeric_hallucination_fails_grounding():
    chunks = [{"text": "James started skiing in 2013 and ice hockey in 2015."}]
    assert not answer._check_grounding(
        "James started skiing at age 10 and hockey at age 19.", chunks
    )


def test_structured_summary_can_replace_a_model_refusal(monkeypatch):
    monkeypatch.setattr(
        answer,
        "generate_answer",
        lambda question, context_chunks, history=None: (
            answer.config.REFUSAL_MESSAGE,
            False,
        ),
    )
    result = answer.answer_or_refuse(
        "favorite game",
        [{
            "chunk_id": "games",
            "text": "## Favorite games Competitive top 3: Apex Legends, CS:GO/CS2, Valorant.",
            "score": 10.0,
            "metadata": {"title": "Favorite games", "category": "favorites"},
        }],
        enforce_confidence_threshold=False,
    )
    assert result["status"] == "answered"
    assert "Apex Legends" in result["answer"]


def test_structured_answers_use_consistent_factual_format():
    games = {
        "chunk_id": "games",
        "text": "## Favorite games Competitive top 3: Apex Legends, CS:GO/CS2, Valorant. Non-competitive top 3: Sennen Koi Hana, Cyberpunk 2077, GTA 5.",
        "score": 10.0,
        "metadata": {"title": "Favorite games", "category": "favorites"},
    }
    result = answer.answer_or_refuse("what is James's favorite game", [games], enforce_confidence_threshold=False)
    assert result["status"] == "answered"
    assert "James's favorite games are:" in result["answer"]
    assert "Non-competitive:" in result["answer"]
    assert "not specified" not in result["answer"]


def test_compound_questions_split_only_at_new_question_clauses():
    assert answer.split_compound_question(
        "What camera does James use and what is his favorite season?"
    ) == ["What camera does James use", "what is his favorite season"]
    assert answer.split_compound_question("Does James play ice hockey and tennis?") == [
        "Does James play ice hockey and tennis"
    ]


def test_compound_results_are_labeled_and_sources_are_deduplicated():
    result = answer.merge_compound_results(
        ["What camera does James use", "What is his favorite season"],
        [
            {
                "status": "answered",
                "answer": "James uses a Nikon Z8.",
                "confidence": 0.8,
                "fallback_used": False,
                "sources": [{"chunk_id": "camera", "category": "hobbies", "text": "camera"}],
                "pipeline": {"total_ms": 2},
            },
            {
                "status": "answered",
                "answer": "Winter.",
                "confidence": 0.9,
                "fallback_used": False,
                "sources": [
                    {"chunk_id": "season", "category": "favorites", "text": "season"},
                    {"chunk_id": "camera", "category": "hobbies", "text": "camera"},
                ],
                "pipeline": {"total_ms": 3},
            },
        ],
    )
    assert result["status"] == "answered"
    assert "Photography and gear:" in result["answer"]
    assert "Favorite season:" in result["answer"]
    assert [source["chunk_id"] for source in result["sources"]] == ["camera", "season"]


def test_unavailable_compound_clause_does_not_expose_raw_context():
    result = answer.merge_compound_results(
        ["camera", "school"],
        [
            {"status": "answered", "answer": "Nikon Z8.", "confidence": 0, "sources": [], "pipeline": {}},
            {"status": "unavailable", "answer": "## Current curriculum private raw chunk", "confidence": 0, "sources": [], "pipeline": {}},
        ],
    )
    assert "couldn't answer this part" in result["answer"]
    assert "private raw chunk" not in result["answer"]


def test_compound_privacy_clause_is_labeled_clearly():
    result = answer.merge_compound_results(
        ["camera", "password"],
        [
            {"status": "answered", "answer": "Nikon Z8.", "confidence": 0, "sources": [], "pipeline": {}},
            {"status": "refused", "answer": answer.config.REFUSAL_MESSAGE, "confidence": 0, "sources": [], "pipeline": {}},
        ],
    )
    assert "Privacy:" in result["answer"]


def test_compound_food_and_season_are_both_split_and_formatted():
    assert answer.split_compound_question(
        "What is James's favorite food and favorite season?"
    ) == ["What is James's favorite food", "favorite season"]

    result = answer.merge_compound_results(
        ["What is James's favorite food", "favorite season"],
        [
            {"status": "answered", "answer": "James's favorite food is Japanese ramen.", "confidence": 0, "sources": [], "pipeline": {}},
            {"status": "answered", "answer": "James's favorite season is winter.", "confidence": 0, "sources": [], "pipeline": {}},
        ],
    )
    assert "Japanese ramen" in result["answer"]
    assert "Favorite food:" in result["answer"]
    assert "favorite season" in result["answer"].lower()


def test_explicit_followup_topic_is_not_contaminated_by_previous_answer():
    from backend.generation.conversation import ConversationState

    state = ConversationState()
    state.record(
        "What is James's favorite food and favorite season?",
        "Favorite food: ramen. Favorite season: winter.",
        "favorites",
    )
    assert state.augment_query("What about his lenses?") == "What about his lenses?"


def test_camera_and_lens_answers_are_targeted():
    chunk = {
        "chunk_id": "camera",
        "text": "## Photography and videography Active photographer and videographer. His primary camera is a Nikon Z8. Camera gear also includes a DJI Action 4 and iPhone 13 Pro; his lenses are a NIKKOR 24-120mm F4 S and NIKKOR 85mm F1.8.",
        "score": 10.0,
        "metadata": {"title": "Photography and videography", "category": "hobbies"},
    }
    lens_result = answer.answer_or_refuse("What about his lenses?", [chunk], enforce_confidence_threshold=False)
    camera_result = answer.answer_or_refuse("What camera does James use?", [chunk], enforce_confidence_threshold=False)
    assert "NIKKOR 24-120mm F4 S" in lens_result["answer"]
    assert "Nikon Z8" in camera_result["answer"]
    assert len(lens_result["answer"]) < len(chunk["text"])


def test_awards_are_answered_from_the_achievements_summary():
    chunk = {
        "chunk_id": "achievements",
        "text": "## Achievements & Awards James's achievements include the 2025 Physics Bowl National Silver Award and a national top 5% placement in China Thinks Big.",
        "score": 10.0,
        "metadata": {"title": "Achievements & Awards", "category": "achievements"},
    }
    result = answer.answer_or_refuse("What awards has James won?", [chunk], enforce_confidence_threshold=False)
    assert result["status"] == "answered"
    assert "Physics Bowl National Silver Award" in result["answer"]


def test_refusal_message_is_helpful_but_does_not_reveal_private_data():
    result = answer.answer_or_refuse("What is James's password?", [], enforce_confidence_threshold=False)
    assert result["status"] == "refused"
    assert "public projects" in result["answer"]
    assert "password" not in result["answer"].lower()


def test_achievement_summary_uses_the_full_qiu_award_name():
    chunk = {
        "chunk_id": "achievements",
        "text": "## Achievements & Awards James's achievements include participation in the 丘成桐中学科学奖 (Qiu Competition).",
        "score": 10.0,
        "metadata": {"title": "Achievements & Awards", "category": "achievements"},
    }
    result = answer.answer_or_refuse("What achievements does James have?", [chunk], enforce_confidence_threshold=False)
    assert "丘成桐中学科学奖" in result["answer"]


def test_bm25_fallback_does_not_apply_neural_confidence_threshold(monkeypatch):
    monkeypatch.setattr(
        answer,
        "generate_answer",
        lambda question, context_chunks, history=None: (
            "James uses a Nikon camera.",
            False,
        ),
    )

    result = answer.answer_or_refuse(
        "What camera does James use?",
        [
            {
                "chunk_id": "camera",
                "text": "James uses a Nikon camera.",
                "score": 0.1,
                "metadata": {"category": "hobbies"},
            }
        ],
        enforce_confidence_threshold=False,
    )

    assert result["status"] == "answered"


def test_sensitive_requests_refuse_even_with_context(monkeypatch):
    def fail_generation(*args, **kwargs):
        raise AssertionError("sensitive requests must not reach generation")

    monkeypatch.setattr(answer, "generate_answer", fail_generation)
    result = answer.answer_or_refuse(
        "What is James's bank account number?",
        [{"chunk_id": "x", "text": "irrelevant", "score": 10.0, "metadata": {}}],
        enforce_confidence_threshold=False,
    )

    assert result["status"] == "refused"
    assert result["answer"] == answer.config.REFUSAL_MESSAGE


def test_generation_failure_does_not_return_raw_context(monkeypatch):
    monkeypatch.setattr(
        answer,
        "generate_answer",
        lambda question, context_chunks, history=None: (context_chunks[0]["text"], True),
    )
    result = answer.answer_or_refuse(
        "What camera does James use?",
        [{"chunk_id": "fact", "text": "Private-looking raw retrieval text", "score": 1.0, "metadata": {}}],
        enforce_confidence_threshold=False,
    )
    assert result["status"] == "unavailable"
    assert result["reason"] == "llm_unavailable"
    assert result["answer"] == answer.config.UNAVAILABLE_MESSAGE
    assert "raw retrieval" not in result["answer"]
