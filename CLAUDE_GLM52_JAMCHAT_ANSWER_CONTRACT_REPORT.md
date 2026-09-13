# JamChat Answer-Contract & Multilingual Quality Audit

**Evaluator:** GLM-5.2 (Claude Code)
**System under test:** JamChat — FastAPI backend, deterministic query planner, BM25 retrieval (178 public chunks), structured-answer templates, qwen2.5:3b via Ollama, neural reranker disabled. No live web search for profile answers. All evaluation performed against the real visitor API at `http://127.0.0.1:8000/api/chat`.
**Commit audited:** `d4dd2cf` "Improve JamChat answer quality and follow-ups" (HEAD at audit time).

---

## 1. Executive verdict (answer-contract preservation)

**JamChat does not reliably preserve the contract of a visitor's question.** When two questions concern the same topic but ask for different details, the chatbot frequently substitutes a nearby fact, broadens or narrows the scope, drops a bound entity, or loses the requested operator. Of 120 evaluated responses, **26 failed (22%) and 20 were weak (17%)** — 39% did not reach "excellent." The defects are not random model noise; they are systematic, deterministic, and reproducible (every weak/failed answer reproduced identically across repeats).

The strongest contract failures, each reproduced against the live runtime:

- **Operator lost to a topical keyword.** "How does James's **FFT guitar tuner** work?" → returns the electric-guitar hobby summary ("Yes - James plays electric guitar. He started in 2025…"). The word "guitar" hijacks routing; the documented FFT mechanism (Web Audio API, real-time FFT, autocorrelation, HPS — present in two chunks) is never surfaced. *(3/3 identical.)*
- **Entity binding dropped.** "What did James film in **Greece**?" → returns **all three** videos (Greece, Japan Winter, Japan Vlog). "What camera did James use to film in **Xinjiang**?" → returns the generic camera inventory (and adds a DJI Action 4 that the Xinjiang chunk does **not** mention). The destination modifier is discarded.
- **Temporal operator inverted/substituted.** "When did James start **skiing**?" → "Self-learned SolidWorks (CAD software) during middle school. Started 3D modeling in 6th grade." (skiing→CAD). "What did James do **before** learning Python?" → the full 9-project list. "What did James do **after** starting electric guitar?" → the guitar summary. The before/after relations are lost.
- **Scope (singular/plural/quantity) not preserved.** "What is James's favorite **game**?" (singular) and "What are James's favorite **games**?" (plural) return byte-identical answers. "Name **one** competitive game" returns the full competitive **and** non-competitive list. "What **model camera** does James use?" returns the **LLM model** answer ("qwen2.5:3b").
- **Exact Unicode value withheld.** "What is the exact name of the Qiu competition?" → refused, even though the chunk title **is** `丘成桐中学科学奖 (Qiu Competition)` and the same name is printed verbatim in the answer to "What awards has he participated in?". The grounding check ignores CJK characters.
- **Pure-Chinese questions refused.** Six of nine pure-Chinese questions ("where photographed", "what camera", "research projects", "when start guitar", "HL subjects", "Qiu name") return `no_retrieval`, while their English equivalents answer correctly.

What **does** work well: well-formed topic-explicit questions, misspellings/noise (`fav game!!!`, `camera???`, `apex rank pls`), the `before <year>` quantifier ("sports before 2020" ✓), "which sport first" ✓, false-premise refusals (Harvard, DSLR-before-Z8, Olympic medal, "publish FFT paper"→corrected to LLM), participation-not-rewritten-as-winning, multi-turn session isolation (no cross-topic contamination), and full determinism (0 non-deterministic repeats).

**Verdict:** The deterministic interpretation layer is the right architecture and is close to excellent on canonical phrasing, but it preserves operator/scope/entity/language/certainty state only **sometimes**. A visitor who varies wording from the canonical form — the exact situation this audit targets — gets a wrong or refused answer about one time in three. None of these failures require a different model or retraining; all are fixable by preserving contract state in the planner, formatters, tokenizer, and grounding check.

---

## 2. Runtime freshness and environment status

| Check | Result |
|---|---|
| `git status -sb` | `main...origin/main`, clean (only untracked audit/report files) |
| HEAD | `d4dd2cf` Improve JamChat answer quality and follow-ups |
| `/api/health?deep=true` | `status:ok`, `reranker_enabled:false`, `bm25_loaded:true`, `retrieval_method:bm25`, `llm_model:qwen2.5:3b`, `query_planner_enabled:true`, `llm_ready:true`, `chunks_loaded:178`, **uptime_seconds:3956.9 (~66 min)** |
| `/api/tags` (Ollama) | `qwen2.5:3b` present (also `qwen3:8b`, unused by the server) |

The runtime is **not stale**: uptime ~66 min means the server reflects the current checkout. Health values match the intended runtime exactly (FastAPI, deterministic planning, BM25, structured answers, qwen2.5:3b, reranker disabled, no web search). **No restart was needed or performed.** All results below are against current code; no historical defect is reported without reproduction.

---

## 3. Method, exact test counts, and scoring rubric

**Method:** Black-box. Each question sent as `POST /api/chat` with `{"question":Q,"session_id":S}`. Single-turn questions (groups 1–7) each used a fresh unique `session_id` (no prior state). Group 9 repeatability used 3 fresh sessions per question; session isolation used two 2-turn sessions. Throttled to ~48 req/min (under the 60/min limit) with 429 backoff; no 429s occurred. Complete JSON (status, answer, normalized_query, confidence, retrieval_score, reason, sources with titles/chunk IDs) was recorded for all 120 responses.

