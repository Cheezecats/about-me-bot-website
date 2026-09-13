# DeepSeek implementation brief: answer the intended question across domains

## Assignment and boundaries

You are improving the existing JamChat project at:
`/Users/cheezecats/Desktop/coding-projects/about-me-bot-website`

Implement a cross-domain improvement to interpretation, evidence selection, answer relevance, conversation memory, and navigation. The goal is to understand reasonable human questions—including fragments, typos, informal phrasing and follow-ups—and answer the actual requested relationship. Do not treat this as a patch for “football player he likes” or “favorite picture.”

DeepSeek V4 is the coding agent for this assignment. Do not replace JamChat’s local Ollama runtime, add a hosted model provider, buy services, download models or change deployment architecture without a separate user instruction.

Preserve the existing uncommitted work. Do not modify or commit Workbuddy or Claude audit reports. Do not include Flappy Bird in public answers, sources, suggestions or actions. Do not commit, push or deploy. Do not invent public-profile facts. The documented Real Madrid / Cristiano Ronaldo era preference does not establish a favorite individual player. Featured photographs are curated picks, not proof of a single favorite photograph.

Read repository instructions, current implementation and tests before editing. Create a baseline report using only your own new review document. Record current tool/model availability: unavailable Ollama is a runtime limitation, not evidence that a semantic case passes or fails.

## 1. Diagnose and measure before changing behavior

Trace representative failures through original text, normalization, interpretation, memory resolution, retrieval candidates, formatter selection, generated answer, relevance checks and destination actions. Reproduce the reported failures where possible; distinguish observed results from hypotheses.

Current inspection points:

- `QueryIntent` represents topics, entities and question operators but has no uniform explicit representation of the requested relationship or expected answer type.
- `query_plan.py` uses canonical rewrites plus keyword exceptions to preserve details; intent merging can accumulate entities without resolving conflicts.
- `structured_answers.py` can dispatch using retrieved summary titles or focused subjects. Its checks must establish whether the requested relationship is supported, not merely whether the subject matches.
- `formatting.py` checks lexical overlap and numbers. These checks alone cannot establish that an answer addresses the question.
- `navigation.py` separately interprets questions and uses navigation verbs to enable most destination replies. Bare “favorite picture” can therefore follow a different semantic path from “show his favorite picture.”
- Factual and navigation memory have separate update rules. Audit when context is inherited, cleared or made ambiguous.

Read the existing human-question, navigation, runtime-resilience, frontend and live-evaluation tests. The last reported baseline was 264 backend tests, 14 frontend tests and 22 live cases; establish the actual current baseline rather than assuming those counts still apply.

## 2. Introduce one shared semantic contract

Extend or replace the existing intent representation incrementally. Produce one validated contract per clause, consumed by factual answering and navigation. Avoid a second independent classifier hidden inside either output path.

Minimum internal fields:

- `subject`: the person or concrete entity being discussed, with a stable ID where known.
- `domain`: broad retrieval context such as photography, sports, music or education; never sufficient by itself to authorize an answer.
- `relation`: the requested property, such as favorite, uses, plays, position, supports, created, started, located, reason, method, result or limitation; include an explicit unresolved value.
- `object_type`: photograph, camera, athlete, team, song, artist, band, project, paper, subject, place, date, explanation or other/unresolved.
- `constraints`: quantity, rank/superlative, exclusions, negation, comparisons and time bounds, preserving distinctions between favorite, liked and used.
- `response_mode`: information, navigation, or both. A different mode must not silently change the subject or relation.
- `context_resolution`: explicit, inherited, ambiguous or unresolved, with the antecedent ID when inherited.
- `original_text`, supporting spans and interpretation provenance; confidence may be logged but must not be treated as proof of correctness.

Keep the original question immutable. Separate retrieval expansion from semantic interpretation. A broad retrieval query may find candidates, but it must never overwrite the contract’s object type, relationship or restrictions.

Use shared linguistic patterns for relations and sentence fragments, plus a small reviewed entity/alias vocabulary. Do not build a growing list of complete example questions. Recognize “player he likes,” “which athlete is he into,” and “favorite footballer” as related requests while preserving the difference between liking someone and naming a single favorite.

