# Evidence-Based Reconstruction of the "Ask James" Data Pipeline

**Project:** Ask James — A RAG-Based Personal Chatbot
**Subject:** IB Computer Science HL Internal Assessment (first assessment 2027)
**Student:** James Sui
**Report date:** 15 July 2026
**Repository root:** `/Users/cheezecats/Desktop/coding-projects/about-me-bot-website/`
**Git history:** 13 commits, 2026-07-10 to 2026-07-14

> This report reconstructs the data pipeline from verifiable evidence in the repository. Where evidence is missing, "UNKNOWN" is stated with an explanation. AI-generated outputs are clearly distinguished from student decisions.

---

## 1. Original Data Sources

### 1.1 Quark Drive — "Personnal Database" folder

| Attribute | Value |
|-----------|-------|
| Location | Quark Cloud Drive (pan.quark.cn), folder "Personnal Database " (with trailing space) |
| Access method | `kuake` CLI v1.5.0 (github.com/zhangjingwei/kuake_cli) + direct Quark API via curl |
| Total items scanned | 8,325 (128 directories, 8,197 files) |
| Total file size | ~2.79 GB |
| File types (top) | .png (7,425), .sol (187), .jpg (82), .pdf (62), .docx (37), .py (32), .pages (28), .ts (25) |
| Files read for extraction | ~45 text-based files (DOCX, TXT, MD, TS, PY, JSON, HTML) |
| Large files skipped (>50 MB) | 7 (all ML datasets — HDF5/parquet) |
| Public/private status | Private — all source files are personal documents stored on a private cloud drive |

**Evidence:** `_extraction_manifest.md` in `hermes_output/`, `docs/hermes-extraction-prompt.md`, session history of Hermes agent.

### 1.2 WorkBuddy extraction — public web sources

| Attribute | Value |
|-----------|-------|
| Source | YouTube (@cheezecats), GitHub (Cheezecats), GitHub Pages (cheezecats.github.io), Bilibili (bili_1614032286) |
| Date of extraction | 2026-07-10 |
| Facts extracted | 63 across 10 categories |
| Output location | `workbuddy_extraction_output/` |
| Public/private status | Public — extracted from publicly accessible web profiles |

**Evidence:** `workbuddy_extraction_output/_extraction_manifest.md` (86 lines, 4,828 B).

### 1.3 Manual knowledge base additions

| Attribute | Value |
|-----------|-------|
| Source | James Sui (hand-written) |
| Files | `kb_extra/*.md` (13 Markdown files) |
| Notable manual additions | `kb_extra/favorites.md` (anime, movies, games, food, music, place, season, book, sports positions, IDE, graduation year), `kb_extra/apex_rank.md` ("Diamond 2, Season 22") |
| Public/private status | Public — curated for the chatbot KB |

**Evidence:** `kb_extra/favorites.md` contains information not found in any Hermes or WorkBuddy extraction output (e.g., favorite anime = "Bang Dream Mygo, Clannad, Jojo's Bizarre Adventure"; favorite music = specific songs and artists; sports positions = "Ice hockey: Defender. Soccer: Offender"). These facts were manually added by James, as Hermes pass 3 explicitly recorded "NO EXPLICIT DATA FOUND" for all of these.

### 1.4 Private KB

| Attribute | Value |
|-----------|-------|
| Intended location | `kb_private/` |
| Actual status | **MISSING** — directory does not exist in the repository |
| Evidence | `docs/IA_DEVELOPMENT_LOG.md` line 224 references `kb_private/`, but `ls` of the repo confirms no such directory exists |

---

## 2. Hermes Agent

### 2.1 Role

Hermes (self-hosted agent on Mac mini, model: deepseek-v4-flash via Volcengine Ark API) performed **mechanical extraction** of candidate facts from the "Personnal Database" folder on Quark Drive. Its role was explicitly defined as: "You are NOT curating, judging importance, or deciding what the knowledge base should contain. You are extracting candidate facts that James will approve, edit, or reject."

**Evidence:** `docs/hermes-extraction-prompt.md` lines 7-13.

### 2.2 Prompts and instructions

Three prompt documents exist in the repository:

| File | Purpose | Date (approx.) |
|------|---------|----------------|
| `docs/hermes-extraction-prompt.md` | Pass 1 — hard fact extraction (11 categories, 11 output files) | 2026-07-10 |
| (Pass 2 prompt) | Subjective & implicit information extraction | 2026-07-10 (delivered in-session, not saved as separate file) |
| `docs/hermes-extraction-prompt-pass3.md` | Pass 3 — targeted depth extraction with anti-hallucination rules | 2026-07-10 |

**Evidence:** `docs/hermes-extraction-prompt.md` (219 lines), `docs/hermes-extraction-prompt-pass3.md`.

### 2.3 Three extraction passes

| Pass | Focus | Output files | New facts | Date |
|------|-------|-------------|-----------|------|
| Pass 1 | Explicit hard facts (bio, education, sports, etc.) | 14 files in `extraction_output/` → `hermes_output/` | 94 | 2026-07-10 |
| Pass 2 | Subjective, implicit, personality-revealing info | `subjective.md` added to `hermes_output/` | 46 (10 tastes, 11 values, 9 emotions/fears, 9 opinions, 7 self-descriptions) | 2026-07-10 |
| Pass 3 | Targeted depth (languages, school, favorites, future, projects, sports, tech, daily life, collaboration, achievements) | 12 files in `extraction_output_pass3/` → `hermes_output/` | 31 new + 6 "NO DATA FOUND" | 2026-07-10 |

