# YouTube Upload-Date Filtering (yt-dlp)

## Why This Exists

The YouTube transcripts JSON (`youtube_transcripts.json`) has 985 videos, 463 with AI summaries — but NONE of them have `_summarized_at` populated. The `upload_date` and `publish_date` fields don't exist in the extraction pipeline's output.

Without upload-date filtering, every full scan would report ALL 463 summarized videos as "new" — including 3-5 year old videos from the "Health" playlist that the operator saved years ago but the pipeline just now summarized.

## The Fix

The `pulse_scan.py` script (at `agent-fleet/teams/social-media/pulse/tooling/pulse_scan.py`) uses yt-dlp to batch-fetch upload dates for candidate videos:

```python
def get_youtube_upload_dates_batch(video_ids):
    """Get upload dates for multiple videos in one yt-dlp call."""
    urls = [f"https://www.youtube.com/watch?v={v}" for v in video_ids]
    result = subprocess.run(
        ["yt-dlp", "--print", "%(id)s %(upload_date)s"] + urls,
        capture_output=True, text=True, timeout=60
    )
    dates = {}
    for line in result.stdout.strip().split('\n'):
        parts = line.strip().split()
        if len(parts) == 2:
            dates[parts[0]] = parts[1]  # video_id -> YYYYMMDD
    return dates
```

## Key Constants

- `YOUTUBE_UPLOAD_CUTOFF_DAYS = 60` — videos older than 60 days are excluded
- `YT_DLP_BATCH_SIZE = 15` — max 15 URLs per yt-dlp call to avoid rate limiting

## Caching

Upload dates are cached in `last_check.json` under `youtube_upload_dates` key (dict of `video_id -> YYYYMMDD`). Only uncached IDs trigger yt-dlp calls on each scan. This means after ~30 scans (with 15 per batch), all 463 videos will be cached and no further yt-dlp calls are needed — the upload-date filter becomes free.

## Quick Mode

In `--quick` mode, yt-dlp calls are skipped entirely. Upload-date filtering falls back to: if a video has no cached upload date and we're in quick mode, it's INCLUDED (safe passthrough). This prevents quick scans from dropping valid new content.

## Testing

```bash
# Test batch upload-date lookup
yt-dlp --print "%(id)s %(upload_date)s" \
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ" \
  "https://www.youtube.com/watch?v=jNQXAC9IVRw"

# Expected output format:
# dQw4w9WgXcQ 20091025
# jNQXAC9IVRw 20050423
```
