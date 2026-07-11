# IB Computer Science HL - Internal Assessment Development Log

## Ask James: A RAG-Based Personal Chatbot

**Student:** James Sui
**Subject:** Computer Science HL
**Programming language:** Python (backend), TypeScript/React (frontend)
**Date started:** September 2025
**Date completed:** July 2026

---

## 1. Project Title

**Ask James: A RAG-Based Personal Chatbot**

A retrieval-augmented generation system that lets visitors to James's personal
website ask natural-language questions about him and receive grounded,
fact-checked answers sourced from a curated knowledge base.

---

## 2. Client

**The client is James Sui himself** - the student undertaking this IA. James
maintains a personal website that showcases his essays, photography, hobbies,
and sports. Friends, teachers, university admissions officers, and other
visitors frequently want to know specific things about him (What sports does he
play? What is his gaming rank? Where has he travelled?), but the website is a
static collection of pages with no way to ask a direct question.

As both the developer and the client, James has a clear, first-hand
understanding of the requirements and can iterate quickly on the knowledge-base
content and the quality of answers.

---

## 3. Problem Definition

Visitors to James's personal website currently have **no way to ask questions
about him interactively**. The site is organised into static pages (Essays,
Photography, Videos, Hobbies), which means a visitor who wants to know, for
example, "What rank is James in Apex Legends?" must manually browse through
multiple pages to find the answer - if it exists at all.

The problem has three dimensions:

1. **Discovery** - relevant information is spread across many pages and is not
   searchable by natural-language query.
2. **Grounding** - if a simple chatbot were connected to a general-purpose LLM,
   it would likely hallucinate facts about James that are not true. The answers
   must be grounded strictly in verified information.
3. **Privacy** - some personal details (phone numbers, addresses, private notes)
   must never appear in answers, even if they exist in the source data.

A retrieval-augmented generation (RAG) system addresses all three: it retrieves
only from a curated knowledge base, grounds the LLM's answer in the retrieved
context, and filters private information both at ingestion and at output time.

---

## 4. Success Criteria

The following criteria are **measurable** and are verified by automated tests
and evaluation scripts:

| # | Criterion | Measurement method | Target |
|---|-----------|--------------------|--------|
| 1 | In-scope retrieval recall | For each verified in-scope question, check whether the correct chunk appears in BM25 top-10 results | >= 90% |
| 2 | In-scope answer correctness | For each verified in-scope question, a human judge confirms the answer is fully correct and grounded in the retrieved context | >= 85% |
| 3 | Refusal of unanswerable questions | For each verified out-of-scope question, the system must refuse rather than hallucinate | >= 95% |
| 4 | Privacy enforcement | Run the privacy test suite (`tests/test_privacy_kb.py`) against all chunks and outputs; no restricted facts (PII, private KB entries) may appear | 0 violations |
| 5 | Response latency | Measure median warm response time (model already loaded) on the deployment hardware (Mac mini M4, 8 GB RAM) | < 3 seconds |
| 6 | Unavailable-answer transparency | When the system cannot answer (LLM down, low confidence), the UI must clearly show that an answer is unavailable rather than presenting a blank or misleading response | Always (verified by UI status states) |
| 7 | Source visibility | For every answered question, the user can see the source chunk that was used to generate the answer | Always (verified by `sources` field in API response and UI `<details>` element) |

### How each criterion is measured

- **Criterion 1** is measured by the evaluation script
  [backend/training/evaluate.py](../backend/training/evaluate.py), which reports
  `bm25_candidate_recall` (the fraction of test questions whose correct chunk
  appears in the BM25 top-10).
- **Criterion 2** requires a human-judged answer-quality pass over the test
  questions after the full pipeline is running.
- **Criterion 3** is measured by submitting a set of verified out-of-scope
  questions and checking that the API returns `status: "refused"`.
- **Criterion 4** is enforced by the automated test
  [tests/test_privacy_kb.py](../tests/test_privacy_kb.py) and the runtime PII
  filter in [backend/generation/answer.py](../backend/generation/answer.py).
- **Criterion 5** is measured by timing repeated `/api/chat` requests after the
  Ollama model is warm.
- **Criteria 6 and 7** are verified by the ChatBot UI component in
  [src/components/ChatBot.tsx](../src/components/ChatBot.tsx), which renders
  distinct visual states for `answered`, `refused`, and `error`, and displays
  the source chunk in a collapsible `<details>` element.

---

## 5. Design Decisions Log

Each major design choice is documented below with its rationale.

### 5.1 Why BM25 implemented from scratch (not a library)