**Why multiple passes:** Pass 1 captured explicit hard facts but was too shallow for high-ask-rate details. Pass 2 targeted subjective/personality information. Pass 3 was specifically designed with anti-hallucination rules to avoid guessing — "Evidence or nothing. Every fact MUST come from a specific passage in a specific file."

**Evidence:** `hermes_output/_extraction_manifest.md`, `hermes_output/_pass3_manifest.md`, `hermes_output/subjective.md`.

### 2.4 What Hermes did to the data

- **Extracted:** Facts from DOCX (via Python zipfile + XML parsing), TXT, MD, TS, PY files
- **Downloaded:** Files one at a time to `/tmp/`, read content, then deleted — zero source files persisted locally
- **Classified:** Facts into 11 categories (bio, education, sports, hobbies, gaming, projects, photo/video, writing, travel, achievements, contact)
- **Flagged:** Uncertainties in `UNCERTAIN.md` (14 items) and `pass3_uncertain.md` (8 items)
- **Did NOT:** Curate, decide importance, infer, synthesize, translate, or edit source files

### 2.5 Output files

**Location:** `hermes_output/` in the project repository (27 files total, uploaded to Quark Drive "output" folder on 2026-07-10).

Key files:

| File | Size | Facts |
|------|------|-------|
| `hermes_output/bio.md` | 4,564 B | 15 |
| `hermes_output/education.md` | 3,820 B | 12 |
| `hermes_output/subjective.md` | 16,562 B | 46 |
| `hermes_output/UNCERTAIN.md` | 6,174 B | 14 flagged items |
| `hermes_output/_extraction_manifest.md` | 5,647 B | — |
| `hermes_output/suggested_qa_pairs.md` | 7,023 B | 20 Q&A pairs |
| `hermes_output/pass3_favorites.md` | 2,811 B | 4 (only 2 explicit "favorite" statements) |
| `hermes_output/pass3_uncertain.md` | 3,479 B | 8 flagged items |

### 2.6 Errors, uncertainty, and hallucinations in Hermes output

**Uncertainties flagged (not hallucinations — Hermes was told to flag):**
- Two different email addresses found (suihe0812@gmail.com vs jamessui1222@gmail.com)
- Math IA topic recorded from memory, not from any file
- School name NOT in any file (Hermes memory had "YK Pao School" but no file confirmed it)
- Multiple paper draft versions — unclear which is final
- Interest shift from biology (10th grade email) to engineering/AI (grade 11 essays)
- Bullying experience flagged as sensitive
- Implied traits (hardworking, resilient, curious) never explicitly stated

**Correction found in WorkBuddy output:**
- Bilibili UID initially recorded as 69948145797 (incorrect, returns 404); corrected to 1614032286 ("confirmed by James")

**Evidence:** `hermes_output/UNCERTAIN.md`, `hermes_output/pass3_uncertain.md`, `workbuddy_extraction_output/_extraction_manifest.md`.

---

## 3. Quark Drive

### 3.1 Role

Quark Drive served as the **primary document store** for James's personal files. It was used for:
- **Document access:** Hermes read files from the "Personnal Database" folder via the Quark API
- **Output storage:** Hermes uploaded 27 extraction output files to a new "output" folder inside "Personnal Database"
- **NOT used for:** OCR, search, synchronization, or data transformation

### 3.2 Files that entered Quark Drive

**Input:** The "Personnal Database" folder pre-existed on Quark Drive with 8,197 files across 128 directories (~2.79 GB). Files were NOT added to Quark Drive as part of this project — they were already there as James's personal cloud storage.

**Output:** 27 markdown files uploaded to `Personnal Database/output/` on 2026-07-10:
- 14 pass 1 files (bio.md, education.md, sports.md, etc.)
- 1 pass 2 file (subjective.md)
- 12 pass 3 files (pass3_languages.md, pass3_school.md, etc.)

### 3.3 Data transformation

Quark Drive did **not** transform data. The `kuake` CLI and direct API calls downloaded files as-is. The only transformation was Hermes's extraction of facts from file content into structured markdown.

**Evidence:** Session history shows Hermes used `curl` to download files via Quark API download URLs, read content with Python, then deleted temp files. No Quark-side processing was involved.

---

## 4. Human Verification

### 4.1 What was manually reviewed or corrected

**Evidence of manual curation by James:**

| Item | Evidence |
|------|----------|
| `kb_extra/` files differ from `hermes_output/` files | `kb_extra/bio.md` is a cleaned, paraphrased version of `hermes_output/bio.md` — same facts but rewritten in James's own voice, with `## Fact:` blocks removed |
| `kb_extra/favorites.md` contains facts NOT in any Hermes output | Hermes pass 3 explicitly recorded "NO EXPLICIT DATA FOUND" for favorite anime, movie, book, food, place, season, band, game, subject, athlete. `kb_extra/favorites.md` contains all of these — James manually added them |
| `kb_extra/apex_rank.md` | Hermes could not find Apex rank in any file. James manually wrote: "James's highest rank in Apex Legends is Diamond 2, which he reached in Season 22." |
| `kb_extra/personality.md` | Contains cleaned/curated version of `hermes_output/subjective.md` facts |
| Bilibili UID correction | WorkBuddy manifest notes: "confirmed by James; original UID 69948145797 was incorrect" |

