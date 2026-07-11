# Ask James RAG Chatbot: Detailed Critical Review and Improvement Roadmap

**Project:** IB Computer Science HL Internal Assessment, first assessment 2027  
**Review date:** 11 July 2026  
**Repository state reviewed:** 106 generated chunks, 119 QA labels, BM25 implementation, DistilBERT training pipeline, Qwen 2.5 3B generation pipeline, and 12 automated tests  
**Intended readers:** James, project supervisor, and AI coding collaborators such as Trae/GLM-5.2

## 1. Executive conclusion

This project contains enough potential computational depth for an IB Computer Science HL computational solution, particularly through the custom BM25 implementation, data pipeline, model training, retrieval evaluation, privacy considerations, and proposed conversational interface. However, the current repository does not yet provide reliable evidence that the claimed three-stage RAG chatbot works as intended.

The main weakness is not that the models are too small or that the architecture is too simple. The main weakness is that the current evaluation does not measure the deployed pipeline. Several training labels are incorrect, the reranker confidence is calculated incorrectly, test negatives are much easier than production candidates, the conversational component is not integrated, and the website currently has no chatbot API or UI.

The project should therefore not add more architectural complexity yet. The next stage should focus on repairing data, establishing trustworthy baselines, integrating the product, and producing defensible evaluation evidence.

### Current high-level assessment

| Area | Current assessment | Main reason |
|---|---|---|
| Algorithmic complexity | Promising | Custom BM25 and multi-stage ranking demonstrate algorithmic thinking. |
| Product completeness | Incomplete | The RAG chain is available only through a CLI; there is no chatbot API or React interface. |
| Retrieval reliability | Weak | BM25 reaches the labeled chunk in its top 10 for only about 70.6% of the authored questions. |
| Reranker evidence | Not trustworthy yet | Labels are noisy, negatives are random, and evaluation does not use BM25 candidates. |
| Confidence/refusal logic | Invalid | A two-logit classifier is scored using `sigmoid(logit_1)` rather than softmax or a logit margin. |
| Privacy protection | Insufficient | Output regexes are narrow and sensitive facts are already present in the public retrieval corpus. |
| Automated testing | Narrow but passing | All 12 tests pass, but generation, reranking, failure handling, conversation, and end-to-end quality are untested. |
| IA potential | Strong if repaired | The project can demonstrate computational thinking through measured design decisions and iteration. |

## 2. Verified repository facts

The following observations were measured directly from the reviewed repository:

- `kb_extra/` contains 13 Markdown files, not 12.
- `data/chunks.json` contains 106 chunks.
- The chunks contain 83 `extra` chunks and 23 `site` chunks.
- Chunk lengths range from 13 to 60 whitespace-separated words.
- The median chunk length is 50 words and the mean is approximately 44.5 words.
- `data/qa_pairs.jsonl` contains 119 unique questions.
- Those questions reference only 51 of the 106 chunks as positives.
- Fifty-five chunks have no positive QA label.
- The generated training split contains 85 questions expanded into 425 pair rows.
- The validation split contains 17 questions expanded into 85 pair rows.
- The test split contains 17 questions, each evaluated against one positive and nine random candidates.
- All 12 existing automated tests pass.
- The repository contains no trained `models/reranker/` artifact.
- The repository contains no `data/eval_results.json` result file.
- `ConversationState` is not used by the CLI or website.
- The current React source has no chatbot component.
- `main.py` has no chatbot endpoint and appears to serve paths from an older static-site structure.

### Measured BM25 candidate ceiling

Using each authored QA pair's labeled positive chunk as the expected result:

| Metric | Result |
|---|---:|
| Labeled chunk at rank 1 | 38.7% |
| Labeled chunk within top 3 | 64.7% |
| Labeled chunk within top 10 | 70.6% |
| No lexical candidate for the labeled chunk | 22 of 119 questions |

These figures are diagnostic rather than final quality scores because some QA labels are themselves wrong. They nevertheless expose a fundamental limitation: a reranker cannot recover a relevant chunk that BM25 does not place in its candidate set.

## 3. Release-blocking findings

### CR-01: The reranker score is mathematically incorrect

**Affected files:**

- `backend/reranker/inference.py`
- `backend/training/evaluate.py`
- `backend/generation/answer.py`

**Issue:** The classifier produces two logits, but the code calculates relevance using:

```python
torch.sigmoid(logits[:, 1])
```

For a two-class classifier trained with cross-entropy, this is not the probability of class 1. The probability depends on both logits:

```python
torch.softmax(logits, dim=-1)[:, 1]
```

An equivalent ranking score is the margin:

```python
logits[:, 1] - logits[:, 0]
```

Cross-entropy is unchanged if the same constant is added to both logits, while `sigmoid(logit_1)` changes. This means the current 0.40 confidence threshold has no valid probabilistic interpretation.

