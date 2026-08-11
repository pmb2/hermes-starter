# Chatterbox TTS API Integration

Chatterbox is a FOSS TTS system (~25K GitHub stars) running as a Docker container.

## Setup

```bash
docker pull travisvn/chatterbox-tts-api:latest
docker run -d --name chatterbox-tts-api -p 8004:5123 travisvn/chatterbox-tts-api:latest
```

Internal port 5123, mapped to host port 8004.

## API: Generate Speech

**Endpoint:** `POST /v1/audio/speech` (OpenAI-compatible)

**⚠️ Windows Docker IPv6 routing:** Always use `127.0.0.1` (IPv4), not `localhost`. On Windows, `localhost` resolves to `::1` (IPv6) which routes through Docker Desktop's `wslrelay.exe` — this causes connections to hang or timeout on long TTS requests (>30s). `127.0.0.1` bypasses the relay entirely and hits the Docker port mapping directly.

```bash
# ✅ WORKS
curl http://127.0.0.1:8004/v1/audio/speech ...

# ❌ HANGS on long requests
curl http://localhost:8004/v1/audio/speech ...
```

**Request body:**
```json
{
  "model": "Chatterbox",
  "input": "The text to synthesize",
  "voice": "Alice.wav",
  "response_format": "wav"
}
```

**Python:**
```python
import requests

resp = requests.post("http://127.0.0.1:8004/v1/audio/speech",
    json={
        "model": "Chatterbox",
        "input": "Narration text here...",
        "voice": "Alice.wav",
        "response_format": "wav"
    },
    timeout=120)

with open("output.wav", "wb") as f:
    f.write(resp.content)
```

## Response

Returns raw WAV bytes. At 24 kHz sample rate. Content-Type: `audio/wav`.

## Voice Files

The default voice file is `Alice.wav` (~2 MB, 24 kHz). Voice files are stored in the container at `/app/voices/`. Custom voices can be mounted via Docker volume.

## Chunked Narration with Gap-Free Concatenation

When generating long narrations (>1000 chars), Chatterbox handles individual chunks more reliably than one massive request. However, naively concatenating chunk WAVs produces audible silence gaps (0.5-1.2s) because each chunk has baked-in trailing silence from the TTS model output.

### Required: Silence Removal Per Chunk

Strip trailing silence from each chunk WAV before concatenating. This uses FFmpeg's `silenceremove` filter which detects where audio falls below a threshold and trims from that point:

```python
def _trim_trailing_silence(wav_path, threshold="-35dB"):
    """Strip trailing silence from a WAV file in-place."""
    trimmed = Path(str(wav_path).replace(".wav", "_trim.wav"))
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(wav_path),
            "-af", f"silenceremove=start_periods=0:stop_periods=-1:stop_duration=0.05:stop_threshold={threshold}",
            "-acodec", "pcm_s16le", str(trimmed)
        ], capture_output=True, timeout=30)
        if trimmed.exists() and trimmed.stat().st_size > 500:
            trimmed.replace(wav_path)  # Replace original
            return True
        elif trimmed.exists():
            trimmed.unlink()
    except:
        pass
    return False
```

Parameters explained:
- `start_periods=0` — Do NOT trim leading silence (preserves natural speech onset)
- `stop_periods=-1` — Trim ALL trailing silence segments
- `stop_duration=0.05` — Consider 50ms of below-threshold audio as "silence"
- `stop_threshold=-35dB` — Below this level is silence (natural for speech WAVs; adjust for loud TTS)

### Required: Concat Audio Filter (NOT Demuxer)

After trimming, concatenate chunks using FFmpeg's **concat audio filter** instead of the concat demuxer with `-c copy`. The filter operates in FFmpeg's filtergraph, producing sample-accurate transitions. The demuxer+stream-copy approach literally pastes raw PCM data including any residual transients:

```python
# ❌ DON'T: This produces gaps
# subprocess.run(["ffmpeg","-y","-f","concat","-safe","0",
#     "-i","chunk_list.txt","-c","copy","output.wav"])

# ✅ DO: Use concat audio filter
inputs = []
for cp in chunk_paths:
    inputs.extend(["-i", str(cp)])
parts = "".join([f"[{i}:a]" for i in range(len(chunk_paths))])
filter_complex = f"{parts}concat=n={len(chunk_paths)}:v=0:a=1[out]"
subprocess.run([
    "ffmpeg", "-y", *inputs,
    "-filter_complex", filter_complex,
    "-map", "[out]", str(output_path)
], capture_output=True, timeout=120)
```

### Progressive Silence Trimming (Optional)

For extremely long narrations, you can also strip leading silence from each chunk (except the first) to overlap speech slightly:

```python
# For chunk i > 0, trim BOTH leading and trailing silence
if i > 0:
    subprocess.run([
        "ffmpeg", "-y", "-i", str(chunk_path),
        "-af", "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-35dB:stop_periods=-1:stop_duration=0.05:stop_threshold=-35dB",
        "-acodec", "pcm_s16le", str(trimmed)
    ], capture_output=True, timeout=30)
```

This creates a tighter, more natural flow between sentences. Use sparingly — over-trimming causes words to overlap.

### Verification

After assembly, check for remaining gaps with the QA pipeline. No silence gaps >0.5s should remain:

```bash
python scripts/qa_pipeline.py outputs/final.mp4 --quick
```

## Alternative TTS: Chatterbox vs Fish Speech

| Criterion | Chatterbox | Fish Speech 2 |
|-----------|------------|---------------|
| Voice quality | ★★★★★ | ★★★★ |
| Docker image size | 14.9 GB | ~5 GB |
| API format | Custom JSON | OpenAI-compatible |
| Speed | Fast (~1s/10s audio) | Very fast (~0.5s/10s) |
| Voice cloning | Built-in | Available |
| Port | 8004 (maps 5123) | 8080 |
