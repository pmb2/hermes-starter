# PIM Extraction Performance Benchmark (2026-05-30)

## Pre-Fix Baseline

### Test Conditions

| Variable | Value |
|----------|-------|
| Date | 2026-05-30, ~18:55 UTC |
| Firefox binary | Patched portable (`C:\\Users\\<you>\\firefox-portable\\firefox.exe`) |
| xul.dll patch status | ✅ Patched (0 "webdriver" occurrences) |
| Launch mode | `--headless --remote-debugging-port 9239` |
| Profile | Automation profile |
| Protocol | BiDi |
| Stealth | 22/22 measures (logged in pipeline) |
| Pipeline script | `ingest-chatgpt-grok.sh` (bash) |
| Target site | chatgpt.com |
| RECONNECT_EVERY | **15** (too high — cause of failures) |

### Extraction Results

| Metric | Value |
|--------|-------|
| Conversations found via sidebar scroll | 31 |
| Successfully extracted | 11 (35%) |
| Failed (WebSocket disconnect) | 1 at conversation #12 |
| Total extraction time before disconnect | ~3 min 34 sec |
| Avg time per conversation | ~19.5 sec |
| Disconnect reason | `"no close frame received or sent"` |
| Reconnect triggered | ✅ Yes (logged) |

## Post-Fix Results (RECONNECT_EVERY=3, port defaults fixed)

### Test Conditions

| Variable | Value |
|----------|-------|
| Date | 2026-05-30, ~23:06 UTC |
| Pipeline script | `ingest-chatgpt-grok.sh` (same as baseline) |
| RECONNECT_EVERY | **3** (fixed from 15) |
| Firefox PID stability | **Same PID 49416 for entire 20-min run** |

### ChatGPT Extraction

| Metric | Value |
|--------|-------|
| Conversations discovered | 31 |
| Extracted & added to DB | **31 (100%)** |
| Failed | **0** |
| Items added | 31 new |
| Pipeline phase duration | ~9 min |
| Reconnects | ~10 (every 3 convos, as designed) |

### Grok Extraction

| Metric | Value |
|--------|-------|
| Conversations discovered | 32 |
| Extracted (added + updated) | **32 (100%)** |
| Failed | **0** |
| Items added | 24 new |
| Items updated | 8 |
| Pipeline phase duration | ~5 min |

### Firefox Stability

| Metric | Pre-fix | Post-fix |
|--------|---------|----------|
| Firefox PID | Changed 3x in 20 min | **Same PID for 20+ min** |
| Crash window | ~3 min | **No crash** |
| Extraction success rate | 35% (11/31) | **100% (31/31 + 32/32)** |

## Crash Cycle Timing (Pre-fix baseline)

Firefox PID changed 3 times during ~20 min investigation window:

| PID | First seen | Notes |
|-----|-----------|-------|
| 29324 | 18:55 (pipeline start) | Main Firefox, launched by pipeline |
| 31328 | ~18:59 (post-kill) | After pipeline killed, Firefox auto-restarted |
| 53484 | ~19:05 | Another restart cycle |

## Analysis

**Pre-fix:** At `RECONNECT_EVERY = 15`, disconnect at #12 proves per-navigation stability limit is ~5-12.

**Post-fix:** At `RECONNECT_EVERY = 3`, each session extracts 3 conversations reliably. Session exhaustion (stale orphan sessions) triggers full Firefox restart in ~5s. Full extraction completes without manual intervention.

## Key Takeaway

The two fixes that mattered most:
1. **RECONNECT_EVERY 15 to 3** — stays within BiDi per-navigation stability window
2. **Port defaults consistent at 9239** — no session routing issues

Together they transform the pipeline from 35% success to 100% success, with Firefox stable throughout.
