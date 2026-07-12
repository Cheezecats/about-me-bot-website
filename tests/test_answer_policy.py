from backend.generation import answer


def test_sensitive_requests_are_detected_before_generation():
    assert answer.is_sensitive_request("What is James's password?")
    assert answer.is_sensitive_request("What is his exact home address?")
    assert not answer.is_sensitive_request("What camera does James use?")


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