**Exact counts:**
- Group 1 (operator & scope): 31 questions (11 operator + 12 singular/plural/quantifier + 8 temporal)
- Group 2 (entity & role binding): 11
- Group 3 (why/how evidence): 9
- Group 4 (exact values & Unicode): 10
- Group 5 (Chinese / mixed / Unicode): 13
- Group 6 (negation & false premises): 10
- Group 7 (minimal & noisy): 11
- Group 9 (repeatability): 7 questions × 3 = 21
- Group 9 (session isolation): 2 sessions × 2 turns = 4
- **Total: 120 evaluated responses** (95 unique single-turn questions + 21 repeats + 4 isolation turns)

**Scoring rubric (0–2 each, max 14):** Operator · Entity binding · Scope · Factuality · Calibration · Presentation · Evidence. Classification: 13–14 excellent, 10–12 acceptable, 7–9 weak, 0–6 failed. A true fact still fails if it answers a different question. Ground truth: `data/profile_facts.json`, `data/chunks.json` (179 chunks, 178 public — Flappy Bird hidden), `kb_extra/`, and the structured-answer code. No fact was inferred as plausible.

**Aggregate result (120 responses):**

| Class | Count | % |
|---|---|---|
| Excellent (13–14) | 70 | 58% |
| Acceptable (10–12) | 4 | 3% |
| Weak (7–9) | 20 | 17% |
| Failed (0–6) | 26 | 22% |

