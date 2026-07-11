# Security Best Practices Report — Ask James RAG Chatbot

**Project:** about-me-bot-website (IB CS HL IA)
**Review date:** 11 July 2026
**Stack:** Python (FastAPI, PyTorch, Transformers, Ollama, httpx) + TypeScript (React 19, Vite, Tailwind CSS)
**Reviewer:** TRAE Security Skill

## Executive Summary

The project has several security gaps that must be addressed before the chatbot is exposed to the public internet via Cloudflare Tunnel. The most critical issue is that sensitive personal data (fears, bullying, academic distress, partial birthday, email, Bilibili UID) is stored in the public knowledge base with only a weak regex output filter as protection. The Groq cloud backend can leak this data externally before the output filter runs. The FastAPI server lacks CORS middleware, host validation, and request validation. The legacy `main.py` serves static files via `FileResponse` with user-controlled path components. No CSP or security headers are deployed on the frontend.

**Findings summary:** 3 Critical, 4 High, 4 Medium, 3 Low

---

## Critical Findings

### SEC-001: Sensitive personal data exposed in public knowledge base with only output-side filtering

**Rule:** FASTAPI-AUTH-001 / General data protection
**Severity:** Critical
**Location:**
- `backend/config.py:69-72` (PII_PATTERNS)
- `backend/generation/answer.py:70-74` (apply_pii_filter)
- `kb_extra/personality.md:51-58` (fears, bullying, academic distress)
- `kb_extra/contact.md` (email, Bilibili UID, partial birthday)
- `kb_extra/bio.md` (age, location)

**Evidence:**
```python
# config.py:69-72
PII_PATTERNS = [
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{3,30}(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr)\b",
]
```
```python
# answer.py:70-74
def apply_pii_filter(text: str) -> str:
    for pattern in config.PII_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return config.REFUSAL_MESSAGE
    return text
```

**Impact:** The PII filter only catches US-style phone numbers and English street addresses. It does not catch email addresses, Chinese phone numbers (11 digits starting with 1), QQ numbers, WeChat IDs, Chinese ID numbers, or any of the sensitive personal facts stored in `personality.md` (fears, bullying experience, academic struggles). The LLM can freely generate answers containing these facts, and the output filter will not block them. Furthermore, the filter runs AFTER the LLM generates the answer, meaning the Groq cloud backend receives the full context (including sensitive chunks) before any filtering occurs.

**Fix:** Implement data classification before indexing. Add `privacy` metadata to each chunk (`public`, `restricted`, `third-party`). Exclude `restricted` chunks from the public BM25 index entirely. Add pre-retrieval filtering for cloud backends. Expand PII patterns to cover email, Chinese phone numbers, QQ, WeChat, and Chinese ID numbers.

---

### SEC-002: Cloud backend (Groq) receives unfiltered context before PII filtering

**Rule:** FASTAPI-SSRF-001 / Data protection
**Severity:** Critical
**Location:** `backend/generation/answer.py:40-56, 59-67`

**Evidence:**
```python
# answer.py:59-67
def generate_answer(question: str, context_chunks: list[dict]) -> str:
    if not context_chunks:
        return config.REFUSAL_MESSAGE
    messages = _build_messages(question, context_chunks)  # context sent to LLM
    if config.LLM_BACKEND == "ollama":
        return _call_ollama(messages)
    if config.LLM_BACKEND == "groq":
        return _call_groq(messages)  # context sent to external API BEFORE pii filter
    raise SystemExit(f"Unknown LLM_BACKEND: {config.LLM_BACKEND}")
```
```python
# answer.py:83-84
answer = generate_answer(question, reranked_chunks[:CONTEXT_TOP_N])
filtered = apply_pii_filter(answer)  # filter runs AFTER generation
```

**Impact:** When `LLM_BACKEND=groq`, the retrieved context chunks (which may contain sensitive personal information per SEC-001) are sent to the Groq cloud API before the PII filter runs. The PII filter only checks the output, not the input. This means sensitive data about James (fears, bullying, academic distress, email, etc.) is transmitted to a third-party server with no pre-transmission filtering.

