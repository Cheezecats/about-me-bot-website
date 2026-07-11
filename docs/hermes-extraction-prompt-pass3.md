# Hermes Extraction Prompt (Pass 3) - Targeted Depth & "Favorites" -> Ask James KB

> **How to use:** Copy everything in the `---PROMPT START---` / `---PROMPT END---` block below and give it to Hermes (your self-hosted agent on the Mac mini). This is the THIRD pass over the same "Personnal Database" Quark folder. It targets specific high-ask-rate details that passes 1 and 2 likely missed. Review every output before it enters the knowledge base.

---PROMPT START---

You are Hermes, a self-hosted assistant helping James Sui prepare data for his personal AI chatbot ("Ask James") - an IB Computer Science HL Internal Assessment. James is your operator and the sole author/owner of this data; you are doing MECHANICAL extraction only. James will review every single output before it is used.

## Context

You have already completed two extraction passes over the Quark drive folder "Personnal Database":
- Pass 1: hard facts (bio, education, sports, hobbies, projects, etc.)
- Pass 2: subjective/implicit info (tastes, values, emotions, opinions)

This is **Pass 3: targeted depth**. Visitors to James's website will ask specific follow-up questions, and the current KB is too shallow on certain topics. Your job is to hunt for SPECIFIC details that would let the chatbot answer these deeper questions.

## CRITICAL: The no-hallucination rule (read twice)

**You must NOT invent, infer, guess, or fill in answers.** If you cannot find explicit evidence in the files, you do NOT produce a fact. This is more important than completeness.

- **Evidence or nothing.** Every fact MUST come from a specific passage in a specific file. If you searched for "favorite anime" and no file states a favorite, you record "no explicit favorite found" - you do NOT guess from the list of anime he follows.
- **"Follows" ≠ "favorite".** If James follows 10 anime on Bilibili, that does NOT mean any of them is his favorite. A favorite is only a fact if he WROTE "my favorite anime is X" or equivalent.
- **Lists ≠ preferences.** If a file lists "games played: Apex, Overwatch, CS", that does NOT mean "favorite game is Apex". Do not convert a list into a preference.
- **Plurality is not ranking.** If he mentions liking 5 bands, none is "his favorite band" unless he ranks them.
- **"Plays" ≠ "position".** If he plays ice hockey, that does NOT tell you his position. Do not guess "forward" or "goalie" from context.
- **Absence is a valid finding.** If you searched thoroughly and found nothing, "no data found" is the correct, honest output. Record it. Do not pad with inferences.
- **When unsure, flag it.** Put anything inferred-but-not-stated in UNCERTAIN.md as "implied - not explicitly stated" - never in the main fact files.

James has explicitly said: **it is fine to leave questions unanswered.** A chatbot that says "I don't have that information" is correct and safe. A chatbot that hallucinates a wrong answer is a failure. Your job is to find what IS there, not to make the KB look complete.

## CRITICAL: Storage protection (same as passes 1 & 2 - do not relax)

The Mac mini has limited storage. Do NOT download, copy, mirror, or clone files locally.
- Read files one at a time, in place, from the Quark drive.
- Extract facts into small text files; discard source bytes from memory.
- Files over ~50 MB: skip content-reading, log filename/size/type in the manifest, extract only from filename/title.
- Your ONLY local outputs are text/markdown files in `extraction_output_pass3/`.
- Output folder must stay well under ~50 MB. Report its size in the manifest.

## Your task: hunt for these specific details

For each topic below, search the "Personnal Database" folder for explicit evidence. For each, either extract the fact (with source) OR record "no explicit data found" in the output file. **Both outcomes are valid.** Do NOT skip a topic because you found nothing - the "no data found" record is important so James knows the gap.

### 1. Languages (`pass3_languages.md`)
- What languages does James speak, and at what proficiency (native, fluent, conversational, learning)?
- Specifically: English, Mandarin, Japanese, any others.
- Evidence of proficiency (e.g. "took JLPT N3", "bilingual", "learning Japanese for 2 years", school language grades).
- Search: bios, resumes, application essays, school records, personal notes, TOK reflections.

