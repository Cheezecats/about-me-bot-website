# GLM-5.2 Prompt: JamChat Answer-Contract and Multilingual Quality Audit

You are GLM-5.2 performing a narrowly focused, black-box answer-quality investigation of the current JamChat chatbot.

This is intentionally different from a general routing, architecture, or follow-up review. The unresolved question is whether JamChat preserves the exact contract of a visitor's question: requested operator, scope, quantity, time, entity, language, and certainty. Earlier tests covered canonical topics and a few follow-up sequences; they did not establish that these answer contracts are reliable across the current implementation.

Project root:

~~~
/Users/cheezecats/Desktop/coding-projects/about-me-bot-website
~~~

## Core research question

When two questions concern the same topic but ask for different details, does JamChat answer the requested detail—or silently substitute a nearby fact, broaden/narrow the scope, or make an unsupported inference?

Do not assume these behaviors are currently broken or fixed. Test them against the current runtime.

## Restrictions

Do not:

- modify source code, tests, data, configuration, prompts, or deployment files;
- install packages or change Ollama settings/models;
- enable the reranker;
- retrain or fine-tune anything;
- commit, stage, or push;
- expose a local service publicly.

You may inspect files read-only, query localhost, run existing tests/builds, and restart the configured local backend if needed.

Create exactly one file:

~~~
/Users/cheezecats/Desktop/coding-projects/about-me-bot-website/CLAUDE_GLM52_JAMCHAT_ANSWER_CONTRACT_REPORT.md
~~~

Do not create or modify any other repository file.

## Runtime freshness

Run:

~~~bash
cd /Users/cheezecats/Desktop/coding-projects/about-me-bot-website
git status -sb
git log -3 --oneline
curl -sS 'http://127.0.0.1:8000/api/health?deep=true'
curl -sS 'http://127.0.0.1:11434/api/tags'
~~~

The intended runtime is FastAPI, deterministic planning, BM25 retrieval, structured answers, qwen2.5:3b through Ollama, disabled neural reranking, short in-memory session state, and no live web search for profile answers.

If health shows an old/stale runtime or behavior contradicts the checkout, restart the existing launchd-managed service once, record old/new uptime, and retest. Do not classify stale code as an answer-quality defect until retesting.

Use the real API:

~~~bash
curl -sS -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"question":"QUESTION","session_id":"SESSION_ID"}'
~~~

For failures, record the complete JSON response, including status, answer, normalized_query, confidence, retrieval_score, reason, suggested_questions, and source titles/chunk IDs.

## Ground truth and scoring

Inspect current public facts in data/profile_facts.json, data/chunks.json, relevant kb_extra files, and structured-answer code. Do not infer a fact merely because it sounds plausible. If the requested detail is not documented, refusal or clarification is correct.

Preserve exact spelling for:

- 丘成桐中学科学奖
- 君の神様になりたい
- Bang Dream Mygo
- NIKKOR 24-120mm F4 S
- NIKKOR 85mm F1.8
- CS:GO/CS2
- Apex Legends
- Uniswap V3

Score each answer from 0–2 on:

- Operator: correct what/where/when/why/how/which/who interpretation;
- Entity binding: correct he/it/there and named-entity binding;
- Scope: singular/plural, all/any, first/highest/top-three, and comparison;
- Factuality: exact and grounded claims;
- Calibration: safe refusal or correction for unsupported assumptions;
- Presentation: direct, readable formatting;
- Evidence: supporting, non-duplicated sources and no sources for refusals.

Maximum is 14. Classify 13–14 excellent, 10–12 acceptable, 7–9 weak, and 0–6 failed. A true fact still fails if it answers a different question.

## Test group 1 — operator and scope preservation

Run independently in fresh sessions:

~~~text
What camera does James use?
Which camera does James use?
What model camera does James use?
What lenses does James use?
Where has James photographed?
When did James start playing electric guitar?
Why does James enjoy gaming?
How did James learn electric guitar?
Who is James's favorite artist?
Which sport did James start first?
How many sports does James play?
~~~

Then test singular/plural and quantifiers:

~~~text
What is James's favorite game?
What are James's favorite games?
Name one competitive game James likes.
Name all of James's competitive favorites.
What is his favorite band?
What are his favorite bands?
What is his favorite camera?
What cameras does he use?
Which of his projects involves AI?
Which projects involve AI?
What was his first sport?
What sports did he start before 2020?
~~~

Check whether the answer's scope exactly matches the wording. A singular question must not receive an unlabelled dump, and a plural question must not be answered with only one retrieved chunk.

Test temporal operators:

~~~text
When did James start skiing?
When did James start ice hockey?
Which sport did James start first?
What season did James reach Diamond 2?
What is James's highest Apex Legends rank?
When is James expected to graduate?
What did James do before learning Python?
What did James do after starting electric guitar?
~~~

Do not reward a plausible answer that changes the temporal relation.

## Test group 2 — entity and role binding

~~~text
What camera did James use to film in Xinjiang?
What did James film in Greece?
What did James photograph in Italy?
What lens does he use for photography?
What instrument does he play, and what genres does he play on it?
What games does he play competitively?
What did he publish about large language models?
Which essay uses Apex Legends?
What did he build for the medical recovery platform?
Where did he train through ice hockey?
Who inspired his interest in computer science?
~~~

Check that modifiers bind to the right object. Flag camera inventory substituted for destination-specific gear, travel lists substituted for videos, project lists substituted for one project, and gaming facts substituted for essays.

## Test group 3 — why/how evidence strength

