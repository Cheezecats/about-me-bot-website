# JamChat Answer-Quality Audit

**Evaluator:** Claude Code (GLM-5.2)
**System under test:** JamChat — FastAPI backend, BM25 retrieval (`data/chunks.json`, 178 public chunks), deterministic query planner + structured-answer layer, qwen2.5:3b via Ollama for non-structured generation. Reranker disabled (BM25-only, the documented production path).
**Method:** A fresh server instance running the current code on disk was queried over HTTP at `/api/chat` (the exact visitor path, including in-memory conversation state via `session_id`). 266 single-turn questions + 25 supplementary edge cases + 33 multi-turn conversation turns across 7 conversations + 31 unique suggested questions + 22 stability questions ×3 repeats = **415 evaluated responses**. Every question was scored 0–2 on six dimensions (intent, factual, directness, completeness, formatting, sources; max 12). Root causes were traced through the planner, intent, retrieval, structured-answer, and conversation modules with file:line references.

---

## Executive verdict

**Ordinary visitors cannot yet reliably ask questions in natural language.** JamChat is genuinely strong on a specific register — well-formed, topic-explicit questions that match a curated template ("What camera does James use?", "gaming", "apex rank?") — and answers them with direct, well-sourced, deterministic facts (88% of single-turn questions scored excellent, 0/22 unstable across repeats). Misspellings and grammar errors are corrected robustly.

However, the chatbot fails on a coherent and predictable set of natural-language variations that real visitors use constantly:

- **"Tell me about X" is routed to the bio** for almost any X, so "Tell me about the Extended Essay", "Tell me about the Physics IA", and "Tell me about James's ice hockey" all return *James's biography* instead of the requested topic.
- **"Who is James's favorite singer?" returns the biography** because `who is james` greedily matches inside the question.
- **"how old is james" is refused** even though the "Age: 17" chunk is correctly retrieved — the model then refuses/grounding-fails.
- **False-premise questions are answered confidently** instead of corrected: "Tell me about James's Harvard degree." returns the bio rather than rejecting the premise.
- **Several short questions collapse to nonsense** because there is no stemming and "james" has low IDF: "What is James?", "When did James start coding?", "What has James achieved?" all retrieve the same irrelevant short bio/contact chunks and are refused, while "What does he play?" and "What does he use?" get hallucinated answers ("PC build project and Fortnite", "unlimited money to buy a gaming computer…").
- **Multi-turn memory cascades into wrong answers**: the travel conversation breaks at "What did he photograph there?" (loses Italy, switches to camera-gear), which then corrupts the "And Greece?" follow-up; the gaming conversation re-answers the Apex rank when asked "Why does he enjoy gaming?"; the essays conversation collapses to bio for three consecutive turns.
- **Refusals systematically display irrelevant sources** ("What is 2 plus 2?" shows source *apex_rank*; "capital of France" shows *Extended Essay (EE)*).

A visitor who phrases questions close to canonical forms gets an excellent experience. A visitor who talks the way people actually talk — "tell me about…", "how old is…", pronoun follow-ups, "his HLs?" — hits a wall of refusals, wrong-topic answers, and context loss about **25% of the time** (18 failed + 15 weak of 291 single/supplementary questions; 8 of 33 conversation turns). The pipeline is sophisticated, but several narrow regex and retrieval decisions undercut it on exactly the inputs the audit is designed to catch.

---

## Test summary

| Metric | Count |
|---|---|
| Single-turn questions tested | 266 |
| Supplementary edge-case questions | 25 |
| Multi-turn conversation turns | 33 (7 conversations) |
| Suggested questions tested | 31 unique |
| Stability samples | 22 questions × 3 = 66 runs |
| **Total evaluated responses** | **415** |

**Single-turn + supplementary (291 questions):**

| Classification | Count | % |
|---|---|---|
| Excellent (11–12) | 250 | 86% |
| Acceptable (9–10) | 8 | 3% |
| Weak (6–8) | 15 | 5% |
| Failed (0–5) | 18 | 6% |

**Conversation turns (33):** ~26 excellent/acceptable, 2 weak, 5 failed.

| Failure category | Count |
|---|---|
| Incorrect refusals (should have answered) | 13 clear + 2 mixed-language |
| Hallucinated / nonsensical model answers | 4 |
| Source failures (irrelevant sources shown) | ≥13 (mostly on refusals) |
| Formatting failures | 7+ distinct patterns |
| Multi-turn context-loss failures | 8 turns across 4 conversations |
| Suggested questions that produced a weak answer | 1 (none refused) |

---

## Results by topic

| Topic | Questions | Avg score | Weakest wording category | Main failure type |
|---|---|---|---|---|
| Writing & essays | 11 | **9.00** | formal / casual | `tell me about` → bio cascade; "Which essay involves Apex" → games topic |
| Meta (chatbot itself) | 8 | 10.25 | formal | `chatbot` token not matched by product_meta regex |
| Bio | 12 | 10.50 | keyword | stopword collapse to "james"; "What is James?" refused |
| Projects | 18 | 10.72 | formal | entity path returns single chunk; stemming ("start coding") |
| Achievements | 8 | 10.75 | formal | stemming ("achieved" ≠ "achievements") |
| Music | 13 | 10.92 | formal | "What music does James like?" → song-only; bands-before-artist bug |
| Travel | 22 | 11.18 | indirect | "travelled with camera" → camera gear; cascade in convo |
| Education | 16 | 11.19 | shorthand | "his HLs?" → no retrieval |
| Videos | 5 | 11.20 | formal | "What has James filmed?" → photography topic, 1 video |
| Contact | 11 | 11.36 | indirect | "Where can I see his work?" refused |
| Sports | 16 | 11.38 | casual | "Tell me about James's ice hockey" → bio |
| Personality | 18 | 11.39 | casual | "wanna study later" → education not aspirations |
| Boundary/unsupported | 12 | 11.42 | — | false-premise "Harvard degree" answered, not rejected |
| Photography | 22 | 11.68 | — | bare "photography" → raw extractive text |
| Favorites | 18 | 11.78 | — | "favorites"/"What are James's favorites?" → anime-only |
| Games | 29 | 11.86 | — | conversation T3 context contamination |
| Hobbies | 21 | 12.00 | — | — |
| Food / Season / Preferences | 6 | 12.00 | — | — |

---

## Semantic consistency results

Paraphrases of the same intent were grouped and compared. Most clusters are consistent, but several **diverge on wording alone**:

**Gaming (mostly consistent):** `gaming` / `What games does James play?` / `What games is James into?` / `what games do james like` / `tell me his game preferences` / `James favorite games?` → all return the curated competitive/non-competitive list. ✅ Consistent. `apex rank?` / `What is James's Apex rank?` / `apex legends ank` / `what rank is james in apex` → all "Diamond 2 … Season 22". ✅

**Music (diverges):**
- `What songs does James like?` / `songs` / `musci` → song only ("君の神様になりたい" by こはならむ).
- `What music does James like?` / `What music does James play?` (in convo) → **also song only**, omitting the artist/bands the broad "music" intent should include.
- `What are James's favorite bands?` / `fav bands?` → bands only.
- `Who is James's favorite singer?` → **biography** (wrong topic entirely).