**Severity:** Critical

**Required correction:**

1. Use softmax probability for displayed confidence and threshold calibration.
2. Use the positive-negative logit margin for ranking, or verify that softmax ranking is used consistently.
3. Retrain or at minimum re-evaluate after the scoring correction.
4. Do not retain `0.40` automatically; recalibrate it on a dedicated answerability dataset.

**Acceptance criteria:**

- Unit tests compare calculated scores against `torch.softmax`.
- Evaluation and production call the same shared scoring function.
- A calibration report explains how the final threshold was selected.
- The report includes false-refusal and unsafe-answer rates, not only overall accuracy.

### CR-02: The QA data contains incorrect positive labels

**Affected files:**

- `data/qa_pairs.jsonl`
- `data/chunks.json`
- generated `data/train.jsonl`, `data/val.jsonl`, and `data/test.jsonl`

**Issue:** Multiple questions are mapped to chunks that do not contain the requested answer. A particularly serious example is chunk `13f9ae177c7da771`. It contains favorite anime, movies, and games, yet it is used as the positive chunk for questions about:

- ice hockey position;
- soccer participation and position;
- favorite music, song, and artist;
- favorite school subject;
- favorite season;
- IDE/editor use.

Other examples include:

- the LA Kings question pointing to a chunk that mentions international training but not the LA Kings;
- the number-of-photos question pointing to a camera-gear chunk that contains no photo count;
- several broad value, future, and personality questions pointing to chunks that contain only a narrow subset of the requested information.

Training on these labels teaches the model false associations. Evaluation against them rewards incorrect rankings.

**Severity:** Critical

**Required correction:** Replace the current label format with an auditable structure such as:

```json
{
  "question_id": "sports-hockey-position-001",
  "question": "What position does James play in ice hockey?",
  "positive_chunk_ids": ["..."],
  "answer_text": "Defender",
  "answer_evidence": "Ice hockey: Defender.",
  "fact_id": "sports.ice_hockey.position",
  "topic_group": "sports-ice-hockey",
  "review_status": "human_verified"
}
```

**Acceptance criteria:**

- Every question has at least one exact answer span or clearly documented semantic evidence.
- A human-readable audit table displays each question beside every positive chunk.
- Questions may have multiple relevant chunks.
- Generated datasets are rebuilt only after all labels pass validation.
- The train/validation/test split groups paraphrases and shared fact IDs together.

### CR-03: Evaluation does not represent production

**Affected files:**

- `backend/training/build_dataset.py`
- `backend/training/evaluate.py`

**Issue:** Test questions are evaluated against one positive and nine uniformly random chunks. Production instead asks the reranker to distinguish among BM25's highest-scoring results. Those are hard candidates containing overlapping terms and topics.

Random candidates are usually trivial. A question about an Apex rank may be compared against photography, food, education, and travel chunks. Good performance in that setting does not show that the reranker can distinguish the correct Apex chunk from other gaming chunks.

**Severity:** Critical

**Required correction:** Evaluate the exact deployed pipeline:

```text
question
  -> tokenizer
  -> BM25 top-k candidates
  -> reranker
  -> confidence/answerability decision
  -> context selection
  -> generator
  -> privacy and grounding checks
  -> final response
```

**Acceptance criteria:**

- Candidate recall is reported before reranking.
- Reranker metrics use saved BM25 candidates from the frozen test corpus.
- End-to-end answer correctness and refusal correctness are reported.
- Latency is reported for each stage and the complete request.
- Results include confidence intervals or variation across repeated splits/seeds where appropriate.

### CR-04: The claimed chatbot product is not integrated

**Affected files:**

- `backend/cli.py`
- `backend/generation/conversation.py`
- `main.py`
- `src/`

**Issue:** The complete chain exists only as a command-line workflow. The React website contains no chatbot. `main.py` contains no RAG API endpoint and appears to reference obsolete `views/`, `styles/`, and `assets/` paths. Conversation state is never instantiated by the application.

**Severity:** Critical

**Required correction:** Build an integrated product with:

- a typed `/api/chat` endpoint;
- startup dependency checks;
- user and session identifiers that do not mix conversation histories;
- query length and content validation;
- loading, unavailable, refused, answered, and error UI states;
- source/evidence display;
- request timeouts and cancellation;
- accessible keyboard and screen-reader behavior;
- deployment instructions for the frontend, API, Ollama, and model files.

**Acceptance criteria:**

- A user can ask a question from the deployed website and receive a grounded answer.
- The UI distinguishes refusal from system failure.
- A missing Ollama service does not crash the API.
- Separate browser sessions do not share history.
- The IA demonstration video can show the complete user workflow.

### CR-05: Privacy is based on weak output detection rather than access control

**Affected files:**