**Fix:** Filter/classify context chunks BEFORE sending to any cloud backend. Implement a `sanitize_context_for_external()` function that removes or redacts restricted chunks before they leave the local server. For the local Ollama backend, this is less critical but still recommended for defense-in-depth.

---

### SEC-003: Legacy `main.py` serves files via `FileResponse` with user-controlled path components

**Rule:** FASTAPI-FILES-001
**Severity:** Critical
**Location:** `main.py:7-24`

**Evidence:**
```python
# main.py:7-9
@app.get("/scripts/{filename}")
async def serve_scripts(filename: str):
    return FileResponse(f"scripts/{filename}")

# main.py:12-14
@app.get("/assets/pictures/{filename}")
async def serve_assets(filename: str):
    return FileResponse(f"assets/pictures/{filename}")
```

**Impact:** The `filename` parameter comes from the URL path. While FastAPI's path routing prevents simple `../` traversal in the `{filename}` capture (it doesn't match slashes by default), this pattern is fragile and depends on routing behavior rather than explicit validation. If the route pattern were ever changed to `{filename:path}` or if the directory structure changes, path traversal becomes possible. Additionally, `FileResponse` does not set `Content-Disposition: attachment`, so HTML/SVG files served from these directories would be rendered inline, enabling stored XSS if an attacker can place files in these directories.

**Fix:** Remove the legacy `main.py` entirely (it serves obsolete static-site paths unrelated to the current Vite/React build). If file serving is needed in the future, use `StaticFiles` with proper configuration, validate filenames against an allowlist, and serve user-uploaded content as attachments.

---

## High Findings

### SEC-004: No CORS middleware configured on FastAPI app

**Rule:** FASTAPI-CORS-001
**Severity:** High
**Location:** `main.py:1-4`

**Evidence:**
```python
# main.py:1-4
from fastapi import FastAPI
from fastapi.responses import FileResponse

app = FastAPI()
```

**Impact:** No `CORSMiddleware` is configured. When the chatbot API endpoint is added, the React frontend (served from `cheezecats.github.io` or `localhost:5173`) will be blocked by the browser's same-origin policy. The config already defines `CORS_ORIGINS` in `config.py:43-49`, but it is never applied to the FastAPI app. When CORS is eventually added, there is a risk of using `allow_origins=["*"]` with credentials, which is explicitly unsafe per OWASP guidance.

**Fix:** Add `CORSMiddleware` with the explicit origin allowlist from `config.CORS_ORIGINS`. Do not use wildcard origins. Do not enable `allow_credentials` unless cookie-based auth is implemented.

---

### SEC-005: No error handling on Ollama or Groq API calls — system crashes on failure

**Rule:** FASTAPI-SSRF-001 / General robustness
**Severity:** High
**Location:** `backend/generation/answer.py:33-56`

**Evidence:**
```python
# answer.py:33-37
def _call_ollama(messages: list[dict]) -> str:
    import ollama
    resp = ollama.chat(model=config.LLM_MODEL, messages=messages)
    return resp["message"]["content"].strip()

# answer.py:40-56
def _call_groq(messages: list[dict]) -> str:
    resp = httpx.post(GROQ_URL, headers=..., json=..., timeout=60.0)
    resp.raise_for_status()  # raises HTTPStatusError on non-2xx
    data = resp.json()
    return data["choices"][0]["message"]["content"].strip()
```

**Impact:** If Ollama is not running, not loaded, or times out, `ollama.chat()` raises an unhandled exception that propagates to the user as a 500 error with a stack trace. If Groq returns a non-2xx status, `raise_for_status()` raises an `HTTPStatusError`. Neither function has try/except, fallback, or graceful degradation. The `Reranker.__init__` in `inference.py:22` also raises `SystemExit` when the model is missing, which would kill the entire API process if triggered during a request.

**Fix:** Wrap all external calls in try/except. Return a typed error response (`{"status": "unavailable", "answer": "..."}`) instead of crashing. Add a deterministic extractive fallback (return the top chunk text directly) when generation fails. Add bounded timeouts for Ollama calls (currently none).