Distinct failed questions: 20 unique (6 more are repeats that re-confirm 2 of them). Distinct weak: 14 unique (6 repeats re-confirm 2). The failure rate on **non-canonical phrasing** (the audit's focus) is far higher than the headline: within groups 1c (temporal), 2 (entity), 5 (CJK), and 6 (negation), the majority of questions failed or were weak.

---

## 4. Operator/scope results (Groups 1a–1c)

**Operator preservation — mostly strong, with two severe inversions:**
- `what/which/where/when/why/how/who` are correctly interpreted for canonical topics (camera, lenses, photographed-places, guitar-start, gaming-why, guitar-how, favorite-artist, sport-first) — all excellent.
- **`what model` → wrong operator entirely.** "What **model camera** does James use?" → `product_meta` answer "This chat currently uses qwen2.5:3b through Ollama…" The product-meta regex `\b(?:what|which)\s+(?:is\s+the\s+)?(?:ai\s+)?model\b` ([policies.py:60](backend/generation/policies.py#L60)) matches the substring "what model". The camera question becomes a chatbot-self question. Severe.
- **`how many` → no quantity.** "How many sports does James play?" → the full 5-sport list, no count. The quantity operator is dropped ([structured_answers.py:204-227](backend/generation/structured_answers.py#L204) `_format_sports` has no count path).
- **`why` stripped by canonicalization.** "Why is Japan his favorite place?" → normalized to "What is James's favorite place?" → restates "Japan, especially Tokyo." The `why` operator is discarded ([query_plan.py:215](backend/generation/query_plan.py#L215) favorite-place canonical fires regardless of `why`); no reason is given (and none is documented, so the correct behavior is to qualify, not assert).

**Singular/plural & quantifier scope — not preserved:**

| Singular question | Plural question | Both return | Issue |
|---|---|---|---|
| "What is James's favorite **game**?" | "What are James's favorite **games**?" | identical full list | singular=plural |
| "What is his favorite **band**?" | "What are his favorite **bands**?" | "Yorushika, Hitorie" | singular=plural |
| "What is his favorite **camera**?" | "What **cameras** does he use?" | 3-camera inventory | singular "favorite"→inventory |
| "Which **of his projects involves** AI?" | "Which **projects involve** AI?" | 3 AI projects | singular=plural |

- "Name **one** competitive game James likes." → full competitive **and** non-competitive list. The quantifier `one` and the qualifier `competitive` are both lost.
- "Name **all** of James's competitive favorites." → **refused** (`model_refusal`). The competitive-games fact is answerable but unreachable through this wording.

Root cause for the qualifier loss: intent is re-detected on the **canonical** form ([query_plan.py:316-317](backend/generation/query_plan.py#L316) `intent = detect_intent(normalized)`), so a qualifier present only in the raw question ("competitive"/"competitively") never reaches the formatter. `_format_games` ([structured_answers.py:111-123](backend/generation/structured_answers.py#L111)) checks the `competitive` entity, but that entity isn't set on the canonical "What are James's favorite games?". Singular/plural is never inspected by any formatter.

**Temporal operators — partially handled, two severe failures:**

| Question | Result | Verdict |
|---|---|---|
| "When did James start **ice hockey**?" | "started in 2015 and plays as a defender" | ✅ (special-cased) |
| "**Which sport** did James start first?" | "skiing first, in 2013" | ✅ |
| "What sports did he start **before 2020**?" | skiing/hockey/tennis | ✅ (`before <year>` works) |
| "What **season** did James reach Diamond 2?" | "Season 22" | ✅ |
| "When is James expected to graduate?" | "2027" | ✅ |
| "When did James start **skiing**?" | "Self-learned SolidWorks… 3D modeling in 6th grade" | ❌ **skiing→CAD** |
| "What did James do **before** learning Python?" | full 9-project list | ❌ `before` lost |
| "What did James do **after** starting electric guitar?" | guitar hobby summary | ❌ `after` lost |

The skiing failure is the worst: only ice hockey has a sport-specific branch ([structured_answers.py:345-348](backend/generation/structured_answers.py#L345)); for any other sport, "start" query-expands to `started/learned/middle/school` ([tokenizer.py:118](backend/retrieval/tokenizer.py#L118)) which retrieves the self-taught CAD/programming chunk, and `format_entity_answer` returns that body because `topic=sports ∈ {sports,travel,education}` ([structured_answers.py:458-459](backend/generation/structured_answers.py#L458)). The `before`/`after` relation questions have no route at all and fall through to the nearest topic's summary.

---

## 5. Entity and role-binding results (Group 2)

| Question | Returned | Expected binding | Verdict |
|---|---|---|---|
| "What did James photograph in **Italy**?" | Tuscany sunset detail | Italy→Tuscany | ✅ |
| "What lens does he use for photography?" | both NIKKOR lenses | lens | ✅ |
| "What instrument does he play, and what genres…?" | guitar summary + genres (compound) | instrument+genres | ✅ |
| "What games does he play **competitively**?" | full list (incl. non-competitive) | competitive-only | ❌ qualifier lost |
| "What did he publish about **large language models**?" | "LLM paper in Curieux" | LLM publication | ✅ |
| "Which **essay uses Apex Legends**?" | Math IA Markov detail | apex_essay | ✅ |
| "Where did he train through **ice hockey**?" | United States, Russia | hockey training | ✅ |
| "What camera did James use to film in **Xinjiang**?" | generic 3-camera inventory | Nikon Z8 + iPhone 13 Pro (per Xinjiang chunk) | ❌ destination lost, DJI Action 4 added |
| "What did James film in **Greece**?" | all 3 videos | Greece video only | ❌ Greece modifier lost |
| "What did he build for the **medical recovery platform**?" | clarification prompt | Flutter medical platform detail | ❌ misrouted |
| "**Who inspired** his interest in computer science?" | hobbies list | "a classmate" (chunk exists) | ❌ wrong topic |

Three distinct binding defects:

1. **Destination entity overridden by topic.** "What camera did James use to film in Xinjiang?" → canonical "What camera gear does James use?" ([query_plan.py:251-254](backend/generation/query_plan.py#L251) fires for `camera`+`use`, ignoring `Xinjiang`); the photography camera formatter then returns the inventory. The Xinjiang chunk explicitly says "Nikon Z8 and iPhone 13 Pro" — the correct, **narrower** answer — but it is never consulted. (Reproduced 3/3.)
2. **Videos formatter ignores the destination.** "What did James film in Greece?" → canonical "What videos has James made?" ([query_plan.py:120-124](backend/generation/query_plan.py#L120)), and the videos branch collects **every** `category=="video"` chunk ([structured_answers.py:372-399](backend/generation/structured_answers.py#L372)). The Greece entity is never used to filter. (The destination gate at [query_plan.py:178-184](backend/generation/query_plan.py#L178) explicitly excludes `film` questions, so Greece routing is bypassed.)
3. **"interest" hijacks topic precedence.** "Who inspired his interest in computer science?" → `interest` matches the hobbies topic pattern `\b(?:hobbies|hobby|interests?|…)\b` ([intent.py:32](backend/generation/intent.py#L32)) before education; the dedicated chunk `education_person_who_sparked_cs_interest_010` ("A classmate helped James discover his interest in computer science…") is never retrieved. The `who inspired` operator and the `computer science` entity are both lost.

---

## 6. Why/how evidence-strength results (Group 3)

Every answered why/how response was checked claim-by-claim against the supporting source. **No fabricated mechanism was emitted** — the grounding layer and structured templates prevented hallucination. The failures are mis-routing and under-answer, not invention:

| Question | Returned | Documented? | Verdict |
|---|---|---|---|
| "Why does James enjoy gaming?" | relax/decompress + friends/peers | yes (gaming_reasons) | ✅ grounded |
| "Why is gaming important to James?" | same | yes | ✅ |
| "How did James learn to code?" | Python, middle school, self-taught | yes | ✅ |
| "How did James learn electric guitar?" | self-taught, online tutorials | yes | ✅ |
| "How does anime influence his visual style?" | Japanese visual aesthetics | yes (canned, grounded) | ✅ |
| "Why does James value self-learning?" | personality_summary | grounded (mentions self-learner) | acceptable |
| "How does James's **FFT guitar tuner** work?" | guitar hobby summary | **mechanism IS documented** (FFT/HPS/autocorrelation) | ❌ wrong topic |
| "How does his **medical recovery platform** work?" | refused (grounding_failed) | features ARE documented (portals, AI assistant) | weak (safe refusal, but documented features withheld) |
| "Why is Japan his favorite place?" | restates "Japan, Tokyo" | no reason documented | weak (should qualify "why not documented") |

The FFT-tuner failure is the headline: two chunks document the mechanism — `writing_ib_physics_ia_007` ("FFT guitar tuner… relationship between string gauge, tension, and fundamental frequency") and `projects_skills_tuneapp_fft_guitar_tuner_006` ("Web Audio API, real-time FFT analysis, autocorrelation, and Harmonic Product Spectrum (HPS) for pitch detection"). The question routes instead to the guitar hobby because "guitar" sets the `instrument` entity ([intent.py:155](backend/generation/intent.py#L155)) and the Electric-guitar structured summary fires ([structured_answers.py:509-511](backend/generation/structured_answers.py#L509)). The `how does … work` operator and the `FFT tuner` entity are discarded.

---

## 7. Exact-value and Unicode preservation results (Group 4)

Exact-value handling is strong **except where a value sits behind a generation path**:

| Question | Returned | Expected | Verdict |
|---|---|---|---|
| favorite song | "君の神様になりたい" by こはならむ | exact | ✅ |
| who sings favorite song | こはならむ (song_artist, ≠ favorite artist DECO*27) | exact | ✅ |
| favorite artist | DECO*27 | exact | ✅ |
| favorite bands | Yorushika, Hitorie | exact | ✅ |
| camera lenses | NIKKOR 24-120mm F4 S + NIKKOR 85mm F1.8 | exact specs, slash/decimal ok | ✅ |
| Apex rank and season | Diamond 2, Season 22 | exact | ✅ |
| awards/competitions participated | list with "Participation in the 丘成桐中学科学奖 (Qiu Competition)" | participation, not winning | ✅ excellent calibration |
| names of videos | Greece / Japan Winter / Japan Vlog | exact | ✅ |
| **exact name of the Qiu competition** | **refused** (grounding_failed, 3/3) | 丘成桐中学科学奖 (Qiu Competition) | ❌ value withheld |
| **title of his Uniswap project** | full 9-project list | "Uniswap V3 research experiment" | ❌ scope lost |

Two defects:
- **Qiu exact name refused.** The chunk `achievements_qiu_competition_participation_004` has title `丘成桐中学科学奖 (Qiu Competition)`. Asked directly, the bot refuses. Root cause is the grounding check (see §11): `check_grounding` ([formatting.py:42-62](backend/generation/formatting.py#L42)) extracts tokens with `[a-z]{4,}` ([formatting.py:48-55](backend/generation/formatting.py#L48)) — **CJK characters are invisible to it** — and requires `overlap/len(answer_words) ≥ 0.55`. A correct answer "丘成桐中学科学奖 (Qiu Competition)" has only two ASCII overlaps (`qiu`, `competition`) out of four ASCII words (0.50 < 0.55), so it is rejected as ungrounded. There is also no structured/canonical route to the Qiu-specific chunk.
- **"Title of his Uniswap project" → full list.** `Uniswap`+`project` → Projects & Skills summary → `_format_projects` returns the numbered list ([structured_answers.py:230-239](backend/generation/structured_answers.py#L230)); the Uniswap-specific chunk title ("Uniswap V3 EE experiment") is not extracted. Singular/title scope lost.

No exact value was **corrupted** when delivered (Unicode, slashes, decimals, rank labels all preserved). The failures are withholding and scope, not mangling.

---

## 8. Chinese and mixed-language results (Group 5)

| Question | Result | English equivalent | Verdict |
|---|---|---|---|
| James最喜欢什么游戏？ | games list ✅ | works | ✅ |
| James有哪些爱好？ | hobbies ✅ | works | ✅ |
| James会弹什么乐器？ | guitar summary ✅ | works | ✅ |
| James喜欢什么音乐？ | **song only** | English "music"→song+artist+bands | ❌ narrower |
| 他什么时候开始弹吉他？ | **refused** (no_retrieval) | "When did he start guitar?"→2025 | ❌ |
| James在哪里拍过照？ | **refused** | "Where photographed?"→3 places | ❌ |
| James的相机是什么？ | **refused** | "What camera?"→inventory | ❌ |
| James的HL科目是什么？ | **refused** | "HL subjects?"→CS/Math/Physics | ❌ |
| James参加过哪些研究项目？ | **refused** | "What research?"→works | ❌ |
| 丘成桐中学科学奖是什么？ | **refused** | (name is in KB) | ❌ |
| favorite game是什么? | **refused** (model_refusal) | "fav game!!!"→works | ❌ |
| James 的 hobbies 是什么? | hobbies ✅ | works | ✅ |
| what are James 的 favorite bands? | bands ✅ | works | ✅ |

Three distinct CJK defects:

1. **Only 4 CJK routing patterns exist** ([query_plan.py:190-197](backend/generation/query_plan.py#L190)): games, hobbies, instrument, and music→**songs**. Six common topics (where-photographed, camera, research, when-start-guitar, HL, Qiu) have no CJK route. The tokenizer ([tokenizer.py:5](backend/retrieval/tokenizer.py#L5) `_TOKEN_SPLIT = [^\w]+`) keeps each CJK run as a **single token**, which matches no English chunk, so BM25 returns nothing → `no_retrieval`. Pure-Chinese coverage is ~30%.
2. **CJK adjacency breaks `\b` word boundaries.** `\w` includes CJK, so "的**HL**科" and "favorite **game**是" have no word boundary around the English token. `\bhl\b` ([intent.py:188](backend/generation/intent.py#L188)) fails on "James的HL科目", and `\bgame\b` ([query_plan.py:211](backend/generation/query_plan.py#L211), [:266](backend/generation/query_plan.py#L266)) fails on "favorite game是什么" (no space before the CJK). Mixed-language input **without spaces** between English and CJK silently drops out of routing. (Mixed input **with spaces** — "James 的 hobbies 是什么?" — works fine.)
3. **CJK music route is narrower than English.** "James喜欢什么音乐？" (music) → canonical "What songs does James like?" ([query_plan.py:192](backend/generation/query_plan.py#L192)) → song-only, omitting the artist and bands that the English "What music does James like?" returns. The same fact answers differently depending on language.

Response language: the bot answers CJK questions in English, which is acceptable (the product intentionally answers in English). The failures are semantic, not language-coherence.

---

## 9. Negation/presupposition results (Group 6)

| Question | Result | Correct handling | Verdict |
|---|---|---|---|
| "Does James **not** play an instrument?" | "Yes - James plays electric guitar…" | affirm he plays | ✅ (acceptable; affirms) |
| "Has James **ever** played ice hockey?" | "started 2015, defender" | affirm | ✅ |
| "Did James **stop** playing guitar?" | "Yes - James plays electric guitar…" | "no, he still plays" | ❌ "Yes -" misleads |
| "Is Apex Legends **not one of his games**?" | **refused** (grounding_failed) | "Apex IS one of his games" | ❌ negation→refusal |
| "Is his favorite game **definitely** Apex?" | full list | address certainty | weak |
| "Did James **win** the Qiu competition?" | **refused** | "participated, not won" | weak (safe but misses documented participation) |
| "Did James **publish a paper about the FFT tuner**?" | "published LLM paper in Curieux" | correct premise to LLM | ✅ excellent |
| "Was his camera **before the Nikon Z8 a DSLR**?" | refused (unsupported) | refuse (no DSLR documented) | ✅ correct |
| "James **studied at Harvard**, right?" | refused (model_refusal) | refute; "studies at YK Pao" | ✅ (safe refusal) |
| "I heard James **hates winter** — is that true?" | "dislikes summer…" | correct to summer | ✅ excellent |

The system **does not affirm false premises** — a real strength (Harvard, DSLR, Olympic medal, FFT-publication all correctly refused or corrected; participation is not rewritten as winning). The defects are on **negation/cessation**:

- "Did James stop playing guitar?" → the instrument entity fires the guitar summary whose leading "Yes -" reads as affirming he stopped. No negation/cessation handling exists in the formatter; the yes/no framing is ignored.
- "Is Apex Legends not one of his games?" → refused. The games canonical ([query_plan.py:266-271](backend/generation/query_plan.py#L266)) requires a positive verb (`play/like/favorite/enjoy`); "not one of his games" has none, so no structured answer fires, retrieval returns the Apex-expertise chunk (not the Favorite-games summary), and generation fails grounding. The bot cannot **affirm against a negation**.
- "Did James win the Qiu?" → refused, even though "participation" is documented and shown in §7's awards answer. Safe, but it neither surfaces participation nor explicitly corrects "win". The `win`+`qiu` combination has no route to the achievements "participation" fact.

---

## 10. Minimal/noisy-input results (Group 7)

Robustness to casing, punctuation, contractions, and short forms is **excellent**:

| Input | Result | Verdict |
|---|---|---|
| `CAMERA` / `camera???` | camera inventory | ✅ |
| `fav game!!!` | full games list | ✅ ("fav" uncorrected but "game" keyword suffices) |
| `what's his lens` | both NIKKOR lenses | ✅ (contraction) |
| `what're James's hobbies` | hobbies list | ✅ |
| `james' music?` | song+artist+bands (full) | ✅ (apostrophe, broad music) |
| `James's favorite artist?` | DECO*27 | ✅ |
| `apex rank pls` | Diamond 2, Season 22 | ✅ |
| `guitar year?` | guitar summary incl. 2025 | ✅ |
| `where photos?` | 3 photographed locations | ✅ |
| `what did he build??` | **clarification** prompt | ❌ misrouted |

Only one defect: "what did he build??" → `clarification` (`ambiguous_followup`). Root: "build" (lemma) is **not** in the projects topic pattern (`built` only, [intent.py:41](backend/generation/intent.py#L41)), so `topic=None`; and "what did he **build**" matches the followup fullmatch `(?:what|…)\s+(?:did|…)\s+(?:he|she|they|it)\b.*` ([intent.py:139-145](backend/generation/intent.py#L139)), setting `followup=True`. With `kind=unknown` + `followup`, [answer.py:288](backend/generation/answer.py#L288) returns the clarification. A standalone, self-contained question is treated as an ambiguous follow-up. The same mechanism breaks "What did he build for the medical recovery platform?" (Group 2).

---

## 11. Evidence-to-claim audit (Group 8)

25+ answered responses were mapped claim→source. Findings:

- **Almost no final answer comes from free-form generation.** Of the answered responses, ~all are `reason=structured_fact` or `compound` (deterministic). The LLM only ran on questions that were ultimately **refused** (and those refusals were caught). This means hallucination risk is low *by construction* — the deterministic layer handles answering, and the model is gated behind grounding.
- **Structured answers are grounded in `profile_facts.json`, not always in the displayed source chunk.** The displayed source is the top BM25 chunk (a topic pointer). Verified examples: the camera answer is sourced to `Photography and videography` (which does contain the camera+lens facts ✓); the music answer to `Favorite music` (contains song/artist/bands ✓); apex rank to `apex_rank` (verbatim ✓); achievements to `Achievements & Awards` (verbatim, "participation" ✓). In these cases the source card genuinely supports the claim.
- **Source cards are topically relevant but not always the literal provenance.** E.g., "What music does James like?" is sourced to `Favorite music` — supportive — but the claim text is assembled from `profile_facts.json`. This is acceptable (profile_facts is the source of truth) but the source→claim link is sometimes **loose**: a broad summary chunk is shown for a specific entity question.
- **No duplicate source titles** were observed in single-topic answers (the `_select_context_chunks` dedup and `seen_titles` logic work).
- **Refusals carry no sources** ([answer.py:364](backend/generation/answer.py#L364) `sources=[]` when `status!="answered"`) — the prior source-on-refusal defect is fixed. ✅
- **Confidence is the raw BM25 top score, not a probability.** Confidence values like 0.329–0.813 are `retrieval_score`s (e.g., 4.9, 16.4, 38.8). They are not surfaced to the visitor as probabilities in the answer text, but internally `reason=structured_fact` answers do not gate on confidence (only generation does). Low-confidence structured answers (e.g., CJK instrument at 0.329) still answer correctly; very low retrieval (`< CONFIDENCE_THRESHOLD`) yields `low_retrieval_confidence` refusal. This is reasonable, but the numeric confidence is a BM25 score, not calibration.
- **One evidence defect: the grounding check is ASCII-blind.** `check_grounding` ([formatting.py:42-62](backend/generation/formatting.py#L42)) tokenizes with `[a-z]{4,}` ([formatting.py:48-55](backend/generation/formatting.py#L48)), so CJK claim tokens (丘成桐中学科学奖, 君の神様, こはならむ) are invisible. This caused the Qiu-name refusal (§7) and is a latent risk for any answer whose substance is non-ASCII.

| Sample claim | Source shown | Fully supported? |
|---|---|---|
| camera = Nikon Z8 + DJI Action 4 + iPhone 13 Pro | Photography and videography | yes (chunk states this) |
| lenses = NIKKOR 24-120mm F4 S + NIKKOR 85mm F1.8 | Photography and videography | yes |
| song = 君の神様になりたい by こはならむ | Favorite music | yes |
| Apex = Diamond 2, Season 22 | apex_rank | yes (verbatim) |
| "Participation in 丘成桐中学科学奖 (Qiu Competition)" | Achievements & Awards | yes (verbatim, "participation") |
| "James started playing ice hockey in 2015…defender" | Ice Hockey / Ice hockey / description | yes |
| FFT tuner = guitar hobby summary | Electric guitar | **no — wrong claim for the question** |

---

## 12. Repeatability and session-isolation results (Group 9)

**Repeatability (7 questions × 3 fresh sessions):** All 7 questions returned **byte-identical** answers across all 3 runs. Determinism is perfect (0 non-deterministic variations). However, 3 of the 7 are **stably wrong**:

| Question | Run 1/2/3 | Verdict |
|---|---|---|
| "What is James's favorite game?" | identical (full list) | consistent (singular-scope issue, stable) |
| "What music does James like?" | identical (full music) | ✅ stable+correct |
| "How does James's FFT guitar tuner work?" | identical (guitar summary) | ❌ stable+wrong |
| "What camera did he use in Xinjiang?" | identical (generic inventory) | ❌ stable+wrong (entity lost) |
| "What is the exact name of the Qiu competition?" | identical (refused) | ❌ stable+wrong (value withheld) |
| "James有哪些爱好？" | identical (hobbies) | ✅ stable+correct |
| "What does James believe in?" | identical (personality_summary) | ✅ stable+correct |

**Session isolation (2 sessions × 2 turns):** Clean — **no cross-topic contamination**.
- Session A: "favorite food?" → ramen; then "What about his lenses?" → lenses (correctly switched to lenses, **not** contaminated by food).
- Session B: "What camera does James use?" → inventory; then "What about his food?" → ramen (correctly switched to food, **not** contaminated by camera).

The `_EXPLICIT_TOPIC_TOKENS` short-circuit ([conversation.py:235](backend/generation/conversation.py#L235)) correctly prevents follow-up contamination when the follow-up names its own topic ("lenses", "food"). Session state is properly scoped per `session_id`.

---

## 13. Complete failure table

Severity: 🔴 severe (wrong/refused answer to an answerable, reasonable question) · 🟠 moderate (scope/operator miss, still partly useful). Score /14. Layer abbreviations: QP=query-plan, INT=intent, FMT=structured formatter, TOK=tokenizer, BM25=retrieval, GND=grounding, POL=policy, CONV=conversation.

| # | Question | Answer (abbreviated) | Expected contract | Score | Sev | Likely cause (layer · file:line) | Regression test |
|---|---|---|---|---|---|---|---|
| 3 | What **model camera** does James use? | "qwen2.5:3b through Ollama…" (LLM model) | camera model (Nikon Z8) | 2 | 🔴 | POL · policies.py:60 `\bwhat\s+model\b` over-matches | assert "Nikon" in ask("What model camera does James use?") |
| 11 | **How many** sports does James play? | 5-sport list, no count | "5 sports" | 9 | 🟠 | FMT · structured_answers.py:204 no count path | assert "5" in ask("How many sports does James play?") |
| 12 | What is his favorite **game**? (sing.) | full list | one/favorite | 9 | 🟠 | FMT · _format_games no singular | (scope) |
| 14 | Name **one competitive** game | full comp+non-comp list | one competitive game | 6 | 🔴 | QP · qualifier lost on canonical (query_plan.py:316) + FMT | assert "Apex" in ask("Name one competitive game James likes.") and answer is short |
| 15 | Name **all** competitive favorites | refused | 3 competitive games | 4 | 🔴 | QP/INT · "competitive favorites" not routed to games | assert "Valorant" in ask("Name all of James's competitive favorites.") |
| 16 | favorite **band** (sing.) | both bands | one/favorite | 9 | 🟠 | FMT · _format_music band branch | (scope) |
| 18 | favorite **camera** (sing.) | 3-camera inventory | primary Nikon Z8 | 9 | 🟠 | FMT · camera formatter ignores "favorite" | (scope) |
| 20 | Which **of his projects involves** AI? (sing.) | 3 AI projects | one | 9 | 🟠 | FMT · _format_projects no singular | (scope) |
| 24 | When did James start **skiing**? | "SolidWorks…3D modeling in 6th grade" | "skiing, 2013" | 2 | 🔴 | BM25+TOK+FMT · only hockey special-cased (structured_answers.py:345); "start"→"middle school" expansion retrieves CAD chunk; entity body returned (structured_answers.py:458) | assert "2013" in ask("When did James start skiing?") |
| 30 | What did James do **before** learning Python? | full 9-project list | what preceded Python (or "not documented") | 5 | 🔴 | QP · no before/after route; substitutes projects summary | assert "before" handled: ask(...) status in {answered(refused ok),…} not full project dump |
| 31 | What did James do **after** starting guitar? | guitar hobby summary | what followed (or qualify) | 5 | 🔴 | QP+FMT · "after" lost; instrument summary fires | assert answer does not equal guitar summary verbatim |
| 32 | camera to film in **Xinjiang** | generic inventory (+DJI Action 4) | "Nikon Z8 and iPhone 13 Pro" | 7 | 🔴 | QP · camera canonical overrides destination (query_plan.py:251) | assert "Xinjiang" relevant and "DJI Action 4" not asserted for Xinjiang |
| 33 | film in **Greece** | all 3 videos | Greece video only | 8 | 🔴 | QP+FMT · videos canonical (query_plan.py:120) + formatter lists all (structured_answers.py:372); destination gate excludes film (query_plan.py:178) | assert "Greece" and not "Hokkaido" in ask("What did James film in Greece?") |
| 37 | games **competitively** | full comp+non-comp list | competitive-only | 8 | 🟠 | QP · "competitively" lost on canonical | assert "Cyberpunk" not in ask("What games does he play competitively?") |
| 40 | build for **medical recovery platform** | clarification prompt | Flutter medical platform detail | 4 | 🔴 | INT · "build" not "built" (intent.py:41) + "what did he" over-fires followup (intent.py:139); answer.py:288 | assert "Flutter" in ask("What did he build for the medical recovery platform?") |
| 42 | **Who inspired** his CS interest | hobbies list | "a classmate" (chunk exists) | 2 | 🔴 | INT · "interest"→hobbies precedence (intent.py:32) | assert "classmate" in ask("Who inspired his interest in computer science?").lower() |
| 47 | How does **FFT guitar tuner** work? | guitar hobby summary | FFT/HPS mechanism (documented) | 2 | 🔴 | INT+FMT · "guitar"→instrument entity (intent.py:155) → guitar summary (structured_answers.py:509) | assert "FFT" in ask("How does James's FFT guitar tuner work?") |
| 59 | **exact name** of Qiu competition | refused (grounding_failed) | 丘成桐中学科学奖 (Qiu Competition) | 4 | 🔴 | GND · check_grounding ASCII-blind (formatting.py:48) + no Qiu canonical | assert "丘成桐中学科学奖" in ask("What is the exact name of the Qiu competition?") |
| 60 | **title** of his Uniswap project | full 9-project list | "Uniswap V3 research experiment" | 6 | 🔴 | FMT · _format_projects full list (structured_answers.py:239) | assert "Uniswap" in ask("What is the title of his Uniswap project?") and answer short |
| 65 | James喜欢什么音乐？ | song only | song+artist+bands (per English) | 8 | 🟠 | QP · CJK music→songs (query_plan.py:192) | assert "DECO*27" in ask("James喜欢什么音乐？") |
| 66 | 他什么时候开始弹吉他？ | refused (no_retrieval) | "2025" | 4 | 🔴 | TOK+QP · no CJK route; CJK single-token (tokenizer.py:5) | assert "2025" in ask("他什么时候开始弹吉他？") |
| 67 | James在哪里拍过照？ | refused | 3 locations | 4 | 🔴 | TOK+QP · no CJK route | assert "Hokkaido" in ask("James在哪里拍过照？") |
| 68 | James的相机是什么？ | refused | camera inventory | 4 | 🔴 | TOK+QP · no CJK route | assert "Nikon" in ask("James的相机是什么？") |
| 69 | James的HL科目是什么？ | refused | HL subjects | 4 | 🔴 | INT · `\bhl\b` fails on CJK adjacency (intent.py:188) | assert "Computer Science" in ask("James的HL科目是什么？") |
| 70 | James参加过哪些研究项目？ | refused | research projects | 4 | 🔴 | TOK+QP · no CJK route | assert "hallucination" in ask("James参加过哪些研究项目？").lower() |
| 71 | 丘成桐中学科学奖是什么？ | refused | the Qiu competition | 4 | 🔴 | TOK+GND · CJK single-token + ASCII grounding | assert "丘成桐中学科学奖" in ask("丘成桐中学科学奖是什么？") |
| 72 | favorite game是什么? | refused | games list | 4 | 🔴 | QP · `\bgame\b` fails on CJK adjacency (query_plan.py:266) | assert "Apex" in ask("favorite game是什么?") |
| 77 | Did James **stop** playing guitar? | "Yes - James plays electric guitar…" | "no, he still plays" | 7 | 🟠 | FMT · no cessation handling; "Yes -" misleads | assert "stop" addressed; answer not misleading "Yes" |
| 78 | Is Apex Legends **not** one of his games? | refused | "Apex IS one of his games" | 5 | 🔴 | QP · games canonical needs positive verb (query_plan.py:266); negation→refusal | assert "Apex" in ask("Is Apex Legends not one of his games?") |
| 79 | Is his favorite game **definitely** Apex? | full list | address certainty | 8 | 🟠 | QP · certainty operator lost | (scope) |
| 80 | Did James **win** the Qiu? | refused | "participated, not won" | 7 | 🟠 | QP · win+qiu not routed to participation fact | assert "participat" in ask("Did James win the Qiu competition?").lower() |
| 92 | what did he build?? | clarification | projects list | 5 | 🔴 | INT · "build" not topic + "what did he" followup (intent.py:139); answer.py:288 | assert status=="answered" for ask("what did he build??") |

(Weak-only items #11, #12, #16, #18, #20, #37, #49, #65, #77, #79, #80 are scope/operator misses — factually grounded but not matching the requested contract. The 6 repeat-failures at #102-104, #108-110 re-confirm #47 and #59.)

**Existing tests would not catch these** because they target canonical phrasing and `status=="answered"`/fact presence, not contract fidelity (singular vs plural, entity binding to a specific destination, operator preservation, CJK segmentation, or grounding on CJK). Each regression test above asserts the **contract**, not just a fact.

---

## 14. Top five improvements (by visitor impact and uncertainty)

1. **Generalize "When did James start `<sport>`?" beyond ice hockey; fix the skiing→CAD retrieval collision.** Add a per-sport start-year path in `_format_sports` (the `started` data already exists in `profile_facts.json`) and stop the `start`→`middle school` query expansion from retrieving the CAD/programming chunk for sport questions. *High impact (#24 is a glaring wrong answer; affects any non-hockey sport), low uncertainty.* Regression: `assert "2013" in ask("When did James start skiing?")`.

2. **Route "How does James's FFT guitar tuner work?" to the Physics-IA / Tune-app chunks.** De-prioritize the `instrument` entity when `FFT`/`tuner`/`tune-app`/`how does … work` is present, and add a canonical that selects the FFT/Physics-IA chunks. *High impact (#47, reproduced 3/3; the mechanism is fully documented), low uncertainty.* Regression: `assert "FFT" in ask("How does James's FFT guitar tuner work?")`.

3. **Preserve singular/plural/quantity and qualifier scope through canonicalization.** (a) Detect qualifiers on the **raw** question (or carry them through the canonical), so "competitive"/"competitively" reach `_format_games`. (b) Add singular/quantity handling: "favorite game/band/camera/project" → primary/single; "Name one" → one item; "How many" → a count. (c) Extract a single project's title for "title of his Uniswap project" instead of the full list. *High breadth (affects #12, #14, #16, #18, #20, #37, #60, #11), medium uncertainty (need a policy for singular when no #1 is ranked — prefer "primary"/list-with-caveat).* Regression: `assert "Cyberpunk" not in ask("What games does he play competitively?")`.

4. **Fix CJK: add segmentation/expansion for pure-Chinese queries, fix `\b` boundaries for mixed input, and widen the CJK music route.** (a) Segment CJK runs (or add CJK routes for where-photographed, camera, research, when-start-guitar, HL, Qiu) so pure-Chinese questions reach the same structured answers as English. (b) Replace `\b…\b` English-token matching with boundary logic that survives CJK adjacency, or insert spacing around CJK before matching (fixes #69 HL, #72 favorite-game). (c) Map CJK "音乐" to the broad music canonical (not song-only). *High impact (6+ refusals + 2 silent mis-routes), medium uncertainty (CJK segmentation approach choice).* Regression: `assert "Nikon" in ask("James的相机是什么？")` and `assert "Computer Science" in ask("James的HL科目是什么？")`.

5. **Fix the grounding check to handle CJK tokens and add a structured/canonical path for exact Unicode values.** Extend `check_grounding` tokenization to include CJK character runs (not just `[a-z]{4,}`), and relax/adjust the 0.55 ratio for answers whose substance is non-ASCII. Add a canonical for "exact name of the Qiu competition" that returns the chunk title `丘成桐中学科学奖 (Qiu Competition)` directly (structured, bypassing generation). *High impact (#59, #71 — a documented exact value is withheld; latent risk for all CJK answers), low uncertainty.* Regression: `assert "丘成桐中学科学奖" in ask("What is the exact name of the Qiu competition?")`.

Also-worth-doing (lower priority): anchor the product-meta `model` regex so "what model camera" does not match ([policies.py:60](backend/generation/policies.py#L60)); recognize lemma "build" as projects and stop "what did he build" over-firing followup ([intent.py:41](backend/generation/intent.py#L41), [:139](backend/generation/intent.py#L139)); honor the destination entity in the videos/camera formatters (#33, #32); add `before`/`after` temporal handling or a calibrated "not documented" (#30, #31); handle negation/cessation/certainty operators (#77, #78, #79).

---

## 15. Conclusion: is another model, retraining, or architecture change justified?

**No.** A different model, retraining, or an architecture change is **not justified** by these findings.

- **The model is barely the answerer.** ~all answered responses are `reason=structured_fact` (deterministic templates from `profile_facts.json`). The LLM (qwen2.5:3b) only ran on questions that were ultimately refused, and those refusals were correctly caught by grounding. The observed wrong answers are **deterministic** — reproduced identically across 3 runs — which by definition means they originate in the deterministic layers (query planner, intent, formatters, tokenizer, grounding), not in model sampling.
- **Every failure is a contract-state preservation failure in the deterministic layer**, with a concrete file:line root cause: operator lost to a greedy regex (policies.py:60), qualifier lost on canonicalization (query_plan.py:316), entity/destination overridden by topic precedence (query_plan.py:120/251, structured_answers.py:372), temporal `before/after` unrouted, sport-start generalized only for hockey (structured_answers.py:345), "build"/"interest" keyword mis-routing (intent.py:32/41), CJK single-tokenization (tokenizer.py:5) plus `\b`-boundary failures (intent.py:188, query_plan.py:266), and an ASCII-blind grounding check (formatting.py:48).
- **No defect requires more model capability.** The FFT mechanism, the CS-inspiration fact, the Xinjiang cameras, and the Qiu exact name are all **already in the knowledge base** — the bot fails to *route to and deliver* them. A larger model would still hit the same routing and grounding logic and would still refuse the Qiu name (grounding is ASCII-blind regardless of model).
- **The architecture (deterministic planner + structured templates + BM25 + gated generation) is sound** — it is exactly what keeps hallucination near zero and makes answers stable. The fix is to make that architecture preserve operator/scope/entity/language/certainty/evidence state more faithfully, not to replace it.

**Recommendation:** implement the five improvements in §14 (all deterministic-layer fixes with regression tests). Re-run this contract audit afterward; the expected outcome is that singular/plural, temporal, entity-bound, and exact-Unicode questions are answered with the requested detail, and pure-Chinese coverage reaches parity with English. Only if, after those fixes, a residual class of failures is shown to stem from model reasoning (not routing/grounding) would a model change be worth evaluating.