### 4.2 How facts were checked against sources

- **Hermes output:** Every fact has a `**Source:**` field with the exact file path in "Personnal Database"
- **WorkBuddy output:** Every fact has a source URL or platform identifier
- **Manual review:** James read Hermes outputs and either (a) approved facts into `kb_extra/`, (b) rewrote them in his own voice, or (c) rejected them (not present in `kb_extra/`)
- **Privacy test suite:** `tests/test_privacy_kb.py` runs automated regex checks against all chunks to verify no PII leaked through

### 4.3 How uncertain facts were handled

- Uncertain facts went into `UNCERTAIN.md` (14 items) and `pass3_uncertain.md` (8 items)
- James manually resolved some: e.g., school name (added to `kb_extra/education.md` despite not being in source files), graduation year (2027, added to `kb_extra/favorites.md`)
- Some uncertainties remain unresolved in the KB — e.g., email address discrepancy (both emails appear in different contexts)

### 4.4 AI-generated vs student decisions

| Stage | AI (Hermes/WorkBuddy) | Student (James) |
|-------|----------------------|-----------------|
| Fact extraction | Extracted candidate facts from files | Reviewed every fact before approval |
| Categorization | Assigned facts to 11 categories | Could reorganize or merge categories |
| Uncertainty flagging | Flagged 22 uncertain items | Resolved some, left others |
| Favorites | Could NOT find most favorites | Manually wrote `kb_extra/favorites.md` with all favorites |
| Apex rank | Could NOT find in any file | Manually wrote `kb_extra/apex_rank.md` |
| Privacy filtering | Followed exclusion rules mechanically | Manually verified and added whitelist entries in tests |
| KB construction | Produced candidate markdown | Curated, rewrote, and approved final `kb_extra/` files |

---

## 5. Privacy Filtering

### 5.1 How private facts were identified

Privacy filtering operated at **three levels**:

**Level 1 — Extraction-time (Hermes):**
- Hermes was given explicit exclusion rules in `docs/hermes-extraction-prompt.md` (lines 105-120): phone numbers, addresses, full birthdates, passwords, family contacts, financial info, medical info, private photos/EXIF
- Hermes flagged sensitive items in `UNCERTAIN.md` rather than extracting them
- The bullying experience was extracted into `subjective.md` but flagged as sensitive in `UNCERTAIN.md` item #12

**Level 2 — Ingestion-time (automated test):**
- `tests/test_privacy_kb.py` scans every chunk in `data/chunks.json` against `PRIVATE_KB_PATTERNS` (defined in `backend/config.py` lines 109-113)
- Patterns cover: US phone numbers, street addresses, email addresses, Chinese mobile numbers (1[3-9]\d{9}), Chinese national IDs (18 digits), QQ/WeChat identifiers, passwords, full dates (YYYY-MM-DD)
- A whitelist (`_WHITELIST` in `test_privacy_kb.py` lines 17-27) allows known public info: Bilibili UID (1614032286), public email (suihe0812@gmail.com), game names that match address patterns, etc.

**Level 3 — Output-time (runtime):**
- `backend/generation/answer.py` applies `apply_pii_filter()` to every LLM output before returning to the user
- If PII is detected in the generated answer, the entire answer is replaced with the refusal message

### 5.2 Filtering timing

| Stage | When | What |
|-------|------|------|
| Extraction | Before facts enter `hermes_output/` | Hermes excluded private data per prompt rules |
| KB curation | Before facts enter `kb_extra/` | James manually reviewed and approved |
| Chunking | Before chunks enter `data/chunks.json` | `test_privacy_kb.py` validates no PII in chunks |
| Runtime | After LLM generates answer | `apply_pii_filter()` scans output |

### 5.3 Privacy test evidence

```
tests/test_privacy_kb.py (4 tests):
- test_no_private_data_in_kb: scans all chunks against PII patterns
- test_chunks_have_required_fields: validates chunk structure
- test_chunk_ids_unique: no duplicate chunks
- test_chunk_word_limit: every chunk ≤ 60 words
```

**Evidence:** `backend/config.py` lines 101-113, `tests/test_privacy_kb.py`, `docs/IA_DEVELOPMENT_LOG.md` Section 7.3.

### 5.4 Known privacy weaknesses (from critical review)

The `docs/DETAILED_RAG_CRITICAL_REVIEW.md` (dated 2026-07-11) identified privacy issues:
- CR-05: "Sensitive information is already indexed" — school/boarding status, partial birthday, family-location stories, fears, bullying, academic distress, university applications
- PII patterns were initially too narrow (only US-style phone and English-style address)
- This was partially addressed by expanding patterns to include Chinese mobile, national ID, QQ/WeChat

**Evidence:** `docs/DETAILED_RAG_CRITICAL_REVIEW.md` lines 228-265.

---

## 6. Knowledge-Base Construction

### 6.1 Organization into categories

The final public KB consists of **13 Markdown files** in `kb_extra/`:

| File | Category | Source |
|------|----------|--------|
| `bio.md` | Personal bio | Curated from Hermes pass 1 + manual |
| `education.md` | Education | Curated from Hermes pass 1 + manual (school name, graduation year) |
| `sports.md` | Sports | Curated from Hermes pass 1 |
| `gaming.md` | Gaming | Curated from Hermes pass 1 + manual |
| `hobbies.md` | Hobbies & interests | Curated from Hermes pass 1 + manual |
| `projects_skills.md` | Projects & skills | Curated from Hermes pass 1 |
| `photo_video.md` | Photography & video | Curated from Hermes pass 1 |
| `writing.md` | Writing & essays | Curated from Hermes pass 1 |
| `travel.md` | Travel | Curated from Hermes pass 1 |
| `achievements.md` | Achievements | Curated from Hermes pass 1 |
| `contact.md` | Contact & links | Curated from Hermes pass 1 + WorkBuddy |
| `personality.md` | Personality & values | Curated from Hermes pass 2 (subjective.md) |
| `favorites.md` | Favorites | **Entirely manual** — James's own answers |
| `apex_rank.md` | Apex Legends rank | **Entirely manual** — not in any source file |

### 6.2 From markdown to data files

**Pipeline:**
1. `kb_extra/*.md` → `backend/ingest/chunker.py` → `data/chunks.json`
2. `data/chunks.json` + `data/qa_pairs.jsonl` → `backend/training/build_dataset.py` → `data/train.jsonl`, `data/val.jsonl`, `data/test.jsonl`
3. `data/chunks.json` → `backend/retrieval/bm25.py` → `data/bm25_index.json`
4. `data/qa_pairs.jsonl` → manual curation → `data/evaluation_questions.jsonl`, `data/unanswerable_questions.jsonl`

### 6.3 Data file inventory

| File | Size | Contents | Evidence |
|------|------|----------|----------|
| `data/chunks.json` | 86,128 B | 106 chunks (83 from kb_extra, 23 from site content.ts) | `DETAILED_RAG_CRITICAL_REVIEW.md` line 34 |
| `data/qa_pairs.jsonl` | 22,103 B | 203 question-positive_chunk_id pairs | `wc -l` on file |
| `data/evaluation_questions.jsonl` | — | Structured evaluation questions with expected terms | File inspection |
| `data/unanswerable_questions.jsonl` | — | 10 privacy/unanswerable questions (password, phone, address, QQ, bank, WeChat, DOB, parents) | File inspection |
| `data/live_evaluation_questions.jsonl` | — | UNKNOWN — file exists but not yet read | — |
| `data/profile_facts.json` | 5,622 B | Structured JSON of key facts (games, food, music, apex rank, etc.) with `_sources` mapping | File inspection |
| `data/bm25_index.json` | — | Serialized BM25 inverted index | `backend/retrieval/bm25.py` |
| `data/bm25_grid_search.json` | — | BM25 hyperparameter grid search results | `backend/training/bm25_grid_search.py` |

### 6.4 Duplicate/contradictory/outdated fact handling

- **Duplicates:** Hermes was instructed to record once but list all sources. The chunker deduplicates by content hash (`content_hash` field in chunks.json).
- **Contradictions:** Placed in `UNCERTAIN.md` (e.g., two email addresses, interest shift biology→engineering). James resolved some manually.
- **Outdated:** Pass 3 instructed to mark confidence "low" and note "as of" dates. Time-sensitive facts (e.g., "rank as of Season 22") include temporal context.

---

## 7. Processing Algorithms and Scripts

### 7.1 Script inventory

| Script | Lines | Purpose |
|--------|-------|---------|
| `backend/ingest/chunker.py` | 276 | Splits Markdown KB files into ≤60-word chunks with metadata (chunk_id, content_hash, source, category, title, heading_path) |
| `backend/ingest/list_chunks.py` | 23 | Lists all chunk IDs and text (utility) |
| `backend/retrieval/tokenizer.py` | 141 | Tokenizes text: lowercase, stopword removal, alias normalization (e.g., "CS:GO"→"csgo", "IA"→"internal assessment"), CJK character handling |
| `backend/retrieval/bm25.py` | 182 | Okapi BM25 implementation: inverted index, IDF, term-frequency saturation (k1=1.5), document-length normalization (b=0.75), save/load to JSON |
| `backend/reranker/inference.py` | 85 | Reranker inference: supports zeroshot CrossEncoder (cross-encoder/ms-marco-MiniLM-L-6-v2) and finetuned DistilBERT. Auto-selects device (CUDA/MPS/CPU) |
| `backend/reranker/scoring.py` | 15 | `rank_scores()`: softmax over 2-class logits (NOT sigmoid — this was a critical bug fix identified in CR-01) |
| `backend/training/build_dataset.py` | 158 | Builds train/val/test splits from qa_pairs.jsonl. Each positive paired with 4 negative chunks (NEGATIVES_PER_POSITIVE=4). Split: 70% train, 15% val, 15% test |
| `backend/training/train_reranker.py` | 256 | Fine-tunes DistilBERT: 8 epochs, lr=2e-5, batch_size=16, early_stopping_patience=2, max_length=256 tokens |
| `backend/training/evaluate.py` | 122 | Evaluates: bm25_candidate_recall, precision_at_1, hit_at_3, MRR |
| `backend/training/ablation_study.py` | 239 | Ablation: compares BM25-only vs BM25+reranker |
| `backend/training/bm25_grid_search.py` | 113 | Grid search over BM25 k1/b parameters |
| `backend/training/calibrate_threshold.py` | 258 | Confidence threshold calibration with asymmetric cost model (unsafe=5×, false_refusal=1×), dual constraints (false_refusal≤20%, unsafe≤10%) |
| `backend/api.py` | 354 | FastAPI app: /api/chat, /api/health endpoints, rate limiting, CORS, security headers |
| `backend/generation/answer.py` | 303 | LLM generation: grounding system prompt, PII output filter, confidence threshold, Ollama/Groq backends |
| `backend/generation/policies.py` | 198 | Request policies: sensitive request blocking, compound question splitting |
| `backend/generation/intent.py` | 118 | Query intent detection: CJK→English routing, topic classification |
| `backend/generation/query_plan.py` | 204 | Query planning: typo correction (fuzzy matching), query expansion with aliases, normalization |
| `scripts/validate_profile_facts.py` | 65 | Validates profile_facts.json structure and consistency |
| `scripts/evaluate_live_chat.py` | 128 | Live chat evaluation harness |