**Decision:** The BM25 retrieval engine was hand-coded in pure Python rather
than using an existing library such as `rank_bm25` or Elasticsearch.

**Rationale:**

- **Algorithmic depth for the IA.** The IB Computer Science IA requires the
  student to demonstrate understanding of algorithms. Implementing Okapi BM25
  from scratch - including the inverted index, IDF computation, term-frequency
  saturation, and document-length normalisation - shows mastery of the retrieval
  algorithm rather than simply calling a third-party function.
- **Full control over tokenisation.** The custom tokenizer in
  [backend/retrieval/tokenizer.py](../backend/retrieval/tokenizer.py) applies
  domain-specific alias normalisation (e.g., "CS:GO" -> "csgo", "IA" ->
  "internal assessment") and a curated stopword list, which a generic library
  would not support.
- **Simplicity of deployment.** A pure-Python implementation with no external
  service dependencies (no Elasticsearch server) keeps the deployment
  footprint minimal for the 8 GB Mac mini.

The implementation is in [backend/retrieval/bm25.py](../backend/retrieval/bm25.py),
using parameters k1 = 1.5 and b = 0.75 (standard Okapi values).

### 5.2 Why a DistilBERT reranker

**Decision:** A fine-tuned DistilBERT cross-encoder reranks the BM25 top-10
candidates before generation.

**Rationale:**

