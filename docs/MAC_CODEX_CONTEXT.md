# Codex Context: JamChat

## Project goal

This is James Sui's personal website with a “JamChat” chatbot. The chatbot should answer questions about James using only the project's knowledge base and refuse private or unsupported questions.

## Current deployment decision

Use the Mac mini as the hosting machine. The Windows RTX 4080 is for training and experiments only.

The current safe runtime is:

```text
BM25 retrieval → top context chunks → Ollama Qwen 2.5 3B → grounding and privacy checks
```

The neural reranker must remain disabled:

```env
RERANKER_ENABLED=false
LLM_BACKEND=ollama
LLM_MODEL=qwen2.5:3b
```

The zero-shot cross-encoder improves ranking, but its refusal calibration is not safe enough for public deployment. Do not enable it or change the confidence threshold without new evaluation.

## Mac setup

From the repository root:

```bash
uv sync --frozen --extra ml --extra dev
ollama pull qwen2.5:3b
.venv/bin/python main.py
```

Check the API:

```bash
curl http://localhost:8000/api/health
```

Expected important fields:

```json
{
  "reranker_enabled": false,
  "reranker_loaded": false,
  "bm25_loaded": true
}
```

## What has already been done

- Rebuilt and cleaned the knowledge base.
- Added privacy-question refusal rules.
- Added BM25 index freshness protection.
- Added tests for privacy behavior and fallback behavior.
- Added Windows and Mac deployment documentation.
- Compared BM25, zero-shot cross-encoder, and fine-tuned DistilBERT.
- Current tests pass.

## Next task

Run the chatbot locally on the Mac and verify:

1. A normal question such as “What camera does James use?” receives a grounded answer.
2. A private question such as “What is James's password?” is refused.
3. `/api/health` reports BM25 loaded and reranker disabled.
4. The frontend can reach the local API.

Do not retrain the model on the Mac. Do not expose port 8000 publicly until local behavior is verified.
