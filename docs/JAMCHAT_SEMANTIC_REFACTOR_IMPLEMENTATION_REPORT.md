# JamChat semantic refactor implementation report

Date: 2026-09-13

## Scope and constraints

This report covers the deterministic implementation of `docs/JAMCHAT_SEMANTIC_REFACTOR_PLAN.md`. The existing dirty worktree was inspected first and preserved. The protected Workbuddy and Claude audit artifacts were not opened or modified. No commit, push, deployment, hosted model call, model download, provider change, or Ollama replacement was made. “DeepSeek” in the plan was treated as the coding-agent reference to GPT-5.6 Luna; the optional model interpreter was deliberately deferred.

The initial local baseline observed before this work was 264 backend tests, 14 frontend tests, and a passing TypeScript check. The first reproduction stage added a 22-case contrast suite covering wrong-object and wrong-relation behavior. Those cases initially failed against the old pipeline and now pass in `tests/test_semantic_contract.py`.

## Staged changes

1. Added a data-driven semantic contract with immutable original wording, subject, domain, relation, object type, constraints, response mode, context resolution, antecedent, supporting spans, provenance, and confidence.
2. Kept retrieval expansion separate from the contract. Shared relation/object patterns and a small reviewed alias vocabulary now handle fragments, informal wording, ordinary typos, and follow-ups across the public domains.
3. Added positive evidence capabilities and contract-filtered candidates. Unknown or unsupported relationships refuse specifically before a related document or formatter can substitute a different fact.
4. Added contract-aware structured rendering, generated-answer envelopes, evidence-ID checks, grounding checks, and content-level contract relevance validation. The model’s self-declared relation is not trusted by itself.
5. Unified bounded conversation state for contracts, relations, object types, evidence, displayed items, and destination IDs. Retrieval-only expansions no longer rewrite the user’s requested relation. Ordinals, typed references, bare navigation references, social turns, and genuine ambiguity are handled at the same boundary.
6. Routed actions through the resolved contract and approved destination catalog. The existing API shape remains unchanged: status, answer, sources, suggestions, and destination-ID actions are retained.
7. Added the temporary `SEMANTIC_CONTRACT_ENABLED` rollback switch. When set to `false` and the service is restarted, the API removes contract-aware navigation/gating while retaining the established query normalization.

## Representative traces

| Request | Previous failure class | Current contract and result |
| --- | --- | --- |
| `favorite picture` / `favoirate picture` | Broad photography retrieval could drift toward equipment, or bare text could take a different navigation path. | `photography / favorite / photograph`; returns qualified “curated photo picks,” excludes camera facts, and offers `authors-choice`. |
| `camera he uses` | Photo-related evidence could be treated as a general photography answer. | `photography / uses / camera`; returns the camera evidence and `photography`, never a favorite-photo claim. |
| `football player he likes` / `favorite footballer` | A high-scoring sports summary could substitute Real Madrid, a position, or Cristiano Ronaldo. | `sports / likes|favorite / athlete`; no supported capability exists, so JamChat refuses without team/position content or actions. |
| `team he supports` vs. `where does he play on the pitch` | Team and position shared the sports retrieval space. | Separate `team / supports` and `position / playing_position` contracts select Real Madrid evidence/actions versus sports-position evidence. |
| `song he likes`, `artist he listens to`, `favorite band` | Music entities could collapse into one broad preference. | Separate song, artist, and band object types with their respective approved catalog actions. |
| `how he learned coding` vs. `what he built with Python` | Learning-method and project evidence could be merged. | Separate `projects / learned_by / method` and `projects / created / project` contracts and formatters. |
| `When did he start?` after tennis or guitar | Retrieval rewrites and pre-resolution navigation state could be reused as the requested relation. | Follow-up inherits the displayed subject/object and resolves to `started`; the evidence remains scoped to tennis or electric guitar. |
| `Take me there` after a photo answer | Navigation could independently reinterpret the raw phrase. | Bare navigation consumes the prior destination contract; typed song/artist references retain their typed object, and multiple unresolved destinations still clarify. |

Intentional public wording changes are limited to semantic safety: a photo preference is described as a curated selection rather than a single proven favorite; an undocumented favorite athlete and undocumented paper limitations receive the standard specific refusal; unavailable runtime errors remain distinct from missing profile facts. Flappy Bird is filtered from chatbot retrieval and is asserted absent from evaluated answers and sources.

## Evaluation corpus and results