- `backend/config.py`
- `backend/generation/answer.py`
- `tests/test_privacy_kb.py`
- `kb_extra/contact.md`
- `kb_extra/bio.md`
- `kb_extra/education.md`
- `kb_extra/personality.md`
- `kb_extra/travel.md`

**Issue:** Sensitive information is already indexed. The output filter checks only a US-style phone number and an English-style street address. It cannot reliably prevent disclosure of sensitive personal facts, particularly when the cloud Groq backend is enabled and retrieved context is sent externally before output filtering.

Potentially sensitive indexed material includes school and boarding status, partial birthday, public identifiers, family-location stories, fears, bullying, academic distress, university applications, and names of other people.

**Severity:** Critical

**Required correction:** Classify facts before indexing:

| Classification | Example behavior |
|---|---|
| Public | May be retrieved and displayed. |
| Public contact | May be displayed only for explicit contact requests. |
| Restricted | Never enters the public index. |
| Third-party | Excluded unless consent and necessity are documented. |
| Temporary | Includes an expiry or verification date. |

Output filtering should remain only as defense in depth.

**Acceptance criteria:**

- Every fact has a publication classification.
- Restricted facts are absent from the public chunks and BM25 index.
- Context sent to a cloud model is filtered before transmission.
- Tests cover Chinese phone numbers, IDs, email, QQ, WeChat, birthdays, addresses, Unicode digits, word-form digits, separators, credentials, and third-party information.
- Intentionally public fields use an explicit allowlist rather than test comments alone.

## 4. Detailed file review

### 4.1 `backend/config.py`

#### Findings

1. `TOP_K = 10` is not tied to candidate-recall evidence.
2. `CONFIDENCE_THRESHOLD = 0.40` is not calibrated.
3. `MAX_HISTORY_TURNS = 3` does not correspond to actual LLM history behavior.
4. `MAX_CHUNK_WORDS = 60` has no ablation evidence.
5. BM25 parameters are textbook defaults rather than project-specific results.
6. Training uses one seed and one split.
7. The target precision value is not linked to client success criteria.
8. PII patterns are too narrow for the project's location and data types.
9. Model configuration does not identify quantization, context size, Ollama version, or prompt version.

#### Recommended design

- Move experimental settings into a versioned YAML or JSON experiment configuration.
- Keep production-safe defaults in Python.
- Record the configuration used for every evaluation result.
- Separate `PUBLIC_FIELD_ALLOWLIST` from PII detection.
- Add explicit Ollama host, timeout, generation temperature, maximum output tokens, and model health settings.

### 4.2 `backend/ingest/chunker.py`

#### Findings

1. Markdown is treated as plain text.
2. Heading boundaries are not respected.
3. There is no overlap.
4. Long sentences are split at arbitrary word positions.
5. Whitespace word counts do not correspond to model tokens.
6. Text-only IDs lose source identity and are unstable as QA foreign keys.
7. Metadata stores the filename as title rather than the section heading.
8. There is no data version, source timestamp, privacy classification, or fact identifier.

#### Better alternative

Parse Markdown into sections and build chunks from semantically related blocks:

```text
source file
  -> heading tree
  -> paragraphs/list items
  -> atomic facts or short related groups
  -> token-aware size enforcement
  -> optional overlap
  -> metadata and privacy classification
```

Suggested metadata:

```json
{
  "chunk_id": "favorites.music.001",
  "content_hash": "full-content-hash",
  "text": "...",
  "metadata": {
    "source": "extra",
    "path": "kb_extra/favorites.md",
    "category": "favorites",
    "heading_path": ["Favorites", "Favorite music"],
    "fact_ids": ["favorites.song", "favorites.artist"],
    "privacy": "public",
    "verified_at": "2026-07-11"
  }
}
```

### 4.3 `backend/retrieval/tokenizer.py`

#### Findings

- Only `[a-z0-9]` tokens survive.
- Chinese and Japanese query terms disappear.
- Punctuation-dependent names are changed inconsistently.
- No stemming, lemmatization, spelling normalization, or alias expansion exists.
- Removing `not` can reverse user intent.
- The tokenizer does not preserve phrases such as `New York Times`, `LA Kings`, or `computer science`.

#### Recommended experiments

Compare:

1. current tokenizer;
2. Unicode word tokenizer without stopword removal;
3. Unicode tokenizer with revised stopwords;
4. alias-expanded tokenizer;
5. word plus character n-grams;
6. semantic retrieval fallback.

Use the same frozen query groups and report candidate Recall@1, @3, @5, and @10.

### 4.4 `backend/retrieval/bm25.py`

#### Positive aspects

- The inverted index is implemented clearly.
- Document frequency and length normalization are visible and explainable.
- Serialization and deterministic scoring are easy to demonstrate for an IA.

#### Weaknesses

- No index-version compatibility check exists.
- Text-identical chunk IDs could collapse source records.
- Query term repetition is counted linearly.
- Candidate generation has no spelling, phrase, semantic, or fuzzy fallback.
- Metadata cannot be used for filters or boosts.
- Parameter selection is unexplained.