Why/how questions are vulnerable to plausible but unsupported LLM prose:

~~~text
Why does James enjoy gaming?
Why is gaming important to James?
How did James learn to code?
How did James learn electric guitar?
How does James's FFT guitar tuner work?
How does his medical recovery platform work?
Why is Japan his favorite place?
Why does James value self-learning?
How does anime influence his visual style?
~~~

For every answer, map each causal or procedural claim to an actual source excerpt. Mark claims that are only evaluator inference. The response must refuse or qualify a mechanism that is not documented; it must not fill the gap with generic explanation.

## Test group 4 — exact values and Unicode fidelity

~~~text
What is James's current favorite song?
Who sings James's favorite song?
Who is his favorite artist?
What are his favorite bands?
What are his camera lenses?
What is his Apex rank and season?
What awards and competitions has he participated in?
What is the exact name of the Qiu competition?
What is the title of his Uniswap project?
What are the names of his videos?
~~~

Check exact Chinese/Japanese names, model names, lens specifications, slashes, decimals, years, and rank labels. Check that participation is not rewritten as winning, publication is not confused with research, and names are not dropped or corrupted.

## Test group 5 — Chinese, mixed-language, and Unicode questions

The current code contains limited CJK routing, but answer quality has not been established. Test independently:

~~~text
James最喜欢什么游戏？
James有哪些爱好？
James会弹什么乐器？
James喜欢什么音乐？
他什么时候开始弹吉他？
James在哪里拍过照？
James的相机是什么？
James的HL科目是什么？
James参加过哪些研究项目？
丘成桐中学科学奖是什么？
favorite game是什么?
James 的 hobbies 是什么?
what are James 的 favorite bands?
~~~

Evaluate semantic routing, response-language coherence, mixed-language retrieval collisions, exact proper nouns, and refusal quality. Do not require Chinese output if the product intentionally answers in English, but require a semantically correct and coherent answer.

## Test group 6 — negation and false premises

~~~text
Does James not play an instrument?
Has James ever played ice hockey?
Did James stop playing guitar?
Is Apex Legends not one of his games?
Is James's favorite game definitely Apex Legends?
Did James win the Qiu competition?
Did James publish a paper about the FFT tuner?
Was James's camera before the Nikon Z8 a DSLR?
James studied at Harvard, right?
I heard James hates winter—is that true?
~~~

Classify each as supported, contradicted, not documented, or ambiguous. The chatbot must correct assumptions or state that the profile does not establish them. It must not turn a question's premise into a fact.

## Test group 7 — minimal and noisy input

~~~text
CAMERA
camera???
fav game!!!
what's his lens
what're James's hobbies
james' music?
James’s favorite artist?
what did he build??
apex rank pls
guitar year?
where photos?
~~~

Check casing, punctuation, contractions, and short forms. Record any case where normalization changes the intended scope or a short query returns a secondary raw chunk instead of a curated answer.

## Test group 8 — evidence-to-claim audit

Inspect at least 25 answered responses and create an evidence map:

| Answer claim | Supporting source title/chunk | Fully supported? |
|---|---|---|

Check every concrete number, name, location, year, and causal claim. Check that source cards match the claims, broad sources do not justify unrelated details, duplicate titles are avoided, refusals/clarifications have no sources, and confidence is not presented as a raw BM25 probability.

## Test group 9 — repeatability and session isolation

Repeat three times in fresh sessions:

~~~text
What is James's favorite game?
What music does James like?
How does James's FFT guitar tuner work?
What camera did he use in Xinjiang?
What is the exact name of the Qiu competition?
James有哪些爱好？
What does James believe in?
~~~

Then test separate sessions:

Session A:
~~~text
What is James's favorite food?
What about his lenses?
~~~

Session B:
~~~text
What camera does James use?
What about his food?
~~~

Report factual, language, source, or formatting variation that is not harmless prose variation.

## Root-cause requirements

For every weak or failed answer, identify the likely layer:

- query normalization;
- operator/intent classification;
- query-plan precedence;
- tokenizer/query expansion;
- BM25 ranking/context selection;
- structured formatter;
- LLM prompt/generation;
- grounding/refusal policy;
- conversation state;
- API/source assembly;
- frontend rendering;
- stale runtime.

Do not recommend model retraining unless you demonstrate that preserving operator, scope, entity, language, and evidence state cannot fix the issue. For each proposed fix, include one minimal regression test and explain why existing tests would not catch it.

## Required report

Create only:

~~~text
/Users/cheezecats/Desktop/coding-projects/about-me-bot-website/CLAUDE_GLM52_JAMCHAT_ANSWER_CONTRACT_REPORT.md
~~~

Use these sections:

1. Executive verdict focused on answer-contract preservation.
2. Runtime freshness and environment status.
3. Method, exact test counts, and scoring rubric.
4. Operator/scope results.
5. Entity and role-binding results.
6. Why/how evidence-strength results.
7. Exact-value and Unicode preservation results.
8. Chinese and mixed-language results.
9. Negation/presupposition results.
10. Minimal/noisy-input results.
11. Evidence-to-claim audit.
12. Repeatability and session-isolation results.
13. Complete failure table with exact question, exact answer, expected contract, score, severity, likely cause, and regression test.
14. Top five improvements ordered by visitor impact and uncertainty.
15. Explicit conclusion on whether another model, retraining, or architecture change is justified.

Be evidence-led. Do not report a historical defect as current without reproducing it. Distinguish a genuine answer-quality failure from an intentionally safe refusal or a language capability limitation.
