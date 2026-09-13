# JamChat review and improvements

Review completed 7 September 2026. Changes remain local; no commit, push, publication, model installation or production-service restart was performed. Workbuddy and Claude audit files were left untouched.

## Findings and changes

| Finding | Improvement |
| --- | --- |
| Topic canonicalization sometimes erased the requested detail, turning a price, reason or timing question into a generic overview. | Preserve the semantic question and its operators separately from the retrieval query. Add conservative absent-detail rules, focused evidence selection and regressions for informal wording and typos. |
| Fuzzy correction could turn legitimate words such as brand or grades into unrelated topics. | Protect real modifiers, require the same initial letter and tighten the similarity cutoff; retain explicit common typo aliases. |
| Non-competitive games were also detected as competitive; still playing guitar was treated as stopping. | Correct qualifier boundaries, continuation/cessation interpretation, exclusions, counts and sport chronology. |
| Specific projects, papers and subjective questions often received broad summaries. | Share a small subject-to-evidence map between planning, retrieval context and memory. Named research questions retain their subject rather than becoming questions about JamChat’s architecture. More specific research details reach generation instead of an overview template. |
| A father’s hometown question incorrectly returned James’s biography in live evaluation. | Extend the existing family-information refusal policy to ordinary family terms. Preserve privacy decisions through normalization. |
| Follow-ups lost a specific sport or selected the wrong numbered project; thanks could overwrite the subject. | Record only sourced profile answers, resolve ordinals from the actual displayed list, retain concrete entities and clarify ambiguous list references. Serialize same-session turns and remove duplicate compound history. |
| Generated answers could mix a valid paragraph with an unrelated claim, or copy first-person quotes as if the bot were James. | Check individual sentences as well as overall vocabulary and numbers. Attribute verbatim first-person quotes. Use a concise prompt that avoids repetitive concluding sentences; retain strict refusal on failed grounding. |
| Optional ML imports burdened the default API and CLI. | Load the reranker only when enabled. Both entry points use the current public BM25 cache and can operate without ML packages. |
| Model failures could expose raw excerpts as apparent answers; empty or truncated responses were not properly handled. | Return retryable unavailability, validate Ollama payloads, cap generation output/concurrency, and share a generation budget across compound clauses. Structured facts remain available during model outages. |
| A cached index could remain stale when timestamps were preserved, and rebuilding the corpus could break QA/source IDs. | Fingerprint actual indexed tokens and public filtering, make score ties stable, preserve existing chunk IDs, and keep overlap within the chunk limit. |
| Website-content export failed outside Vite. | Transpile the pure data module with the existing TypeScript dependency and supply its asset base explicitly. Rebuild the corpus, including 17 previously unindexed public photo-caption chunks. |
| Several fact sections lacked evidence mappings, and Grade 11 was presented as current. | Require source mappings for every registry section, add the missing mappings, and retain the documented 2025–2026 date for grade statements. Photo-location overviews explicitly give examples. |
| Resetting chat allowed an old request to append into the new conversation; rapid sends could duplicate requests. | Extract a cancellable chat client, rotate session IDs on reset, discard late responses and guard synchronous duplicate sends. Validate response shapes and distinguish rate limits, network failures and model unavailability. |
| Small screens, keyboard input and formatting needed attention. | Widen answer bubbles, wrap long text, constrain the panel to the dynamic viewport, guard IME composition, restore focus, add accessible labels, support restrained inline formatting, and make interpretation/source details collapsible. |
| Deployment documentation mixed legacy multipage serving with the React SPA and described model outages inaccurately. | Document actual build-time API/base configuration, legacy route limitations, shallow/deep health, optional ML dependencies, single-worker memory and tunnel assumptions. Add frontend type and client checks before the existing Pages build. |

## Verification

- Baseline backend: **171 tests passed** before edits.
- Final backend: **236 tests passed**, including privacy, query contracts, focused retrieval, follow-ups, compound answers, grounding, malformed model payloads, capacity, public filtering, stable IDs and optional-dependency isolation.
- Frontend: **6 client tests passed**; TypeScript check passed. Tests cover cancellation and late replies, duplicate sends, timeouts, HTTP 429 versus HTTP 200 unavailability, malformed responses and display helpers.
- Existing live API corpus: **22/22 passed**, with no false refusals or unexpected answers on those cases.
- Separate Ollama corpus: **8/8 passed**; repeated final run **16/16 passed**. All repeated cases used the generated-answer path. Local median latency was about **2.5 seconds**, approximate p95 **3.9 seconds**. This is a small warm-model sample, not a production performance guarantee.
- The initial open-ended runs exposed false refusals and unattributed first-person quotations. The final prompt and quote-attribution behavior were checked against the actual installed `qwen2.5:3b` model; the grounding threshold was not relaxed.
- Production frontend build passed. A separate GitHub Pages build verified the repository base path and injected API origin in the CSP. The normal build’s `404.html` matches `index.html` for the existing SPA fallback.
- Profile-fact validation, unique chunk IDs, public filtering, CLI smoke test and whitespace/diff checks passed. Rebuilt corpus: **196 total chunks, 195 public retrieval chunks**.
- Browser checks used the production build against a separate API on port 8001: informal camera question, expanded evidence, unsupported camera-cost follow-up, tennis → thanks → start-date follow-up, mobile layout, and reset during model generation. Test services were separate from the deployed backend.

The saved live evaluation reports are machine-local under `/tmp/jamchat-live-final.json` and `/tmp/jamchat-generative-final-repeated.json`. The test questions and evaluator are in the repository so these checks can be repeated.

## Remaining limits and maintenance

1. **Interpretation is explainable but rule based.** Unseen phrasing and complex references can still fail. Add visitor-derived cases before broadening the rules. No embedding service, query-interpreter model or unvalidated reranker was introduced.
2. **Grounding is a lexical safeguard, not a proof of entailment.** It can reject sound paraphrases and miss unsupported claims that reuse source vocabulary. Keep the public profile narrow and evaluate model or prompt changes with both supported and unanswerable cases.
3. **The fact registry duplicates curated source data.** Source mappings establish file-level traceability; they do not automatically verify facts. Source cards are supporting retrieved excerpts, not citations for every sentence of a structured answer. Source and registry updates must be reviewed together.
4. **Profile data has a time boundary.** Grade 11 is dated; age remains a statement from the published profile. Do not infer a new grade, age, university admission, recent purchase or personal relationship without updated public evidence.
5. **Deployment remains a single-process service.** Conversation history, locks, concurrency slots and rate limits are local to one process. A restart loses sessions. A shared store or sticky routing would be needed before adding workers. The Cloudflare client-IP header assumes the API is reachable through the trusted tunnel/local boundary.
6. **The public API hostname must stay aligned with the frontend build.** A Quick Tunnel address may change after restart. A stable named tunnel would avoid that operational problem, but changing public hosting was outside this local implementation pass.
7. **Health and timeouts have practical limits.** A deep health check confirms the model is listed, not that inference will succeed. The generation budget is not a hard deadline for queued session locks or all server computation. Browser cancellation discards a late answer but cannot guarantee an already running Ollama computation stops immediately.

See [the architecture](CHATBOT_ARCHITECTURE.md) and [deployment guide](DEPLOYMENT.md) for commands, configuration and rollback behavior. No dependency versions, model weights or public hosting configuration were changed.
