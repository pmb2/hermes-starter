# Trailer & Derivative Video Builder

Build derivative videos (trailers, compilations, remixes) from existing or new FLUX keyframes.

## Two Builders

### `build_trailer.py` (v1 — Legacy)
- Reuses existing Ep1 FLUX keyframes only
- 6 scenes, 3 keyframes each
- Single Chatterbox TTS call (may timeout on long text)
- Output at `outputs/sycamore-series-trailer.mp4`

### `build_trailer_v2.py` (v2 — Current)
- 8 scenes with 6 unique FLUX prompts each (48 keyframes total)
- Two modes:
  - `--generate-flux`: Generate new FLUX keyframes via ComfyUI
  - `--skip-flux` (default): Reuse existing Ep1 keyframes as fallback
- TTS chunking: splits narration into ~1000-char chunks to avoid Chatterbox timeouts
- Pillow-based text overlay (reliable, vs broken FFmpeg drawtext)
- Auto-runs QA pipeline after build (`--skip-qa` to bypass)
- Writes manifest.json for social post generator
- Scene videos built with Ken Burns zoompan

## Key Commands

```bash
# Full rebuild with 48 new FLUX keyframes (schnell at 20 steps, ~28 min):
PYTHONUNBUFFERED=1 python build_trailer_v2.py --generate-flux \
  --model flux1-schnell-fp8.safetensors --steps 20

# Quick reuse without TTS:
python build_trailer_v2.py --skip-tts --skip-qa --skip-flux

# With FLUX.1-dev (once downloaded):
python build_trailer_v2.py --generate-flux \
  --model flux1-dev-fp8.safetensors --steps 30
```

## TTS Chunking Logic

The `generate_tts()` function in v2 splits long narration at sentence boundaries (~1000 chars per chunk). Each chunk is sent to Chatterbox with 120s timeout (not 300s). Chunks are concatenated via FFmpeg concat demuxer. This avoids the hang/retry loop that plagues single-large-request approach.

## Text Overlay

Uses `scripts/text_overlay.py` — creates a single RGBA PNG with Pillow, then composites via FFmpeg overlay filter. This avoids the Windows FFmpeg 8.1 drawtext crash (exit code 4294967274 = STATUS_ACCESS_VIOLATION from libfreetype).

## Known Limitations

- 48 FLUX keyframes × ~35s each = ~28 min total generation time on RTX 3090
- With `--lowvram`, expect 2-5 min per frame
- VRAM must be >17GB free for `--normalvram` mode
