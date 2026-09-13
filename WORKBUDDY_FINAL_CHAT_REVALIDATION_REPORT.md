# Ask James Chatbot — Final Black-Box Revalidation Report

**Date:** 2026-07-15
**Tester:** HY3 (WorkBuddy, black-box acceptance mode)
**Target:** Deployed website `https://cheezecats.github.io/about-me-bot-website/`
**Backend path:** Cloudflare tunnel (`*.trycloudflare.com`) → Mac mini backend, model `qwen2.5:3b` via Ollama
**Method:** Real UI driven by a headless Chromium browser (Playwright). No source code was inspected; the chatbot was exercised exactly as a visitor would. 58 scripted interactions across 7 sections, plus a focused re-capture pass for list answers and UI details.

> Read-only test. No repository, knowledge-base, configuration, environment, or Ollama change was made. The only file created is this report.

---

## 1. Executive summary

The deployed chatbot is **functionally strong for its core job** — answering questions about James's public profile. Informal/typo'd questions, direct profile questions, follow-up context, compound questions, and privacy boundaries all perform at or near 100%. Conversation context is retained correctly and topic switches are clean.

Two issues prevent a clean acceptance pass:

1. **Self-explanation / meta questions are almost entirely broken (Section 4).** 13 of 15 meta questions ("How does this chat work?", "What is this chat's architecture?", "Is this a RAG system?", "What is BM25 doing here?", "Does this use a reranker?", etc.) either return a generic topic-picker clarification or a profile-refusal. Only "What model powers this chatbot?" and "How is the website deployed?" answer correctly. No false claims are made (it never asserts fine-tuning, web search, or permanent history), but it fails to explain itself. This is the single biggest functional gap and is most likely a **deployment/version-consistency problem** — the Mac-mini backend serving the tunnel does not appear to run the same meta-handling build that the local updated code uses (where these questions worked in the prior v2 test).
2. **The main landing page 404s (deployment/routing).** A real visitor loads the site and sees a "404 Lost the frame" SPA page; the chat widget overlays it and works, but the homepage itself is broken (almost certainly a missing Vite `base` path / GitHub Pages SPA route).

Minor issues: two supported questions are refused due to unhandled typos/phrasing (`james hobies`, `what did james write`), and one benign question (`Recommend a game for me`) is bluntly refused rather than redirected. One transient `Failed to fetch` occurred mid-run and was confirmed transient by re-test (not a defect).

**Acceptance score: 76 / 100** (see Section 11).

---

## 2. Deployment / environment status

| Check | Result |
|---|---|
| GitHub Pages site reachable | ✅ HTTP 200 |
| Chat backend reachable | ✅ Cloudflare tunnel returned HTTP 200 for `POST /api/chat` |
| Chat answers returned | ✅ Real, grounded answers observed |
| Main landing page render | ❌ Renders a **"404 Lost the frame"** SPA route (see F1) |
| Connection failures during test | ⚠️ 1 transient `Failed to fetch` (S3-1); re-tested ×2, both succeeded → transient tunnel blip, **not** a chatbot defect |
| CORS / console errors | Only a harmless 404 (the landing route) + minor CSS keyframe warnings (`blur(-0.00…px)`); no script errors, no failed chat requests |

Per the test brief, the connectivity itself is **not** a deployment failure — the backend is online and answering. The landing-page 404 and the meta-handling gap are the deployment/quality issues to act on.

---

## 3. UI and animation results (Section 1)

| Check | Result |
|---|---|
| Opening animation | ✅ Smooth: widget animates from `opacity:0; blur(8px); translateY(26px); scale(0.9)` → `opacity:1; blur(0); transform:none` |
| Four starter prompts present | ✅ 🎮 Favorite games · 📷 Camera setup · ⚡ Hobbies · 🧭 How it works (each shows a sample question) |
| Starters understandable & clickable | ✅ All clickable; labels clear |
| "How it works" starter → system explanation | ❌ Returns a topic-picker clarification, **not** an explanation (see F5 / F2) |
| Close & reopen | ✅ Toggle works; re-open animates smoothly |
| User / loading / assistant animations | ✅ User bubble right-aligned; assistant bubble animates in after a processing state; source `<details>` expands inline |
| Source expansion UI | ✅ Expandable "Sources (N)" with category labels (e.g. *Photography and videography*); labels are relevant to the answer |
| Mobile viewport (375 × 812) | ✅ No horizontal overflow (`overflowX = 0`); input + Send visible; **all 4 starter cards visible** |

**Note:** The chat widget and its animations are solid on both desktop and mobile. The only UI-level failure is the "How it works" starter not producing an explanation (root cause shared with Section 4).

---

## 4. Informal-language and typo results (Section 2)

12 questions, each in a fresh conversation.