#### Recommended improvements

- Save `index_version`, `chunk_dataset_hash`, tokenizer version, and parameters.
- Reject loading an index built from a different chunk dataset.
- Add optional category/field boosts only if experiments justify them.
- Measure whether a hybrid score improves recall:

```text
hybrid_score = alpha * normalized_bm25 + (1 - alpha) * cosine_similarity
```

Do not add hybrid retrieval merely because it is fashionable; retain it only if the test set demonstrates a clear improvement.

### 4.5 `backend/training/build_dataset.py`

#### Findings

- Uniform random negatives make ranking artificially easy.
- Relevant alternative chunks may be incorrectly labeled negative.
- The split is not fully reproducible because questions are collected through a set before shuffling.
- Questions about the same fact can appear across different splits.
- Topic distribution is not stratified.
- No dataset version or review state is saved.

#### Recommended negative composition

For each training question, consider:

- 2–4 hard negatives from BM25 top results;
- 1–2 same-category semi-hard negatives;
- 1 random negative for general separation;
- all known positive chunks excluded from the negative pool.

Store the retrieval rank and negative source so the training data can be audited.

### 4.6 `backend/training/train_reranker.py`

#### Findings

- A 66M model is fully updated using only 85 independent training questions.
- The apparent 425 training rows are not 425 independent questions.
- Validation accuracy is inflated by a 4:1 negative-positive balance.
- Validation rows from the same question are correlated.
- Early stopping patience 1 is unstable on only 17 validation questions.
- Only one split and seed are used.
- There is no scheduler, weight decay experiment, gradient clipping, or layer-freezing comparison.
- There is no training history artifact beyond console output.

#### Recommended model experiment matrix

| Experiment | Training | Purpose |
|---|---|---|
| BM25 only | None | Minimum baseline |
| Embedding cosine | None | Semantic retrieval baseline |
| Zero-shot MiniLM cross-encoder | None | Tests whether fine-tuning is necessary |
| Frozen DistilBERT encoder + small head | Head only | Lower overfitting risk |
| Fine-tuned MiniLM | Full/partial | Smaller trainable reranker |
| Fine-tuned DistilBERT | Full | Current approach after data repair |

Select the simplest system that meets the client success criteria.

### 4.7 `backend/training/evaluate.py`

#### Findings

- Uses the incorrect score transformation.
- Uses random rather than production candidates.
- Calls Hit@3 `precision_at_3`.
- Does not report BM25 candidate recall.
- Does not test threshold refusal behavior.
- Does not evaluate the LLM answer.
- Uses only 17 test questions.
- Reports no category breakdown or uncertainty.

#### Required evaluation layers

1. **Ingestion:** fact coverage, chunk integrity, privacy classification.
2. **Candidate retrieval:** Recall@k and zero-candidate rate.
3. **Reranking:** MRR, Hit@1, Hit@3, nDCG where multiple positives exist.
4. **Answerability:** precision, recall, F1, false-refusal rate, unsafe-answer rate.
5. **Generation:** factual correctness, evidence support, completeness, citation correctness.
6. **System:** latency, peak memory, cold start, failure recovery, concurrent sessions.
7. **User evaluation:** task completion and feedback against written success criteria.

### 4.8 `backend/reranker/inference.py`

#### Findings

- Duplicates scoring logic rather than sharing it with evaluation.
- Missing files produce `SystemExit` instead of a recoverable service error.
- All candidates are processed in one batch without a configured maximum.
- No model or tokenizer version validation exists.

#### Recommendation

Create a shared scorer module used by training evaluation and production. Return typed errors such as `RerankerUnavailable` and allow a BM25 fallback.

### 4.9 `backend/generation/answer.py`

#### Findings

- Ollama calls have no explicit bounded timeout or exception mapping.
- Groq context may contain private data before the output filter runs.
- Generation settings are not fully specified for Ollama.
- The LLM receives three chunks despite the overview claiming one.
- Returned answers do not expose supporting chunk IDs.
- The system trusts prompt grounding without an entailment check.
- Refusal is recognized only if output exactly equals one string.
- There is no deterministic fallback when generation is unavailable.

#### Recommended response schema

```json
{
  "status": "answered",
  "answer": "James's highest Apex Legends rank is Diamond 2.",
  "confidence": 0.87,
  "sources": [
    {
      "chunk_id": "apex_rank.rank.001",
      "title": "Apex Legends rank",
      "evidence": "James's highest rank ... Diamond 2 ..."
    }
  ],
  "pipeline": {
    "retrieval_ms": 3,
    "rerank_ms": 41,
    "generation_ms": 812,
    "fallback_used": false
  }
}
```

Use distinct statuses for `answered`, `refused`, `unavailable`, and `error`.