### 7.2 Key algorithmic details

**Chunking (`chunker.py`):**
- Input: `kb_extra/*.md` + `src/data/content.ts`
- Method: Markdown heading-aware splitting, ≤60 words per chunk
- Output: `data/chunks.json` with `chunk_id`, `text`, `content_hash`, `metadata` (source, category, title, heading_path, section_index)
- No overlap between chunks (identified as a limitation in the critical review)

**Tokenization (`tokenizer.py`):**
- Lowercase, regex `\w+` with `re.UNICODE`
- Stopword removal (custom list, preserves "not")
- Alias normalization: "CS:GO"→"csgo", "IA"→"internal assessment", etc.
- CJK limitation: each CJK character becomes a separate token (no word segmentation)

**BM25 (`bm25.py`):**
- Okapi BM25 from scratch (no library)
- Parameters: k1=1.5, b=0.75 (standard defaults, grid-searched in `bm25_grid_search.py`)
- Inverted index with IDF, term frequency saturation, document-length normalization
- Serializable to JSON for persistence

**Reranker scoring (`scoring.py`):**
- `rank_scores(logits)`: applies `torch.softmax(logits, dim=-1)[:, 1]` (corrected from sigmoid per CR-01)
- `score_logits(logits)`: returns probabilities and logit margins

**Confidence threshold (`calibrate_threshold.py`):**
- Asymmetric cost: unsafe answer = 5× penalty, false refusal = 1× penalty
- Dual constraints: false_refusal_rate ≤ 20%, unsafe_answer_rate ≤ 10%
- Calibration split: 70% calibration, 30% holdout
- Threshold must pass on both sets before deployment

### 7.3 Commands

```bash
# Build chunks from KB
python -m backend.ingest.chunker

# Build BM25 index
python -m backend.retrieval.bm25

# Train reranker (on Windows RTX 4080)
python -m backend.training.train_reranker

# Evaluate
python -m backend.training.evaluate

# Calibrate threshold
python -m backend.training.calibrate_threshold

# Run tests
pytest tests/ -v

# Start API server
python main.py
```

---

## 8. Training Data

### 8.1 Dataset construction

| Split | Questions | Pair rows | Source |
|-------|-----------|-----------|--------|
| Train | 85 | 425 (85 × 5: 1 positive + 4 negatives) | `build_dataset.py` from `qa_pairs.jsonl` |
| Validation | 17 | 85 | Same |
| Test | 17 | 170 (17 × 10: 1 positive + 9 random negatives) | Same |

**Evidence:** `DETAILED_RAG_CRITICAL_REVIEW.md` lines 40-43.

### 8.2 Positive/negative example creation

- **Positives:** Each QA pair in `qa_pairs.jsonl` has a `positive_chunk_id` field pointing to the correct chunk
- **Negatives:** 4 per positive, sampled from BM25 results (`NEGATIVES_PER_POSITIVE = 4` in `config.py`)
- **Critical issue (CR-02):** Multiple QA labels were incorrect — e.g., chunk `13f9ae177c7da771` (containing favorites) was used as positive for questions about ice hockey position, soccer, music, school subject, season, and IDE. This was identified in the critical review but **UNKNOWN** whether all labels were corrected before final training.

### 8.3 AI-labeled data

- QA pairs were initially suggested by Hermes (`hermes_output/suggested_qa_pairs.md`, 20 pairs) and WorkBuddy (`workbuddy_extraction_output/suggested_qa_pairs.md`, 20 pairs)
- James manually expanded these to 203 pairs in `data/qa_pairs.jsonl`
- **UNKNOWN** whether any QA pairs were generated or labeled by AI beyond the initial suggestions

### 8.4 Private data prevention in training

- `tests/test_privacy_kb.py` ensures no PII in chunks (which are the source of training data)
- `data/unanswerable_questions.jsonl` contains 10 privacy questions (password, phone, address, etc.) used to test refusal behavior
- `backend/generation/answer.py` applies PII filter on output

### 8.5 Training environment