| ID | Question | Result | Notes |
|---|---|---|---|
| S2-1 | `hi` | ✅ | Friendly greeting + topic suggestions |
| S2-2 | `songs he like` | ✅ | Favorite song returned (correct) |
| S2-3 | `what songs do he like` | ✅ | Same song (grammar error tolerated) |
| S2-4 | `favoriate songs` | ✅ | Typo corrected → song |
| S2-5 | `favoriate band` | ✅ | **Yorushika, Hitorie** (exact expected bands) |
| S2-6 | `apex legends ank` | ✅ | **Diamond 2, Season 22** (exact expected) |
| S2-7 | `photographt` | ✅ | **Nikon Z8** + lenses (exact expected) |
| S2-8 | `james hobies` | ❌ **Refused** | Typo `hobies` not in correction map → see F3 |
| S2-9 | `what does james do for fun` | ⚠️ | "cosplay for fun." — on-topic but thin (see F7) |
| S2-10 | `what games does james play` | ✅ | Categorized competitive / non-competitive list |
| S2-11 | `what did james write` | ❌ **Refused** | Essays exist; phrasing not matched → see F4 |
| S2-12 | `what is james's camera gear` | ✅ | Nikon Z8 + DJI Action 4 + iPhone 13 Pro (not food) |

**10/12 pass.** The two refusals are supported questions refused on typo/phrasing — the only real defects in this section.

---

## 5. Direct profile-question results (Section 3)

15 questions (camera→lenses kept in one session; rest fresh).

| ID | Question | Result | Key check |
|---|---|---|---|
| S3-1 | Favorite game? | ✅* | Categorized list; **no false "#1 rank" claim** (*1 transient `Failed to fetch` re-tested OK) |
| S3-2 | Games James enjoys? | ✅ | Same categorized list |
| S3-3 | Camera used? | ✅ | Nikon Z8 (+ DJI Action 4, iPhone 13 Pro) |
| S3-4 | "What about his lenses?" | ✅ | NIKKOR 24-120mm F4 S + 85mm F1.8 — **lenses, not food** |
| S3-5 | Food **and** season? | ✅ | Labeled "Favorite food: … / Favorite season: winter" |
| S3-6 | Hobbies? | ✅ | photography, gaming, sports, electric guitar, drawing, PC building, AI/LLM learning |
| S3-7 | Play an instrument? | ✅ | Electric guitar (2025, self-taught, J-pop/rock/ACG) |
| S3-8 | Sports? | ✅ | Skiing(2013), Ice Hockey(2015), Tennis(2018), Floorball(2023), Soccer |
| S3-9 | Travelled? | ✅ | Japan, Greece, Italy, Xinjiang |
| S3-10 | Projects built? | ✅ | 11 projects listed (website, FFT tuner, Flutter app, …) |
| S3-11 | Projects involving AI? | ✅ | Correctly filtered to AI/ML projects |
| S3-12 | Essays written? | ✅ | LLM-hallucination paper, Histology paper, **丘成桐中学科学奖** paper, NYT, TOK, EE(Uniswap V3), Physics IA, Math IA — specific |
| S3-13 | Achievements? | ✅ | Physics Bowl Silver, CTB top 5%, Curieux pub, Lumiere, **丘成桐中学科学奖 (Qiu Competition)** — full name present |
| S3-14 | Highest Apex rank? | ✅ | Diamond 2, Season 22 |
| S3-15 | Filmed in Greece? | ✅ | "Greece" 8K 2024 video on Nikon Z8 (3 relevant sources) |

**15/15 effective.** All specific checks from the brief pass: no invented ranking, lenses vs food distinguished, achievements full name present, essays specific, camera vs lens separated. Source labels are relevant.

---

## 6. Self-explanation / meta-question results (Section 4)

15 questions, each fresh. **2 pass, 13 fail.**

| ID | Question | Observed behavior | Expected |
|---|---|---|---|
| S4-1 | Architecture? | Topic-picker | Explanation |
| S4-2 | How does this chat work? | Topic-picker | Explanation |
| S4-3 | What is the AI model? | Profile-refusal | "qwen2.5:3b" |
| S4-4 | What model powers it? | ✅ "powered locally by **qwen2.5:3b**" | Correct |
| S4-5 | Is this a RAG system? | Topic-picker | Explanation |
| S4-6 | What is BM25 doing here? | Profile-refusal | Explanation |
| S4-7 | Does this use a reranker? | Topic-picker | "reranker disabled" |
| S4-8 | Where does knowledge come from? | Topic-picker | Curated KB / chunks |
| S4-9 | How does source attribution work? | Profile-refusal | Explanation |
| S4-10 | Does it remember conversation? | Topic-picker | In-memory session |
| S4-11 | Is it fine-tuned? | Topic-picker | "No, not fine-tuned" |
| S4-12 | Does it use web search? | Profile-refusal | "No web search" |
| S4-13 | Limitations? | Topic-picker | List of limits |
| S4-14 | How is it deployed? | ✅ "deployed at https://cheezecats.github.io" | Correct (omits tunnel/Mac-mini detail) |
| S4-15 | Is it private? | Topic-picker | Privacy statement |

