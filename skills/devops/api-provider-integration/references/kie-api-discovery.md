# Kie.ai API — Discovered via Live Testing (Jul 2026)

All values confirmed against production. Replaces any assumptions from docs.

## Base

```
Base URL: https://api.kie.ai
Auth: Bearer <KIE_API_KEY>
```

## Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/jobs/createTask` | POST | Create video/image generation task |
| `/api/v1/jobs/recordInfo?taskId=<id>` | **GET** (not POST!) | Poll task status |
| `/api/v1/chat/credit` | GET | Check credit balance → `{"data": 80.0}` |
| `/api/v1/common/download-url` | POST | Convert temp URL → signed R2 URL (20 min) |

## Model Names (API `"model"` field)

| Use case | API model name | Docs URL has |
|----------|---------------|--------------|
| Seedance 2.0 | `bytedance/seedance-2` | ✅ |
| Seedance 2.0 Fast | `bytedance/seedance-2-fast` | ✅ |
| Seedance 2.0 Mini | `bytedance/seedance-2-mini` | ✅ |
| GPT Image 2 (t2i) | `gpt-image-2-text-to-image` | ❌ `gpt/` prefix in URL |
| GPT Image 2 (i2i) | `gpt-image-2-image-to-image` | ❌ `gpt/` prefix in URL |

## Resolution (GPT Image 2)

**Capitalized K only:** `1K` `2K` `4K` — not `1k`/`2k`/`4k`/`1024`.

Pricing: 1K=$0.03 (6cr), 2K=$0.05 (10cr), 4K=$0.08 (16cr).

## Task States

| `data.state` | Meaning | Action |
|---------------|---------|--------|
| `generating` | Still processing | Poll again |
| `pending` / `queueing` | Queued | Poll again |
| `success` | Done | Parse `data.resultJson` |
| `fail` | Failed | Check `data.failMsg` |

Result extraction: `json.loads(data["resultJson"])["resultUrls"][0]`

## Download URL

POST body key is `"url"` — all other variants (`fileUrl`, `imageUrl`, etc.) return 422.

```json
{"url": "https://tempfile.aiquickdraw.com/..."}
→ {"code": 200, "data": "<signed_r2_url_20min>"}
```

## Prompt Rejection

Non-ASCII characters (→, —, " ", ' ') cause `"Internal Error, Please try again later"`
with `state: fail, failCode: 500`. Sanitize before sending.

Tested: 2/2 fails with `→` in prompt, 3/3 succeeds without.

## Retry Pattern

Transient Internal Errors hit ~30% of requests. Retry 3× with 5s/10s/15s backoff.
This is the expected pattern, not a bug.
