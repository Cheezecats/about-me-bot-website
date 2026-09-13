from __future__ import annotations

import json

import pytest

from backend import config
from backend.generation import answer
from backend.generation.answer import GeneratedDraft, answer_or_refuse
from backend.generation.contracts import SemanticContract
from backend.generation.formatting import check_grounding
from backend.generation.query_plan import build_query_plan
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
        ("What model camera does James use?", "Nikon Z8"),
        ("When did James start skiing?", "2013"),
        ("How does James's FFT guitar tuner work?", "Web Audio API"),
        ("What did James build for the medical recovery platform?", "patient portal"),
        ("Who inspired his interest in computer science?", "classmate"),
        ("What is the exact name of the Qiu competition?", "丘成桐中学科学奖"),
        ("What is the title of his Uniswap project?", "Uniswap V3"),
        ("What camera did James use to film in Xinjiang?", "iPhone 13 Pro"),
        ("What did James film in Greece?", "Ionian Sea"),
        ("Where did James train for hockey?", "United States"),
    ],
)
def test_reported_answer_contracts_are_answered_from_focused_evidence(question, expected, runtime):
    result = ask(question, runtime)
    assert result["status"] == "answered", (question, result)
    assert expected.lower() in result["answer"].lower(), (question, result)
    assert "## " not in result["answer"]
    assert "provided context" not in result["answer"].lower()


def test_destination_video_query_does_not_return_the_whole_video_list(runtime):
    result = ask("What did James film in Greece?", runtime)
    assert result["status"] == "answered"
    assert "Greece" in result["answer"]
    assert "Hokkaido" not in result["answer"]
    assert "Japan Winter" not in result["answer"]


def test_camera_question_does_not_turn_into_a_model_identity_question(runtime):
    result = ask("What model camera does James use?", runtime)
    assert result["status"] == "answered"
    assert "Nikon Z8" in result["answer"]
    assert "qwen2.5" not in result["answer"].lower()


def test_negative_and_cessation_questions_correct_false_or_unsupported_premises(runtime):
    apex = ask("Is Apex Legends not one of his games?", runtime)
    assert apex["status"] == "answered"
    assert apex["answer"].startswith("No —")
    assert "Apex Legends" in apex["answer"]

    guitar = ask("Did James stop playing guitar?", runtime)
    assert guitar["status"] == "answered"
    assert guitar["answer"].startswith("No —")
    assert "stopped" in guitar["answer"]

    qiu = ask("Did James win the Qiu?", runtime)
    assert qiu["status"] == "answered"
    assert "participated" in qiu["answer"]
    assert "does not say that he won" in qiu["answer"]


def test_scope_and_quantity_contracts_are_preserved(runtime):
    one = ask("Name one competitive game James likes.", runtime)
    assert one["status"] == "answered"
    assert one["answer"].count("Apex Legends") == 1
    assert "CS:GO" not in one["answer"]

    count = ask("How many sports does James play?", runtime)
    assert count["status"] == "answered"
    assert "5 sports" in count["answer"]

    favorite = ask("What is James's favorite game?", runtime)
    assert favorite["status"] == "answered"
    assert "does not rank one single favorite game" in favorite["answer"]


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("James喜欢什么音乐？", "DECO*27"),
        ("James什么时候开始弹吉他？", "2025"),
        ("James用什么相机？", "Nikon Z8"),
        ("丘成桐中学科学奖是什么？", "丘成桐中学科学奖"),
        ("James最喜欢什么游戏？", "Apex Legends"),
    ],
)
def test_cjk_and_mixed_language_questions_reach_the_same_curated_answers(question, expected, runtime):
    result = ask(question, runtime)
    assert result["status"] == "answered", (question, result)
    assert expected.lower() in result["answer"].lower(), (question, result)


@pytest.mark.parametrize(
    "question",
    [
        "What did James do before learning Python?",
        "What did James do after starting guitar?",
    ],
)
def test_unsupported_temporal_comparisons_do_not_substitute_unrelated_facts(question, runtime):
    result = ask(question, runtime)
    assert result["status"] == "refused"
    assert result["sources"] == []


def test_unicode_grounding_accepts_a_grounded_cjk_answer_and_rejects_unrelated_text():
    context = [{"text": "丘成桐中学科学奖 (Qiu Competition)"}]
    assert check_grounding("丘成桐中学科学奖 (Qiu Competition)", context)
    assert not check_grounding("东京大学 (University of Tokyo)", context)


