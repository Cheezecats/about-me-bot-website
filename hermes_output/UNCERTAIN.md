# UNCERTAIN - Items Flagged for Review

## 1. Email address discrepancy
- **Issue:** Two different email addresses found:
  - suihe0812@gmail.com (on personal website, public-facing)
  - jamessui1222@gmail.com (in Pycademy intro, school club context)
- **Sources:**
  - /Personnal Database/cheezecats.github.io/src/data/content.ts
  - /Personnal Database/升学 2(1)/Pycademy/James pycademy intro.docx
- **Note:** Both may be valid. James should decide which to include in the KB.

## 2. Math IA topic
- **Issue:** The Math IA topic (Markov chain packet loss in Apex Legends) is recorded from Hermes memory (user profile), not directly extracted from a file in the "Personnal Database" folder. No file containing the Math IA was found during scanning.
- **Confidence:** medium - needs James's confirmation
- **Note:** If the Math IA file exists elsewhere, it should be added to the Personnal Database for verification.

## 3. School name
- **Issue:** Files consistently say "an international high school in Shanghai" but never name the specific school. The Hermes user profile says "Yk Pao School Shanghai" but this was not found in any file in the Personnal Database.
- **Confidence:** low for the specific school name
- **Note:** James should confirm whether to include the school name.

## 4. Grade level / expected graduation
- **Issue:** Files mention "10th grade" (Pycademy intro) and "grade 11" (folder name). The bio says age 17. No explicit graduation year was found in any file.
- **Note:** James should provide expected graduation year if desired.

## 5. PPTX files could not be read
- **Issue:** Two .pptx files were found but text extraction was not possible:
  - /Personnal Database/grade 11/隋和 + 王浩翔.pptx (11MB) - likely a school presentation
- **Note:** May contain additional facts if James wants to review manually.

## 6. .pages files could not be read
- **Issue:** Several .pages files (Apple Pages format) could not be extracted:
  - /Personnal Database/升学 2(1)/Pycademy/James pycademy intro.pages
  - /Personnal Database/升学 2(1)/summer school app.pages
  - /Personnal Database/升学 2(1)/Mechincal Questions.pages
- **Note:** .docx versions of these files exist and were read successfully.

## 7. Large ML dataset files - content not read
- **Issue:** 7 files over 50MB were skipped (ML datasets in HDF5/parquet format). These are data files unlikely to contain personal facts.
- **Files:**
  - train-00000-of-00165.parquet (372.7MB)
  - train_dino_features.hdf5 (439.9MB) x2
  - train_embed.hdf5 (203.3MB)
  - test_dino_features.hdf5 (73.3MB) x2
  - dinolegacy_features.hdf5 (75.3MB)
- **Note:** These confirm James's ML research activities but contain no personal facts.

## 8. Private info encountered - redacted
- **Issue:** The "Brainstorming Questions 2025 Final James.docx" contains personal reflections and family details (father's hometown, growing up experiences). Only non-sensitive facts were extracted (hometown = Shanghai, father's border town hometown). Any more sensitive details were not extracted.
- **Note:** James should review this file himself for any additional facts he wants in the KB.

## 9. "edit llm.docx" appears to be an edited/draft version
- **Issue:** This 489KB file (40,327 chars extracted) appears to be a heavily edited draft of the LLM hallucination paper with track changes or similar. May contain outdated or conflicting information compared to the final version.
- **Source:** /Personnal Database/升学 2(1)/丘竞赛/edit llm.docx
- **Note:** Facts were taken from the cleaner final versions instead.

## 10. Multiple versions of the same paper
- **Issue:** The histology classification paper exists in multiple drafts:
  - "James Sui paper.docx" (earlier version)
  - "sept draft.docx" (September draft)
  - "Building the Best Pipeline for Histology Patch Classification.docx" (most complete version)
  - "How Changing Neural Network Architectures Improves Performance..." (combined paper version)
- **Note:** Facts were extracted from the most complete version. James should verify which is the final published version.

## 11. Social media handles not captured
- **Issue:** The Pycademy intro lists Instagram, WeChat, Line, Snapchat, Twitter but does not provide handles/URLs. Only the YouTube channel URL was found publicly.
- **Note:** James should add specific handles if he wants them in the KB.

## 12. Sensitive: Bullying experience (second pass)
- **Issue:** James wrote about being bullied by a teacher's child in dorm. He describes school staff failing to resolve the situation fairly. This was extracted into subjective.md but flagged here as sensitive.
- **Source:** /Personnal Database/升学 2(1)/Brainstorming Questions 2025 Final James.docx (Feelings section)
- **Note:** James should decide whether to include this in the public KB. It reveals resilience but also involves another person.

## 13. Implied but not explicitly stated (second pass)
- **Issue:** The following traits are strongly implied across multiple essays but James never directly wrote "I am [trait]":
  - **Hardworking** — implied by descriptions of long hours, balancing projects with academics, self-learning. Never stated as "I am hardworking."
  - **Resilient** — implied by bouncing back from academic disappointment within a day, learning from bullying. Never stated as "I am resilient."
  - **Curious** — implied by self-learning, research, wide interests. Never stated as "I am curious."
  - **Introverted-leaning** — implied by descriptions of difficulty making friends initially, preferring small groups. Never stated.
- **Note:** These are interpretations, not extracted facts. James should decide if he wants to add any as self-descriptions.

## 14. Family cultural background
- **Issue:** James wrote "despite having both Chinese parents we rarely celebrate traditional festivals such as the Chinese New Year." This implies a non-traditional family upbringing but is stated factually, not as an opinion.
- **Source:** /Personnal Database/升学 2(1)/Brainstorming Questions 2025 Final James.docx
- **Note:** Could be relevant for "about me" but James should confirm comfort level.
