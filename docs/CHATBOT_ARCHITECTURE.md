# Ask James Chatbot Architecture

The live chatbot is intentionally local-first:

```text
React chat UI
    ↓
FastAPI /api/chat
    ↓
intent + privacy policy checks
    ↓
conversation-aware query expansion
    ↓
deterministic query planner (typos, informal phrasing, CJK aliases, entity targets)
    ↓
BM25 retrieval with topic aliases and summary bonuses
    ↓
deterministic structured answer, when a curated fact can answer safely
    ↓ otherwise
Ollama Qwen 2.5 3B with grounded context
    ↓
grounding + privacy checks + labeled sources
```

## Backend modules

| Module | Responsibility |
| --- | --- |
| `backend/generation/intent.py` | Explainable topic, entity, comparison, filter, and follow-up detection |
| `backend/generation/query_plan.py` | Reversible query normalization and retrieval planning for informal or misspelled questions |
| `backend/generation/policies.py` | Privacy, small-talk, product-metadata, unsupported-request, and refusal policies |
| `backend/generation/structured_answers.py` | Data-driven answers from `data/profile_facts.json` |
| `backend/generation/compound.py` | Safe splitting and labeled merging of multi-part questions |
| `backend/generation/formatting.py` | Grounding checks and source metadata formatting |
| `backend/generation/conversation.py` | Bounded session history, entity memory, and follow-up query expansion |
| `backend/generation/answer.py` | Orchestration and Ollama/Groq generation fallback |
| `backend/retrieval/tokenizer.py` | Aliases, typo corrections, stopwords, and query expansions |
| `backend/retrieval/bm25.py` | Deterministic lexical retrieval and topic-summary ranking |

## Data ownership

- `kb_extra/*.md` is the evidence-oriented knowledge base used to build retrieval chunks.
- `data/chunks.json` is the generated retrieval corpus.
- `data/profile_facts.json` is the canonical reviewed fact registry for deterministic answer formatting; its `_sources` map records the supporting KB files.
- `data/evaluation_questions.jsonl` is the regression corpus for supported, unsupported, and privacy cases.
- `data/live_evaluation_questions.jsonl` contains open-ended cases that exercise the live Ollama generation path.

The structured-answer layer checks that a retrieved summary matches the detected
topic before formatting it. Unsupported requests such as a favorite restaurant
therefore remain refusals instead of silently returning a nearby music or
photography fact.

When a fact changes, update the relevant `kb_extra` source and the corresponding reviewed profile fact. Rebuild the chunks and BM25 index before testing:

```bash
.venv/bin/python -m backend.ingest.chunker
.venv/bin/python -m backend.retrieval.bm25
.venv/bin/python scripts/validate_profile_facts.py
.venv/bin/pytest -q
npm run build
```

With the Mac mini backend and Ollama running, evaluate the real HTTP path and record latency, status accuracy, and term coverage:

```bash
.venv/bin/python scripts/evaluate_live_chat.py --repeats 3
```

The generated `data/eval_results.json` file is intentionally machine-local and ignored by Git.

The reranker remains opt-in and disabled in the Mac mini runtime until it has a validated model, calibrated threshold, and evaluation evidence.

## Query-planner rollout and rollback

The deterministic planner is enabled by default because it fixes common query-understanding failures before retrieval, such as `apex legends ank`, `songs he like`, and `favoriate band`. It does not modify the knowledge base or train a model.

To compare against the previous request path, set:

```dotenv
QUERY_PLANNER_ENABLED=false
```

Restart the backend after changing the setting. `/api/health` reports the active value as `query_planner_enabled`, and chat responses expose `normalized_query`, `planner_used`, and `planner_confidence` for evaluation. Restoring `QUERY_PLANNER_ENABLED=true` returns to the improved path without deleting or rewriting the legacy implementation.