| Attribute | Value | Evidence |
|-----------|-------|----------|
| Training computer | Windows PC with NVIDIA RTX 4080 | `docs/WINDOWS_TRAINING_RUNBOOK.md` |
| Deployment computer | Mac mini M4, 8 GB RAM | `docs/MAC_DEPLOYMENT_RUNBOOK.md`, `docs/IA_DEVELOPMENT_LOG.md` |
| Model | DistilBERT (`distilbert-base-uncased`, ~66M params) | `backend/config.py` line 32 |
| Framework | PyTorch + Hugging Face Transformers | `.venv` packages |
| Training params | 8 epochs, lr=2e-5, batch_size=16, early_stopping_patience=2 | `backend/config.py` lines 83-88 |
| Max sequence length | 256 tokens | `backend/reranker/inference.py` line 77 |
| Random seed | 42 | `backend/config.py` line 93 |
| Evaluation metrics | Precision@1, Hit@3, MRR, BM25 candidate recall | `backend/training/evaluate.py` |
| Target precision@1 | 0.70 | `backend/config.py` line 92 |

### 8.6 Trained model status

**The trained model does NOT exist in the repository.** The `models/` directory is missing. The `DETAILED_RAG_CRITICAL_REVIEW.md` confirms: "The repository contains no trained `models/reranker/` artifact" (line 45).

The `docs/MAC_DEPLOYMENT_RUNBOOK.md` line 60 states: "The reranker is intentionally disabled for now."

---

## 9. Final Product Status

### 9.1 Component classification

| Component | Status | Evidence |
|-----------|--------|----------|
| BM25 retrieval (`backend/retrieval/bm25.py`) | **USED in final deployed chatbot** | `config.py`: `RERANKER_ENABLED=false`; `api.py` line 145: `"retrieval_method": "reranker" if reranker_loaded else "bm25"` |
| DistilBERT reranker | **EXPERIMENTAL — NOT enabled in production** | `config.py` line 29: `RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "false")`; `test_reranker_policy.py`: `test_reranker_is_opt_in_by_default`; `models/` directory missing |
| Zero-shot cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) | **EXPERIMENTAL — available as fallback backend** | `config.py` line 30: `RERANKER_BACKEND = "zeroshot_cross_encoder"` (default); `inference.py` supports both |
| Qwen 2.5 3B (Ollama) | **USED in final deployed chatbot** | `config.py` line 49: `LLM_MODEL = "qwen2.5:3b"`; `MAC_DEPLOYMENT_RUNBOOK.md` |
| Groq (llama-3.1-8b-instant) | **DEVELOPMENT ONLY — optional backend** | `config.py` lines 51-52; PII sanitization step in `answer.py` |
| Query planner | **USED in final deployed chatbot** | `config.py` line 42: `QUERY_PLANNER_ENABLED = true` (default) |
| Confidence threshold (0.40) | **DEVELOPMENT ONLY — uncalibrated** | `DETAILED_RAG_CRITICAL_REVIEW.md` CR-01: "The current 0.40 confidence threshold has no valid probabilistic interpretation"; `calibrate_threshold.py` exists but UNKNOWN if run |
| `kb_private/` directory | **REJECTED — does not exist** | `IA_DEVELOPMENT_LOG.md` references it, but directory is missing |
| WorkBuddy extraction | **USED during development** | `workbuddy_extraction_output/` informed `kb_extra/` content |
| Hermes extraction (passes 1-3) | **USED during development** | `hermes_output/` informed `kb_extra/` content |

### 9.2 Is the trained reranker enabled in the final live request path?

**NO.** The reranker is **opt-in and disabled by default** (`RERANKER_ENABLED=false`). The final deployed chatbot uses **BM25-only retrieval**. Evidence:

1. `backend/config.py` line 29: `RERANKER_ENABLED = os.getenv("RERANKER_ENABLED", "false")`
2. `tests/test_reranker_policy.py`: test asserts `RERANKER_ENABLED is False` by default
3. `docs/MAC_DEPLOYMENT_RUNBOOK.md` line 60: "The reranker is intentionally disabled for now"
4. `models/` directory does not exist — no trained model is available
5. `backend/api.py` lines 59-65: reranker only loads if `RERANKER_ENABLED` is true
6. WorkBuddy memory (2026-07-12): "reranker disabled/BM25"
7. WorkBuddy memory (2026-07-13): health endpoint reports `"reranker_enabled": false`

---

## 10. Evidence Table

