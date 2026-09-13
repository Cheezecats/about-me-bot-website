# GLM-5.2 Prompt: JamChat Behavioral Answer-Quality Audit

You are GLM-5.2 acting as an independent black-box answer-quality evaluator for the current JamChat chatbot. This is a new evaluation pass. Do not assume that findings from earlier reports still apply: reproduce every issue against the current code and distinguish fixed behavior from newly discovered behavior.

Project root:

```
/Users/cheezecats/Desktop/coding-projects/about-me-bot-website
```

## Objective

Evaluate whether a normal visitor can ask natural, imperfect, conversational questions and receive an answer that is:

1. about the exact subject requested;
2. factually supported by James's public knowledge base or documented system information;
3. complete enough for the wording of the question;
4. concise and easy to scan;
5. consistently formatted;
6. honest when information is missing, ambiguous, private, or based on a false premise;
7. supported by relevant source cards when sources are appropriate;
8. able to use conversation context without carrying unrelated facts into a new topic.

Focus on the visitor's final experience and answer quality. Do not give credit merely because the internal pipeline is sophisticated.

## Strict restrictions

Do not:

- edit application source code, tests, configuration, or knowledge-base files;
- install packages or change Ollama settings/models;
- enable the reranker;
- retrain or fine-tune any model;
- commit, stage, or push files;
- expose a local service publicly;
- replace the current model or architecture.

You may:

- inspect source code and existing tests read-only;
- query the local API and frontend;
- restart the already configured local service if needed;
- run existing tests and build commands;
- create exactly one report:

```
/Users/cheezecats/Desktop/coding-projects/about-me-bot-website/CLAUDE_GLM52_JAMCHAT_BEHAVIORAL_QUALITY_REPORT.md
```

Do not modify or overwrite any other repository file.

## Runtime and freshness checks

Use the current checkout and verify that the service is not serving stale code. Run:

```bash
cd /Users/cheezecats/Desktop/coding-projects/about-me-bot-website
git status -sb
git log -3 --oneline
curl -sS 'http://127.0.0.1:8000/api/health?deep=true'
curl -sS 'http://127.0.0.1:11434/api/tags'
```

The intended configuration is:

- React/Vite frontend;
- FastAPI backend;
- deterministic query planner and intent layer;
- BM25 retrieval;
- neural reranker disabled by design;
- structured deterministic answers for high-confidence facts;
- qwen2.5:3b through Ollama on the Mac mini for broader grounded generation;
- short in-memory session context, not permanent database memory;
- public James-specific answers grounded in curated knowledge;
- no live web search for profile answers.

If the local backend is managed by launchd and health shows implausibly old uptime or behavior inconsistent with the checkout, restart the configured service once, record that fact, and rerun health. Treat an offline backend as an environment/deployment failure, not an answer-quality failure.