The new single-turn corpus contains 34 phrasing groups and 238 variants across achievements, contact, education, favorites, music, photography, projects, sports, and travel. Nine groups (63 cases, 26.5%) are marked holdout. The conversation corpus contains 30 sequences, including 10 holdout sequences.

Deterministic results:

- Contract interpretation: 238/238 (100%) matched the annotated subject, domain, relation, and object type.
- Answerable holdout support: 56/56 (100%), with eligible evidence intersecting the reviewed expected-title set in each case.
- Missing-information holdout handling: 7/7 (100%) refused without an eligible capability; these cases are not included in supported-answer success.
- Holdout interpretation by domain: achievements 7/7, contact 7/7, education 7/7, favorites 7/7, music 7/7, photography 7/7, projects 7/7, sports 7/7, travel 7/7.
- Conversation transitions: 30/30 sequences passed, including all 10 holdout sequences.
- Contrast and corpus assertions: 22 contrast cases plus 238 single-turn assertions passed; the suite checks evidence eligibility, status, forbidden substitutions, actions, sources, and absence of Flappy Bird rather than phrase presence alone.
- False refusals or unnecessary clarifications on answerable holdout cases: 0/56.

The missing sports holdout is deliberately the undocumented individual-athlete preference. Its 7/7 safe refusals demonstrate missing-fact behavior, not supported-answer quality.

## Verification

Completed commands and results:

- `./.venv/bin/pytest -q tests/test_semantic_evaluation.py`: 240 passed.
- `./.venv/bin/pytest -q`: 533 passed.
- `npm test`: 14 passed.
- `npm run typecheck`: passed.
- `./.venv/bin/python scripts/validate_profile_facts.py`: profile facts valid.
- `npm run build`: production root build passed.
- `VITE_BASE_PATH=/about-me-bot-website/ npm run build`: GitHub Pages base-path build passed, including SPA fallback copy.
- `git diff --check`: passed.
- `SEMANTIC_CONTRACT_ENABLED=false ...` rollback smoke: passed; navigation remained usable and stored no semantic contract.

The browser smoke check rendered the local homepage and JamChat dialog, including the public-profile grounding copy. The interactive chat request could not be completed because the local backend was inaccessible from the browser/sandbox namespace: the attempted preview bind hit `listen EPERM`, and the existing process on port 8000 was not controllable from this task. The browser check therefore does not claim interactive action, mobile, focus, or draft/history success. Frontend tests still cover route basename handling, actions, focus/history-related state behavior, malformed responses, rate-limit/unavailable distinctions, and rendering safeguards.

## Runtime, model, and latency status

The configured local environment uses `LLM_BACKEND=ollama` and `LLM_MODEL=qwen2.5:3b`. The sandbox could not see the loopback service, but a host-context read-only probe confirmed that Ollama is running and that both `qwen2.5:3b` and `qwen3:8b` are installed. The current checkout was run on isolated loopback port 8001 and evaluated without writing results or contacting a hosted provider.

The required model-dependent evaluation was run against a saved 20-case fixture, three repeats (60 requests total). The final repeat set produced 45/60 strict passes (75%), 0 unexpected answered responses for refused cases, 3 false refusals, and 0 Flappy Bird leaks. All 60 requests returned HTTP 200; the model was deterministic for most prompts but varied on some repeats. The strict misses were concentrated in four generated explanation prompts: some answers were grounded but omitted a distinctive evidence detail, while the AI-while-studying prompt occasionally refused. Diagnostic hardening runs ranged from 36/60 to 48/60 as parser and prompt changes were applied; this variance is why the final result is reported as a model limitation rather than converted into a deterministic pass.

Fresh deterministic planner timing over 238 cases measured warm-process p50 0.65 ms and p95 0.92 ms. The final local live-model run measured p50 2018.1 ms and p95 3609.0 ms, with observed latency from 689.6 to 5204.0 ms. A pre-change latency baseline and separate cold-start latency were not captured, so the required baseline regression comparison remains unmet. The 20-cases-by-3 live model-repeat gate is now measured but does not meet a 95% strict content target. The optional model interpreter remains disabled/not implemented; no parser latency or variation is reported.

## Remaining limitations and rollout

The parser is deterministic and intentionally bounded by reviewed linguistic patterns and aliases. It is not a claim that arbitrary natural language is solved. Unresolved wording still follows the existing clarification/refusal policies. Live generation is now evaluated, but the local Qwen 2.5 3B run remains below the strict content target and needs either prompt/model-quality work or a reviewed deterministic formatter for the affected explanations. No unsupported factual assertion or Flappy Bird leak was observed in the 60-request run.