Explicit current-turn subjects and constraints override inherited context. Conflicting interpretations remain unresolved; do not union incompatible entities and arbitrarily answer one of them.

An optional semantic parser may supplement this deterministic layer for unresolved wording. If implemented, use the existing local model behind `SEMANTIC_PARSER_ENABLED=false` initially. Require schema-valid output, allowlisted fields, supporting input spans, and no invented facts or URLs. Permit at most one parsing call, with a six-second sub-budget inside the existing overall request deadline and shared model concurrency limit. Invalid output, timeout or disagreement must yield deterministic handling or a focused clarification. Enable only after separate held-out and latency evaluation; do not make it a prerequisite for documented common questions.

## 3. Select evidence and render answers by relationship

Build a small evidence adapter over the existing public profile facts, reviewed documents and website data. Preserve the current sources of truth; avoid copying the entire profile into another manually maintained database.

Each answerable capability must identify its subject/object types, supported relationship and constraints, source references, and whether it is an exact fact, documented selection or explanatory evidence. Add mappings for all existing public domains: biography, photography, videos, music, hobbies, sports, gaming, projects, research/writing, education, travel, preferences/personality and contact.

Distinguish these situations:

- **Clear intent and supporting evidence:** answer directly.
- **Clear intent, missing fact:** state specifically what is undocumented. Do not ask the visitor to reword a question whose meaning is already understood.
- **Ambiguous intent:** ask one short question identifying the competing subjects or meanings.
- **Runtime failure:** report unavailability; do not disguise it as a missing profile fact.
- **Related documented alternative:** offer it explicitly as an alternative, without claiming it answers the missing fact.

Keep BM25 initially. Rank or filter candidates against the contract before they can authorize a formatter. A high sports score cannot authorize a position answer to a player-preference request. A photography document cannot authorize a camera answer to a photograph-preference request.

Replace broad default permission with positive formatter eligibility. A formatter declares what relationship, object type and constraints it can satisfy. Unknown eligibility means it cannot render a factual answer. Apply the same eligibility check to every fallback; an LLM refusal must not trigger an unrelated summary.

For generated explanations, supply only eligible evidence and the immutable contract. Require an internal structured draft containing the proposed answer, answered relation and cited evidence IDs. Validate schema, evidence IDs, factual grounding, requested constraints and semantic relevance before returning it. Do not accept the model’s self-declared relation as sufficient: check the content against the permitted evidence/capability. Retain useful existing lexical/number checks as additional safeguards, not the final relevance test. Reject a draft when relevant support cannot be established; do not introduce a second unbounded LLM “judge” loop.

Preserve nuanced, sourced explanations where the documents support them. Do not obtain better safety metrics simply by refusing every difficult question.

## 4. Unify memory, navigation and answer presentation

Track the last resolved subject, relation, eligible evidence, displayed ordered items and destination IDs in one bounded conversation context. Retain explicit ambiguity when an answer lists several candidates. Social turns should not erase a useful antecedent; a new subject must not inherit an unrelated prior relation.

Resolve pronouns and ordinals against the actual displayed items, including shortened lists. Distinguish a prior favorite song from an artist, a football team from an athlete, and a project from a related research paper. Test factual-to-navigation and navigation-to-factual transitions. Session reset and expiry must clear all context consistently.

Navigation actions consume the same resolved contract and approved catalog as the answer. They must not independently reinterpret raw text. Bare “favorite picture” should explain the existing curated selection and offer its link just as an explicit request to see it does. A camera answer may offer the gallery as additional exploration only when appropriate, never as a substitute for an unsupported requested fact.

Keep the public API compatible: retain current status, answer, sources, suggestions and destination-ID actions. Put detailed interpretation traces behind a development-only diagnostic option; do not expose internal reasoning, raw prompts or visitor logs in the public UI. No endpoint for arbitrary URL execution.

Use concise, question-specific missing-information and clarification messages. Preserve source display, safe Markdown, mobile navigation, focus behavior, base-path compatibility, and conversation/draft preservation. Do not redesign the frontend or add embeds/autoplay for this task.

## 5. Build an evaluation suite that measures generalization

Create a data-driven suite of at least 200 single-turn cases across the public domains and 30 multi-turn sequences. Include answerable cases, clearly missing facts and genuine ambiguities. Cases must specify expected subject/relation/object type, evidence eligibility, acceptable answer content, forbidden substitutions, status and actions—not just words that should appear.

