# Deployment Guide — Ask James

This guide covers deploying the full **Ask James** RAG chatbot stack: the FastAPI
backend, the React frontend, an optional validated cross-encoder reranker, and the Cloudflare
Tunnel that exposes the local Mac mini to the public internet.

---

## 1. Architecture Overview

The chatbot uses a policy-first retrieval-augmented generation pipeline. A
deterministic query planner first normalizes common typos and informal phrasing,
then curated fact questions can be answered deterministically; open-ended
questions continue through local Ollama generation. The reranker is currently
disabled by design.

```
User Question
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 0 — Query Planning                               │
│  • Corrects common typos and informal wording            │
│  • Identifies topic/entity targets                       │
│  • Rewrites only when a deterministic rule matches       │
│  • QUERY_PLANNER_ENABLED=false restores the legacy path  │
└─────────────────────────────────────────────────────────┘
     │ normalized retrieval query
     ▼
┌─────────────────────────────────────────────────────────┐
│  Stage 1 — BM25 Retrieval (from scratch, pure Python)   │
│  • Tokenizer: lowercase, alias-normalise, stopword strip │
│  • Okapi BM25 scoring (k1=1.5, b=0.75)                  │
│  • Inverted index over all knowledge-base chunks         │
│  • Returns top-10 candidate chunks                       │
└─────────────────────────────────────────────────────────┘
     │  top-10 candidates
     ▼
┌─────────────────────────────────────────────────────────┐
│  Policy + structured answer layer                      │
│  • Privacy and unsupported-request checks               │
│  • Entity-specific and comparison answers               │
│  • Follow-up and compound-question handling             │
└─────────────────────────────────────────────────────────┘
     │  focused context when generation is needed
     ▼
┌─────────────────────────────────────────────────────────┐
│  LLM Generation (Qwen 2.5 3B via Ollama)                │
│  • Grounded system prompt restricts answers to context  │
│  • Generates a natural-language answer or refuses        │
│  • PII filter post-processes the output                 │
└─────────────────────────────────────────────────────────┘
     │
     ▼
  JSON response: { answer, status, reason, sources[], retrieval_method }
```

### Key components

| Component | Location | Purpose |
|-----------|----------|---------|
| BM25 index | [backend/retrieval/bm25.py](../backend/retrieval/bm25.py) | Lexical retrieval with inverted index |
| Tokenizer | [backend/retrieval/tokenizer.py](../backend/retrieval/tokenizer.py) | Normalisation, alias mapping, stopword removal |
| Reranker | [backend/reranker/inference.py](../backend/reranker/inference.py) | Configurable zero-shot or fine-tuned cross-encoder inference |
| Generation | [backend/generation/answer.py](../backend/generation/answer.py) | Ollama/Groq call, grounding, PII filter |
| Intent and facts | [backend/generation/intent.py](../backend/generation/intent.py), [backend/generation/structured_answers.py](../backend/generation/structured_answers.py) | Entity-aware and deterministic answers |
| API | [backend/api.py](../backend/api.py) | FastAPI app, `/api/chat` and `/api/health` |
| Config | [backend/config.py](../backend/config.py) | Environment variables and constants |

---

## 2. Mac Mini Deployment Setup

The backend runs on a **Mac mini (M4, 16 GB RAM)**. The BM25 index and reranker
inference run on-device; the LLM runs locally via Ollama.

### 2.1 Prerequisites

- macOS with Python 3.12+ (check with `python3 --version`)
- Node.js 20+ and npm (for frontend build)
- `sentence-transformers` when enabling the default zero-shot cross-encoder

### 2.2 Install Ollama and pull the model

```bash
# Install Ollama (downloads the macOS app)
brew install ollama

# Start the Ollama daemon (runs on localhost:11434)
ollama serve

# In a separate terminal, pull the Qwen 2.5 3B model (~2 GB download)
ollama pull qwen2.5:3b

# Verify it loads and responds
ollama run qwen2.5:3b "Say hello in one sentence."
```

> **Note:** On first inference Ollama loads the model into memory. On this 16 GB
> Mac mini, the 3B model occupies roughly 2–3 GB, leaving substantially more
> headroom for the OS and a larger local model if we validate one later. If you
> encounter memory pressure, ensure no other heavy apps are running.

### 2.3 Install Python dependencies

