# JamChat architecture

JamChat combines deterministic public-profile answers with a small local language model. The website uses React 19, TypeScript, Vite, Tailwind CSS and React Router. FastAPI runs separately from the static frontend.

## Request path

```text
React chat client → FastAPI validation and rate limit
                 → session lock and follow-up resolution
                 → compound clauses and deterministic query plan
                 → BM25 retrieval, optional calibrated reranker
                 → privacy / supported-detail checks
                 → structured public facts or focused evidence
                 → otherwise Ollama → PII and grounding checks
                 → answer status, evidence excerpts and follow-up suggestions
```

Session resolution and retrieval run before answer-policy selection, but a policy refusal does not send the question or evidence to an LLM. Each compound clause keeps its own answer contract. A supported clause can answer alongside a refused clause.

| Area | Implementation and behavior |
| --- | --- |
| Query planning | `generation/query_plan.py` cleans common typos and informal phrases, preserving question operators, negation and time constraints separately from retrieval aliases. Real-word protections and conservative fuzzy matching reduce accidental changes such as brand → band. |
| Interpretation | `generation/intent.py` identifies topics, entities, quantity, comparisons and temporal relations. `generation/evidence.py` maps named subjects to specific source titles, shared with conversation memory. |
| Answer contracts | `generation/contracts.py` distinguishes details a summary can answer from absent details such as a purchase price. `generation/policies.py` handles privacy, unsupported requests, social replies and questions about JamChat itself. |
| Retrieval | `retrieval/tokenizer.py` handles aliases and lexical normalization. `retrieval/bm25.py` scores a wider candidate pool before heading/category bonuses, with stable ties. A content/tokenization fingerprint invalidates stale indexes. |
| Structured answers | `generation/structured_answers.py` formats reviewed facts and focused excerpts. Subject, quantity, exclusions and dates determine the answer. Missing focused evidence cannot be replaced by an unrelated document from the same category. |
| Generation | `generation/answer.py` sends the resolved question and selected public evidence to Ollama. Prior conversation text is used for resolution, not as evidence. Groq is an optional explicitly configured alternative; private-pattern chunks are removed before an external call. |
| Output checks | `generation/formatting.py` checks numbers, factual vocabulary and each sentence, as well as excluding hidden content. PII and refusal normalization run before the response. Verbatim first-person quotes are attributed to James. |
| Frontend | `src/lib/chat.ts` validates responses and owns cancellation, timeouts and duplicate-request prevention. `ChatBot.tsx` renders replies, sources, optional interpretation details and follow-up buttons. |

## Knowledge and provenance

- `kb_extra/*.md`: curated evidence for public profile questions.
- `src/data/content.ts`: website biography, captions, sports, essays and videos.
- `data/profile_facts.json`: reviewed facts used by templates. Every top-level section needs a nonempty `_sources` mapping to existing evidence files. This validates traceability, not semantic correctness; human review remains necessary.
- `data/chunks.json`: generated chunks from the sources above. Export website data first with `node scripts/export_content.mjs`; the chunker consumes the exported JSON. A fresh rebuild currently produces 196 chunks, of which 195 are eligible for public retrieval.
- `data/bm25_index.json`: ignored, rebuildable cache. The API and CLI validate it against the filtered corpus on startup.

The chunker caps overlap at the configured 60-word limit and preserves existing IDs when headings move or sections are inserted. Repeated photo titles are matched by text before assigning remaining IDs, protecting QA references. The public retrieval loader filters excluded content by both ID and text, including after a rebuild.

Source cards are excerpts from retrieved knowledge-base chunks. Structured replies also use the reviewed fact registry; the cards are supporting context, not a sentence-by-sentence citation system. Curated overviews are selections, not exhaustive lifetime inventories. Grade 11 is explicitly dated to the 2025–2026 academic year. Age is reported as a profile statement rather than calculated from an undocumented birth date.

## Conversation and reliability

The browser creates a random session ID per chat. The backend retains up to three answered, sourced turns per session, expires idle sessions after one hour, and bounds the store to 1,000 sessions. Social replies and refusals do not replace the last grounded topic. Same-session turns are serialized. References to numbered items resolve against the displayed answer; ambiguous references to an entire list ask for clarification.