### 4.10 `backend/generation/conversation.py`

#### Findings

- Almost every normal question beginning with a question word is classified as a follow-up.
- Only the latest turn influences rewriting.
- Capitalized-word extraction is a fragile topic detector.
- The component is not connected to any application entry point.
- History is stored only in process memory and has no session separation.
- There are no tests for correction, topic switching, or pronoun resolution.

#### Recommendation

Implement one of two honest designs:

1. **Simple design:** no multi-turn claim; every query is independent.
2. **Conversation design:** session-scoped history, explicit query rewriting, bounded summary, topic-switch detection, and test cases.

For a small personal fact bot, the simple design may provide a better and more reliable first release.

### 4.11 `backend/cli.py`, `main.py`, and React application

#### Findings

- CLI exits when the reranker is absent.
- No conversation state is used.
- `main.py` is disconnected from the current Vite/React structure.
- No FastAPI request/response models exist for chat.
- No endpoint health reporting exists.
- No frontend chat interface exists.

#### Recommendation

Treat product integration as a core IA deliverable, not an optional deployment step. The client should be able to use and evaluate the actual solution through the website.

## 5. Knowledge-base review

### `achievements.md`

**Issue:** Claims such as awards and publication are valuable chatbot content but lack source and verification metadata. The Coursera fact also appears elsewhere.

**Severity:** Major

**Recommendation:** Store evidence URL/document, date achieved, date verified, canonical fact ID, and whether the claim is intended for public display.

### `apex_rank.md`

**Issue:** This is a good atomic fact but may become outdated and has no source metadata.

**Severity:** Minor

**Recommendation:** Add season, verification date, and source. Keep it as one atomic chunk.

### `bio.md`

**Issue:** Mixes safe public biography with family details, location, age, and emotionally sensitive content.

**Severity:** Critical

**Recommendation:** Split into publication classes. Replace dynamic age with date-independent wording or derive it from a consented date only when appropriate.

### `contact.md`

**Issue:** Contains public email, Bilibili UID, display identity, and partial birthday. This conflicts with the impression that regex privacy tests protect all personal data.

**Severity:** Critical

**Recommendation:** Define which contact fields are intentionally public. Remove birthday unless it is necessary for a documented user requirement.

### `education.md`

**Issue:** Contains school, grade, boarding information, named associates, and time-dependent status.

**Severity:** Major

**Recommendation:** Apply data minimization, verification dates, expiry dates, and third-party consent rules.

### `favorites.md`

**Issue:** Favorite facts are dynamic and multiple unrelated headings become one chunk. Japanese and Chinese names are not supported by the current tokenizer.

**Severity:** Major

**Recommendation:** Store one favorite category per fact group and add multilingual aliases/transliterations.

### `gaming.md`

**Issue:** Objective facts, personal opinions, long quotations, and technical game knowledge are mixed together.

**Severity:** Major

**Recommendation:** Label fact type and use aliases for CS:GO/CS2, Apex terms, and multilingual game titles.

### `hobbies.md`

**Issue:** Uses relative dates and includes names of collaborators.

**Severity:** Major

**Recommendation:** Replace relative time with a fixed date or approximate start year. Remove unnecessary third-party names or document consent.

### `personality.md`

**Issue:** Contains fears, bullying, academic distress, applications, and other sensitive personal information. These are not ordinary public portfolio facts.

**Severity:** Critical

**Recommendation:** Exclude sensitive sections from the public index unless there is a strong, explicit requirement and informed consent.

### `projects_skills.md`

**Issue:** Contains dynamic GitHub counts and claims about complex projects without per-claim evidence.

**Severity:** Major

**Recommendation:** Link repository or artifact evidence and avoid volatile statistics unless automatically refreshed and dated.

### `sports.md`

**Issue:** Contains useful detailed facts but overlaps with site-derived chunks, potentially producing multiple near-duplicate candidates.

**Severity:** Minor

**Recommendation:** Identify a canonical source or intentionally support multiple positives during training and evaluation.

### `travel.md`

**Issue:** Contains detailed historical travel and family-location information, along with a spelling error (`Toscany`).

**Severity:** Major

**Recommendation:** Generalize sensitive location information, correct the typo, and classify each travel fact separately.

### `writing.md`

**Issue:** Dense sections combine title, methodology, models, dataset, and findings. Terminology is inconsistent (`Pikon` versus `Phikon`).

**Severity:** Major

**Recommendation:** Normalize names and create one structured record per written work with title, summary, methods, results, publication status, and evidence.

## 6. Architecture alternatives

The current architecture should be treated as one experimental candidate, not the assumed correct solution.

### Alternative A: Structured facts plus templates

**Pipeline:** normalized question/intent -> structured fact lookup -> deterministic response

**Advantages:**

- best privacy control;
- deterministic answers;
- no hallucination;
- very low latency and memory;
- easy to test.