def test_generated_draft_requires_at_least_one_actual_citation():
    contract = SemanticContract(
        original_text="What does James think failure leads to?",
        subject="james",
        domain="personality",
        relation="result",
        object_type="unresolved",
        context_resolution="explicit",
        supporting_spans=("failure", "leads to"),
    )
    context = [{
        "chunk_id": "failure",
        "text": "Failure is nothing more than a piece of data that will result in a more appropriate design.",
    }]

    draft = GeneratedDraft(
        answer="James sees failure as data that can result in a more appropriate design.",
        answered_relation="result",
        evidence_ids=(),
    )

    assert not draft.validate(contract, context)


def test_direct_outcome_language_can_answer_a_documented_reason():
    contract = SemanticContract(
        original_text="Why does James see failure as useful?",
        subject="james",
        domain="personality",
        relation="reason",
        object_type="explanation",
        context_resolution="explicit",
        supporting_spans=("why", "failure"),
    )
    context = [{
        "chunk_id": "failure",
        "text": "Failure is nothing more than a piece of data that will result in a more appropriate design.",
    }]
    draft = GeneratedDraft(
        answer="Failure is nothing more than a piece of data that will result in a more appropriate design.",
        answered_relation="reason",
        evidence_ids=("failure",),
    )

    assert draft.validate(contract, context)


def test_explanatory_draft_cannot_just_repeat_the_requested_topic():
    contract = SemanticContract(
        original_text="What interests him about computer hardware?",
        subject="james",
        domain="education",
        relation="reason",
        object_type="explanation",
        context_resolution="explicit",
        supporting_spans=("interests", "computer hardware"),
    )
    context = [{
        "chunk_id": "hardware",
        "text": "Computer hardware and chip design interest James because he enjoys understanding how computers work at the hardware level.",
    }]
    draft = GeneratedDraft(
        answer="Computer hardware.",
        answered_relation="reason",
        evidence_ids=("hardware",),
    )

    assert not draft.validate(contract, context)


def test_generated_draft_must_be_grounded_in_its_cited_evidence():
    contract = SemanticContract(
        original_text="What does James think failure leads to?",
        subject="james",
        domain="personality",
        relation="result",
        object_type="unresolved",
        context_resolution="explicit",
        supporting_spans=("failure", "leads to"),
    )
    context = [
        {
            "chunk_id": "education",
            "text": "James studies Mathematics and Physics.",
        },
        {
            "chunk_id": "failure",
            "text": "Failure is nothing more than a piece of data that will result in a more appropriate design.",
        },
    ]

    draft = GeneratedDraft(
        answer="James sees failure as data that can result in a more appropriate design.",
        answered_relation="result",
        evidence_ids=("education",),
    )

    assert not draft.validate(contract, context)


def test_a_citation_cannot_turn_a_nearby_biographical_fact_into_a_reason():
    contract = SemanticContract(
        original_text="Why does James use AI while studying?",
        subject="james",
        domain="hobbies",
        relation="reason",
        object_type="explanation",
        context_resolution="explicit",
        supporting_spans=("why", "use AI"),
    )
    context = [{
        "chunk_id": "ai-usage",
        "text": (
            "James regularly uses AI models for learning. He submitted a piece to the NYT "
            "Growing up with AI contest about the frustration and hope of switching between AI models."
        ),
    }]
    draft = GeneratedDraft(
        answer="James uses AI while studying because he submitted a piece to the NYT contest.",
        answered_relation="reason",
        evidence_ids=("ai-usage",),
    )

    assert not draft.validate(contract, context)


def test_plain_model_text_is_not_given_synthetic_provenance(runtime, monkeypatch):
    question = "How does James think about failure?"
    chunks, index = runtime
    plan = build_query_plan(question)
    monkeypatch.setattr(
        answer,
        "generate_answer",
        lambda *args, **kwargs: (
            "James sees failure as data that can result in a more appropriate design.",
            False,
        ),
    )
    # The deterministic evidence formatter is exercised separately.  Bypass
    # it here so this test reaches the model-draft boundary it is guarding.
    monkeypatch.setattr(answer, "_format_single_source_explanation", lambda *args: None)

    result = answer.answer_or_refuse(
        question,
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )

    assert result["status"] == "refused"
    assert result["reason"] == "invalid_draft"
    assert result["sources"] == []


