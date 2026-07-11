import json

from backend import config


def _load_pairs() -> list[dict]:
    return [
        json.loads(line)
        for line in config.QA_PAIRS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_chunks_by_id() -> dict[str, dict]:
    chunks = json.loads(config.CHUNKS_PATH.read_text(encoding="utf-8"))
    return {chunk["chunk_id"]: chunk for chunk in chunks}


def test_qa_questions_are_unique_and_reference_existing_chunks():
    pairs = _load_pairs()
    chunks_by_id = _load_chunks_by_id()

    questions = [pair["question"] for pair in pairs]
    assert len(questions) == len(set(questions))
    assert all(pair["positive_chunk_id"] in chunks_by_id for pair in pairs)


def test_corrected_qa_mappings_contain_required_evidence():
    """Protect manually reviewed mappings from future chunk-ID migrations."""

    required_evidence = {
        "Tell me about James": ("james sui", "student", "shanghai"),
        "Does James play any instruments?": ("electric guitar",),
        "What instrument does James play?": ("electric guitar",),
        "Did James film anything in Greece?": ("video", "greece"),
        "What school does James go to?": ("yk pao school",),
        "Where does James study?": ("yk pao school",),
        "Does James do IB?": ("ibdp",),
        "Did James transfer schools?": ("transferred",),
        "How did James learn to code?": ("self-learned python",),
        "Did James train with the LA Kings?": ("los angeles kings",),
        "Has James played ice hockey internationally?": ("international matches",),
        "Does James play Valorant?": ("valorant",),
        "Does James play CSGO?": ("cs:go",),
        "What anime does James like?": ("clannad", "jojo", "k-on"),
        "Does James like ramen?": ("ramen",),
        "Has James been to Japan?": ("traveled to japan",),
        "Has James been to Italy?": ("traveled to italy",),
        "Has James been to Russia?": ("russia", "ice hockey"),
        "Has James been to the United States?": ("united states", "los angeles"),
        "What is James's Math IA about?": ("markov chain", "apex legends"),
        "What is James's Physics IA about?": ("fft guitar tuner",),
        "What is James's Extended Essay about?": ("uniswap v3",),
        "What is James's TOK exhibition about?": ("tok exhibition",),
        "What does James think about failure?": ("failure", "data"),
        "Does James want to study semiconductors?": ("semiconductors",),
        "What camera does James use?": ("nikon z8",),
        "Does James build PCs?": ("built a pc",),
        "What camera gear does James use?": ("nikon z8", "nikkor"),
        "What lens does James use?": ("nikkor",),
        "What is James's LLM paper about?": ("llm hallucination",),
        "What is James's histology paper about?": ("histology",),
        "What is James's NYT submission about?": ("switching between different ai models",),
        "What was James's Tongji research about?": ("anti-collision",),
    }

    pairs_by_question = {pair["question"]: pair for pair in _load_pairs()}
    chunks_by_id = _load_chunks_by_id()

    for question, expected_terms in required_evidence.items():
        assert question in pairs_by_question
        chunk_id = pairs_by_question[question]["positive_chunk_id"]
        text = chunks_by_id[chunk_id]["text"].lower()
        for term in expected_terms:
            assert term in text, (question, chunk_id, term, text)


def test_unsupported_questions_are_not_training_labels():
    questions = {pair["question"] for pair in _load_pairs()}
    unsupported = {
        "What videos has James made?",
        "What essays has James written?",
        "What is James's father's hometown?",
        "What awards has James won?",
        "What does James value?",
        "What does James think about AI?",
        "What does James think about engineering?",
        "How many photos does James have on his website?",
    }
    assert questions.isdisjoint(unsupported)
