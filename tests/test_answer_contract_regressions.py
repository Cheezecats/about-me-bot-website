from __future__ import annotations

import pytest

from backend import config
from backend.generation.answer import answer_or_refuse
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