The project uses `pyproject.toml` for dependency management. Install the core
runtime dependencies plus the ML extras (needed for the reranker):

```bash
# From the project root
pip install fastapi uvicorn python-dotenv httpx ollama

# ML dependencies required to load either reranker backend
pip install torch transformers sentence-transformers

# Development / testing
pip install pytest
```

Alternatively, install everything at once:

```bash
pip install -e ".[ml,dev]"
```

### 2.4 Set environment variables

Create a `.env` file in the project root (it is loaded automatically by
`python-dotenv` in [backend/config.py](../backend/config.py)):

```dotenv
# LLM backend — "ollama" for local, "groq" for cloud (optional alternative)
LLM_BACKEND=ollama

# The Ollama model tag to use for generation
LLM_MODEL=qwen2.5:3b

# Comma-separated list of allowed CORS origins.
# Include your GitHub Pages URL and the tunnel URL (once created).
CORS_ORIGINS=https://cheezecats.github.io,http://localhost:5173,https://ask-james.example.com

# Restrict which Host headers the API accepts. Keep the local-only default
# until a reverse proxy or tunnel is deliberately configured.
ALLOWED_HOSTS=localhost,127.0.0.1,[::1]
HOST=127.0.0.1

# Leave disabled unless threshold calibration reports recommended_for_deployment: true.
RERANKER_ENABLED=false
RERANKER_BACKEND=zeroshot_cross_encoder

# Deterministic normalization for informal and misspelled questions.
# Set false temporarily to compare with the legacy request path.
QUERY_PLANNER_ENABLED=true
```

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_BACKEND` | `ollama` | Which generation backend to use (`ollama` or `groq`) |
| `LLM_MODEL` | `qwen2.5:3b` | Ollama model tag |
| `CORS_ORIGINS` | `https://cheezecats.github.io,http://localhost:5173` | Allowed origins for browser requests |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1],testserver` | TrustedHostMiddleware allow-list |
| `HOST` | `127.0.0.1` | Bind address; keep local-only during development |
| `MAX_REQUESTS_PER_MINUTE` | `60` | Per-client in-memory API rate limit |
| `GROQ_API_KEY` | *(empty)* | Only needed if `LLM_BACKEND=groq` |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Only needed if `LLM_BACKEND=groq` |
| `RERANKER_ENABLED` | `false` | Enables only a validated reranker |
| `RERANKER_BACKEND` | `zeroshot_cross_encoder` | `zeroshot_cross_encoder` or `finetuned_distilbert` |
| `QUERY_PLANNER_ENABLED` | `true` | Enables deterministic query normalization; set `false` for legacy rollback/comparison |

### 2.5 Run the API

```bash
# Option A — using the project entry point (runs on localhost:8000)
python main.py

# Option B — using uvicorn directly
uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

On startup the API will:

1. Load (or build) the BM25 index from `data/bm25_index.json`.
2. Load the knowledge-base chunks from `data/chunks.json`.
3. Load the configured reranker only when `RERANKER_ENABLED=true`.
   - Otherwise, the API starts in **BM25-only mode**. Responses expose
     `retrieval_method: "bm25"` and `reranker_fallback_used: true`.
4. Initialise an in-memory conversation store.

You should see output similar to:

```
[bm25] indexed 120 chunks, avgdl=8.42, vocab=540
INFO:     Uvicorn running on http://127.0.0.1:8000
```

---

## 3. Cloudflare Tunnel Setup

The Mac mini sits behind a NAT router with no public IP. A **Cloudflare Tunnel**
exposes `localhost:8000` to the internet over a secure, outbound-only
connection — no port forwarding required.

### 3.1 Install cloudflared

```bash
brew install cloudflared
```

### 3.2 Authenticate with Cloudflare

```bash
cloudflared tunnel login
```

This opens a browser window. Select the domain you want to use (e.g.
`example.com`). Cloudflare stores a certificate at
`~/.cloudflared/cert.pem`.

### 3.3 Create the tunnel

```bash
cloudflared tunnel create ask-james
```

This creates a tunnel with a UUID and generates a credentials file at
`~/.cloudflared/<UUID>.json`. Note the tunnel UUID for the next steps.

### 3.4 Configure the tunnel

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: <TUNNEL_UUID>
credentials-file: /Users/james/.cloudflared/<TUNNEL_UUID>.json

ingress:
  - hostname: ask-james.example.com
    service: http://localhost:8000
  - service: http_status:404
```

