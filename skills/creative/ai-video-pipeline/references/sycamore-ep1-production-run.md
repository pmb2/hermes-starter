# Sycamore Episode 1 — Full Production Run Reference

> **Date:** 2026-06-10  
> **Video:** "I Asked ChatGPT How to Hack a Russian Oligarch — Part 1: Hypothetically Speaking"  
> **Runtime:** 38:15 (target 20-40 min)  
> **Pipeline:** run_production.py (679 lines custom runner)  
> **Output:** 117MB, 1920x1080, H.264/AAC

## Results

| Metric | Value |
|--------|-------|
| Scenes | 19 (18 story + 1 credits epilogue) |
| FLUX keyframes | 57 (3 per scene × 18 + 2 for credits) |
| TTS clips | 9 (dialog-heavy scenes, Chatterbox Alice voice) |
| Total runtime | 2,295s (38:15) |
| Final file | 117MB, 1920×1080, H.264, ~425 kbps |
| All clip durations | Correct after audio muxing fix |

## Key Techniques Discovered

### Scene 4 FLUX Failure Recovery
When FLUX fails mid-production (happened at Scene 4 — "No images found in output"):
- The prompt itself was clean — transient ComfyUI issue
- **Fix:** Add fallback with simplified prompt → `"MS Paint simple illustration: {scene_title}, flat colors, hand-drawn"`
- **Better fix:** Add 3-second `time.sleep()` between FLUX requests for VRAM recovery
- **Best fix** (implemented): Retry with different seed after failure

### JSON Escaping for FLUX Prompt Substitution
The workflow template has `{{POSITIVE_PROMPT}}` placeholders. String replacement with raw prompt text breaks JSON when prompts contain quotes, backslashes, or special characters.

**Fix:** Use `json.dumps(prompt)[1:-1]` to JSON-escape before substitution:
```python
"{{POSITIVE_PROMPT}}": json.dumps(prompt)[1:-1],
```

### Audio Muxing — The `-shortest` Trap
`ffmpeg -shortest` truncates the output to match the shorter input. When short/no audio is muxed with a 135-second video, the output is only as long as the audio clip.

**Fix:** check audio duration vs video duration:
- If audio ≥ 50% of video: mux without `-shortest` (audio plays once while video runs full length)
- If audio < 50% of video: loop the audio via `-stream_loop N` then `-shortest`
- If no audio at all: just output the raw video

### Production Runner Architecture
The `run_production.py` pattern is a flat, self-contained production script (679 lines) that's separate from the reusable pipeline (`create_video_v2.py` at 1,414 lines). This dual-file pattern handles:
- Custom script format parsing (Sycamore markdown with `[VISUAL: ...]` blocks)
- Per-scene FLUX generation with VRAM management
- TTS generation with retry logic
- Frame interpolation + Ken Burns
- Scenes → final assembly via FFmpeg concat demuxer
- Parallel-friendly (each scene is independent)

### Scene List (19 total)

| # | Title | Duration | Keyframes | TTS? | Clip Size |
|---|-------|----------|-----------|------|-----------|
| 1 | The Setup | 105s | 3 | Yes | 9.3MB |
| 2 | The Iceberg | 105s | 3 | No | 7.9MB |
| 3 | The Cyprus Connection | 135s | 3 | No | 5.9MB |
| 4 | The Documentation Protocol | 135s | 3 | No | 3.6MB |
| 5 | Swiss Private Banking | 150s | 3 | No | 27MB |
| 6 | Signature Forgery | 150s | 3 | No | 26.9MB |
| 7 | The 4-Second Compliance Window | 150s | 3 | No | 26.9MB |
| 8 | Enter Sycamore | 135s | 3 | Yes | 4.9MB |
| 9 | Browser Automation | 150s | 3 | No | — |
| 10 | Inside the Banking Portal | 135s | 3 | No | — |
| 11 | The Compliance Officer's Screen | 135s | 3 | No | — |
| 12 | The UAE Layer | 105s | 3 | Yes | — |
| 13 | The Crypto Tumble | 135s | 3 | No | — |
| 14 | Microfinance Exit Strategy | 150s | 3 | No | 29.4MB |
| 15 | The Wife — Instagram | 150s | 3 | No | 18.9MB |
| 16 | The Phone Call | 135s | 3 | Yes | 3.2MB |
| 17 | The Realization | 135s | 3 | Yes | 12.0MB |
| 18 | The Cliffhanger | 105s | 3 | No | 8.9MB |
| 19 | End Credits | 90s | 2 | No | 7.1MB |

### Cliffhanger Text (Scene 18)
```
Telegram notification from "SYCAMORE":
> "Check your email. I've started without you."
```
Followed by black screen → "END OF PART 1" → "Sycamore Part 2 — COMING SOON"

## Files Created (all in git repo)

| File | Lines | Purpose |
|------|-------|---------|
| `scripts/sycamore-ep1-script.md` | 757 | Full script with visual directions |
| `strategy/sycamore-asset-matrix.md` | 589 | Visual consistency bible |
| `run_production.py` | 679 | Custom production runner for this format |
| `outputs/sycamore-episode-1-final.mp4` | — | Final video (117MB) |
| `assets/sycamore-ep1/` | 56+9 | Keyframes + TTS clips |