Memory and rate limits are per process. Restarting loses sessions; multiple workers would require a shared store or sticky routing. No durable transcript database is added. Resetting the widget cancels the client request and rotates the ID; it does not delete the old server session immediately, which instead expires normally. An already running model call may finish server-side, but its late reply cannot appear in the new chat.

The model path allows two simultaneous calls per process. Ollama uses temperature 0, a 4,096-token context and at most 384 output tokens. Compound clauses share a 28-second remaining generation budget; HTTP timeouts bound model calls, not a hard wall-clock deadline for all processing or queued session locks. Empty, malformed and token-truncated Ollama replies become `unavailable` with retry support. Model outages preserve structured fact answers. Deep health checks report model installation/reachability, not a guarantee that the next inference succeeds.

The UI uses a 35-second request timeout, guards rapid duplicate sends, supports IME composition, restores focus on open/reset/close and limits the panel to the dynamic viewport. It renders a restricted set of links, lists, emphasis and code without raw HTML. A rate limit, an offline API and an unavailable model have distinct handling.

## Evaluation and rollback

```bash
node scripts/export_content.mjs
.venv/bin/python -m backend.ingest.chunker
.venv/bin/python -m backend.retrieval.bm25
.venv/bin/python scripts/validate_profile_facts.py
.venv/bin/python -m pytest -q
npm run typecheck
npm test
npm run build
```

`data/evaluation_questions.jsonl` supports offline regressions. `data/live_evaluation_questions.jsonl` checks the HTTP path, including structured facts and product information. `data/generative_evaluation_questions.jsonl` specifically exercises model synthesis. `scripts/evaluate_live_chat.py` uses fresh session IDs for each independent case and run to avoid contaminated reruns.

`QUERY_PLANNER_ENABLED=false` bypasses API retrieval planning for comparison; it does not disable privacy policies or all intent handling. Restart after changing it. The API exposes normalized wording and planner diagnostics. `RERANKER_ENABLED=false` remains the production default. No model weights or dependency versions were changed by this review.

Rule-based interpretation and lexical grounding have limits: novel phrasing can still be misunderstood, and word overlap cannot prove entailment. Changing the model or enabling the experimental reranker needs fresh behavior evaluation and threshold calibration. The bounded fixtures should grow from actual visitor failures rather than an unbounded collection of speculative rules.

## Curated navigation actions (September 2026)

`data/chat_destinations.json` is shared by Python and React. A navigation reply
returns an additive `actions: string[]` of destination IDs, never model-generated
URLs. Old responses without actions continue to work; the frontend ignores
unknown IDs and only renders supported routes or allowlisted HTTPS destinations.
Actions are distinct from sources and suggested questions.

Navigation interpretation runs before canonical question rewriting, with privacy,
hidden-content and unsupported-detail guards. It recognizes page, curated-photo,
music and football destinations. Ordinary successful sourced answers can also
carry relevant actions. Session-local destination subjects support explicit
navigation follow-ups; ambiguous subjects prompt clarification. A navigation
subject change clears unrelated factual context, and a fresh session clears both.

Internal cards use React Router (including its deployment basename), close the
widget while retaining its draft/transcript, and focus the destination heading.
The route scroll handler waits for lazy page content and supports hashes and
browser history. `/photography#authors-choice` targets the existing featured
selection. Its count is read from `data/content_export.json`; regenerate that
export when photo selections change. If it is missing, JamChat explicitly cannot
verify the picks and offers the general gallery instead.

External cards open a new tab with `noopener noreferrer`. The favorite song has
verified YouTube/Spotify links; other documented artists have explicitly labelled
search links. No runtime browsing, service credentials, embeds or autoplay are
introduced. Real Madrid/CR7-era preference provenance is recorded in the public
favorites evidence file; no current-roster claim is inferred.

The build regenerates `data/photo_dimensions.json` from JPEG thumbnail headers
using `scripts/export_photo_dimensions.mjs`. These intrinsic image sizes reserve
gallery space so lazy image loading does not displace an anchor destination.
