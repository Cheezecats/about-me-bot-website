# Mac Mini Deployment Runbook

This guide assumes the Mac mini is new or has not been configured for this project yet. The Mac is the hosting machine; the Windows RTX 4080 remains the training and experiment machine.

## 1. Install the basic tools

Open Terminal and check what is already installed:

```bash
git --version
python3 --version
brew --version
uv --version
ollama --version
node --version
```

If Homebrew is missing, install it from [brew.sh](https://brew.sh), then reopen Terminal. Install the project tools:

```bash
xcode-select --install
brew install git python@3.12 uv node
brew install --cask ollama
```

## 2. Get the project

```bash
mkdir -p ~/Projects
cd ~/Projects
git clone https://github.com/Cheezecats/about-me-bot-website.git
cd about-me-bot-website
```

If the repository is already present:

```bash
cd ~/Projects/about-me-bot-website
git status
git pull --ff-only origin main
```

Do not discard local files if `git status` reports changes.

## 3. Create the Python environment

```bash
cd ~/Projects/about-me-bot-website
uv python install 3.12
uv venv --python 3.12
uv sync --frozen --extra ml --extra dev
```

Verify Python and Apple GPU support:

```bash
.venv/bin/python -c "import sys, torch; print(sys.version); print('torch=', torch.__version__); print('mps=', torch.backends.mps.is_available())"
```

MPS may be `True` or `False`; the chatbot can still run on CPU. The reranker is intentionally disabled for now.

## 4. Install and test Qwen

Open the Ollama application once, or start the service:

```bash
ollama serve
```

In a second Terminal window:

```bash
ollama pull qwen2.5:3b
ollama run qwen2.5:3b "Say hello in one sentence."
```

## 5. Configure the backend

From the project root, create a local `.env` file. Do not commit this file:

```bash
cat > .env <<'EOF'
LLM_BACKEND=ollama
LLM_MODEL=qwen2.5:3b
RERANKER_ENABLED=false
CORS_ORIGINS=http://localhost:5173
EOF
```

## 6. Run and test the API

```bash
.venv/bin/python main.py
```

In another Terminal window:

```bash
curl http://localhost:8000/api/health
```

Expected health response:

```json
{
  "status": "ok",
  "reranker_enabled": false,
  "reranker_loaded": false,
  "bm25_loaded": true
}
```

Test a normal question:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What camera does James use?"}'
```

Test a privacy refusal:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is James password?"}'
```

## 7. Optional frontend

```bash
npm install
npm run dev
```

## 8. Before public deployment

Confirm normal questions answer correctly, private questions are refused, Ollama starts after reboot, and the Mac does not sleep while hosting the site. Only then expose the API through a secure tunnel such as Cloudflare Tunnel. Do not directly port-forward port 8000.