**Disadvantages:**

- limited language flexibility;
- more manual schema design;
- weaker support for broad narrative questions.

### Alternative B: BM25 plus LLM

**Pipeline:** BM25 -> top chunks -> grounded generation

**Advantages:**

- retains custom algorithmic depth;
- much simpler than the current system;
- no reranker training data required.

**Disadvantages:**

- lexical mismatch remains;
- top result quality may be insufficient.

### Alternative C: Embeddings plus cosine similarity

**Advantages:**

- handles paraphrases and vocabulary mismatch;
- simple for a 106-chunk corpus;
- all embeddings can remain in memory.

**Disadvantages:**

- less interpretable than custom BM25;
- model dependency;
- can miss exact names and identifiers.

### Alternative D: Hybrid BM25 plus zero-shot cross-encoder

**Advantages:**

- strong semantic reranking without project-specific fine-tuning;
- provides a fair test of whether training adds value.

**Disadvantages:**

- additional latency and model memory;
- candidate recall is still limited by BM25 unless hybrid retrieval is added.

### Alternative E: Current fine-tuned three-stage system

**Advantages:**

- greatest opportunity for ML experimentation;
- can learn project-specific phrasing after the dataset is repaired.

**Disadvantages:**

- highest complexity;
- greatest overfitting and maintenance risk;
- hardest to evaluate correctly;
- currently unsupported by sufficient clean data.

### Selection rule

Choose the simplest architecture that satisfies written client success criteria. If the fine-tuned reranker improves end-to-end answer accuracy by only a negligible amount while increasing latency and failure risk, it should not be selected merely because it appears more advanced.

## 7. Model choice for an 8GB Mac mini

Qwen 2.5 3B is a reasonable candidate, particularly because the KB contains Chinese and Japanese names and terms. A 4-bit 3B model should generally fit within an 8GB unified-memory system, but the complete process also includes macOS, Ollama, the Python runtime, PyTorch, DistilBERT, and KV cache. Suitability must therefore be measured rather than assumed.

| Model | Approximate design trade-off |
|---|---|
| Qwen 2.5 3B | Strong multilingual fit; reasonable size; current default. |
| Phi-3 Mini 3.8B | Strong compact reasoning baseline; heavier and primarily attractive for English-heavy tasks. |
| Llama 3.2 3B | Broad ecosystem; Chinese is not one of its officially supported primary languages. |
| Gemma 2 2B | Smaller and likely faster; may provide weaker answer quality and instruction adherence. |

### Required hardware measurements

- cold model load time;
- time to first token;
- tokens per second;
- peak unified-memory use;
- total response latency;
- latency with reranker loaded simultaneously;
- behavior under two concurrent requests;
- answer correctness and refusal behavior;
- energy or CPU/GPU usage if practical.

## 8. Confidence and refusal redesign

The current system treats the top reranker probability as answerability. These are different concepts:

- **Ranking confidence:** Is candidate A more relevant than candidates B–J?
- **Answerability:** Does any available chunk actually contain enough information to answer?
- **Generation grounding:** Is the generated answer supported by the selected evidence?

A top candidate can win the ranking while still being irrelevant. A system should therefore not use ranking confidence alone as proof of answerability.

### Suggested decision design

```text
if no retrieval candidate:
    refuse
elif retrieval evidence fails answerability rule:
    refuse
elif reranker confidence/margin is below calibrated threshold:
    refuse or return cautious sourced result
else:
    generate from evidence
    validate output support
    return answer and sources
```

### Threshold selection

Build a validation corpus containing:

- answerable in-scope questions;
- unanswerable questions about James;
- questions about other people;
- sensitive/private requests;
- ambiguous questions;
- misspellings and aliases;
- multilingual questions;
- adversarial instructions;
- follow-up questions and topic switches.

Then select a threshold based on an explicit cost, for example:

- unsafe or unsupported answers cost 5;
- false refusals cost 1;
- correct answers and correct refusals cost 0.

Report the actual refusal rate. A threshold of 0.40 does not mean 40% of questions will be refused.

## 9. Test strategy

### Unit tests

- Unicode and multilingual tokenization;
- aliases and punctuation variants;
- BM25 equation against hand-calculated examples;
- index-dataset version mismatch;
- Markdown section parsing;
- stable structural IDs;
- softmax relevance scoring;
- threshold boundary behavior;
- refusal normalization;
- PII normalization and classification;
- conversation topic switching.

### Integration tests

- BM25 result -> reranker -> answer decision;
- missing reranker fallback;
- Ollama unavailable fallback;
- Ollama model missing;
- Groq missing API key;
- timeout and malformed model response;
- cloud backend context privacy filtering;
- session history isolation;
- source evidence returned to frontend.

### End-to-end quality groups

At minimum, create separate frozen groups for:

1. identity and biography;
2. education;
3. sports;
4. gaming and favorites;
5. projects and skills;
6. writing and research;
7. travel and photography;
8. out-of-scope questions;
9. privacy probes;
10. adversarial prompts;
11. multilingual queries;
12. multi-turn conversations.

Do not allow generated paraphrases of the same fact to cross training and test groups.

### Generation evaluation rubric

Each answer can be scored manually on:

| Dimension | Score 0 | Score 1 | Score 2 |
|---|---|---|---|
| Correctness | Incorrect | Partially correct | Fully correct |
| Grounding | Unsupported | Partially supported | Fully supported |
| Completeness | Misses key fact | Partially complete | Complete and concise |
| Privacy | Discloses restricted data | Unclear | Policy-compliant |
| Refusal | Wrong decision | Cautious/ambiguous | Correct answer/refusal |

Use at least two reviewers for a subset if possible and document disagreement resolution.

## 10. IB Computer Science IA positioning

For first assessment in 2027, the project should emphasize computational thinking applied to a real-world problem. The strongest IA narrative is not “I used three AI models.” It is:

1. A real user has difficulty finding and presenting accurate information about James through a large portfolio.
2. The problem is decomposed into content ingestion, retrieval, ranking, answerability, generation, privacy, and interface design.
3. Multiple algorithms and architectures are considered.
4. A custom BM25 index demonstrates algorithmic implementation.
5. Tests reveal lexical mismatch and candidate-recall limitations.
6. Alternative retrieval/reranking designs are compared quantitatively.
7. The selected solution is justified against measurable client criteria.
8. The finished product is evaluated with the client and improved based on evidence.

### Potential success criteria

These must ultimately be agreed with the actual client, but suitable measurable examples include:

- At least 90% of verified in-scope questions retrieve a relevant chunk within the candidate set.
- At least 85% of verified in-scope questions produce a fully correct and grounded answer.
- At least 95% of unanswerable questions are refused.
- No restricted facts are returned in the privacy test suite.
- Median warm response latency is below a client-agreed value on the target Mac mini.
- The interface clearly shows when an answer is unavailable rather than presenting a crash.
- The user can see the source used for an answer.
- Separate users do not share conversation state.

### Current weakest IA evidence

The weakest area is evaluation connected to a finished product. At present there is no integrated chatbot, no saved reranker result, no valid confidence calibration, and no realistic end-to-end test. Improving these areas will contribute more to the IA than adding a fourth model or more advanced generation prompt.

### Authorship and documentation

Because AI coding tools are being used, James should preserve evidence of personal authorship and understanding:

- retain a development log;
- document which code was suggested by AI and how it was checked or changed;
- be able to explain the BM25 equation, inverted index, data split, loss function, reranker scoring, and evaluation metrics;
- record rejected alternatives and reasons;
- ensure the final submission follows the school's current IB academic-integrity guidance.

## 11. Prioritized implementation roadmap

### Phase 0: Freeze and document the baseline

**Priority:** Immediate

- Save the current test output.
- Add a dataset and index version.
- Create a script that reproduces current BM25 diagnostic metrics.
- Record that no trained reranker or evaluation result is currently present.

**Exit condition:** The old system can be reproduced and compared fairly after changes.

### Phase 1: Repair the knowledge and QA data

**Priority:** Immediate; blocks model training

- Define public/restricted/third-party/temporary fact policy.
- Remove restricted facts from the public KB.
- Parse Markdown by headings.
- Introduce stable fact and chunk IDs.
- Manually audit all 119 QA pairs.
- Add exact answer evidence and multiple positives.
- Group paraphrases and shared facts.
- Regenerate chunks and datasets.

**Exit condition:** Every positive label is human-verified and contains evidence for the answer.

### Phase 2: Establish retrieval baselines

**Priority:** High

- Repair Unicode tokenization and aliases.
- Evaluate BM25 across several `k`, `k1`, and `b` values.
- Test embeddings and optional hybrid retrieval.
- Freeze a realistic test suite.

**Exit condition:** Candidate recall meets the agreed target or limitations are explicitly documented.

### Phase 3: Rebuild reranker experiments

**Priority:** High

- Use BM25 hard negatives.
- Correct scoring.
- Compare zero-shot MiniLM, smaller/frozen models, and DistilBERT fine-tuning.
- Use grouped splits and multiple seeds.
- Save metrics and training histories.

**Exit condition:** The selected reranker demonstrates a meaningful end-to-end improvement over the simpler baseline.

### Phase 4: Redesign refusal and grounding

**Priority:** High

- Build answerable/unanswerable validation groups.
- Calibrate threshold after scoring correction.
- Add evidence/source output.
- Add grounding and refusal tests.
- Add deterministic extractive fallback.

**Exit condition:** False-refusal and unsupported-answer rates meet client criteria.

### Phase 5: Integrate the website product

