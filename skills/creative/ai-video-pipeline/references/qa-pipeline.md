# QA Pipeline: Post-Generation Audio & Repetition Detection

Script: `scripts/qa_pipeline.py`
Dependencies: `pip install jiwer librosa pydub faster-whisper`

## Usage

```bash
# Quick check (CPU whisper, no GPU needed)
python scripts/qa_pipeline.py outputs/my-video.mp4 --quick

# Full check with WhisperX (GPU, word-level timestamps)
python scripts/qa_pipeline.py outputs/my-video.mp4

# Compare against original script
python scripts/qa_pipeline.py outputs/my-video.mp4 --script scripts/original-script.md

# Save report to specific path
python scripts/qa_pipeline.py outputs/my-video.mp4 --output my-report.md
```

## What It Checks

| Check | Method | Output |
|-------|--------|--------|
| **Word stutter** | Regex for consecutive same-word ("the the the") | Locations + counts |
| **Phrase repetition** | n-gram analysis (3-8 word windows) | Repeated phrases |
| **Sentence repetition** | Line-by-line comparison of ~20+ char segments | Duplicate sentences |
| **Script comparison** | jiwer WER + alignment | Insertions, deletions, substitutions vs original script |
| **Silence gaps** | librosa silence detection | Gaps >0.5s with timestamps |
| **Clipping** | librosa peak detection | Samples at max amplitude |
| **Excessive onsets** | librosa onset detection | Clicks/pops rate per second |
| **Transcription** | faster-whisper (CPU) or WhisperX (GPU) | Full transcript + word-level timestamps |

## Modes

### --quick (CPU-only)
Uses `faster-whisper` on CPU with `int8` quantization. No GPU required. Produces approximate word timestamps via even-split of segment durations. Good for post-commit CI checks.

### Full (default, GPU)
Uses `WhisperX` with wav2vec2 alignment for accurate word-level timestamps (within 10-50ms). Requires CUDA. Best for final QA before release.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | PASS — fewer than 3 issues |
| 1 | FAIL — 3+ issues found |

## Threshold Tuning by Content Type

The QA pipeline's default thresholds are calibrated for fast-paced narrated content. For **documentary/trailer narration** with natural dramatic pacing, raise thresholds to avoid false positives:

| Check | Default Threshold | Documentary/Trailer | Why |
|-------|-------------------|-------------------|-----|
| Silence gaps | 0.5s | **1.5s** | Documentary narrators pause 0.5-1.2s between sentences for dramatic effect |
| Excessive onsets | 10/s | **10/s** (already calibrated for trailer audio) | Trailer audio with musical emphasis hits 5-9/s — normal. Only >10/s with audible clicks is a problem |

Update these in `scripts/qa_pipeline.py`:
- Line 241: `if gap_dur > 1.5:` (documentary)
- Line 261: `if len(onset_frames) > len(y) / sr * 10:` (trailers — already correct)

For **pure speech TTS without music**, the onset threshold can safely be lowered to >6/s. For **trailer/music content**, keep at >10/s.

## Common Findings

- **Silence gaps 0.5-0.8s spaced evenly** — STRONG indicator of TTS chunk concat gaps. Each gap corresponds to a boundary between TTS chunks. Caused by baked-in trailing silence in each chunk WAV. Fix: strip trailing silence per chunk via FFmpeg `silenceremove` filter before concatenation (see `references/chatterbox-tts.md` for implementation). After the fix, no gaps >0.5s should remain.
- **Silence gaps >1s erratic** — Genuine issue. Long pauses in TTS output between sentences or section breaks. May need to shorten narration or adjust speaking pace.
- **Excessive onsets** — Threshold is >10 onsets/second (librosa onset detection). Chatterbox TTS natural speech rhythm can reach 5-8/s. Trailer content with dramatic emphasis or musical overlay can hit 8-10/s. Only a problem if >10/s AND coinciding with audible clicks/pops in the audio. For pure speech TTS without music, lowering to >6/s is safe. For trailer/music content, keep at >10/s. See `scripts/qa_pipeline.py` line 261.
- **Repeated sentences** — Often from dramatic parallel structures ("Sycamore isn't X. Sycamore is Y."). These are intentional but still flagged. Review manually.

## Integration Points

- `create_video_v2.py` — Run QA after assembly step
- `build_trailer.py` — Run QA after trailer assembly
- A `--qa` flag on either script would auto-run QA post-production