---

### SEC-006: No request validation or size limits on chatbot input

**Rule:** FASTAPI-VALID-001 / FASTAPI-LIMITS-001
**Severity:** High
**Location:** `backend/cli.py:26-27` (only validation exists), no FastAPI endpoint yet

**Evidence:**
```python
# cli.py:26-27
if len(question) > config.MAX_QUERY_LEN:
    raise SystemExit(f"Question too long (max {config.MAX_QUERY_LEN} characters).")
```

**Impact:** The CLI has a basic length check, but when the FastAPI `/api/chat` endpoint is built, it must use Pydantic models for request validation. Without proper validation, the API is vulnerable to oversized payloads, unexpected field types, and memory/CPU DoS. The `MAX_QUERY_LEN=500` constant exists but is only enforced in the CLI path.

**Fix:** When building the chat endpoint, use a Pydantic model like:
```python
class ChatRequest(BaseModel):
    question: str = Field(max_length=500)
    session_id: str | None = None
```
Reject extra fields. Enforce request body size limits at the edge (Cloudflare/proxy) and in the app.

---

### SEC-007: No security headers or CSP deployed on frontend

**Rule:** REACT-HEADERS-001 / REACT-CSP-001
**Severity:** High
**Location:** `index.html:1-29`

**Evidence:**
```html
<!-- index.html has no CSP meta tag, no security headers -->
<meta charset="UTF-8" />
<meta name="viewport" content="..." />
<meta name="description" content="..." />
<!-- No Content-Security-Policy anywhere -->
```

**Impact:** No `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options`, or `Referrer-Policy` headers are set anywhere (not in `index.html`, not in any server config, not in any edge config visible in the repo). When the chatbot UI is added, LLM-generated answers will be rendered in the DOM. Without CSP, any XSS vulnerability in the rendering pipeline has full access to the page. The `GenerativeCanvas.tsx:135` uses `node.innerHTML = ""` (clearing, not injecting), which is safe for now, but the chatbot component will need to render LLM output.

**Fix:** Add a CSP header at the edge (Cloudflare) or via a `<meta>` tag in `index.html`. Start with a restrictive policy like `script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com`. Add `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY`.

---

## Medium Findings

### SEC-008: PII regex patterns are too narrow for the project's data types

**Rule:** FASTAPI-VALID-001 / Data protection
**Severity:** Medium
**Location:** `backend/config.py:69-72`

**Evidence:**
```python
PII_PATTERNS = [
    r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",  # US phone only
    r"\b\d{1,5}\s+[A-Za-z0-9.\s]{3,30}(?:Street|St|Avenue|Ave|Road|Rd|Lane|Ln|Drive|Dr)\b",  # English address only
]
```

**Impact:** The patterns miss: email addresses (`suihe0812@gmail.com` is in `kb_extra/contact.md`), Chinese phone numbers (11 digits, e.g., `13812345678`), QQ numbers, WeChat IDs, Chinese ID numbers (18 digits), and Chinese addresses. The project is for a student in Shanghai with Chinese and Japanese content, so these patterns are insufficient.

**Fix:** Add patterns for email, Chinese phone (`\b1[3-9]\d{9}\b`), QQ (`\b[1-9]\d{4,10}\b`), and Chinese ID (`\b\d{17}[\dXx]\b`). Better yet, move to a data classification approach (SEC-001) rather than relying on regex.

---

### SEC-009: Groq API key loaded from environment with empty string default

**Rule:** FASTAPI-AUTH-002 / Secret management
**Severity:** Medium
**Location:** `backend/config.py:40`

**Evidence:**
```python
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
```

**Impact:** If the environment variable is not set, `GROQ_API_KEY` defaults to an empty string. The `_call_groq` function will then send `Authorization: Bearer ` (empty token) to the Groq API, which will return a 401 error. While not a direct secret leak, it means the system can silently fail in a confusing way. There is no startup check that verifies the API key is present when `LLM_BACKEND=groq`.