def test_contract_rollback_keeps_the_legacy_plain_text_generation_path(monkeypatch):
    monkeypatch.setattr(config, "SEMANTIC_CONTRACT_ENABLED", False)
    monkeypatch.setattr(answer, "format_structured_answer", lambda *args: None)
    monkeypatch.setattr(answer, "generate_answer", lambda *args, **kwargs: ("James enjoys photography.", False))

    result = answer.answer_or_refuse(
        "How does James describe his hobbies?",
        [{
            "chunk_id": "hobbies",
            "text": "James enjoys photography.",
            "score": 10.0,
            "metadata": {"category": "hobbies", "title": "Hobbies"},
        }],
        enforce_confidence_threshold=False,
    )

    assert result["status"] == "answered"
    assert result["reason"] == "generated"
    assert result["sources"][0]["chunk_id"] == "hobbies"


def test_generation_receives_the_resolved_contract_without_replanning(monkeypatch):
    contract = SemanticContract(
        original_text="Why does that matter?",
        subject="james",
        domain="personality",
        relation="reason",
        object_type="explanation",
        context_resolution="inherited",
        antecedent_id="failure_view",
        supporting_spans=("why", "that"),
        provenance="memory",
    )
    captured: dict[str, object] = {}

    def call_ollama(messages, timeout):
        captured["messages"] = messages
        return json.dumps(
            {
                "answer": "Failure provides data for a more appropriate design.",
                "answered_relation": "reason",
                "evidence_ids": ["failure"],
            }
        )

    monkeypatch.setattr(answer, "_call_ollama", call_ollama)
    raw, fallback = answer.generate_answer(
        "Why does that matter?",
        [{"chunk_id": "failure", "text": "Failure provides data for a more appropriate design."}],
        contract=contract,
    )

    assert not fallback
    assert json.loads(raw)["evidence_ids"] == ["failure"]
    prompt = captured["messages"][-1]["content"]
    assert "relation=reason" in prompt
    assert "context_resolution=inherited" not in prompt  # metadata stays internal, semantics do not change


@pytest.mark.parametrize(
    "question",
    [
        "What does he find rewarding about tennis?",
        "What interests him about computer hardware?",
    ],
)
def test_interest_and_rewarding_questions_resolve_to_reasons(question):
    assert build_query_plan(question).intent.contract.relation == "reason"


@pytest.mark.parametrize(
    ("question", "relation"),
    [
        ("How does James think about failure?", "describes"),
        ("What motivates his interest in engineering?", "reason"),
    ],
)
def test_views_and_motivations_have_explicit_relationships(question, relation):
    assert build_query_plan(question).intent.contract.relation == relation


def test_informal_game_ability_question_is_interpreted_as_a_rank_request():
    contract = build_query_plan("How good is James at Apex?").intent.contract

    assert contract.relation == "rank"
    assert contract.object_type == "rank"


def test_relationship_scoped_overview_uses_reviewed_video_evidence_without_generation(runtime, monkeypatch):
    question = "How does James describe his videos?"
    chunks, index = runtime
    plan = build_query_plan(question)
    monkeypatch.setattr(answer, "generate_answer", lambda *args, **kwargs: pytest.fail("overview reached generation"))

    result = answer.answer_or_refuse(
        question,
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )

    assert result["status"] == "answered"
    assert result["reason"] == "structured_fact"
    assert "Greece" in result["answer"]
    assert all(source["category"] == "video" for source in result["sources"])


@pytest.mark.parametrize(
    ("question", "terms"),
    [
        ("What does democratizing technology mean to James?", ("energy", "hardware")),
        ("How would James make technology more accessible?", ("energy", "hardware")),
    ],
)
def test_single_source_explanations_preserve_all_documented_mechanisms(question, terms, runtime, monkeypatch):
    chunks, index = runtime
    plan = build_query_plan(question)
    monkeypatch.setattr(answer, "generate_answer", lambda *args, **kwargs: pytest.fail("exact explanation reached generation"))

    result = answer.answer_or_refuse(
        question,
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )

    assert result["status"] == "answered"
    assert result["reason"] == "structured_evidence"
    assert all(term in result["answer"].lower() for term in terms)


def test_single_source_explanation_selects_the_sentence_that_answers_the_reason(runtime, monkeypatch):
    question = "What does James enjoy about the challenge of tennis?"
    chunks, index = runtime
    plan = build_query_plan(question)
    monkeypatch.setattr(answer, "generate_answer", lambda *args, **kwargs: pytest.fail("exact tennis explanation reached generation"))

    result = answer.answer_or_refuse(
        question,
        retrieve(plan.retrieval_query, index, chunks, k=config.TOP_K),
        enforce_confidence_threshold=False,
        intent_question=plan.normalized_question,
        intent_override=plan.intent,
    )

    assert result["reason"] == "structured_evidence"
    assert "individual" in result["answer"].lower()
    assert "challenging" in result["answer"].lower()
    assert "rewarding" in result["answer"].lower()