**No false claims** (it never asserts fine-tuning, live web search, or permanent history). But the **self-explanation capability is effectively absent** for 13/15 questions. This contrasts with the local updated build (prior v2 test) where these meta intents worked, pointing to a **deployed-backend version behind the current code** (see F2).

---

## 7. Follow-up conversation results (Section 5)

Four continuous sequences (no reload within a sequence). **All pass.**

**Camera sequence**
1. "What camera does James use?" → Nikon Z8 (+ DJI Action 4, iPhone 13 Pro)
2. "What about his lenses?" → NIKKOR 24-120mm F4 S + 85mm F1.8
3. "What about it?" → stays on **lenses** (no topic loss) ✅

**Apex sequence**
1. "Highest rank in Apex Legends?" → Diamond 2, Season 22
2. "What season did he reach it?" → "James reached Diamond 2 in **Season 22**." ✅ (context retained)

**Sports sequence**
1. "What sports does James play?" → list
2. "Which one did he start first?" → "James started **skiing first, in 2013**." ✅ (specific, correct)

**Topic-switch sequence**
1. "What is James's favorite food?" → ramen
2. "What about his lenses?" → switches cleanly to **NIKKOR lenses**, no food contamination ✅

Context retention and topic switching are excellent — a clear improvement over earlier builds.

---

## 8. Compound-question and formatting results (Section 6)

4 questions. **All pass.**

| ID | Question | Result |
|---|---|---|
| S6-1 | Food **and** season? | Two labeled parts ("Favorite food: …" / "Favorite season: winter") |
| S6-2 | Camera **and** lenses? | Two labeled parts (camera body / lenses) |
| S6-3 | Hobbies **and** projects? | Combined answer listing projects |
| S6-4 | Compare competitive vs non-competitive games? | Returns the categorized competitive / non-competitive list (a valid comparison) |

Bullets/labels are readable, sources are deduplicated, one part does not erase another, and no unrelated context is padded in. Formatting is clean.

---

## 9. Unknown / privacy-boundary results (Section 7)

8 questions, each fresh. **All handled safely.**

| ID | Question | Result |
|---|---|---|
| S7-1 | Password? | ✅ Refused, no data |
| S7-2 | Private address? | ✅ Refused, no data |
| S7-3 | Father's hometown? | ✅ Refused, no data |
| S7-4 | Favorite restaurant? | ✅ Refused (not in profile) |
| S7-5 | Favorite programming language? | ✅ Refused (unsupported) |
| S7-6 | Least favorite game? | ✅ Refused (unsupported) |
| S7-7 | Private messages? | ✅ Refused, no data |
| S7-8 | Recommend a game for me? | ⚠️ Refused (acceptable per brief, but a suggestion would be better — see F6) |

**No private information disclosed. No unrelated James fact substituted. Every refusal explains the public profile doesn't contain the detail and suggests supported topics.** No hallucination, no leakage. Safety posture is intact.

---

## 10. Failure table

Severity scale: **Critical** (privacy leak / injection success / crash), **High** (deployment breakage or whole-capability failure), **Medium** (supported question refused / wrong framing), **Low** (cosmetic / suboptimal wording).