**Fix:** Add a startup validation check: if `LLM_BACKEND == "groq"` and `GROQ_API_KEY` is empty, raise a clear configuration error at startup, not at request time.

---

### SEC-010: No OpenAPI/docs protection planned for production

**Rule:** FASTAPI-OPENAPI-001
**Severity:** Medium
**Location:** `main.py:4` (`app = FastAPI()`)

**Evidence:**
```python
app = FastAPI()  # default: docs_url="/docs", openapi_url="/openapi.json" exposed
```

**Impact:** When the chatbot API is deployed publicly via Cloudflare Tunnel, the default `/docs` and `/openapi.json` endpoints will be publicly accessible, exposing the full API schema to anyone. This is an information disclosure amplifier.

**Fix:** Disable docs in production: `FastAPI(docs_url=None, redoc_url=None, openapi_url=None)`. Or protect them behind authentication/network restrictions.

---

### SEC-011: `innerHTML` usage in GenerativeCanvas (currently safe, but a risk pattern)

**Rule:** REACT-DOM-001
**Severity:** Medium
**Location:** `src/components/GenerativeCanvas.tsx:135`

**Evidence:**
```typescript
node.innerHTML = "";
```

**Impact:** Currently this only clears the node (assigns empty string), which is safe. However, this is a DOM XSS sink pattern. If future code changes assign untrusted content to `innerHTML` on this or similar nodes, it becomes an XSS vector. The chatbot UI will need to render LLM-generated text, which must be done via React's escaped JSX interpolation (`{value}`), not `innerHTML`.

**Fix:** No immediate fix needed for the empty-string assignment. When building the chatbot UI, ensure LLM output is rendered via JSX interpolation, not `innerHTML` or `dangerouslySetInnerHTML`. If markdown rendering is needed, sanitize with DOMPurify.

---

## Low Findings

### SEC-012: No TrustedHostMiddleware configured

**Rule:** FASTAPI-HOST-001
**Severity:** Low
**Location:** `main.py:4`

**Impact:** No `TrustedHostMiddleware` is configured. In production behind Cloudflare Tunnel, arbitrary Host headers could be accepted. This is low severity because Cloudflare Tunnel typically handles host validation at the edge, but defense-in-depth is recommended.

**Fix:** Add `TrustedHostMiddleware` with the production hostname when deploying.

---

### SEC-013: No dependency pinning or lockfile for Python

**Rule:** FASTAPI-SUPPLY-001
**Severity:** Low
**Location:** `pyproject.toml`

**Evidence:**
```toml
dependencies = [
    "fastapi>=0.128.0",
    "uvicorn>=0.40.0",
    ...
]
```

**Impact:** Dependencies use `>=` minimum version constraints with no upper bound or lockfile. This means `pip install` can resolve to different versions across machines (MacBook, 4080 PC, Mac mini), leading to non-reproducible builds and potential exposure to supply-chain attacks via dependency confusion or typosquatting. Security-relevant dependencies (Starlette, python-multipart) have had historical CVEs.

**Fix:** Generate a lockfile (`pip-compile` / `pip freeze > requirements.lock`) and use it for deployment installs. Regularly audit with `pip-audit`.

---

### SEC-014: `localStorage` usage for theme preference (low risk)

**Rule:** REACT-AUTH-001 / JS-STORAGE-001
**Severity:** Low
**Location:** `src/components/ThemeProvider.tsx:25, 41`

**Evidence:**
```typescript
const stored = window.localStorage.getItem("theme");
window.localStorage.setItem("theme", theme);
```

**Impact:** This stores only a theme preference (`"light"` or `"dark"`), not sensitive data. This is safe. However, it should be noted that `localStorage` is accessible to any JS running on the page, so if an XSS vulnerability is introduced (e.g., via the chatbot rendering LLM output unsafely), the stored data could be read or tampered with. Since only theme data is stored, the risk is negligible.

**Fix:** No fix needed. When building the chatbot, do NOT store session tokens, user identifiers, or conversation history in `localStorage`. Use server-side session management instead.