So "music" is silently narrowed to "songs" by the canonical router ([query_plan.py:245-251](backend/generation/query_plan.py#L245)), and "favorite singer" routes to bio. The factual answer changes depending on wording.

**Photography (diverges):**
- `What camera does James use?` / `camera` / `what camera's he got` → Nikon Z8 + secondary cameras. ✅
- `What lenses does James use?` / `lenses` / `what lense does he use` → both NIKKOR lenses. ✅
- `What camera and lenses does James use?` → both. ✅
- `Where has James photographed?` / `where james take photos` → 3 locations. ✅
- `Has he travelled with his camera?` → **camera gear** (wrong — should be locations). ❌
- `What has James filmed?` → **1 video only** (Japan Vlog), whereas `What videos has James made?` → all 3 videos. Wording changes the answer from complete to incomplete.

**Writing (diverges badly):**
- `What essays has James written?` → full numbered list. ✅
- `Tell me about the Extended Essay.` → **biography**. ❌
- `What about the Math IA?` (standalone) → correct Math IA detail; **(in conversation)** → biography. ❌
- `Which essay involves Apex Legends?` → **refused** (apex routes to games topic, blocking the writing template). ❌

**Personality / future interests (diverges):**
- `What are James's future academic interests?` / `future plans?` / `aspirations` → semiconductors/aerospace/quantum. ✅
- `what does he wanna study later` → **education summary** (IBDP, HL subjects) instead of aspirations. ❌

**Education:**
- `What are James's Higher Level subjects?` / `his HLs?` shorthand → `his HLs?` is **refused** (no retrieval) while the formal form works. ❌

**Sports:**
- `What sports does James play?` / `sports` → list. ✅
- `Tell me about James's ice hockey.` → **biography**. ❌

**Travel destinations:** `Italy` / `What did James do in Italy?` / `What did he photograph in Italy?` → Tuscany sunset. ✅ Consistent. But the conversation follow-ups "What did he photograph there?" and "And Greece?" break (see Multi-turn).

---

## Failed and weak questions

Each entry: question → answer → score → expected → root cause (file:line) → recommended correction → regression test.

### F1. "Tell me about the Extended Essay." → returns biography
- **Answer:** "James Sui is a 17-year-old student living in Shanghai, China. He describes himself as a student, photographer, athlete, technologist; his tagline is…" (source: *Bio summary*)
- **Score:** 2/12 (failed) — intent 0, factual 0, directness 0, completeness 0, formatting 2, sources 0
- **Expected:** The Extended Essay detail (Uniswap V3, CS+Economics, capital efficiency/slippage/impermanent loss).
- **Root cause:** [intent.py:23](backend/generation/intent.py#L23) — the bio topic pattern is `tell\s+me\s+about|about\s+james` (the `tell me about` alternative has **no** `james`). Any "Tell me about X" matches `tell\s+me\s+about` → `topic=bio`. `build_query_plan` then applies the bio retrieval override (`topic_queries["bio"]` = "James Sui 17 student Shanghai technologist", [query_plan.py:301](backend/generation/query_plan.py#L301)), so retrieval returns bio chunks and the bio structured answer fires.
- **Recommended correction:** Tighten [intent.py:23](backend/generation/intent.py#L23) to `tell\s+me\s+about\s+james` (matching the canonical rule at [query_plan.py:102](backend/generation/query_plan.py#L102)), so "Tell me about the Extended Essay" falls through to the writing topic.
- **Regression test:** `assert "Uniswap" in ask("Tell me about the Extended Essay.")["answer"]`.

### F2. "Tell me about the Physics IA." → returns biography
- **Answer:** biography (source: *Bio summary*).
- **Score:** 2/12 (failed)
- **Expected:** Physics IA detail (FFT guitar tuner, string gauge/tension/frequency).
- **Root cause:** Same as F1 — [intent.py:23](backend/generation/intent.py#L23) `tell\s+me\s+about` matches.
- **Recommended correction:** Same as F1.
- **Regression test:** `assert "FFT" in ask("Tell me about the Physics IA.")["answer"]`.

### F3. "Tell me about James's ice hockey." → returns biography
- **Answer:** biography (source: *Bio summary*).
- **Score:** 2/12 (failed)
- **Expected:** Ice hockey detail (started 2015, defender, Eagles Club, LA Kings coaches, Russia/Japan matches).
- **Root cause:** [query_plan.py:102](backend/generation/query_plan.py#L102) — `tell\s+me\s+about\s+james` greedily matches the substring "tell me about james" inside "Tell me about James's ice hockey" (no trailing word boundary), canonicalizing to "Who is James?" → bio.
- **Recommended correction:** Anchor the canonical bio regex, e.g. `tell\s+me\s+about\s+james\b(?!\s*'?s)` or require `tell\s+me\s+about\s+james\s*$` / end-of-input, so possessive/qualifier forms are not captured.
- **Regression test:** `assert "hockey" in ask("Tell me about James's ice hockey.")["answer"].lower()`.

### F4. "Who is James's favorite singer?" → returns biography
- **Answer:** biography (source: *Bio summary*).
- **Score:** 2/12 (failed)
- **Expected:** DECO*27 (favorite artist). "singer" should map to the music/artist entity.
- **Root cause:** [query_plan.py:102](backend/generation/query_plan.py#L102) — `who\s+is\s+james` matches inside "Who is James's favorite singer?" → "Who is James?" canonical → bio.
- **Recommended correction:** Same boundary fix as F3 for `who\s+is\s+james`; add "singer" to the artist entity regex at [intent.py:160](backend/generation/intent.py#L160) (currently `artist` = `\bartists?\b`, missing "singer").
- **Regression test:** `assert "DECO*27" in ask("Who is James's favorite singer?")["answer"]`.

### F5. "how old is james" → refused despite correct retrieval
- **Answer:** refusal (reason: `grounding_failed`). Retrieved sources: *Bio summary, Age, Self-description* — the "Age" chunk literally says "17 years old".
- **Score:** 7/12 (weak) — intent 1, factual 2, directness 0, completeness 1, formatting 2, sources 1
- **Expected:** "James is 17 years old."
- **Root cause:** [intent.py:23](backend/generation/intent.py#L23) — "how old" matches no topic pattern (bio pattern requires `who is`/`tell me about`/`bio`/`born`/`live`/etc.), so `topic=None`, `kind=unknown`. The structured bio answer (which includes "17-year-old") only fires when `intent.topic == "bio"` ([structured_answers.py:286](backend/generation/structured_answers.py#L286)). With no structured answer, the query goes to qwen2.5:3b, which produced text that failed the grounding check ([answer.py:337](backend/generation/answer.py#L337)).
- **Recommended correction:** Add `how\s+old|age` to the bio topic pattern at [intent.py:23](backend/generation/intent.py#L23) (or add an age structured path). Then the bio structured answer ("…17-year-old student…") fires deterministically.
- **Regression test:** `assert "17" in ask("how old is james")["answer"]`.

### F6. "What is James?" → refused
- **Answer:** refusal (reason: `model_refusal`). Sources: *Full name, Contact and socials, Photography* (irrelevant).
- **Score:** 5/12 (failed)
- **Expected:** A bio overview (James Sui, 17, Shanghai, student/photographer/athlete/technologist).
- **Root cause:** "What is James?" tokenizes to the single term `james` (all other tokens are stopwords; [tokenizer.py STOPWORDS](backend/retrieval/tokenizer.py)). `james` appears in most chunks → very low IDF → BM25 returns an arbitrary ordering of short chunks (*Full name*, *Contact and socials*). No canonical rule matches "What is James?" (only "Who is James" does, [query_plan.py:102](backend/generation/query_plan.py#L102)).
- **Recommended correction:** Add `what\s+is\s+james` to the bio canonical rule at [query_plan.py:102](backend/generation/query_plan.py#L102). Consider a minimum-query-length / `james`-only fallback that routes to bio.
- **Regression test:** `assert "Shanghai" in ask("What is James?")["answer"]`.

### F7. "When did James start coding?" → refused
- **Answer:** refusal (reason: `model_refusal`). Sources: *Full name, Contact and socials, Photography* (identical to F6 — the query collapsed to "james").
- **Score:** 5/12 (failed)
- **Expected:** Self-taught Python during middle school.
- **Root cause:** [intent.py:164](backend/generation/intent.py#L164) — the `coding_origin` entity requires `\b(?:learn|learned|self-taught|taught|started)\b`, but the question uses "start" (not "started"), so the entity does not fire and no `coding_origin` retrieval override is applied. Worse, `start` and `coding` match **no** chunk token (no stemming — chunks say "started" and "programming"/"code", not "coding"), so the query again collapses to `james` and returns the same irrelevant short chunks as F6.
- **Recommended correction:** (a) accept `start` in the `coding_origin` regex; (b) add stemming or query expansion for `coding`→`code`/`programming` and `start`→`started` in the tokenizer; (c) make `coding_origin` route to the projects/education coding chunk.
- **Regression test:** `assert "Python" in ask("When did James start coding?")["answer"]`.

### F8. "What has James achieved?" → refused
- **Answer:** refusal (reason: `grounding_failed`). Sources: *Full name, Contact and socials, Photography* (james-only collapse).
- **Score:** 5/12 (failed)
- **Expected:** The achievements list (Physics Bowl Silver, CTB top 5%, Curieux, Lumiere, Qiu).
- **Root cause:** [bm25.py:133](backend/retrieval/bm25.py#L133) — `achievement_query` is `query_terms & {"award","awards","achievement","achievements","won"}`; "achieved" is not in the set, so no summary bonus is applied to the *Achievements & Awards* chunk. With no stemming, "achieved" matches nothing, and the query collapses to "james".
- **Recommended correction:** Add stemming (or expand "achieved"→"achievements") and include "achieved"/"accomplishment" in the achievement query set.
- **Regression test:** `assert "Physics Bowl" in ask("What has James achieved?")["answer"]`.

### F9. "What research has James done?" → refused
- **Answer:** refusal (reason: `model_refusal`). Top source: *Fun fact: cosplay* (score 8.16) — irrelevant.
- **Score:** 5/12 (failed)
- **Expected:** LLM hallucination research, histology classification, Lumiere program.
- **Root cause:** Retrieval collision — the rare word "done" matches "James has done cosplay before" in the short *Fun fact: cosplay* chunk, which BM25 (favoring short docs) ranks above the genuine research chunks (*Lumiere Research Program* scored 4.89, *Writing & Essays* 4.32). No canonical rule recognizes "research" as a writing summary query.
- **Recommended correction:** Add a canonical rule mapping "what research" → writing summary; discount very-short personality "fun fact" chunks for research/essay queries.
- **Regression test:** `assert "hallucination" in ask("What research has James done?")["answer"].lower()`.

### F10. "Which essay involves Apex Legends?" → refused
- **Answer:** refusal (reason: `model_refusal`). Source: *Writing & Essays* (the correct chunk was retrieved at score 22.9).
- **Score:** 6/12 (weak)
- **Expected:** "The Math IA (Markov chain packet-loss model applied to Apex Legends)."
- **Root cause:** [intent.py:28](backend/generation/intent.py#L28) — the games topic pattern `\b(?:…|apex|…)\b` is listed **before** the writing pattern ([intent.py:36](backend/generation/intent.py#L36)), so "Apex" forces `topic=games`. The Writing & Essays structured answer ([structured_answers.py:504-512](backend/generation/structured_answers.py#L504)) is then gated by `_summary_matches_intent`, which requires `topic in {writing}` ([structured_answers.py:59](backend/generation/structured_answers.py#L59)) — fails for `games`, so structured returns None and qwen2.5:3b is asked, but it refuses despite the Math IA line being in the context.
- **Recommended correction:** When "essay"/"IA" co-occurs with "apex", prefer the writing topic (reorder or add an essay-override before the games pattern). Optionally add an "apex essay" sub-branch to the Writing template.
- **Regression test:** `assert "Markov" in ask("Which essay involves Apex Legends?")["answer"]`.

### F11. "his HLs?" → refused (no retrieval)
- **Answer:** refusal (reason: `no_retrieval`). No sources.
- **Score:** 7/12 (weak)
- **Expected:** HL subjects (Computer Science, Mathematics AA, Physics).
- **Root cause:** [intent.py:173](backend/generation/intent.py#L173) — `higher_level_subjects` regex is `\b(?:hl|higher\s+level|…)\b`; `\bhl\b` does not match "HLs" (no boundary between "hl" and "s"). The query tokenizes to `hls`, which matches no chunk → empty retrieval.
- **Recommended correction:** Change to `\bhl(?:s)?\b` and/or add "hls"→"higher level" normalization in the planner.
- **Regression test:** `assert "Computer Science" in ask("his HLs?")["answer"]`.

### F12. "How does this chatbot work?" → refused (should be product_meta)
- **Answer:** refusal (reason: `model_refusal`). Sources: *Views on talent vs hard work, Values hard work over talent, Values teamwork* (irrelevant).
- **Score:** 5/12 (failed)
- **Expected:** The RAG architecture explanation (the `product_meta_answer` "architecture" block).
- **Root cause:** [policies.py:58](backend/generation/policies.py#L58) — the product_meta regex `how\s+does\s+(?:this|the|jamchat)\s+(?:chat|bot|assistant)?\s*work` requires `chat`/`bot`/`assistant` as a **separate** token. The single token "chatbot" matches none of them (it tries "chat" then fails on "bot…work"), so `is_product_meta_request` returns False. Note: "How does JamChat work?" and "How does this chat work?" **do** match — the failure is specific to the word "chatbot".
- **Recommended correction:** Add `chatbot` to the alternation: `(?:chat|bot|assistant|chatbot)?`.
- **Regression test:** `assert "retrieval" in ask("How does this chatbot work?")["answer"].lower()`.

### F13. "Where does the chatbot's knowledge come from?" → refused (should be product_meta)
- **Answer:** refusal (reason: `model_refusal`). Source: *TOK Exhibition* (irrelevant).
- **Score:** 5/12 (failed)
- **Expected:** The knowledge-base explanation (`product_meta_answer` "knowledge" block).
- **Root cause:** [policies.py:60-61](backend/generation/policies.py#L60) — the knowledge pattern requires `data`/`information` ("where does the data/information come from"), but the question says "knowledge"; and the chatbot-possessive pattern needs `chat`/`bot`/`assistant` as a separate token, which "chatbot's" is not.
- **Recommended correction:** Add "knowledge" to the come-from pattern and `chatbot` to the possessor alternation.
- **Regression test:** `assert "knowledge base" in ask("Where does the chatbot's knowledge come from?")["answer"].lower()`.

### F14. "Where can I see his work?" → refused
- **Answer:** refusal (reason: `model_refusal`). Sources: *Views on talent vs hard work, Values hard work over talent, Values teamwork* — "work" matched the "hard work" personality chunks.
- **Score:** 5/12 (failed)
- **Expected:** Contact links (GitHub, YouTube, website).
- **Root cause:** "work" is generic; no intent rule maps "see his work" to contact/projects. Retrieval matches "hard work" personality chunks. This is a reasonable visitor question with no routing path.
- **Recommended correction:** Add a canonical rule mapping "see his/James's work" → contact (GitHub/YouTube/website).
- **Regression test:** `assert "github" in ask("Where can I see his work?")["answer"].lower()`.

### F15. "what does he wanna study later" → education summary (wrong)
- **Answer:** "James studies the IBDP at YK Pao School and is currently in Grade 11. His Higher Level subjects are…"
- **Score:** 6/12 (weak) — intent 1, factual 0 (wrong topic), directness 1, completeness 1, formatting 2, sources 1
- **Expected:** Future academic interests (semiconductors, aerospace, quantum computing).
- **Root cause:** [query_plan.py:119](backend/generation/query_plan.py#L119) and [intent.py:174](backend/generation/intent.py#L174) — the aspirations regex is `want(?:s)?\s+to\s+study`; "wanna study" does not match. "study" then matches the education topic pattern ([intent.py:39](backend/generation/intent.py#L39)), returning the education summary.
- **Recommended correction:** Add `wanna\s+study|wants?\s+to\s+study|study\s+later|study\s+after` to the aspirations pattern.
- **Regression test:** `assert "semiconductors" in ask("what does he wanna study later")["answer"].lower()`.

### F16. "What music does James like?" → song only (incomplete)
- **Answer:** "James's current favorite song is '君の神様になりたい' by こはならむ." (omits artist DECO\*27 and bands).
- **Score:** 10/12 (acceptable)
- **Expected:** Song + artist + bands (the broad "music" intent).
- **Root cause:** [query_plan.py:245-251](backend/generation/query_plan.py#L245) routes "What music does James like?" to the canonical "What songs does James like?" (song-only). Then [structured_answers.py:130-131](backend/generation/structured_answers.py#L130) returns the song-only branch because the `song` entity is present.
- **Recommended correction:** Route broad "music" (without "song"/"track") to the full music answer (the `else` branch at [structured_answers.py:134-137](backend/generation/structured_answers.py#L134)), reserving song-only for explicit "song"/"track".
- **Regression test:** `assert "DECO*27" in ask("What music does James like?")["answer"]`.

### F17. "What are James's favorite bands and artists?" → bands only
- **Answer:** "James's favorite bands are Yorushika, Hitorie." (omits artist DECO\*27).
- **Score:** 10/12 (acceptable)
- **Expected:** Bands + artist.
- **Root cause:** [structured_answers.py:128](backend/generation/structured_answers.py#L128) — `_format_music` checks `if "band" in intent.entities and "song" not in intent.entities: return bands-only` **before** the artist/combined branches. When both `band` and `artist` entities are present, the band branch fires first and returns bands only.
- **Recommended correction:** Reorder so the combined `band`+`artist` case is handled before the band-only case (e.g. `if "band" in entities and "artist" in entities: return combined`).
- **Regression test:** `assert "DECO*27" in ask("What are James's favorite bands and artists?")["answer"]`.

### F18. "Has he travelled with his camera?" → camera gear (wrong)
- **Answer:** "James's primary camera is a Nikon Z8. He also uses a DJI Action 4 and an iPhone 13 Pro."
- **Score:** 6/12 (weak)
- **Expected:** Photographed locations (Hokkaido, Tuscany, Athens).
- **Root cause:** [query_plan.py:220-223](backend/generation/query_plan.py#L220) — the camera-gear canonical (`not lens and camera and (what|which|his|james|use|does)`) matches because "his" + "camera" are present; "travelled" is ignored. No rule captures "travelled with camera" → photographed places.
- **Recommended correction:** Add a rule: if `travel`/`travelled` + `camera`/`photograph` → photographed_places canonical (before the camera-gear rule).
- **Regression test:** `assert "Hokkaido" in ask("Has he travelled with his camera?")["answer"]`.

### F19. "What has James filmed?" → 1 of 3 videos
- **Answer:** Only the Japan Vlog chunk body ("James filmed a video titled 'Japan Vlog' (4K, 2024)…").
- **Score:** 8/12 (weak)
- **Expected:** All videos (Greece, Japan Winter, Japan Vlog) — which is what `What videos has James made?` returns.
- **Root cause:** [intent.py:108-111](backend/generation/intent.py#L108) routes "filmed" + "what/has" to `topic=photography` (not `videos`), because the photography pattern ([intent.py:27](backend/generation/intent.py#L27)) includes `filmed` and the videos pattern does not include "filmed". The photography topic then takes the entity path ([structured_answers.py:414-415](backend/generation/structured_answers.py#L414)) which returns a single chunk body, not the multi-video formatter.
- **Recommended correction:** Route "what has James filmed" / "what did he film" to the `videos` topic so the video formatter ([structured_answers.py:332-359](backend/generation/structured_answers.py#L332)) produces the full list.
- **Regression test:** `assert "Greece" in ask("What has James filmed?")["answer"]`.

### F20. "What has James built?" → single project (FTC Robotics)
- **Answer:** "Member of a newly created FTC (FIRST Tech Challenge) robotics team. Designed, built, and tested competition robots."
- **Score:** 7/12 (weak)
- **Expected:** The full projects list.
- **Root cause:** "built" matches the projects entity path ([structured_answers.py:416](backend/generation/structured_answers.py#L416)) which returns `_body_without_heading(chunk)` of the top retrieved chunk. Retrieval returned *FTC Robotics*, *PC build project*, *PC building* (all "build"-related) rather than the *Projects & Skills* summary, so only FTC Robotics is shown. No canonical rule maps "what has James built" → projects summary.
- **Recommended correction:** Add a canonical rule mapping "what has James built/made/created" → projects summary (so the numbered list fires).
- **Regression test:** `assert "FFT guitar tuner" in ask("What has James built?")["answer"]`.

### F21. "What does he play?" → nonsensical hallucination
- **Answer:** "PC build project and Fortnite" (source: *Fortnite as gateway to tech, PC build project, Ice hockey description*).
- **Score:** 2/12 (failed) — hallucination
- **Expected:** A clarification (the standalone pronoun "he" with no topic is genuinely ambiguous).
- **Root cause:** "What does he play?" does not match the followup pattern ([intent.py:43-47](backend/generation/intent.py#L43)) (unlike "When did he start?" and "Which one is his favorite?", which match and correctly clarify). So `kind=unknown, followup=False` and it proceeds to retrieval + generation, where qwen2.5:3b stitches together unrelated chunks into a nonsense answer that nonetheless passes grounding.
- **Recommended correction:** Treat standalone pronoun-subject questions with no topic ("What does he play/use/do?") as clarification (`ambiguous_followup`) rather than letting the model answer.
- **Regression test:** `assert ask("What does he play?")["status"] == "clarification"`.

### F22. "What does he use?" → nonsensical hallucination
- **Answer:** "unlimited money to buy a gaming computer for a friend who was refused one by his parents" (source: *Values friendship above material things*).
- **Score:** 2/12 (failed) — hallucination
- **Expected:** Clarification.
- **Root cause:** Same as F21 — pronoun-subject, no topic, no followup match → retrieval + generation returns an irrelevant chunk's content as an answer.
- **Recommended correction:** Same as F21.
- **Regression test:** `assert ask("What does he use?")["status"] == "clarification"`.

### F23. "favorites" / "What are James's favorites?" → anime only, with model typo
- **Answer:** "Anime (top favorites) Bang Dream, Mygoy, Clannad, Jojo's Bizarre Adventure (all parts), and K-ON." (only anime; "Mygoy" is a model typo of "Mygo").
- **Score:** 4–5/12 (failed)
- **Expected:** A favorites overview (games, anime, music, food, season, place, etc.) or at least a non-anime-only answer.
- **Root cause:** No canonical rule for a broad "favorites" overview; retrieval returns the *Anime (top favorites)* chunk and qwen2.5:3b answers with anime only, introducing "Mygoy". The grounding check passes because most words overlap.
- **Recommended correction:** Add a structured "favorites overview" answer (or route "favorites" to a multi-favorite summary); do not let the model free-form list favorite titles.
- **Regression test:** `assert "Apex Legends" in ask("What are James's favorites?")["answer"]` (i.e. not anime-only).

### F24. "Tell me about James's Harvard degree." (false premise) → bio answer
- **Answer:** biography (source: *Bio summary*).
- **Score:** 4/12 (failed)
- **Expected:** Reject/correct the premise (James has no Harvard degree).
- **Root cause:** [query_plan.py:102](backend/generation/query_plan.py#L102) `tell\s+me\s+about\s+james` matches "Tell me about James's Harvard degree" → "Who is James?" → bio. The false premise is never examined.
- **Recommended correction:** Same boundary fix as F3; additionally, false-premise detection for named institutions/awards not in the KB would be ideal, but fixing the greedy regex is the minimum.
- **Regression test:** `assert "Harvard" not in ask("Tell me about James's Harvard degree.")["answer"]` and status == refused or a premise correction.

### F25. "What does James believe in?" → first-person, narrow
- **Answer:** "I believe this ability of self-learning is a crucial soft skill…" (first person; only one value).
- **Score:** 7/12 (weak)
- **Expected:** James's values (hard work over talent, democratizing technology, teamwork, politeness) in third person.
- **Root cause:** No canonical rule; `topic=None` (no "personality"/"values" keyword matches "believe in"). Retrieval returns the *Values self-learning* chunk and qwen2.5:3b echoes its first-person quote verbatim without converting to third person. Grounding passes.
- **Recommended correction:** Route "believe in"/"values" to the personality topic so the curated `personality_summary` fires; add a third-person instruction to the grounding prompt for personality quotes.
- **Regression test:** `assert "James" in ask("What does James believe in?")["answer"]` and `" I " not in answer`.

---

## Multi-turn conversation failures

Each conversation used a unique `session_id`. Failures are shown as transcripts with the point at which state was lost.

### C1. Essays conversation — collapses to bio for 3 consecutive turns

| Turn | Question | Normalized | Answer (abbreviated) | Result |
|---|---|---|---|---|
| 0 | What essays has James written? | What essays has James written | Full numbered writing list | ✅ |
| 1 | Tell me about the Extended Essay. | Tell me about the Extended Essay. | **Biography** (Bio summary) | ❌ F1 |
| 2 | What about the Math IA? | **Who is James?** | **Biography** | ❌ |
| 3 | Which one involves Apex Legends? | **Who is James?** | **Biography** | ❌ |

**Where state was lost:** Turn 1 misroutes to `bio` (root cause F1: [intent.py:23](backend/generation/intent.py#L23) `tell\s+me\s+about`). This sets `last_topic=bio`. Turn 2 ("What about the Math IA?") is a followup; `augment_query` prepends the bio context prefix `James bio Shanghai` ([conversation.py:155-156](backend/generation/conversation.py#L155)), and the canonical rule `james'?s?\s+bio` ([query_plan.py:102](backend/generation/query_plan.py#L102)) matches "James bio" → "Who is James?" → bio. Turn 3 inherits the same poisoned state. Note: **"What about the Math IA?" answers correctly in isolation** (returns the Markov/Apex Math IA detail) — the failure is purely the conversation context cascade.

### C2. Travel conversation — breaks at "there" / "Greece"

| Turn | Question | Normalized | Answer | Result |
|---|---|---|---|---|
| 0 | Where has James travelled? | Where has James traveled | Visited list (Japan, Greece, Italy, Xinjiang) | ✅ |
| 1 | What about Italy? | What did James do in Italy? | Tuscany sunset | ✅ |
| 2 | What did he photograph there? | travel What did he photography there | **Camera gear** (Nikon Z8, lenses) | ❌ |
| 3 | And Greece? | photography camera lens And Greece | **Camera gear** | ❌ |

**Where state was lost:** Turn 2 — "What did he photograph there?" — the pronoun "there" (Italy) is not resolved to a destination. `augment_query` prepends only `travel` ([conversation.py:155](backend/generation/conversation.py#L155)), and the photographed-places canonical ([query_plan.py:132-137](backend/generation/query_plan.py#L132)) requires `where`/`what places`/`which`, which "what did he photograph" does not satisfy. The question then routes to `photography` topic (the word "photograph" matches the photography pattern [intent.py:27](backend/generation/intent.py#L27)) and returns camera gear. This overwrites `last_topic` from `travel` to `photography`. Turn 3 ("And Greece?") is a followup, but the travel-destination branch in `augment_query` ([conversation.py:197-201](backend/generation/conversation.py#L197)) only fires when `last_topic == "travel"` — which is now `photography` — so "Greece" is not kept intact; the photography context prefix is prepended instead, and the destination canonical (which needs a `what about`/`where` cue or ≤3 tokens, [query_plan.py:147-150](backend/generation/query_plan.py#L147)) does not fire on the prefixed query.

### C3. Gaming conversation — re-answers Apex rank instead of "why"

| Turn | Question | Normalized | Answer | Result |
|---|---|---|---|---|
| 0 | What games does James like? | What are James's favorite games? | Game list | ✅ |
| 1 | What is his Apex rank? | What is James's highest rank in Apex Legends? | Diamond 2, Season 22 | ✅ |
| 2 | When did he reach it? | What is James's highest rank in Apex Legends? | Diamond 2, Season 22 | ⚠️ (rank re-answered; season is included but not focused) |
| 3 | Why does he enjoy gaming? | **What is James's highest rank in Apex Legends?** | **Diamond 2, Season 22** | ❌ |

**Where state was lost:** Turn 3 — "Why does he enjoy gaming?" is a followup. Because `last_topic=games` is in the list-like set, `_keywords` ([conversation.py:160-161](backend/generation/conversation.py#L160)) extracts capitalized terms from the previous answer ("apex", "legends", "diamond") and prepends them, producing "Apex Legends rank … Why does he enjoy gaming?". The canonical apex-rank rule ([query_plan.py:230-233](backend/generation/query_plan.py#L230)) then matches `apex`+`rank` and re-routes to the rank answer. The user's actual intent ("why does he enjoy gaming" → gaming_reason) is overridden by the context prefix. Note: **"Why does he enjoy gaming?" answers correctly in isolation** (returns "relax and decompress… connected with friends").

### C4. Instrument conversation — drifts to favorite music

| Turn | Question | Normalized | Answer | Result |
|---|---|---|---|---|
| 0–4 | Does James play an instrument? / Has he ever learned… / What instrument… / what instrument he play / When did he start? | (various) | Electric guitar, 2025, self-taught | ✅ |
| 5 | What kind of music does he play? | What kind of music does he play | Favorite song + artist + bands (not guitar genres) | ❌ |
| 6 | How did he learn? | music songs How did he learn | Favorite song only | ❌ |

**Where state was lost:** Turn 5 — "What kind of music does he play?" in instrument context should answer the guitar genres (J-pop, rock, ACG). But "music" is in `_EXPLICIT_TOPIC_TOKENS` ([conversation.py:14-25](backend/generation/conversation.py#L14)), so `augment_query` short-circuits and returns the question unchanged ([conversation.py:207](backend/generation/conversation.py#L207)), dropping the instrument context. It routes to the favorite-music answer instead. Turn 6 ("How did he learn?") is then poisoned by `last_topic=music` and answers with the favorite song, losing the guitar "self-taught" fact.

### Conversations that worked well
The **photography**, **hobbies**, and **education** conversations completed cleanly, including pronoun follow-ups ("What about his lenses?", "Where has he used them?", "When does he graduate?", "Anything else?"). The education conversation even handled "What does he want to study afterward?" correctly via generation (reason: `generated`), returning Purdue/Michigan/Penn programs — showing the aspirations path works when the phrasing matches `want to study`.

---

## Suggested-question failures

All **31 unique suggested questions were answerable** (0 refusals) — the bot never suggests a question its own routing cannot handle. This is a genuine strength of the deterministic suggestion engine ([suggestions.py](backend/generation/suggestions.py)).

However, one suggestion produces a **weak answer**:

- **"What music does James like?"** (suggested after a hobbies answer) → returns the **song only**, omitting the artist/bands (same root cause as F16). The suggestion is answerable but incomplete. *Fix F16 and this resolves.*

Two minor suggestion-quality issues:
- After answering "What are James's favorite bands?", the bot suggests **"What are James's favorite bands?"** again ([suggestions.py:41](backend/generation/suggestions.py#L41)) — suggesting the exact question just asked.
- The music-topic suggestions ([suggestions.py:40-41](backend/generation/suggestions.py#L40)) always offer "favorite bands" + "instrument", never "favorite song" or "favorite artist", so the narrower music facts are under-suggested.

---

## Answer-formatting problems

Correct or partially-correct answers that are poorly presented:

1. **"Yes-James" (missing space)** — [structured_answers.py:365](backend/generation/structured_answers.py#L365) and [structured_answers.py:471](backend/generation/structured_answers.py#L471): `"Yes-James does digital drawing…"` and `"Yes-James plays electric guitar…"`. Should be `"Yes — James…"` or `"Yes, James…"`.
2. **"Question 2:" labels** — [compound.py:39](backend/generation/compound.py#L39): when a split clause has no classifiable topic, the compound merger labels it `Question 2:` (e.g. "Does he play guitar and when did he start?" → "Hobbies: …\n\nQuestion 2: Which topic would you like to continue with…"). Awkward and exposes internal splitting.
3. **First-person answers** — "What does James believe in?" → "I believe this ability of self-learning…" (the model echoes James's first-person quote without conversion). The grounding prompt ([config.py:81-89](backend/config.py#L81)) does not instruct third-person conversion.
4. **Raw extractive chunk text** — bare "photography" and "Is photography something he takes seriously?" return the raw chunk body starting "Active photographer and videographer. His primary camera is a Nikon Z8…" (the photography title branch returns None for bare photography, [structured_answers.py:472-483](backend/generation/structured_answers.py#L472), falling to `extractive_answer`). Readable but unpolished vs. the curated templates.
5. **Model-introduced typos** — "What are James's favorites?" → "Mygoy" (for "Mygo"). The grounding check ([formatting.py:42-62](backend/generation/formatting.py#L42)) only verifies word overlap, not spelling fidelity.
6. **"Yes-James plays electric guitar. He started in 2025, is self-taught, and focuses on J-pop, rock, and ACG."** — the `is self-taught` phrasing ([structured_answers.py:471](backend/generation/structured_answers.py#L471)) is slightly awkward (reads as "is self-taught" dangling).

---

## Unsupported-question behavior

### Correct refusals (13)
- `What is James's favorite restaurant?`, `favorite university?`, `least favorite game?` → `unsupported` (clean, no sources). ✅
- `What is James's home address?`, `password?`, `phone number?` → `privacy` (clean). ✅
- `family` → `ambiguous_request` (clean). ✅
- `Recommend me a good game.` → `unsupported` (clean). ✅
- `What is James's favorite programming language?` → `unsupported` (clean). ✅
- `What is the capital of France?`, `What is 2 plus 2?` → `model_refusal` (correct refusal, **but irrelevant sources shown** — *Extended Essay (EE)* and *apex_rank* respectively). ⚠️
- `Why did James win an Olympic medal?`, `What Olympic medal did James win?` → `model_refusal` (correct false-premise refusal, **but irrelevant sources shown** — *Full name, Contact and socials, Fun fact: cosplay*). ⚠️
- `What DSLR did James use before the Nikon Z8?` → `model_refusal` (correct, **but irrelevant sources shown** — *Greece, Japan Winter, Xinjiang*). ⚠️

### Incorrect refusals (should have answered) — 13 clear + 2 mixed-language
See F5–F14 above. The most damaging for visitors: "how old is james", "What is James?", "When did James start coding?", "What has James achieved?", "What research has James done?", "his HLs?", "Where can I see his work?", "How does this chatbot work?", "Where does the chatbot's knowledge come from?".

### Hallucinations (4)
- F21 "What does he play?" → "PC build project and Fortnite"
- F22 "What does he use?" → "unlimited money to buy a gaming computer for a friend…"
- F23 "What are James's favorites?" → "Mygoy" (fabricated spelling)
- F25 "What does James believe in?" → first-person quote presented as a direct answer (semantically narrow, not fully hallucinated, but ungrounded as a complete answer)

### False-premise handling
- ✅ "Why did James win an Olympic medal?" / "What Olympic medal did James win?" — correctly refused.
- ❌ "Tell me about James's Harvard degree." — **answered with the bio** instead of rejecting the premise (F24). The greedy `tell me about james` regex routes it away from any premise check.
- ❌ "What DSLR did James use before the Nikon Z8?" — correctly refused, but does not explicitly correct the premise (no DSLR is documented); shows irrelevant sources.

### Systematic source-on-refusal problem
Every refusal that passes through retrieval (`model_refusal`, `grounding_failed`, `low_retrieval_confidence`) returns the retrieved chunks as sources ([answer.py:294](backend/generation/answer.py#L294) builds sources before the refusal branches). On a refusal, these sources are definitionally irrelevant to the (non-)answer. A visitor asking "What is 2 plus 2?" sees "Source: apex_rank", which is confusing and undermines trust. **Recommendation:** suppress sources (or replace with none) whenever `status != "answered"`.

---

## Missing but reasonable visitor questions

Questions a visitor would reasonably expect "Ask James" to answer, that currently fail:

| Question | Problem | Missing data or code? |
|---|---|---|
| "What is James?" / "Who is James?" (non-canonical) | Refused (james-only collapse) | Code — no canonical rule for "what is james"; stopword/IDF collapse |
| "how old is james" | Refused despite correct retrieval | Code — "how old" not routed to bio; model/grounding fails |
| "Where can I see his work?" | Refused (matches "hard work") | Code — no "see his work" → contact route |
| "What research has James done?" | Refused (cosplay collision) | Code — no "research" canonical; retrieval collision |
| "What has James achieved?" | Refused (stemming) | Code — "achieved" not matched |
| "his HLs?" | Refused (no retrieval) | Code — "HLs" not normalized |
| "How does this chatbot work?" | Refused (should be meta) | Code — "chatbot" token not in product_meta regex |
| "favorites" / "What are James's favorites?" | Anime-only | Code — no favorites-overview structured answer |
| "What has James built?" | Single project only | Code — no "built" → projects summary route |
| "Tell me about the Extended Essay/Physics IA" | Biography | Code — `tell me about` over-broad |
| "What does he play?" / "What does he use?" (standalone) | Hallucination | Code — should clarify, not generate |

None of these are missing-data problems — **every** fact needed to answer them exists in `data/profile_facts.json` and `kb_extra/`. All failures are code-structure (routing, normalization, retrieval, conversation-state) issues.

---

## Highest-priority improvements

Ranked by expected effect on real visitor answer quality:

1. **Fix the `tell me about` over-broad bio pattern** ([intent.py:23](backend/generation/intent.py#L23)) and the greedy `who is james` / `tell me about james` canonical ([query_plan.py:102](backend/generation/query_plan.py#L102)). *One regex change fixes F1, F2, F3, F4, F24, and the entire essays-conversation cascade (C1).* Highest leverage.
2. **Suppress sources on non-answered responses** ([answer.py:294](backend/generation/answer.py#L294)). *Eliminates ≥13 source-failure cases in one change; large trust improvement.*
3. **Add stemming / query expansion** (tokenizer) so `achieved`→`achievements`, `start`→`started`, `coding`→`code/programming`, and a `james`-only-query fallback to bio. *Fixes F6, F7, F8 and the general "short question → james-only collapse → irrelevant short chunks" class.*
4. **Add `chatbot` to the product_meta regex** ([policies.py:58](backend/generation/policies.py#L58), [:60-61](backend/generation/policies.py#L60)). *Fixes F12, F13 — two very common visitor meta-questions.*
5. **Route bare "filmed" to the videos topic** ([intent.py:108](backend/generation/intent.py#L108)) and add `how old`/`age` to bio topic. *Fixes F5, F19.*
6. **Fix `_format_music` band-before-artist ordering** ([structured_answers.py:128](backend/generation/structured_answers.py#L128)) and route broad "music" to the full music answer. *Fixes F16, F17 and the weak music suggestion.*
7. **Make pronoun-subject standalone questions clarify** (extend the followup pattern or add a pronoun-only-no-topic rule). *Fixes F21, F22 hallucinations.*
8. **Stop `_keywords` from overriding explicit user intent in conversation** ([conversation.py:160-161](backend/generation/conversation.py#L160)) — do not prepend previous-answer terms when the followup contains its own topic/wh-word. *Fixes C3 (gaming "why" → rank) and reduces cascade risk.*
9. **Resolve destination pronouns in conversation** ("there" → last destination) and keep `last_topic` stable across photography/travel boundary. *Fixes C2 (travel cascade).*
10. **Add canonical routes** for "wanna study"→aspirations (F15), "his HLs"→HL (F11), "see his work"→contact (F14), "what has built"→projects summary (F20), "favorites"→overview (F23), "believe in"→personality (F25).
11. **Fix "Yes-James" formatting** ([structured_answers.py:365](backend/generation/structured_answers.py#L365), [:471](backend/generation/structured_answers.py#L471)) and compound "Question 2:" labels ([compound.py:39](backend/generation/compound.py#L39)). *Polish.*
12. **Reorder games-vs-writing topic precedence** when "essay"/"IA" is present ([intent.py:28 vs :36](backend/generation/intent.py#L28)). *Fixes F10.*

---

## Regression test matrix

Reusable table for a test suite. "Expected follow-up behavior" assumes the question is asked as turn 2 after the canonical starter.

| Canonical intent | Natural-language variants | Expected facts | Expected source titles | Expected status | Expected follow-up behavior |
|---|---|---|---|---|---|
| Bio / age | "Who is James?", "What is James?", "how old is james", "tell me about james" | 17, Shanghai, student/photographer/athlete/technologist | Bio summary | answered | "What is James like as a person?" works |
| Personality / values | "What is James like as a person?", "What does James believe in?", "his values?" | nice, outgoing, hard work | Self-description (nice and outgoing) | answered | aspirations follow-up works |
| Future interests | "What are James's future academic interests?", "future plans?", "what does he wanna study later", "aspirations" | semiconductors, aerospace, quantum computing | Future aspirations | answered | — |
| Hobbies | "What are James's hobbies?", "hobbies", "what does he do for fun", "free time", "他的爱好是什么？" | photography, gaming, sports, electric guitar | Hobbies & Interests | answered | "Anything else?" → cosplay/3D printer |
| Games | "gaming", "games", "What games does James play?", "what games do james like", "James最喜欢什么游戏？" | Apex Legends, CS:GO/CS2, Valorant, Cyberpunk | Favorite games | answered | Apex rank follow-up works |
| Apex rank | "apex rank?", "What is James's Apex rank?", "apex legends ank", "他的apex rank是多少？" | Diamond 2, Season 22 | apex_rank | answered | "When did he reach it?" → Season 22 |
| Guitar / instrument | "Does James play an instrument?", "guitar", "instrument", "他会弹什么乐器？", "What instrument does he play?" | electric guitar, 2025, self-taught | Electric guitar | answered | "When did he start?" → 2025; "What kind of music does he play?" → J-pop/rock/ACG (currently fails) |
| Music (broad) | "What music does James like?", "favorite music", "musci" | song + DECO\*27 + Yorushika/Hitorie | Favorite music | answered | — |
| Music (bands+artists) | "What are James's favorite bands and artists?", "fav bands?" | Yorushika, Hitorie, DECO\*27 | Favorite music | answered | — |
| Anime | "anime", "What is James's favorite anime?", "his fav anime" | Bang Dream Mygo, Clannad, Jojo, K-ON | Favorite anime / Anime (top favorites) | answered | — |
| Photography (camera) | "What camera does James use?", "camera", "what camera's he got" | Nikon Z8, DJI Action 4, iPhone 13 Pro | Photography and videography | answered | "What about his lenses?" works |
| Photography (lenses) | "What lenses does James use?", "lenses", "what lense does he use" | NIKKOR 24-120mm F4 S, NIKKOR 85mm F1.8 | Photography and videography | answered | — |
| Photographed places | "Where has James photographed?", "where james take photos", "Has he travelled with his camera?" | Hokkaido, Tuscany, Athens | Italy/Greece/Japan destination chunks | answered | "What did he photograph in Italy?" → Tuscany sunset |
| Photography (overview) | "photography", "photographt" | Nikon Z8 + locations overview | Photography and videography | answered | — |
| Videos | "What videos has James made?", "videos", "What has James filmed?" | Greece, Japan Winter, Japan Vlog | Greece, Japan Winter, Japan Vlog | answered | — |
| Sports | "What sports does James play?", "sports", "his sports?" | skiing, ice hockey, tennis, floorball, soccer | Sports | answered | "Which sport did James start first?" → skiing 2013 |
| Sports (position) | "What position does he play in ice hockey?" | defender | Sports / Ice hockey | answered | — |
| Travel | "Where has James travelled?", "travel", "Where has he been?" | Japan, Greece, Italy, Xinjiang | Travel | answered | "What about Italy?" → Tuscany |
| Destination: Italy | "What did James do in Italy?", "Italy", "What did he photograph in Italy?" | Tuscany, sunset | Italy (Tuscany) | answered | — |
| Projects | "What projects has James built?", "projects", "What has James built?", "school projects?" | FFT guitar tuner, Flutter, econ grapher, … | Projects & Skills | answered | "Which projects involve AI?" works |
| AI projects | "Which projects involve AI?", "What AI projects has James done?" | hallucination evaluator, histology benchmark | Projects & Skills | answered | — |
| Programming languages | "What programming languages does James know?", "What programming languages does he use?" | Python, C, C++, TypeScript, Dart, Solidity | Programming languages | answered | — |
| Coding origin | "How did James learn to code?", "When did James start coding?" | self-taught, Python, middle school | Self-taught programming | answered | — |
| Essays (list) | "What essays has James written?", "essays" | Extended Essay, Math IA, Physics IA, hallucination, … | Writing & Essays | answered | "Tell me about the Extended Essay." → Uniswap (currently fails) |
| Essay: Extended Essay | "Tell me about the Extended Essay.", "What is his Extended Essay about?" | Uniswap V3, capital efficiency, slippage | Writing & Essays | answered | — |
| Essay: Math IA | "What about the Math IA?", "Which one involves Apex Legends?" | Markov, Apex Legends, 20Hz tick | Math IA / Writing & Essays | answered | — |
| Achievements | "What are James's achievements?", "acheivements", "What has James achieved?", "awards" | Physics Bowl Silver, CTB top 5%, Curieux | Achievements & Awards | answered | — |
| Education | "Where does James study?", "education", "school" | IBDP, YK Pao School, Grade 11 | Education | answered | "What subjects does he take?" works |
| HL subjects | "What are James's Higher Level subjects?", "his HLs?", "Which ones are Higher Level?" | Computer Science, Mathematics AA, Physics | Education | answered | — |
| Graduation | "When does James graduate?", "graduation", "when does he finish school" | 2027 | Expected graduation | answered | — |
| Favorites (food/season/place) | "What is James's favorite food?", "favorite season", "favorite place" | ramen; winter; Japan/Tokyo | Favorite food / season / place | answered | — |
| Favorites (overview) | "favorites", "What are James's favorites?" | multiple categories (not anime-only) | (multiple) | answered | — |
| Contact | "How can I contact James?", "contact", "Where can I see his work?" | email, YouTube, GitHub, website | Contact and socials | answered | — |
| Chatbot meta | "What model powers this chat?", "How does this chatbot work?", "Where does the chatbot's knowledge come from?", "Does this chat remember conversations?" | qwen2.5:3b, RAG/BM25, knowledge base, session memory | (none — product_meta) | answered | — |
| Boundary (refuse) | "favorite restaurant?", "home address?", "password?", "family", "Recommend me a good game." | (refusal, no sources) | (none) | refused | — |
| False premise (refuse/correct) | "Why did James win an Olympic medal?", "Tell me about James's Harvard degree.", "What DSLR before the Nikon Z8?" | (refusal or premise correction, no irrelevant sources) | (none) | refused | — |
| Compound | "What camera and lenses does James use?", "What is his favorite food and favorite season?" | both sub-answers, no "Question 2:" label | (both) | answered | — |

---

## Notes on the knowledge base (fact consistency)

- **Electric guitar start date:** `profile_facts.json` and `hobbies.md` say "2025", but chunk `hobby_electric_guitar_001` says "About a year ago" (a fragile relative timestamp). The structured layer uses 2025 (correct), but if that chunk is retrieved for generation, the model could produce a relative-time answer. Recommend replacing "about a year ago" with "2025".
- **Soccer position:** `favorites.md` says "Offender (forward)"; `sports.md` and `profile_facts.json` say "forward". The structured answer uses "forward" (consistent). Minor wording variance only.
- **Flappy Bird:** correctly hidden from the public chunk list via `HIDDEN_CHAT_CHUNK_IDS` ([config.py:42](backend/config.py#L42)) and text-stripped in `load_chunks` ([bm25.py:119-120](backend/retrieval/bm25.py#L119)). ✅
- **No contradictions** were found between `profile_facts.json`, `chunks.json`, and `kb_extra/` on core facts (rank, camera, lenses, HL subjects, graduation, achievements, destinations). The structured layer is the single source of truth and is internally consistent.

---

*Prepared by GLM-5.2 via Claude Code. All findings are reproducible against the current code on `main` (commit `ec06c19`) using the test scripts under `/tmp/jamchat_audit/`.*