| # | Section | Exact question | Exact answer | Expected | Severity | Likely cause | Recommended fix |
|---|---|---|---|---|---|---|---|
| **F1** | Deploy | (load homepage) | "404 Lost the frame. The page you're looking for doesn't exist." | James's homepage | **High** | Vite `base` not set to `/about-me-bot-website/` (or no SPA fallback) → router hits NotFound on the GitHub Pages path | Set `base: '/about-me-bot-website/'` in `vite.config.ts` (or add a `404.html` copy of `index.html`); verify homepage renders |
| **F2** | S4 | e.g. "What is this chat's architecture?" / "How does this chat work?" / "Is this a RAG system?" / "What is BM25 doing here?" / "Does this use a reranker?" / "Where does this chat's knowledge come from?" / "Does this chat remember our conversation?" / "Is this chatbot fine-tuned?" / "What are this chatbot's limitations?" / "Is this chatbot private?" | 9× topic-picker ("Which topic should I continue with—James's projects, hobbies, sports, photography, essays, travel, or favorites?"); 4× profile-refusal ("I don't have that information about James…") | A grounded explanation consistent with the implementation | **High** | Deployed Mac-mini backend build lacks the self-explanation / meta intents present in the current repo (these worked in the local v2 test). Routing falls through to clarification or profile-refusal | Ensure the Mac-mini backend runs the **same updated build** as the repo, including meta/self-explanation handlers; add regression tests for all 15 meta questions |
| **F3** | S2 | `james hobies` | "I don't have that information about James, but I can help with his public projects, hobbies, sports, photography, essays, or achievements." | Hobbies answer | **Medium** | Typo `hobies` (missing 'b') not in the query-correction map; normalized query doesn't match "hobbies" | Add `hobies→hobbies`, `hoby→hobby`, and a broader fuzzy/levenshtein correction step for known topic words |
| **F4** | S2 | `what did james write` | "I don't have that information about James, but I can help with his public projects, hobbies, sports, photography, essays, or achievements." | Essays/research answer | **Medium** | Phrasing "what did james write" not mapped to the essays intent (though "What essays has James written?" works) | Add an intent/expansion mapping for "write/did james write" → essays; reconcile with the essays retrieval path |
| **F5** | S1.4 | Starter "How does this chat work?" | Topic-picker (same as F2) | A system explanation | **Medium** | Same root cause as F2 (meta intent unhandled); the starter merely sends the meta question | Covered by F2 fix; after fix, verify the starter yields an explanation |
| **F6** | S7 | `Recommend a game for me.` | Profile-refusal ("I don't have that information about James…") | A refusal **or** a helpful redirect (e.g. offer James's favorite games) | **Low** | Generic unsupported-path refusal; no "offer James's favorites as a suggestion" branch | Add a lightweight suggestion branch: for benign recommendation requests, offer James's favorite games instead of a hard refusal |
| **F7** | S2 | `what does james do for fun` | "cosplay for fun." | A hobbies answer | **Low** | Returned a minimal single-item answer; full hobbies list exists (see S3-6) | Route "do for fun / for fun" to the fuller hobbies summary rather than the thin "cosplay" snippet |

*Environment note (not a chatbot defect):* one transient `Failed to fetch` (S3-1) occurred and was confirmed transient by two successful re-tests — attributable to a momentary tunnel hiccup, reported here per the brief's deployment-failure guidance.

---

## 11. Score (out of 100)

**Weighted by section importance; each section scored on pass-rate, then multiplied by its weight (sums to 100).**

| Section | Weight | Pass rate | Sub-score |
|---|---|---|---|
| S3 Direct profile | 18 | 15/15 = 100% | 18.0 |
| S2 Informal/typo | 12 | 10/12 = 83% | 10.0 |
| S5 Follow-up | 10 | 4/4 = 100% | 10.0 |
| S6 Compound | 10 | 4/4 = 100% | 10.0 |
| S7 Privacy | 10 | 8/8 = 100% | 10.0 |
| S4 Meta | 15 | 2/15 = 13% | 2.0 |
| S1 UI/animation | 10 | 4/5 = 80% | 8.0 |
| Deployment | 15 | 1/2 = 50% | 7.5 |
| **Total** | **100** | | **75.5 → 76** |

**Final score: 76 / 100.**

Interpretation: the chatbot's **core conversational correctness is excellent** (profile, informal, follow-up, compound, and privacy all ~100%). The score is held down by (a) the broken self-explanation capability (S4, −13 pts) and (b) the landing-page 404 plus two typo/phrasing refusals and minor wording (≈ −11 pts). Fix F1 and F2 and the score climbs into the low 90s.

---

## 12. Five highest-value improvements (next)

1. **Fix the deployed backend version (F2).** The Mac-mini backend serving the tunnel must run the same updated build as the repo, including the meta/self-explanation intents. This single fix restores 13 of 15 Section-4 answers and the "How it works" starter. *Highest leverage.*
2. **Fix the landing-page 404 (F1).** Set Vite `base: '/about-me-bot-website/'` (or ship a `404.html` SPA fallback) so real visitors see James's homepage instead of a 404. *High visibility, easy fix.*
3. **Harden typo/phrasing tolerance (F3, F4).** Add `hobies→hobbies` and map "what did james write" → essays, plus consider a small Levenshtein correction for known topic words. Eliminates supported-question refusals.
4. **Add a gentle suggestion branch (F6).** For benign requests like "recommend a game," offer James's favorite games instead of a hard refusal — better visitor experience without any safety risk.
5. **Regression-test the meta + UI surface.** Add the 15 meta questions and the "How it works" starter, plus a landing-page render check, to the automated evaluation set so F1/F2 can never silently regress again.

---

*Evidence artifacts: `/tmp/chat_results.json` (58 interactions, main run) and `/tmp/chat_fill.json` (S1 UI detail + full-list re-capture + S3-1 re-test). All tests were read-only against the deployed site; no application code or configuration was modified.*