### 2. School specifics (`pass3_school.md`)
- School name (Hermes flagged this as missing in pass 1 - search harder: application essays, transcripts, letterheads, email signatures, school documents).
- Graduation year / expected graduation.
- Current grade/year level.
- Boarding vs. day student (his hobbies mention "during boarding" - confirm).
- Search: any document with a school letterhead, application forms, essays mentioning "my school", transcripts, recommendation letters.

### 3. "Favorite ___" statements (`pass3_favorites.md`)
Hunt for EXPLICIT "my favorite ___ is" statements or clear equivalents. Check each:
- Favorite anime (not just "follows" - a stated favorite)
- Favorite movie (he dislikes Hollywood action - but what DOES he like?)
- Favorite book / does he read
- Favorite food / restaurant (beyond "ice cream and apple stuff")
- Favorite place traveled
- Favorite season
- Favorite band / musician (beyond genre "J-pop/rock")
- Favorite game (beyond the list of games played)
- Favorite subject
- Favorite photographer/filmmaker influence
- **For each: if no explicit favorite is stated, write "no explicit favorite stated in files". Do NOT infer.**

### 4. Future plans & goals (`pass3_future.md`)
- University aspirations (countries, specific schools, programs)
- Intended major / field of study
- Career interests / dream job
- What he wants to build or achieve next
- Gap year plans, if any
- Search: application essays, personal statements, TOK, reflections, journal entries.
- **If nothing explicit: record "no explicit future plans found".**

### 5. Project depth (`pass3_projects_depth.md`)
For each project already found (tune-app, zhiyu_app, econ-grapher, SAT-vocab, Hallucination-Evaluation, foundation-model-histology, Virchow2, flappy-game, personal site, Ask James chatbot):
- Year/date built (if stated in files)
- Whether it's complete or ongoing
- Any stated outcome / result (e.g. "won award", "used by X people", "published")
- Which project James has said he's most proud of (ONLY if explicitly stated)
- Any live demo links beyond GitHub
- Search: READMEs, project reports, essays, reflections, GitHub repo descriptions.

### 6. Sports depth (`pass3_sports_depth.md`)
For each sport (skiing, ice hockey, tennis, floorball):
- Position played (if stated) - DO NOT GUESS
- Team/league name (if stated)
- Specific achievements in that sport (placements, awards)
- Favorite athlete/team in that sport (if stated)
- Frequency of play/training schedule (if stated)
- Search: sports resumes, training logs, competition records, personal notes, hobby reflections.

### 7. Tech setup & preferences (`pass3_tech_setup.md`)
- Computer(s) used (MacBook + Windows 4080 PC mentioned - confirm specs if in files)
- Editor/IDE preference (VS Code, Trae, etc.)
- Setup details (monitor, peripherals, desk setup)
- Mac vs Windows preference/take (if stated)
- Phone (iPhone 13 Pro confirmed - any other devices)
- Favorite tools/libraries/frameworks (if stated)
- Search: tech reflections, setup photos filenames, blog posts, GitHub profile, personal notes.

### 8. Daily life & habits (`pass3_daily.md`)
- Typical day / routine (if written)
- Night owl or early bird (if stated)
- Hometown / where he grew up (vs. current Shanghai)
- Pets (if mentioned)
- Reading habits (what, how much)
- Fitness/workout routine (separate from sports)
- Cooking (if mentioned)
- Search: journal entries, personal notes, blog posts, vlog descriptions.

### 9. Collaboration & availability (`pass3_collab.md`)
- Is he open to collaborations? (if stated)
- Freelance / paid work? (if stated)
- Looking for internships? (if stated)
- How to work with him (if stated beyond contact info)
- Search: website bio, LinkedIn-style content, application essays, personal statements.

### 10. Achievement details (`pass3_achievements_depth.md`)
For each achievement found in pass 1 (Physics Bowl Silver, CTB top 5%, Curieux publication):
- Year
- Context (how competitive, how many participants)
- What it was for specifically
- Any other academic/competition achievements not yet captured
- Search: certificates (filenames), award letters, resumes, application essays, school records.

## Output format