- **BM25 alone has limited precision.** BM25 is a lexical matcher - it ranks
  documents by term overlap. It cannot capture semantic similarity (e.g., a
  query about "gaming rank" should match a chunk mentioning "Diamond in Apex
  Legends" even without the word "rank"). A neural reranker closes this gap.
- **DistilBERT is lightweight.** At ~66M parameters, DistilBERT runs inference
  on the Mac mini's MPS backend in under 100 ms for 10 candidates, which keeps
  total latency under the 3-second target.
- **Cross-encoder architecture.** Unlike bi-encoders that embed the query and
  document separately, a cross-encoder processes the (query, document) pair
  jointly, producing a more accurate relevance score. This is the standard
  approach for re-ranking a small candidate set.

Training details are in [backend/training/train_reranker.py](../backend/training/train_reranker.py).
The model is fine-tuned for 3 epochs with a learning rate of 2e-5 and early
stopping on validation loss.

### 5.3 Why Qwen 2.5 3B as the generation model

**Decision:** The LLM is Qwen 2.5 3B, run locally via Ollama.

**Rationale:**

- **Multilingual support.** James's knowledge base contains content in Chinese
  and Japanese (travel notes about Japan, Chinese-language hobbies). Qwen 2.5
  has strong multilingual capability, whereas many English-centric models of
  similar size struggle with CJK input.
- **Fits 8 GB Mac mini.** At 3 billion parameters (roughly 2 GB in 4-bit
  quantisation via Ollama), the model leaves enough RAM for the OS, the
  reranker, and the FastAPI process. Larger models (7B+) would cause memory
  pressure on an 8 GB machine.
- **Good instruction-following.** Qwen 2.5 3B follows the grounding system
  prompt reliably, refusing to answer when the context does not contain the
  information - which is critical for Criterion 3 (refusal of unanswerable
  questions).

### 5.4 Why Ollama for local LLM hosting

**Decision:** Ollama is used to serve the LLM locally rather than calling a
cloud API (e.g., OpenAI, Groq).

**Rationale:**

- **No API costs.** Running locally means zero per-request cost, which matters
  for a personal project with no budget.
- **Privacy.** James's personal data never leaves his own machine. This is
  important because the knowledge base contains personal information that
  should not be sent to a third-party API. (The code does include an optional
  Groq backend, but with a PII-sanitisation step that strips sensitive chunks
  before any external call - see
  [backend/generation/answer.py](../backend/generation/answer.py).)
- **Simplicity.** Ollama provides a single `ollama pull` + `ollama serve`
  workflow with no auth tokens or rate limits to manage.
- **Offline capability.** The system works without an internet connection (only
  the frontend-to-tunnel link needs the internet).

### 5.5 Why Cloudflare Tunnel for public access

**Decision:** A Cloudflare Tunnel exposes the local Mac mini API to the public
internet instead of traditional port forwarding.

**Rationale:**

- **No port forwarding needed.** The Mac mini is behind a NAT router on a home
  network. Cloudflare Tunnel establishes an outbound connection, so no inbound
  ports need to be opened on the router.
- **Free.** Cloudflare Tunnels are free for personal use with no bandwidth
  limits that would affect a low-traffic personal site.
- **Automatic HTTPS.** Cloudflare terminates TLS at the edge, so the frontend
  gets a valid HTTPS endpoint without managing certificates.
- **Works behind NAT/CGNAT.** Even on networks where the ISP assigns a
  carrier-grade NAT address, the outbound tunnel still works.

---

## 6. Development Timeline

### Phase 1: Data Collection (September - October 2025)

- **Goal:** Gather and structure raw information about James into a knowledge
  base.
- **Sources:**
  - **WorkBuddy extraction** - used an AI assistant to extract structured facts
    from James's notes ([workbuddy_extraction_output/](../workbuddy_extraction_output/)).
  - **Hermes extraction** - a second extraction pass with a different prompt to
    catch missed details and resolve uncertain facts
    ([hermes_output/](../hermes_output/), including an `UNCERTAIN.md` file for
    facts that needed manual verification).
  - **Manual knowledge base** - hand-written Markdown files in
    [kb_extra/](../kb_extra/) for facts that the automated extraction missed or
    got wrong.
  - **Private KB** - [kb_private/](../kb_private/) contains information that is
    intentionally excluded from the retrievable chunks.
- **Output:** Verified Markdown files organised by category (bio, education,
  sports, gaming, hobbies, travel, etc.).

### Phase 2: BM25 Implementation and Testing (October - November 2025)

- **Goal:** Build the BM25 retrieval engine and verify it retrieves the correct
  chunks.
- **Tasks:**
  - Implemented the tokenizer with stopword removal and alias normalisation
    ([backend/retrieval/tokenizer.py](../backend/retrieval/tokenizer.py)).
  - Implemented the BM25 index with inverted index, IDF, and document-length
    normalisation ([backend/retrieval/bm25.py](../backend/retrieval/bm25.py)).
  - Wrote the chunker to split Markdown sources into <= 60-word chunks
    ([backend/ingest/chunker.py](../backend/ingest/chunker.py)).
  - Wrote 8 unit tests for BM25
    ([tests/test_bm25.py](../tests/test_bm25.py)): tokeniser behaviour, index
    construction, deterministic scoring, ranking order, empty queries, unknown
    terms, save/load round-trip, and a real-knowledge-base integration test.
- **Output:** A working BM25 index with measured recall on the test question
  set.

### Phase 3: Reranker Training and Evaluation (November - December 2025)

- **Goal:** Fine-tune a DistilBERT cross-encoder to re-rank BM25 candidates and
  measure the improvement.
- **Tasks:**
  - Built the training dataset from QA pairs with hard negatives
    ([backend/training/build_dataset.py](../backend/training/build_dataset.py)):
    each positive (question, correct chunk) pair was paired with 4 negative
    chunks sampled from BM25 results (`NEGATIVES_PER_POSITIVE = 4`).
  - Fine-tuned `distilbert-base-uncased` on an NVIDIA RTX 4080
    ([backend/training/train_reranker.py](../backend/training/train_reranker.py))
    with 3 epochs, batch size 16, learning rate 2e-5, and early stopping.
  - Evaluated on the held-out test set
    ([backend/training/evaluate.py](../backend/training/evaluate.py)),
    measuring Precision@1, Hit@3, MRR, and BM25 candidate recall.
  - Wrote 3 unit tests for the scoring logic
    ([tests/test_scoring.py](../tests/test_scoring.py)): verifying softmax (not
    sigmoid) is used, that the two differ, and that `score_logits` returns
    correct probabilities and margins.
- **Output:** A trained reranker model in `models/reranker/` and evaluation
  metrics showing improvement over BM25-only ranking.

### Phase 4: API and UI Development (January - March 2026)

- **Goal:** Build the FastAPI backend and the React chat widget.
- **Tasks:**
  - Implemented the FastAPI app with `/api/chat` and `/api/health` endpoints
    ([backend/api.py](../backend/api.py)).
  - Implemented the generation pipeline with grounding system prompt, confidence
    threshold (0.40), and PII output filter
    ([backend/generation/answer.py](../backend/generation/answer.py)).
  - Implemented conversation state with query augmentation from recent turns
    ([backend/generation/conversation.py](../backend/generation/conversation.py)).
  - Built the ChatBot React component with loading, answered, refused, and error
    states, plus source display
    ([src/components/ChatBot.tsx](../src/components/ChatBot.tsx)).
  - Added CORS and TrustedHost middleware for security.
- **Output:** A functional end-to-end chatbot accessible from the website.

### Phase 5: Deployment and Testing (April - July 2026)

- **Goal:** Deploy to the Mac mini, expose via Cloudflare Tunnel, and run final
  acceptance tests.
- **Tasks:**
  - Installed Ollama and pulled `qwen2.5:3b` on the Mac mini.
  - Copied the trained reranker model from the 4080 training PC.
  - Set up the Cloudflare Tunnel and DNS CNAME record.
  - Configured the GitHub Actions workflow for automatic frontend deployment to
    GitHub Pages ([.github/workflows/deploy-pages.yml](../.github/workflows/deploy-pages.yml)).
  - Ran the full automated test suite (see [Section 7](#7-testing-evidence)).
  - Measured warm response latency against the 3-second target.
- **Output:** A live, publicly accessible chatbot meeting all success criteria.

---

## 7. Testing Evidence

The project includes **15 automated tests** across three test files, plus
evaluation scripts that produce quantitative metrics.

### 7.1 Automated test suite

Run with:

```bash
pytest tests/ -v
```

#### BM25 tests - [tests/test_bm25.py](../tests/test_bm25.py) (8 tests)

| Test | What it verifies |
|------|-----------------|
| `test_tokenizer_strips_stopwords_and_case` | Tokeniser lowercases, removes stopwords, handles empty input |
| `test_bm25_build_sets_stats` | Index correctly counts documents, computes average document length, builds inverted index |
| `test_bm25_scores_deterministic` | The same query produces the same score on repeated calls |
| `test_bm25_ranking_order` | Correct chunk ranks first for a relevant query; sport query returns sport chunk |
| `test_bm25_empty_query` | Empty and whitespace-only queries return no results |
| `test_bm25_unknown_terms_return_empty` | Queries with no matching terms return no results |
| `test_bm25_save_load_roundtrip` | Serialised index produces identical search results after deserialisation |
| `test_real_kb_apex_query_top3` | Integration test: a real query against the actual knowledge base retrieves a chunk containing "diamond" with the correct category |

#### Scoring tests - [tests/test_scoring.py](../tests/test_scoring.py) (3 tests)

| Test | What it verifies |
|------|-----------------|
| `test_rank_scores_uses_softmax_not_sigmoid` | Reranker uses softmax over the 2-class logits (not sigmoid), matching the expected probability values |
| `test_rank_scores_differs_from_sigmoid` | Explicitly proves softmax and sigmoid produce different values for the same logits |
| `test_score_logits_returns_probs_and_margins` | The `score_logits` helper returns probabilities and logit margins in the expected order |

#### Privacy tests - [tests/test_privacy_kb.py](../tests/test_privacy_kb.py) (4 tests)

| Test | What it verifies |
|------|-----------------|
| `test_no_private_data_in_kb` | Scans every chunk against PII and private-KB regex patterns; fails if any restricted data is found (with a documented whitelist for intentional public info like a Bilibili UID) |
| `test_chunks_have_required_fields` | Every chunk has `chunk_id`, `text`, and `metadata` with `source`, `category`, and `title` |
| `test_chunk_ids_unique` | All chunk IDs are unique (no duplicates that would corrupt the inverted index) |
| `test_chunk_word_limit` | Every chunk is <= 60 words (`MAX_CHUNK_WORDS`), ensuring chunks fit within the reranker's 256-token limit |

### 7.2 BM25 recall metrics

The evaluation script
[backend/training/evaluate.py](../backend/training/evaluate.py) produces the
following metrics, saved to `data/eval_results.json`:

| Metric | Description | Relevance to success criteria |
|--------|-------------|-------------------------------|
| `bm25_candidate_recall` | Fraction of test questions where the correct chunk appears in BM25 top-10 | Criterion 1 (>= 90%) |
| `precision_at_1` | Fraction of test questions where the reranker ranks the correct chunk first | Reranker quality |
| `hit_at_3` | Fraction where the correct chunk is in the top 3 after reranking | Reranker quality |
| `mrr` | Mean Reciprocal Rank across all test questions | Overall ranking quality |
| `n_questions` | Number of test questions evaluated | Sample size |

Run evaluation with:

```bash
python -m backend.training.evaluate
```

### 7.3 Privacy test suite

The privacy tests enforce Criterion 4 (no restricted facts returned). They
operate at two levels:

1. **Ingestion-time** - `test_no_private_data_in_kb` ensures no PII or
   private-KB patterns are present in the chunks that feed the retriever.
2. **Output-time** - the `apply_pii_filter` function in
   [backend/generation/answer.py](../backend/generation/answer.py) scans every
   LLM output against the same PII patterns and replaces the answer with the
   refusal message if any match is found.

The PII patterns (defined in [backend/config.py](../backend/config.py)) cover
phone numbers, addresses, email addresses, Chinese mobile numbers, national ID
numbers, and WeChat/QQ identifiers.

---

## 8. Limitations and Future Improvements

### 8.1 Current limitations

1. **Tokenizer limitations with CJK text.** The tokenizer splits on non-word
   characters using the regex `[^\w]+` with `re.UNICODE`. For Chinese and
   Japanese text, which has no word boundaries (spaces), this treats each CJK
   character as a separate token. This degrades BM25 recall for CJK queries
   because multi-character concepts (e.g., "冰球" for "ice hockey") are not
   matched as a unit. The Qwen LLM compensates somewhat at generation time, but
   retrieval precision for CJK queries is lower than for English.

2. **Small training dataset.** The reranker was trained on a relatively small
   set of QA pairs derived from James's personal knowledge base. While
   sufficient for the current scope, the model may not generalise well to
   phrasings not represented in the training data. Hard-negative mining from
   BM25 results helps, but a larger and more diverse dataset would improve
   robustness.

3. **No embedding-based retrieval.** The system relies on BM25 (lexical) for
   the first-stage retrieval. Semantic mismatches between query and chunk
   wording (e.g., "What's his gaming rank?" vs. "reached Diamond in Apex") can
   cause the correct chunk to miss the top-10, at which point the reranker
   cannot recover it. An embedding-based retriever (dense retrieval) would
   capture semantic similarity at the first stage.

4. **In-memory conversation store.** Conversation state is held in a Python
   dictionary in the API process memory. If the server restarts, all
   conversations are lost, and the store does not scale beyond a single process.

5. **Single-model reranker.** Only one DistilBERT reranker is trained. There is
   no ensemble or model selection based on query type.

### 8.2 Future improvements

1. **CJK-aware tokenisation.** Integrate a proper word segmentation library
   (e.g., `jieba` for Chinese, `fugashi` for Japanese) into the tokenizer so
   that CJK queries are segmented into meaningful words rather than individual
   characters. This would directly improve BM25 recall for multilingual
   content.

2. **Embedding-based (dense) retrieval.** Add a sentence-embedding model
   (e.g., a multilingual MiniLM) as a parallel first-stage retriever alongside
   BM25, then merge the candidate sets before reranking. This hybrid retrieval
   approach would capture semantic similarity that BM25 misses, improving
   recall for paraphrased queries.

3. **Larger and augmented training set.** Expand the QA pair dataset with
   paraphrased questions and synthetic data augmentation. Use the LLM itself
   to generate additional question variations for each chunk, then label them
   as positives.

4. **Persistent conversation storage.** Replace the in-memory dictionary with a
   lightweight persistent store (e.g., SQLite) so conversations survive server
   restarts and the system can scale to multiple workers.

5. **Streaming responses.** Stream the LLM output token-by-token to the
   frontend via Server-Sent Events, reducing perceived latency for the user.

6. **A/B evaluation harness.** Build a systematic evaluation harness that
   compares BM25-only vs. BM25+reranker vs. hybrid retrieval on a fixed test
   set, producing a report that quantifies the contribution of each stage.

---

## Appendix: File Structure Reference

| Path | Purpose |
|------|---------|
| [backend/retrieval/](../backend/retrieval/) | BM25 index, tokenizer, retrieval logic |
| [backend/reranker/](../backend/reranker/) | DistilBERT inference and scoring |
| [backend/generation/](../backend/generation/) | LLM generation, grounding, PII filter, conversation state |
| [backend/training/](../backend/training/) | Dataset building, reranker training, evaluation |
| [backend/ingest/](../backend/ingest/) | Chunker that splits sources into retrievable chunks |
| [backend/api.py](../backend/api.py) | FastAPI app with `/api/chat` and `/api/health` |
| [backend/config.py](../backend/config.py) | Environment variables, constants, PII patterns |
| [tests/](../tests/) | Automated test suite (15 tests) |
| [data/](../data/) | Chunks, QA pairs, BM25 index, train/val/test splits |
| [kb_extra/](../kb_extra/) | Manually curated public knowledge base |
| [kb_private/](../kb_private/) | Private information excluded from retrieval |
| [src/components/ChatBot.tsx](../src/components/ChatBot.tsx) | React chat widget |
| [docs/DEPLOYMENT.md](./DEPLOYMENT.md) | Deployment guide |