| Stage | Input files | Tool/script | Student action | AI action | Output files | Verification method | Used in final product? |
|-------|------------|-------------|----------------|-----------|-------------|--------------------|-----------------------|
| Web extraction | YouTube, GitHub, Bilibili profiles | WorkBuddy (AI assistant) | Reviewed outputs | Extracted 63 facts from public profiles | `workbuddy_extraction_output/*.md` | Manual review by James | Yes — informed `kb_extra/` |
| Cloud drive extraction (pass 1) | Personnal Database (8,197 files on Quark) | Hermes agent + kuake CLI | Reviewed outputs | Extracted 94 facts from DOCX/TXT/MD files | `hermes_output/*.md` (14 files) | Manual review + UNCERTAIN.md | Yes — informed `kb_extra/` |
| Subjective extraction (pass 2) | Same 21 files re-read | Hermes agent | Reviewed outputs | Extracted 46 subjective facts | `hermes_output/subjective.md` | Manual review | Yes — informed `kb_extra/personality.md` |
| Depth extraction (pass 3) | Same 21 files re-read | Hermes agent | Reviewed outputs | Extracted 31 facts, flagged 8 gaps | `hermes_output/pass3_*.md` (12 files) | Manual review + pass3_uncertain.md | Yes — confirmed gaps |
| KB curation | hermes_output/ + workbuddy_output/ | Manual (James) | Approved, rewrote, added missing facts | — | `kb_extra/*.md` (13 files) | Manual verification against sources | Yes — primary KB |
| Chunking | `kb_extra/*.md` + `content.ts` | `backend/ingest/chunker.py` | — | — | `data/chunks.json` (106 chunks) | `tests/test_privacy_kb.py`, `test_bm25.py` | Yes |
| QA pair creation | `suggested_qa_pairs.md` + manual | Manual (James) | Wrote 203 QA pairs | Suggested 40 initial pairs | `data/qa_pairs.jsonl` | `tests/test_qa_pairs.py` | Yes |
| BM25 index build | `data/chunks.json` | `backend/retrieval/bm25.py` | — | — | `data/bm25_index.json` | `tests/test_bm25.py` (8 tests) | Yes |
| Dataset building | `qa_pairs.jsonl` + `chunks.json` | `backend/training/build_dataset.py` | — | — | `data/train.jsonl`, `val.jsonl`, `test.jsonl` | — | Development only |
| Reranker training | `data/train.jsonl` | `backend/training/train_reranker.py` | Ran on Windows RTX 4080 | — | `models/reranker/` (MISSING) | `backend/training/evaluate.py` | NO — not deployed |
| Evaluation | `data/test.jsonl` | `backend/training/evaluate.py` | — | — | `data/eval_results.json` (MISSING) | — | Development only |
| Threshold calibration | `data/val.jsonl` + unanswerable set | `backend/training/calibrate_threshold.py` | — | — | UNKNOWN | `tests/test_threshold_calibration.py` | NO |
| Privacy filtering | `data/chunks.json` | `tests/test_privacy_kb.py` | — | — | Pass/fail | Automated regex scan | Yes |
| API serving | `bm25_index.json` + Ollama | `backend/api.py` (FastAPI) | — | — | `/api/chat` responses | `tests/test_api_runtime.py`, `test_answer_policy.py` | Yes |
| Frontend | React + Vite | `src/components/ChatBot.tsx` | — | — | GitHub Pages site | WorkBuddy adversarial tests | Yes |
| Adversarial testing | Live API | WorkBuddy (293 requests) | — | Ran 293 test interactions | `WORKBUDDY_ADVERSARIAL_CHATBOT_REPORT.md` | Automated + manual | Development only |

---

## 11. IA Relevance (2027 IB CS HL Criteria)