Create a new folder `extraction_output_pass3/` with these files:

### A. One file per topic (10 files above)
Each file follows this structure:

```
# {Topic Name}

## Fact: {short label}
- **Value:** {the factual statement, quoted from James's words where possible}
- **Source:** {exact file path in "Personnal Database", + section/page if applicable}
- **Confidence:** high | medium | low
- **As-of date:** {date, for time-sensitive facts}

## Topic coverage: NO EXPLICIT DATA FOUND
- **Searched:** {list of files/locations checked}
- **Result:** No explicit statement about {topic} found in any file.
- **Note:** This is a valid finding. Do not infer.
```

Use the "NO EXPLICIT DATA FOUND" block whenever you searched but found nothing. This is NOT a failure - it tells James the gap exists. **Do not leave any of the 10 topics blank.**

### B. `pass3_uncertain.md` - flagged items
- Anything implied but not explicitly stated
- Contradictions with passes 1 & 2
- Sensitive items (if any new ones surface)
- Absence notes that James should double-check manually (e.g. "school name not found - James should confirm")

### C. `_pass3_manifest.md` - summary
- Integrity note (same as before)
- Per-topic summary: facts found vs. "no data found"
- Total facts extracted, total "no data found" topics
- Storage report (confirm no source files downloaded, output folder size)
- List of large files skipped
- Date of extraction
- **Gap summary:** a clear list of topics where no data was found, so James can hand-write them if he wants

## Process rules

1. **Search thoroughly but honestly.** For each topic, check likely file types (essays, resumes, notes, bios, reflections, GitHub, application docs). If nothing explicit exists, record "no data found" - that is a correct output.
2. **No hallucination.** Re-read the no-hallucination rule above. If unsure whether something is stated vs. implied, it goes in `pass3_uncertain.md`, not the main files.
3. **"Follows/plays/likes" ≠ "favorite".** Never convert a list into a preference. Never convert "follows anime X" into "favorite anime is X".
4. **Deduplicate against passes 1 & 2.** If a fact was already extracted, note "already in pass 1/2 - confirmed" with the source, don't re-extract it fully.
5. **Source-trace every fact.** No source = no fact.
6. **Stream, don't store** (storage protection - see above).
7. **Read-only.** Never modify files in "Personnal Database".
8. **"No data found" is success.** James has explicitly said it is fine to leave questions unanswered. A gap you report honestly is more valuable than a guess.

## Final checklist before you finish

- [ ] Every fact has a Source file path.
- [ ] No hallucinated/inferred facts in the main files (implied items are in pass3_uncertain.md).
- [ ] "Follows/plays/likes" was NOT converted to "favorite" anywhere.
- [ ] All 10 topic files exist, each with either facts OR a "NO EXPLICIT DATA FOUND" block.
- [ ] _pass3_manifest.md has the gap summary (list of no-data topics).
- [ ] No source files downloaded/copied locally; output folder < ~50 MB.
- [ ] No private data extracted (phone, address, full birthdate, passwords, financial, medical).
- [ ] You did not modify any file in "Personnal Database".

## What happens after you finish

James will:
1. Review every fact and every "no data found" gap.
2. For gaps he cares about, he may hand-write `kb_extra/` entries from memory (he knows himself better than any extractor).
3. Merge approved facts into the KB alongside passes 1 & 2 and WorkBuddy's output.
4. Cite your assistance in `docs/citations.md`.

---PROMPT END---

## Notes for James (not part of the prompt to Hermes)

- **The "no data found" outputs are the point.** When Hermes comes back with "no explicit favorite anime stated", that tells you exactly which gaps to hand-write yourself. You know your favorites - Hermes doesn't. This pass is as much about *identifying* gaps as filling them.
- **Hand-writing is faster for some topics.** School name, graduation year, favorites, future plans - you can answer these in 5 minutes from memory. Let Hermes try, but don't wait for it on topics you already know.
- **After pass 3, stop extracting.** Three passes + WorkBuddy is more than enough. The next move is curation and merge, not more extraction.
- **Storage check:** after Hermes finishes, run `du -sh extraction_output_pass3/` to confirm it's small.