For rollback during the review cycle, restart the backend with:

```text
SEMANTIC_CONTRACT_ENABLED=false
```

This disables the new contract-aware gate and navigation boundary in the API while leaving the existing query planner available. Restore or omit the variable to return to the default enabled path. No deployment was performed.

## Completion addendum: evidence-scoped drafts and cross-domain explanations

This addendum supersedes the earlier live-model figures above. It records the
final deterministic hardening performed after that report, without changing the
protected Workbuddy or Claude audit artifacts.

### Changes in this pass

- Model answers now have to be an exact JSON draft with an answer, resolved
  relation, and non-empty cited chunk IDs. The IDs are checked for uniqueness,
  existence, and grounding against the cited chunks only; the service no longer
  assigns synthetic citations to unstructured model text.
- Explanatory relations use sentence-level relevance checks. A fact merely
  adjacent to the subject can no longer supply a causal explanation for a
  separate fact.
- Focused-source access is now an explicit entity/relation allowlist instead
  of permission to answer any relationship about a focused title.
- A narrow, evidence-extractive path returns a complete reviewed sentence for
  a single authorized explanatory source. This preserves coordinated evidence
  such as both documented accessibility mechanisms without relying on local
  model compression.
- A resolved `lists` relationship now authorizes the existing reviewed
  overview renderers even when the visitor phrases it as “how does James
  describe…”. This is relationship-based, rather than a videos-specific
  exception, and prevents a supported multi-video overview from reaching the
  model-draft path.
- Deterministic interpretation now covers view, motivation, reward/interest,
  and game-ability wording. The last is a general games-domain rank relation,
  not an Apex-specific answer exception. Entity-specific retrieval priority is
  retained so the documented CS-inspiration source is not overwritten by a
  broad education-reason expansion.

### Final verification

- `./.venv/bin/python -m pytest -q`: **550 passed**.
- `npm test -- --run`: **14 passed**; `npm run typecheck`, `npm run build`, and
  `git diff --check` also passed.
- The 20-case cross-domain semantic fixture, repeated three times through the
  local API, passed **60/60** (p50 **4.7 ms**, p95 **5.5 ms**). These cases
  intentionally use the deterministic structured-evidence path, so they prove
  end-to-end API behavior but are not evidence of model-draft quality.
- The existing mixed 22-case API fixture, including its two refusal cases,
  passed **22/22** (p50 **4.5 ms**, p95 **5.4 ms**) on a separate fresh local
  rate-limit window.
- `data/live_model_draft_evaluation_cases.jsonl` records 20 answerable
  overview prompts across hobbies, achievements, videos, music, education,
  projects, sports, preferences, games, and writing. Before the final
  overview-rendering correction, all reached the JSON-draft model path; three
  independent fresh-server runs produced **59/60** strict passes after manual
  review. The sole safe `grounding_failed` refusal was a videos overview
  (false refusal **1.7%**), with no accepted unsupported answer, p50
  **6080.6 ms**, and p95 **8983.5 ms**. After the correction, the same fixture
  passed **20/20** end to end: 18 prompts used reviewed structured answers and
  the two favorite-games prompts used and passed the draft path. The previously
  flaky videos prompts were structured, source-scoped answers.

The mixed and model-draft outputs were manually reviewed. The live report's
`unexpected_answers` count is only meaningful where a fixture contains
expected-refusal cases; the model-draft fixture is all answerable, so it must
not be used to claim a general unsafe-answer rate. The regression tests cover
empty/unknown/duplicate citations, unrelated citations, unsupported causal
mixing, broad focused-title access, and the excluded Flappy Bird content.

### Remaining acceptance gaps

The optional model-based *interpreter* remains intentionally unimplemented.
The existing local generator was evaluated, but no pre-change warm/cold latency
baseline was captured for a valid percentage-regression comparison. This pass
also did not add a fresh blind holdout after inspecting the existing corpus or
repeat the browser interaction smoke test. The pre-correction 20-prompt repeat
still verifies the draft validator, but a new 20-prompt repeat that all reaches
the *current* model-routing path would be needed to refresh that exact gate.
Those gates remain unmet; the test, build, deterministic API, and
local-generator results above are the verified scope. No commit, push,
deployment, hosted provider call, runtime-model change, or protected-audit edit
was made.
