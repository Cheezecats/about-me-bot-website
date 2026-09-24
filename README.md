# James’s personal website and JamChat

A React/TypeScript portfolio with photography, videos, hobbies and essays. JamChat answers questions about James’s reviewed public profile using FastAPI, BM25 retrieval, structured facts and local Ollama generation.

## Run locally

Use Node.js 20+ and Python 3.12+. From the project root:

```bash
npm ci
uv sync --frozen --extra dev
ollama pull qwen2.5:3b
```

Keep Ollama running, then start the backend and frontend in separate terminals:

```bash
.venv/bin/python main.py
```

```bash
npm run dev
```

Vite proxies `/api` to the backend on port 8000. For a separate public API, set `VITE_CHAT_API_URL` before building. The default runtime does not need PyTorch or a reranker; the complete backend test suite and training tools additionally need `uv sync --frozen --extra ml --extra dev`.

## Maintain the knowledge base

Review facts in `kb_extra/*.md` and their corresponding entries in `data/profile_facts.json`. Website data lives in `src/data/content.ts`. Do not treat raw extraction reports as approved public facts.

```bash
node scripts/export_content.mjs
.venv/bin/python -m backend.ingest.chunker
.venv/bin/python -m backend.retrieval.bm25
.venv/bin/python scripts/validate_profile_facts.py
```

Restart the API after changing the corpus or fact registry. Existing chunk identifiers are preserved when sections move; the cached index is checked against the public corpus’s content. Facts excluded from public chat stay excluded after rebuilding.

## Verify

```bash
.venv/bin/python -m pytest -q
npm run typecheck
npm test
npm run build
```

With the API and Ollama running:

```bash
.venv/bin/python scripts/evaluate_live_chat.py --output /tmp/jamchat-api-evaluation.json
.venv/bin/python scripts/evaluate_live_chat.py --cases data/generative_evaluation_questions.jsonl --output /tmp/jamchat-model-evaluation.json
```

These evaluations measure behavior on a small fixed corpus, not general language understanding. Each run uses fresh sessions.

See [architecture](docs/CHATBOT_ARCHITECTURE.md), [deployment](docs/DEPLOYMENT.md), and the [JamChat review](docs/JAMCHAT_REVIEW.md) for implementation details, verification results and remaining limitations.

## JamChat destination links

JamChat can offer clickable cards for website pages, the sports timeline,
documented music and games, and the curated photo selection. The favorite song
has a static cover preview with Spotify and YouTube links. Edit `data/chat_destinations.json` to
maintain destination labels and links; both frontend and backend use that catalog.
Restart the API and rebuild the frontend after catalog changes. The photo-picks
count follows the content export, so run the knowledge-base export steps above
when changing featured photos. `npm run build` also refreshes thumbnail dimensions
to keep photo deep links stable as images load. No provider API keys are needed.