**Priority:** High

- Add FastAPI chat and health endpoints.
- Add React chatbot UI.
- Handle unavailable/refused/error states.
- Implement session-scoped conversation or remove the unsupported multi-turn claim.
- Add end-to-end tests.

**Exit condition:** A client can complete the intended workflow through the website.

### Phase 6: Hardware and user evaluation

**Priority:** Medium

- Benchmark Qwen and at least two alternatives on the actual Mac mini.
- Measure latency and memory.
- Conduct client testing against success criteria.
- Record feedback and implement justified changes.

**Exit condition:** Final architecture and model choices are supported by evidence rather than assumption.

### Phase 7: IA documentation

**Priority:** Continuous and final

- Maintain design decisions and iteration log.
- Include pseudocode and diagrams for custom algorithms.
- Explain failures and improvements honestly.
- Connect every evaluation result to a success criterion.
- Demonstrate the complete solution in the final video.

## 12. Suggested issue backlog for Trae/GLM-5.2

Each task should be implemented and reviewed separately. Do not combine all changes into one unreviewable rewrite.

| ID | Task | Priority | Depends on |
|---|---|---:|---|
| DATA-001 | Create QA audit/report script with answer evidence | P0 | None |
| DATA-002 | Add stable fact IDs and structural chunk IDs | P0 | DATA-001 design |
| DATA-003 | Parse Markdown headings and retain metadata | P0 | DATA-002 |
| PRIV-001 | Define and enforce publication classifications | P0 | None |
| ML-001 | Create shared correct relevance scorer | P0 | None |
| EVAL-001 | Evaluate BM25 candidate recall on frozen groups | P0 | DATA-001 |
| EVAL-002 | Replace random test candidates with BM25 candidates | P0 | EVAL-001 |
| RET-001 | Implement Unicode tokenizer and alias normalization | P1 | EVAL-001 baseline |
| TRAIN-001 | Mine hard negatives and prevent false negatives | P1 | DATA-001, RET-001 |
| TRAIN-002 | Add grouped reproducible splitting | P1 | DATA-001 |
| EVAL-003 | Add end-to-end pipeline evaluation | P1 | EVAL-002, ML-001 |
| SAFE-001 | Add pre-retrieval/pre-cloud privacy enforcement | P1 | PRIV-001 |
| GEN-001 | Add Ollama error handling and extractive fallback | P1 | None |
| API-001 | Add typed chat and health endpoints | P1 | GEN-001 |
| UI-001 | Add accessible chatbot interface | P1 | API-001 |
| CONV-001 | Decide and implement or remove multi-turn behavior | P2 | API-001 |
| BENCH-001 | Benchmark local model alternatives on 8GB Mac | P2 | EVAL-003 |
| IA-001 | Map results and client feedback to success criteria | P1 | Continuous |

## 13. Instructions for AI coding collaborators

When using this document with Trae/GLM-5.2 or another coding agent:

1. Ask it to address one issue ID at a time.
2. Require it to inspect the current file before editing.
3. Require tests for every behavioral change.
4. Do not allow it to regenerate QA labels without human review.
5. Do not accept claims of improved accuracy without a frozen comparison set.
6. Preserve unrelated user changes in the repository.
7. Require a short decision record explaining the chosen alternative.
8. Re-run the full test suite after each logical phase.
9. Keep data migrations separate from model-training changes.
10. Treat privacy classification changes as requiring explicit human approval.

Example task prompt:

```text
Implement ML-001 from docs/DETAILED_RAG_CRITICAL_REVIEW.md.

Before editing, inspect backend/reranker/inference.py and
backend/training/evaluate.py. Create one shared function for converting
two-class logits into ranking scores and calibrated-probability inputs.
Use the class-1 minus class-0 margin for ranking and softmax class-1
probability for displayed confidence. Add unit tests that would fail under
the previous sigmoid(logit_1) implementation. Do not change the configured
confidence threshold in this task because calibration is separate.
```

## 14. Final recommendation

The project should continue, but it should temporarily stop presenting the fine-tuned reranker or 0.40 threshold as validated. The strongest next version is not necessarily the version with the most stages. It is the version whose data is correct, whose evaluation matches production, whose privacy boundary is explicit, whose failure behavior is safe, and whose design decisions can be explained and defended.

The custom BM25 implementation should probably remain because it contributes clear algorithmic depth. The DistilBERT reranker should remain only if repaired experiments show a meaningful improvement over BM25, embeddings, or a zero-shot compact cross-encoder. Qwen 2.5 3B is a reasonable local generation candidate, especially for multilingual content, but it should be selected through measurements on the actual 8GB Mac mini.

Most importantly for the IA, the final report should show how testing exposed weaknesses and caused the design to evolve. That evidence of computational thinking is more persuasive than claiming that a complicated pipeline worked on its first attempt.