Cover fragments, complete questions, typos, informal wording, unusual word order, mixed clauses, varying specificity, negation, comparisons, quantities and time references. Use ordinary natural phrasing, not only synthetic misspellings. Include non-English forms already supported by the project without claiming new language coverage.

Essential contrast cases:

| Request | Required distinction |
| --- | --- |
| favorite picture / favoirate picture / photograph he likes most | Curated photo picks with qualification; never camera specifications |
| camera he uses / what shoots his photos | Camera/equipment; never declare it his favorite photograph |
| football player he likes / favorite footballer | Individual athlete preference; do not substitute position or team, and do not infer a favorite player |
| team he supports / favorite football club | Documented Real Madrid preference; not James’s soccer position |
| where does he play on the pitch | Playing position, not geographic location or supported club |
| song he likes / artist he listens to / favorite band | Track, artist and band are distinct types |
| how he learned coding / what he built with Python | Learning method versus project evidence |
| project name / paper method / research limitations | Named artifact, methodology and limitations are distinct requests |
| subjects he takes / subject he likes most / why he likes it | Enrollment, preference and documented reason |
| places he visited / favorite place / where he photographed | Travel history, preference and photography location |
| when he started / how long he has played / whether he still plays | Start date, duration and current participation are not interchangeable |
| camera price / guitar brand / reason for a preference absent from the profile | Specific missing information; no generic biography as replacement |

Add metamorphic tests: paraphrases should preserve the contract; replacing photo with camera, player with team, or song with artist must change it appropriately. Adding “why,” “not,” “before” or “one” must preserve that restriction instead of returning the original answer unchanged.

Reserve at least 25% of the new single-turn cases and ten conversation sequences as a frozen holdout before implementation. Separate phrasing patterns and conversation structures, not only one-word changes. Do not tune against the holdout after inspecting failures; preserve it and report results honestly. Later fixes require a fresh additional blind set.

Acceptance criteria:

- Existing meaningful behavioral contracts stay passing; do not silently weaken assertions. Document and justify any correction to an old test that encoded the wrong behavior.
- Zero wrong-object/wrong-relation answers on the explicit contrast suite, and zero excluded/private content leaks.
- At least 95% correct subject/relation/object interpretation and at least 95% supported-answer success on the new held-out single-turn cases, reported separately by domain. Missing-information cases must not inflate supported-answer success.
- False refusals or unnecessary clarifications on answerable holdout cases at or below 5%; all ten held-out conversation sequences satisfy their annotated context transitions.
- Report unsupported factual assertions separately. Automated phrase checks alone are insufficient: manually review every held-out failure and all generated answers in the smaller runtime evaluation set.
- Repeat a representative set of at least 20 model-dependent cases three times. Report variation, relevance failures, timeouts and latency. Mock-based passes are not proof of live model quality.
- Preserve the current overall request deadline and concurrency controls. Measure baseline versus new warm p50/p95 latency; investigate more than 10% regression on the deterministic path. Report cold-start and optional-parser latency separately.

If a gate is missed, state which one and why. Do not claim that all natural language is solved, or lower a target after seeing the outcome.

## 6. Delivery and rollout

Implement in small reversible stages: baseline/contrast tests; shared contract; evidence eligibility and rendering; unified navigation/memory; optional parser experiment. Keep the existing pipeline behind a temporary `SEMANTIC_CONTRACT_ENABLED` feature flag during development. Run the new path in local evaluation, then make it the default only after the acceptance gates pass. Keep the flag for rollback through one review cycle; avoid indefinite duplicate implementations.

Run backend/frontend tests, profile validation, type checking, production build, existing live evaluations and the new suite. Verify root and GitHub Pages base-path builds. Browser-check photo-pick and music actions, ambiguous follow-ups, mobile rendering, heading focus and preserved draft/history. Ensure a direct/unknown question cannot bypass grounding through navigation or a fallback branch.

Deliver working local changes plus an implementation report containing: architecture changes, before/after representative traces, all test commands and results, per-domain and holdout metrics, runtime/model availability, latency, remaining limitations, and exact rollback instructions. Document any intentionally changed public wording/status. Do not touch protected audit reports, commit, push or deploy.
