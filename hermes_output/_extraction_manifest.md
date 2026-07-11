# Extraction Manifest

> **Candidate facts extracted by Hermes (self-hosted agent) for human review by James Sui. Approved subset to be used in the Ask James knowledge base.**

## Summary

- **Total files scanned (recursively):** 8,325 items (128 directories, 8,197 files)
- **Files read for content extraction:** ~45 text-based files (DOCX, TXT, MD, TS, PY, JSON, HTML)
- **Large files skipped (>50MB):** 7 (all ML datasets - HDF5/parquet, no personal content)
- **Files that could not be read:** .pages files (3), .pptx files (2), .pdf files (not extractable with current tools - ~62 files, mostly reference papers not authored by James)
- **Total facts extracted (pass 1):** 94 across 11 category files
- **Total facts extracted (pass 2 - subjective):** 33 in subjective.md (10 tastes, 11 personality/values, 9 emotions/fears, 9 opinions, 7 quotable self-descriptions)
- **Total facts (combined):** ~127
- **Total QA pairs suggested:** 20
- **Total UNCERTAIN items:** 14
- **Output folder size:** see storage report below

## Facts Extracted Per Category

| Category | File | Facts |
|----------|------|-------|
| Personal Bio | bio.md | 15 |
| Education | education.md | 12 |
| Sports | sports.md | 6 |
| Hobbies & Interests | hobbies.md | 8 |
| Gaming | gaming.md | 8 |
| Projects & Skills | projects_skills.md | 10 |
| Photography & Video | photo_video.md | 8 |
| Writing & Essays | writing.md | 8 |
| Travel | travel.md | 7 |
| Achievements & Awards | achievements.md | 6 |
| Contact & Links | contact.md | 6 |
| Subjective (pass 2) | subjective.md | 46 |
| **Total** | | **~140** |

## File Types Encountered

| Type | Count | Notes |
|------|-------|-------|
| .png | 7,425 | Mostly ML dataset images (NCTCRCHE100K, CRC-VAL-HE-7K, legacysurvey) |
| .sol | 187 | Solidity contracts (Uniswap V3 EE experiment) |
| .jpg | 82 | Photography + ML dataset images |
| .pdf | 62 | Mostly reference papers; 2 are James's published papers (not extractable) |
| .dll | 57 | DLL files (Windows-related, likely from Foundry/Node) |
| .json | 56 | Config files, ML responses, build artifacts |
| .jpeg | 39 | ML dataset images |
| .docx | 37 | Main source of extracted facts |
| .py | 32 | ML code (DINO, MNIST, loss curves, synthetic data) |
| .pages | 28 | Apple Pages format - could not read (DOCX versions available for key files) |
| .ts | 25 | TypeScript (website source + Uniswap tests) |
| .tsx | 19 | React components (website) |
| .heic | 13 | Apple image format - not read |
| .csv | 12 | ML training loss data |
| .yml | 12 | CI/CD configs |
| .md | 12 | Documentation + TOK exhibition files |
| .hdf5 | 11 | ML feature embeddings (LARGE - skipped) |
| .txt | 4 | EE text, SimpleQA benchmark data |
| .pptx | 2 | Presentations (not extractable) |
| .xlsx | 2 | Spreadsheets (not extractable) |
| .mov | 1 | Video file (not read) |
| Other | ~50 | Various config/build files |

## Large Files Skipped (>50MB)

| File | Path | Size | Type |
|------|------|------|------|
| train-00000-of-00165.parquet | /Personnal Database/Ai stuff/multimodal universe/ | 372.7MB | Parquet (ML dataset) |
| train_dino_features.hdf5 | /Personnal Database/Ai stuff/MNIST TRANS/ | 439.9MB | HDF5 (ML embeddings) |
| train_embed.hdf5 | /Personnal Database/Ai stuff/MNIST TRANS/ | 203.3MB | HDF5 (ML embeddings) |
| test_dino_features.hdf5 | /Personnal Database/Ai stuff/MNIST TRANS/ | 73.3MB | HDF5 (ML embeddings) |
| train_dino_features.hdf5 | /Personnal Database/Ai stuff/DINO/ | 439.9MB | HDF5 (ML embeddings) |
| test_dino_features.hdf5 | /Personnal Database/Ai stuff/DINO/ | 73.3MB | HDF5 (ML embeddings) |
| dinolegacy_features.hdf5 | /Personnal Database/Ai stuff/DINO Synthetic_dataset/ | 75.3MB | HDF5 (ML embeddings) |

All large files are ML research data files. None contain personal facts. Their existence confirms James's ML research activities (DINO, MNIST, histology classification).

## Categories With Limited Data

- **Contact & Links:** Only public email and YouTube channel found. No LinkedIn, GitHub profile URL (only inferred from Pages domain), or specific social media handles.
- **Achievements & Awards:** Found 4-5 awards. There may be more in .pages/.pptx files that could not be read.
- **Standardized test scores:** None found in any file (correctly excluded per privacy rules).

## Storage Report

- **Source files downloaded to local storage:** 0 (each file was downloaded to /tmp/, read, then immediately deleted)
- **Source files mirrored/copied:** 0
- **extraction_output/ folder size:** ~84 KB
- **Disk impact:** Negligible - only small markdown text files written
- **Temp file cleanup:** All files downloaded to /tmp/qk_* were deleted after reading

## Categories Not Found

- **Birth year:** Not explicitly stated in any file (only age 17 mentioned on website)
- **Languages spoken:** Not explicitly stated (English and Chinese implied from context but not stated)
- **Gaming ranks/levels:** No specific ranks (e.g., Apex Legends Diamond rank) found in the Personnal Database files. The Hermes user profile mentions "Diamond 2 Season 22" but this was not found in any scanned file.

## Process Notes

- Files were read one at a time via the Quark Drive API (download URL → curl to /tmp/ → read → delete)
- DOCX files were parsed using Python zipfile + XML extraction (no external dependencies)
- PDF files could not be text-extracted with available tools (pymupdf not installed)
- .pages files are ZIP archives but use a complex format that could not be parsed
- The "Personnal Database " folder name has a trailing space, which broke the kuake CLI's path resolution. Workaround: used FIDs directly via the Quark API.