### Criterion A: Problem specification
- **Main documentation (2,000 words):** Problem definition (visitors can't ask questions), three dimensions (discovery, grounding, privacy), success criteria table (7 measurable criteria)
- **Appendix:** `docs/IA_DEVELOPMENT_LOG.md` Section 3-4 (full success criteria table with measurement methods)
- **Evidence:** `docs/IA_DEVELOPMENT_LOG.md` lines 38-96

### Criterion B: Planning
- **Main documentation:** Development timeline (5 phases), design decisions log (5 major decisions with rationale)
- **Appendix:** Full design decisions log, `docs/WINDOWS_TRAINING_RUNBOOK.md`, `docs/MAC_DEPLOYMENT_RUNBOOK.md`
- **Evidence:** `docs/IA_DEVELOPMENT_LOG.md` lines 99-298

### Criterion C: System overview
- **Main documentation:** Architecture diagram (BM25 → optional reranker → Qwen 2.5 3B → PII filter), data flow
- **Appendix:** `docs/CHATBOT_ARCHITECTURE.md`, `docs/DETAILED_RAG_CRITICAL_REVIEW.md`
- **Evidence:** `docs/IA_DEVELOPMENT_LOG.md` Section 5, `backend/config.py`

### Criterion D: Development
- **Main documentation:** BM25 implementation rationale, chunker design, tokenizer alias system, reranker training setup, grounding prompt design
- **Appendix:** Source code listings (`backend/retrieval/bm25.py`, `backend/ingest/chunker.py`, `backend/reranker/inference.py`, `backend/generation/answer.py`), test suite evidence
- **Evidence:** `docs/IA_DEVELOPMENT_LOG.md` Section 5.1-5.4, Section 7

### Criterion E: Evaluation
- **Main documentation:** Success criteria results (recall, refusal rate, privacy, latency), limitations, future improvements
- **Appendix:** `WORKBUDDY_CHATBOT_TEST_REPORT.md`, `WORKBUDDY_ADVERSARIAL_CHATBOT_REPORT.md`, `DETAILED_RAG_CRITICAL_REVIEW.md`, `data/eval_results.json` (if it exists)
- **Evidence:** `docs/IA_DEVELOPMENT_LOG.md` Section 7-8, WorkBuddy reports

### What belongs in appendices only
- Hermes/WorkBuddy extraction prompts and outputs (evidence of data pipeline, not core algorithm)
- Full critical review (`DETAILED_RAG_CRITICAL_REVIEW.md`) — evidence of iteration
- WorkBuddy test reports — evidence of testing but not core development
- BM25 grid search and ablation study results — supporting evidence

---

## 12. AI Disclosure

| Tool | Date/period | Purpose | What it generated or changed | How James verified it | Where to acknowledge |
|------|------------|---------|-----------------------------|----------------------|---------------------|
| **Hermes** (self-hosted agent, deepseek-v4-flash via Volcengine Ark) | 2026-07-10 | Data extraction from Quark Drive "Personnal Database" | 27 markdown files with ~170 candidate facts across 3 passes | Manual review of every fact before approval into `kb_extra/` | `docs/citations.md` (not yet created), IA appendix |
| **WorkBuddy** (AI assistant, HY3 role) | 2026-07-10 | Web profile extraction (YouTube, GitHub, Bilibili) | 63 facts in `workbuddy_extraction_output/` | Manual review; Bilibili UID correction | `docs/citations.md`, IA appendix |
| **WorkBuddy** (AI assistant, HY3 role) | 2026-07-12 to 2026-07-13 | Chatbot testing (62 + 293 requests) | 3 test reports: `WORKBUDDY_CHATBOT_TEST_REPORT.md`, `WORKBUDDY_CHATBOT_RETEST_REPORT.md`, `WORKBUDDY_ADVERSARIAL_CHATBOT_REPORT.md` | James read reports; some defects were fixed by developer | IA appendix, testing evidence section |
| **WorkBuddy** (AI assistant, HY3 role) | 2026-07-12 (evening) | Full engineering review | `WORKBUDDY_FULL_REVIEW_REPORT.md` (15 sections) | James read report; identified P2/P3 issues | IA appendix |
| **Trae / GLM-5.2** (AI coding collaborator) | UNKNOWN | Code development assistance | UNKNOWN — referenced in `DETAILED_RAG_CRITICAL_REVIEW.md` line 6 as "Intended readers: James, project supervisor, and AI coding collaborators such as Trae/GLM-5.2" | UNKNOWN | UNKNOWN — needs James's confirmation |
| **Ollama / Qwen 2.5 3B** | 2026-07-12 onwards | LLM generation in production chatbot | Generates answers to user questions from retrieved context | Grounding system prompt + PII filter + WorkBuddy adversarial testing | IA documentation (generation model) |
| **Hugging Face Transformers** | UNKNOWN | Reranker model (DistilBERT) | Pre-trained model used for fine-tuning | Evaluation metrics (if run) | IA documentation (reranker) |

---

## Missing Evidence That James Should Recover

1. **`models/reranker/` directory** — The trained DistilBERT model does not exist in the repo. If training was completed on the Windows RTX 4080, the model artifact needs to be copied back. If training was NOT completed, this should be stated.

2. **`data/eval_results.json`** — Evaluation results file referenced in `evaluate.py` but not present. If evaluation was run, the results need to be saved. If not, this should be stated.

3. **`docs/citations.md`** — Referenced in `docs/hermes-extraction-prompt.md` line 206 ("Cite your assistance in the project's `docs/citations.md`") but does not exist. Must be created for IA submission.

4. **`kb_private/` directory** — Referenced in `docs/IA_DEVELOPMENT_LOG.md` line 224 but does not exist. Either create it with restricted facts or remove the reference.

5. **BM25 recall measurement** — `DETAILED_RAG_CRITICAL_REVIEW.md` reported BM25 candidate recall at 70.6% (line 59), but `IA_DEVELOPMENT_LOG.md` Criterion 1 targets ≥90%. The critical review later noted "shipped BM25 recall_at_10=0.858" (WorkBuddy memory 2026-07-12). Which figure is current? Need to re-run `python -m backend.training.evaluate` and save results.

6. **QA label corrections** — CR-02 identified multiple incorrect positive labels in `qa_pairs.jsonl`. Were these corrected? Need to verify current label quality.

7. **Threshold calibration results** — `calibrate_threshold.py` exists (258 lines) but UNKNOWN if it was run. The 0.40 threshold in `config.py` is uncalibrated per CR-01. Need calibration output or justification for the chosen threshold.

8. **Trae/GLM-5.2 usage details** — Referenced as an "AI coding collaborator" in the critical review but no details on what it did, when, or how it was verified. Need James's statement.

9. **`data/live_evaluation_questions.jsonl`** — **RESOLVED.** Subagent confirmed: 22 live eval questions with `expected_status` (answered/refused) and `terms` fields. Covers both personal facts and chatbot architecture questions. Used for live chat evaluation via `scripts/evaluate_live_chat.py`.

10. **Git remote URL** — `docs/WINDOWS_TRAINING_RUNBOOK.md` references `github.com/Cheezecats/about-me-bot-website.git` but the local repo has no remote configured (`.git` exists but `git remote -v` output not captured). Need to confirm the GitHub repo exists and is the canonical source.

11. **Deployment evidence** — Is the chatbot currently live? The Cloudflare Tunnel setup is documented but no evidence of active deployment (tunnel URL, uptime) was found. Need to confirm deployment status.

12. **`.env` and `.env.local` contents** — These files exist but were not read (to avoid exposing secrets). Need to verify they don't contain hardcoded API keys that would violate IA security guidelines.

---

*End of report. All claims are sourced from files in the repository at `/Users/cheezecats/Desktop/coding-projects/about-me-bot-website/` or from Hermes session history on 2026-07-10. Items marked UNKNOWN require James's confirmation or additional evidence recovery.*