Replace `<TUNNEL_UUID>` with the UUID from step 3.3, and
`ask-james.example.com` with your actual subdomain.

### 3.5 Create the DNS CNAME record

```bash
cloudflared tunnel route dns ask-james ask-james.example.com
```

This creates a CNAME record pointing `ask-james.example.com` to
`<TUNNEL_UUID>.cfargotunnel.com` automatically.

### 3.6 Run the tunnel

```bash
cloudflared tunnel run ask-james
```

Verify the tunnel is working:

```bash
curl https://ask-james.example.com/api/health
```

### 3.7 Run as a background service (recommended)

To keep the tunnel running across reboots:

```bash
sudo cloudflared service install
```

This installs `cloudflared` as a launchd service that starts on boot.

> **Important:** Add the tunnel URL to your `CORS_ORIGINS` environment variable
> so browser requests from the frontend are accepted.

---

## 4. Frontend Deployment

The frontend is a React 19 + Vite + Tailwind CSS v4 application. The chat widget
lives in [src/components/ChatBot.tsx](../src/components/ChatBot.tsx).

### 4.1 Build the React app

```bash
npm install
npm run build
```

This produces static files in `dist/`. The build also runs
`scripts/copy-404.mjs` to copy a `404.html` for GitHub Pages SPA routing.

### 4.2 Set the API URL

