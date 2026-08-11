# Cron Guardian: HTTP 404 model_not_found Should Not Pause Jobs (2026-08-10)

A real-world case of the "non-transient still acts immediately" rule being too
broad.

## The Problem

Cron Guardian (`cron-guardian.py`) checks model health with a two-tier probe:

1. **Tier 1** — HTTP GET `/models` (reachability)
2. **Tier 2** — HTTP POST `/chat/completions` (credits/inference)

The OmniRoute proxy at `localhost:20128` returns HTTP 404 from `GET /models`
(because OmniRoute doesn't expose that endpoint). The `check_model_health()`
function treated this as `healthy=True, has_credits=False` — but the downstream
pause logic checked `if not healthy or not has_credits:` and paused ALL jobs.

So every 15 minutes, the Cron Guardian paused 54 cron jobs because a 404
response was classified as "no credits."

## The Fix

Add an explicit HTTP 404 handler in `check_model_health()`:

```python
except urllib.error.HTTPError as e:
    body = e.read().decode(errors="ignore")[:300]
    if e.code == 404:
        # 404 from /models means the proxy doesn't expose this endpoint.
        # This is NOT a credit issue — treat as healthy.
        return True, f"model_not_found (HTTP 404 — proxy may not expose /models)", True
    if e.code == 429:
        return True, f"API reachable but credits exhausted (HTTP 429)", False
    # All other HTTP errors
    return False, f"HTTP {e.code}: {body}", False
```

Key insight: `has_credits=True` on the 404 branch. The downstream pause logic
only pauses when `has_credits=False`, so the 404 no longer triggers a pause.

## Why This Happened

The Cron Guardian was designed for direct provider API health checks (OpenAI,
DeepSeek, etc.) where `/models` always returns 200. When the user added an
OmniRoute proxy, the check started hitting a different API surface. The
guardian needs to be proxy-aware.

## Design Principle

HTTP 404 is NOT a credit/outage signal. It's a "this endpoint doesn't exist"
signal. Never treat it as a model outage. The correct classification:

| HTTP Code | Classification | Action |
|-----------|---------------|--------|
| 200 | Healthy | Continue |
| 401/403 | Auth failure | Pause (non-transient) |
| 404 | Not found | Continue (proxy quirk) |
| 429 | Rate limited | Continue (not an outage) |
| 5xx | Server error | Pause (provider down) |
| Timeout/DNS | Transient | Retry, then pause