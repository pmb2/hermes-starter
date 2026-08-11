# PIM .env API Key Configuration

## Current Setup (as of 2026-05-30)

**Primary: OpenCode Go API** (has working credits)
- Base URL: `https://opencode.ai/zen/go/v1`
- Model: `deepseek-v4-flash`
- API Key: Stored in `~/.local/share/opencode/auth.json` under `opencode-go.key`
- Key length: 67 chars, starts with `sk-3Ihav...`

**Fallback: GitHub Copilot API** (when OpenCode Go key unavailable)
- Uses `gh auth token` (40-char GitHub OAuth)
- Triggers when `~/.local/share/opencode/auth.json` is missing or corrupt

**OpenRouter: REMOVED as primary** (returns 401 Unauthorized or 402 Payment Required)
- Previously used but had no credits
- Falls back to OpenRouter only if neither OpenCode Go nor Copilot keys are available

## .env File Layout

Written by `ingest-chatgpt-grok.sh` or `pim-pipeline.py` before extraction phases:

```env
LLM_PROVIDER=openrouter
LLM_API_BASE_URL=https://opencode.ai/zen/go/v1
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=*** primary key}
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=nomic-embed-text
DATABASE_URL=sqlite+aiosqlite:///./pim.db
```

## Key Injection Logic (in Python)

```python
# Priority: OpenCode Go > GitHub Copilot > OpenRouter
auth_path = os.path.expanduser(r"~/.local/share/opencode/auth.json")
if os.path.exists(auth_path):
    with open(auth_path) as f:
        auth = json.load(f)
        oc_key = auth.get("opencode-go", {}).get("key", "")

llm_key = oc_key or gh_token  # gh_token from `gh auth token`
llm_base = "https://opencode.ai/zen/go/v1"
```

## Embedding 404 When Using OpenCode Go as LLM Provider

When `LLM_API_BASE_URL=https://opencode.ai/zen/go/v1`, the PIM embedder at `app/core/embedder.py` sends to `https://opencode.ai/zen/go/v1/embeddings` which returns **404 Not Found** — OpenCode Go does not serve an embeddings API endpoint. The pipeline still works (extraction and summarization complete) but embeddings fail silently (logged as warnings).

**Fix options:**
1. **Use OpenRouter for embeddings** — hardcode `https://openrouter.ai/api/v1` in the embedder's base URL (OpenRouter supports `/embeddings`)
2. **Use local sentence-transformers** — set `EMBEDDING_PROVIDER=local` in .env (already set, but the embedder code doesn't check `EMBEDDING_PROVIDER` — it always uses the API)

The embedder code at `app/core/embedder.py:50` has a fallback:
```python
base_url = settings.llm_api_base_url or "https://openrouter.ai/api/v1"
```
But this only activates when `LLM_API_BASE_URL` is empty. Since the .env explicitly sets it to OpenCode Go, the fallback never fires.

**Fix for immediate use:** Change the embedder to use a separate base URL for embeddings, or check `EMBEDDING_PROVIDER` setting and handle `local` properly.

## Verification

```bash
# Test OpenCode Go API directly:
python -c "
import json, httpx, asyncio
async def test():
    with open(os.path.expanduser(r'~/.local/share/opencode/auth.json')) as f:
        key = json.load(f)['opencode-go']['key']
    async with httpx.AsyncClient(timeout=15) as c:
        r = await c.post('https://opencode.ai/zen/go/v1/chat/completions',
            headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
            json={'model': 'deepseek-v4-flash', 'messages': [{'role':'user','content':'hello'}], 'max_tokens': 50})
        print(r.status_code, r.json()['choices'][0]['message']['content'])
asyncio.run(test())
"
# Should print: 200 hello
```