The chat widget reads its API endpoint from the Vite environment variable
`VITE_CHAT_API_URL` (see [ChatBot.tsx:27](../src/components/ChatBot.tsx#L27)):

```typescript
const API_URL = import.meta.env.VITE_CHAT_API_URL || "/api/chat";
```

Create a `.env` file (or set it in your CI environment) **before building**:

```bash
# Point to the Cloudflare Tunnel URL
VITE_CHAT_API_URL=https://ask-james.example.com/api/chat
```

> **Note:** Vite inlines environment variables at build time, so this must be
> set before `npm run build`.

### 4.3 Deploy to GitHub Pages

The repository includes a GitHub Actions workflow at
[.github/workflows/deploy-pages.yml](../.github/workflows/deploy-pages.yml)
that automatically builds and deploys to GitHub Pages on every push to `main`.

To enable it:

1. Go to **Settings → Pages** in the GitHub repository.
2. Set **Source** to **GitHub Actions**.
3. Add `VITE_CHAT_API_URL` as a repository secret (Settings → Secrets and
   variables → Actions) so the workflow can inject it at build time.
4. Push to `main` — the site deploys to `https://cheezecats.github.io/<repo>/`.

### 4.4 Alternative: serve via FastAPI

If you prefer a single-origin deployment, place the built `dist/` contents into
a `views/` directory in the project root. The API in [backend/api.py](../backend/api.py)
automatically serves `views/index.html` at `/` and the other routes
(`/essays`, `/photography`, `/videos`, `/hobbies`) when the `views/` directory
exists (see [api.py:204-224](../backend/api.py#L204-L224)). In this mode, set
`VITE_CHAT_API_URL` to `/api/chat` (the default) so requests stay same-origin.

---

## 5. Trained Model Deployment

The DistilBERT reranker is trained on a separate **PC with an NVIDIA RTX 4080
GPU** (see [backend/training/train_reranker.py](../backend/training/train_reranker.py))
because the 8 GB Mac mini lacks the VRAM for comfortable training. At inference
time the model runs on the Mac mini's MPS (Metal) backend or CPU.

### 5.1 Train the model (on the 4080 PC)

```bash
# 1. Build the training dataset from QA pairs + chunks
python -m backend.training.build_dataset

# 2. Fine-tune DistilBERT
python -m backend.training.train_reranker

# 3. Evaluate on the held-out test set
python -m backend.training.evaluate
```

This produces a model directory at `models/reranker/` containing:
- `config.json` — model architecture config
- `pytorch_model.bin` (or `model.safetensors`) — trained weights
- `tokenizer.json`, `vocab.txt`, etc. — tokenizer files

### 5.2 Copy the model to the Mac mini

```bash
# From the 4080 PC — copy the entire reranker directory
scp -r models/reranker/ james@mac-mini.local:~/about-me-bot-website/models/reranker/
```

Or compress and transfer:

```bash
# On the training PC
tar czf reranker.tar.gz -C models reranker
scp reranker.tar.gz james@mac-mini.local:~/about-me-bot-website/

# On the Mac mini
cd ~/about-me-bot-website
tar xzf reranker.tar.gz -C models/
rm reranker.tar.gz
```

### 5.3 Verify the model loads

Restart the API and check the health endpoint — `reranker_loaded` should be
`true` (see [Section 6](#6-health-check)).

---

## 6. Health Check

The API exposes a health endpoint that reports the status of each pipeline
stage:

```bash
curl http://localhost:8000/api/health
```

**All systems nominal:**

```json
{
  "status": "ok",
  "reranker_loaded": true,
  "bm25_loaded": true
}
```

**BM25-only fallback (reranker model missing):**

```json
{
  "status": "ok",
  "reranker_loaded": false,
  "bm25_loaded": true
}
```

The implementation is in [backend/api.py:83-89](../backend/api.py#L83-L89).
Use this endpoint for monitoring and uptime checks via the Cloudflare Tunnel:

```bash
curl https://ask-james.example.com/api/health
```

---

## 7. Troubleshooting

### Ollama is not running

**Symptom:** Chat requests return HTTP 503 with `status: "unavailable"`, or the
API logs show `Ollama generation timed out`.

**Cause:** The Ollama daemon is not running on `localhost:11434`, or it crashed.

**Fix:**

```bash
# Check if Ollama is running
ollama list

# If not, start it
ollama serve
```

Verify connectivity:

```bash
curl http://localhost:11434/api/tags
```

The generation code in [backend/generation/answer.py](../backend/generation/answer.py)
has a 30-second timeout (`OLLAMA_TIMEOUT`). If Ollama is slow to respond (e.g.,
the model is still loading on first call), the first request may time out.
Subsequent requests should be fast once the model is warm in memory.

### Model is missing in Ollama

**Symptom:** Error like `model "qwen2.5:3b" not found, try pulling it first`.

**Fix:**

```bash
ollama pull qwen2.5:3b
```

Confirm the model name in `LLM_MODEL` matches exactly what Ollama expects. List
available models with `ollama list`.

### Reranker not loaded (BM25-only fallback)

**Symptom:** `/api/health` returns `reranker_loaded: false`, and chat responses
have `fallback_used: true`.

**Cause:** The `models/reranker/` directory does not exist or is incomplete (see
[inference.py:22-26](../backend/reranker/inference.py#L22-L26)).

**Fix:**

1. Confirm the directory exists and contains model + tokenizer files:
   ```bash
   ls -la models/reranker/
   # Should show: config.json, pytorch_model.bin, tokenizer.json, vocab.txt, ...
   ```
2. If missing, copy the trained model from the 4080 training PC (see
   [Section 5](#5-trained-model-deployment)).
3. Ensure `torch` and `transformers` are installed:
   ```bash
   pip install torch transformers
   ```
4. Restart the API.

**Impact:** In fallback mode the system still works — it uses the BM25 ranking
order directly without the neural reranker. Answer quality may be lower for
queries where BM25's lexical matching is insufficient, but the system degrades
gracefully rather than failing entirely.

### CORS errors in the browser

**Symptom:** Browser console shows `Access-Control-Allow-Origin` errors when the
chat widget tries to call the API.

**Fix:** Add the frontend's origin to `CORS_ORIGINS` in your `.env` file and
restart the API. For example, if the frontend is at
`https://cheezecats.github.io`:

```dotenv
CORS_ORIGINS=https://cheezecats.github.io,https://ask-james.example.com,http://localhost:5173
```

### Cloudflare Tunnel returns 502 Bad Gateway

**Symptom:** `curl https://ask-james.example.com/api/health` returns 502.

**Cause:** The FastAPI server is not running on `localhost:8000`, or the tunnel
ingress hostname doesn't match.

**Fix:**
1. Confirm the API is running locally: `curl http://localhost:8000/api/health`
2. Verify the `service:` URL in `~/.cloudflared/config.yml` is
   `http://localhost:8000`.
3. Check `cloudflared` logs: `cloudflared tunnel run ask-james` (run in
   foreground to see errors).