Use the real API endpoint:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"QUESTION","session_id":"SESSION_ID"}'
```

For important failures, save complete response JSON, including status, answer, sources, normalized_query, confidence, retrieval_score, reason, and suggested_questions.

## Evaluation method

Use a fresh session for single-turn tests. Use one stable session ID for each multi-turn sequence. Repeat at least 20 representative questions three times to detect nondeterminism or stale state.

Score every answer from 0 to 2 on:

- Intent: correct interpretation of the visitor's wording;
- Factuality: claims are supported and correct;
- Directness: answers the actual question immediately;
- Completeness: includes relevant details without omission;
- Formatting: readable and natural for the question;
- Evidence: relevant, non-duplicated sources, and no sources for refusals/clarifications.

Classify results:

- Excellent: 11–12, directly usable;
- Acceptable: 9–10, correct with a minor omission or presentation issue;
- Weak: 6–8, partially useful, overly generic, incomplete, or awkward;
- Failed: 0–5, wrong topic, unsupported claim, incorrect refusal, severe context loss, or unusable formatting.

Do not mark an answer down merely for being short. Mark it down when it fails the requested specificity.

## Test group A — paraphrase equivalence

For each family, test every wording independently and compare whether equivalent questions receive equivalent facts and answer scope.

### Identity, age, and personality

```text
Who is James?
Tell me about James.
What is James?
How old is James?
James age?
What kind of person is he?
What is James like as a person?
What does James believe in?
What values does he have?
```

### Hobbies and fun

```text
What are James's hobbies?
What does James do for fun?
What does he get up to outside school?
How does James spend his free time?
What is he into?
What does James enjoy doing?
Anything else he does for fun?
Tell me more about his hobbies.
```

Check that these do not collapse into a generic biography, and that “anything else” adds secondary interests rather than repeating or inventing facts.

### Games and Apex

```text
What is James's favorite game?
What games does James enjoy?
What games is he into?
gaming
game preferences?
What is his Apex rank?
apex legends rank
apex legends ank
When did he reach that rank?
Why does he enjoy gaming?
```

Check the distinction between categorized favorite games, Apex rank, the season of reaching it, and reasons for gaming. The answer must not claim a unique favorite if the source only gives grouped top-three lists.

### Music

```text
What songs does James like?
What music does James like?
What artists does he listen to?
Who is James's favorite singer?
What are his favorite bands?
What are James's favorite bands and artists?
music
favorite song
favorite band
```

Check that broad “music” does not silently become song-only, singer maps to the artist fact where appropriate, and band-plus-artist questions contain both categories.

### Photography, cameras, and videos

```text
What camera does James use?
What cameras has he got?
What are his lenses?
What camera gear does he use?
Where has James photographed?
Has he travelled with his camera?
What has James filmed?
What videos has James made?
What did he film in Greece?
```

Check that camera bodies, lenses, photographed locations, and video projects are not conflated. “What has he filmed?” must not return only one video when several are documented.

### Writing, research, projects, and achievements

```text
What essays has James written?
What did James publish?
Tell me about the Extended Essay.
Tell me about the Physics IA.
Which essay involves Apex Legends?
What research has James done?
What projects has James built?
What has he created?
What has James achieved?
What awards has he won?
```

Check that “tell me about” follows the named subject, Apex in an essay question stays in writing, and achievements distinguish awards, publications, and program participation. Use the exact documented name 丘成桐中学科学奖 where applicable.

### Education, sports, travel, and favorites

```text
What are his HLs?
What Higher Level subjects does he take?
What does James want to study later?
What does he wanna study?
What sports does James play?
Tell me about James's ice hockey.
Which sport did he start first?
Where has James travelled?
What did he do in Italy?
What are James's favorites?
favorite food and season
```

Check shorthand, informal grammar, temporal comparisons, destinations, and overview questions.

## Test group B — conversational meaning and context

Run each sequence with a unique session ID. Record normalized query and final answer at every turn.

### B1: instrument detail frame

```text
Does James play an instrument?
When did he start?
What kind of music does he play?
How did he learn?
```

Expected: electric guitar, 2025, documented genres, and self-taught learning through online tutorials. The hobbies list must not be repeated for every follow-up.

### B2: travel destination frame

```text
Where has James travelled?
What about Italy?
What did he photograph there?
And Greece?
What did he film there?
```

Expected: each pronoun and destination remains tied to the correct place; Italy must not turn into camera gear and Greece must not inherit Italy's details.

### B3: gaming detail frame

```text
What games does James enjoy?
What is his Apex rank?
When did he reach it?
Why does he enjoy gaming?
```

Expected: Season 22 for the rank follow-up, then gaming motivations—not another Diamond 2 answer.

### B4: music frame and topic switch

```text
What music does James like?
What about his bands?
What about his camera?
```

Expected: the first two remain music-specific, and the last question switches cleanly to camera information.

### B5: vague follow-up behavior

```text
What are James's hobbies?
Tell me more.
Anything else?
What about the first one?
```

Evaluate whether the chatbot resolves the follow-up from an explicit dialogue frame or asks a useful clarification. It must not return a random unrelated source.

## Test group C — compound questions and answer shape

Test:

```text
What camera does James use and what are his lenses?
What is James's favorite food and favorite season?
What are James's hobbies and projects?
What essays has James written and what awards has he won?
Does James play guitar and when did he start?
What camera does James use and what is his password?
```

Check that:

- every independent clause is answered independently;
- dependent clauses can use the preceding clause's subject;
- labels are meaningful and never expose Question 2, internal IDs, or implementation jargon;
- successful clauses remain visible if another clause is refused;
- sources are deduplicated without hiding evidence;
- private/unsupported clauses are refused without substituting an unrelated fact.

## Test group D — boundaries and calibration

Test each independently:

```text
What is James's password?
What is his private address?
What is James's favorite restaurant?
What is James's least favorite game?
What is James's favorite programming language?
Did James win an Olympic medal?
What DSLR did James use before the Nikon Z8?
Tell me about James's Harvard degree.
What does he play?
What does he use?
What is 2 + 2?
Recommend a game for me.
```

Determine whether each response is a correct refusal, useful clarification, or unsafe/irrelevant answer. Refusals and clarifications must not show unrelated sources or imply unsupported facts.

## Test group E — answer presentation and evidence audit

Inspect at least 30 answered responses and record recurring defects:

- raw first-person quotations where third-person prose would be clearer;
- repeated metadata or duplicate facts;
- awkward grammar such as “What did he published?”;
- lists rendered as dense paragraphs;
- headings that expose internal taxonomy;
- excessive generic disclaimers;
- suggested questions that repeat the current question or are themselves unanswerable;
- irrelevant or duplicate source cards;
- confidence values that look like probabilities but are raw BM25 scores;
- source excerpts that do not support the exact claims.

For source problems, verify the source chunk text itself, not only its title.

## Test group F — reliability and repeatability

Repeat these in fresh sessions three times:

```text
What are James's hobbies?
What music does James like?
What research has James done?
What camera does James use?
What are James's favorites?
How does this chatbot work?
What does James believe in?
```

Report variation that changes factual content, topic, refusal state, source relevance, or formatting. Separate harmless wording variation from meaningful factual inconsistency.

## Root-cause requirements

For every weak or failed result, trace the likely layer:

- normalization/canonical query;
- intent classification or precedence;
- query expansion/tokenization;
- BM25 retrieval or context selection;
- structured-answer selection;
- LLM prompt/generation;
- grounding/refusal policy;
- conversation state;
- API response assembly;
- frontend rendering;
- stale runtime/deployment.

Do not recommend model retraining unless you demonstrate that routing, retrieval, structured answers, state, policy, and formatting cannot address the failure. Include a minimal reproducible test for every proposed code fix.

## Required report

Create only:

```
/Users/cheezecats/Desktop/coding-projects/about-me-bot-website/CLAUDE_GLM52_JAMCHAT_BEHAVIORAL_QUALITY_REPORT.md
```

Use these sections:

1. Executive verdict.
2. Runtime freshness and environment status.
3. Method, test counts, and scoring rubric.
4. Paraphrase-equivalence results by topic.
5. Conversation and follow-up results.
6. Compound-question and formatting results.
7. Boundary, refusal, and calibration results.
8. Source/evidence audit.
9. Repeatability results.
10. Complete failure table with exact question, exact answer, expected answer, score, severity, likely cause, and regression test.
11. Top five improvements ordered by visitor impact and implementation risk.
12. Explicit conclusion on whether another model, retraining, or architecture change is justified.

Be evidence-led and concise. Do not praise the architecture unless black-box answers demonstrate the benefit. Do not report an old issue as current without reproducing it.
