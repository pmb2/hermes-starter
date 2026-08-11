# Gemini Summarization for YouTube Transcripts

## Overview
The `yt_summarize.py` script at `${USER_HOME}/FireFox-Phantom-MCP/yt_summarize.py` batch-processes video transcripts through Google's Gemini API (or OpenRouter fallback) to produce structured AI summaries. Added May 29, 2026.

## Dual Provider Architecture

```
Google Gemini API (primary)
  → gemini-2.5-flash-lite (free tier, separate quota pool)
  → If quota exhausted → falls to OpenRouter fallback

Open Router (fallback)  
  → nvidia/nemotron-3-nano-30b-a3b:free (free, no credits needed)
  → Sequential processing to avoid rate limits
```

**Key finding:** OpenRouter's `google/gemini-2.0-flash-001` shows $0.00 pricing but still requires credits — fails with HTTP 402 for non-trivial prompted token counts. Google's own API via `google-generativeai` is genuinely free.

## Model Selection

| Provider | Model | Cost | Quota | Notes |
|----------|-------|------|-------|-------|
| Google API | `gemini-2.5-flash-lite` | Free | ~1,000/day | Separate quota from 2.0-flash — try this first |
| Google API | `gemini-2.0-flash` | Free | 1,500/day | Shared pool with 2.0-flash-001 |
| OpenRouter | `nvidia/nemotron-3-nano-30b-a3b:free` | Free | Rate-limited | Works without credits, 30B params |
| OpenRouter | `liquid/lfm-2.5-1.2b-instruct:free` | Free | Unratelimited | 1.2B — lower quality but always available |

## How it Works

1. **Input**: Reads `youtube_transcripts.json` from `${USER_HOME}\FireFox-Phantom-MCP`
2. **Filtering**: Skips entries with existing `summary` field (idempotent)
3. **Processing**: `ThreadPoolExecutor` with N parallel workers (configurable via `--batch-size`)
4. **API**: Google's `google-generativeai` library for primary; OpenRouter REST API for fallback
5. **Output**: Saves `summary` dict back into `youtube_transcripts.json` + standalone `youtube_summaries.json`
6. **Persistence**: Incremental save after each batch via `youtube_summary_progress.json`

## Prompt

The structured prompt asks for JSON output only:
- `one_liner`: Single sentence (max 20 words)
- `topics`: Up to 5 specific topics
- `insights`: 3 bullet points, each under 25 words
- `actionable`: Concrete actions the operator could take (or empty array)
- `relevance`: Category from list (AI_Engineering, Business_Development, Health_Wellness, Legal_Compliance, Finance_Investment, General_Knowledge)
- `importance_rating`: 1 (trivia) to 10 (must-know)
- `key_quotes`: Up to 2 verbatim quotes (or empty array)

## Rate Limiting

- **Google:** 4 retries with 3s/6s/12s/24s backoff + staggered parallel starts + 4s inter-batch delay
- **OpenRouter:** Sequential (batch_size=1) with 2s inter-request delay
- Use `--batch-size 1 --provider openrouter` for guaranteed completion when rate-limited

## Performance

- **Google parallel (batch_size=5):** ~20-30 videos/min = 478 videos in ~20 min
- **OpenRouter sequential (batch_size=1):** ~5-6 videos/min = 478 videos in ~80 min

## Integration

Auto-triggered by `yt_transcripts.py`. Full pipeline: `yt_extract.py → yt_transcripts.py (calls yt_summarize.py) → pim_sync_mempalace.py`
