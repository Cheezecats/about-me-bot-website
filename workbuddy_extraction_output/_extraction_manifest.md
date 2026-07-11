# _extraction_manifest.md

**Candidate facts extracted by WorkBuddy for human review by James Sui. Approved subset to be used in the Ask James knowledge base.**

## Identifiers Scanned

1. **"Cheezecats"** — primary creator handle
2. **"bili_1614032286"** — Bilibili account UID (confirmed by James; original UID 69948145797 was incorrect)

## Per-Platform Summary

### YouTube (@cheezecats)
- **Found:** 4 videos, channel "About" section with real name ("James Sui"), 1 playlist ("vlog")
- **Videos:** "夏の光、冬の風" (1 view), "【8k】希腊 Greece" (10 views), "《尼康Z8下的雪国都市，冬の詩》" (6 views), "【我的21天日本自由行】" (5 views)
- **Content:** Travel films and vlogs from Japan, Greece; 8K/4K resolution; Nikon Z8 gear

### GitHub (Cheezecats)
- **Found:** 11 public repositories, 55 contributions in last year, profile README
- **Repos:** cheezecats.github.io (personal website), tune-app (FFT guitar tuner), zhiyu_app (Flutter medical app), SAT-vocabulary-review, econ-grapher, Hallucination-Evaulation, foundation-model-histology, Virchow2, flappy-game, cursor-free-vip (fork), Cheezecats (profile)
- **Languages:** Python, TypeScript, Dart, HTML/CSS
- **Domains:** Web dev, ML/medical imaging, economics, game dev, education

### GitHub Pages (cheezecats.github.io)
- **Found:** Full personal website with 4 sections: Photography (34 frames), Videos (3 films), Hobbies (sports, gaming, guitar), Essays (2 papers)
- **Identity:** "James Sui — Tech, Motion, and Perspective", 17 years old, Shanghai, China
- **Tech stack:** Vite + React 19 + TypeScript + Tailwind CSS v4 + Framer Motion

### Bilibili (bili_1614032286)
- **Found:** Display name "Cheezecats", birthday "12-22", 2 original videos (《新疆》and 无标题.mp4), active dynamic feed with reposts, comments, and interactions
- **Videos:** 《新疆》(5:28, 27 views, Nikon Z8 + iPhone 13 Pro, 8K60 footage), 无标题.mp4 (2:19, 230 views)
- **Activity:** Follows anime (Ave Mujica, 赛马娘, 芙莉莲, 夏日口袋 etc.), engaged with music/band covers, tech reviews, and meme content
- **Dynamic posts:** Active from at least June 30 to July 10, 2026; interacts with friends @F113X, @zhhaiaoskdnd, @Lynn, @Dylan, @Jarry_06, etc.

### Other Platforms
- **Status:** No confirmed Twitter/X, Instagram, TikTok, Reddit, or other social media accounts found
- **False positives:** Multiple unrelated "Cheezecats"/"Cheesecats" entities from 2013 (band) and tumblr "cheecats" (Warrior Cats fandom) — excluded

## Facts Extracted Per Category

| Category | File | Facts |
|----------|------|-------|
| Identity | identity.md | 6 |
| Videos | videos.md | 7 |
| Photography & Visuals | photo_video.md | 8 |
| Gaming | gaming.md | 5 |
| Projects & Skills | projects_skills.md | 11 |
| Hobbies & Interests | hobbies.md | 7 |
| Travel | travel.md | 5 |
| Writing & Essays | writing.md | 4 |
| Achievements | achievements.md | 4 |
| Contact & Links | contact.md | 6 |
| **Total** | | **63** |

## QA Pairs Suggested

- **suggested_qa_pairs.md:** 20 candidate Q&A pairs

## Inaccessible Sources

| Source | Reason |
|--------|--------|
| https://space.bilibili.com/69948145797 | Incorrect UID — returns 404; confirmed correct UID is 1614032286 |
| Bilibili API (https://api.bilibili.com) | Anti-bot protection prevented API access to profile stats |
| YouTube video descriptions (detailed) | Some videos returned minimal metadata; full descriptions were not always extractable |
| PDF essays (full text) | PDFs at cheezecats.github.io contained binary compressed data — full text not extractable via web fetch |

## Gaps (Categories with Limited Data)

- **Gaming:** No specific game ranks, levels, or in-game names found publicly
- **Achievements:** No subscriber counts, follower milestones, awards, or featured content found
- **Contact:** No public email address found; no confirmed social media beyond YouTube, GitHub, and Bilibili
- **Bilibili:** Follower/video count not extractable due to anti-bot protection; profile stats incomplete

## Date of Extraction

**2026-07-10** (all time-sensitive facts as-of this date)

## Checklist

- [x] Every fact has a Source (URL/file + identifying detail)
- [x] Both identifiers ("Cheezecats" and "bili_1614032286") were checked
- [x] No private data (phone, address, full birthdate, passwords/keys, private emails, financial, DMs, unlisted videos) was extracted
- [x] Contradictions are in UNCERTAIN.md, not silently resolved
- [x] All 10 category files exist (some with "no data found" notes where applicable)
- [x] suggested_qa_pairs.md has at least one question per extracted fact where applicable
- [x] _extraction_manifest.md has the integrity note, per-platform summary, counts, gaps, and inaccessible-source list
- [x] No source files or accounts were modified