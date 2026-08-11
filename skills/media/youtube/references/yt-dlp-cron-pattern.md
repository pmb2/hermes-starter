# yt-dlp Cron Pattern — Authenticated Playlist Extraction

## Architecture

Three-layer pattern for reliable YouTube ingestion:

```
Layer 1: Auth check (run first)
  └─ yt-dlp --cookies-from-browser firefox → WL playlist probe
  
Layer 2: Playlist extraction (core)
  ├─ yt-dlp --flat-playlist --dump-single-json → JSON with entries[]
  └─ ⚠️ Must access raw["entries"], not raw (youtube skill pitfall #10)
  
Layer 3: Ingest + Monitoring
  ├─ PIM DB insert (dedup by video_id)
  ├─ Rotating log file (yt_intelligence.log)
  └─ Status JSON (yt_last_status.json)
```

## Reference Implementation

The working implementation lives at:
`${MY_REPOS}\Documents\github\hermes-config\scripts\yt_intelligence.py`

### Key Patterns

**Auth check on startup:**
```python
def _check_auth():
    """Probe WL playlist to verify Firefox cookies work."""
    result = subprocess.run(cmd + ["--cookies-from-browser", "firefox",
                           "https://www.youtube.com/playlist?list=WL"], ...)
    return result.returncode == 0 and result.stdout.strip()
```

**Playlist entries extraction:**
```python
raw = json.loads(result.stdout)
if isinstance(raw, dict) and "entries" in raw:
    entries = raw["entries"]        # ← THIS is the correct way
elif isinstance(raw, list):
    entries = raw
else:
    entries = [raw]
```

**Persistent logging:**
```python
def log(msg, level="INFO"):
    t = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] [{level}] {msg}", flush=True)
    with open("yt_intelligence.log", "a") as f:
        f.write(f"[{t}] [{level}] {msg}\n")

def save_status(status):
    status["last_run_iso"] = datetime.now(timezone.utc).isoformat()
    with open("yt_last_status.json", "w") as f:
        json.dump(status, f, indent=2)
```

## Cron Monitoring

After each run, check `yt_last_status.json`:
- `errors` list — empty = clean run
- `total_videos_found` — should match expected playlist size
- `new_items_inserted` — should be > 0 on first run
- `last_run_iso` — confirms cron is firing

## When to Re-auth

- Auth check fails → YouTube session expired in Firefox
- Open Firefox, log into youtube.com, re-run
- No remote debugging port needed — yt-dlp reads cookies directly from the running browser profile
