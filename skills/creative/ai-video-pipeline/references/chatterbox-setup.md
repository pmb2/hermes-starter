# Chatterbox TTS Setup

Chatterbox is a SoTA open-source TTS system (25K GitHub stars by Resemble AI) with voice cloning. Two Docker images are available.

## Docker Image Comparison

| Aspect | travisvn/chatterbox-tts-api | devnen/Chatterbox-TTS-Server |
|--------|-----------------------------|------------------------------|
| **Port** | 5123 (internal) | 8004 (docker-compose default) |
| **Hub port** | Map `-p 8082:5123` | Map `-p 8004:8004` |
| **Size** | 14.9GB | Build from source (~8GB) |
| **API** | OpenAI-compatible `/v1/audio/speech` | Custom `/tts` + OpenAI `/v1/audio/speech` |
| **Reliability** | ⚠️ Crashes on TTS requests (empty reply) | ✅ Stable, tested working |
| **Voices** | Default only | 28 predefined voices (Alice, Bob, etc.) |
| **Web UI** | No | Yes (port 8004) |

**RECOMMENDED: devnen/Chatterbox-TTS-Server** — the travisvn image has a bug causing HTTP 000 (empty reply) on generation. The devnen build works reliably.

## Option A: devnen/Chatterbox-TTS-Server (RECOMMENDED)

### Clone and Build

```bash
git clone https://github.com/devnen/Chatterbox-TTS-Server.git
cd Chatterbox-TTS-Server

# For CUDA 13.0+ (check `nvidia-smi` for your version):
docker compose -f docker-compose-cu130.yml up --build -d
```

### API Usage

**This IS the working endpoint.** The `/tts` endpoint uses a custom FastAPI schema:

```bash
curl -X POST http://127.0.0.1:8004/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Your text to speak here.",
    "voice_mode": "predefined",
    "predefined_voice_id": "Alice.wav",
    "output_format": "wav"
  }' \
  -o output.wav
```

**Key field names (not OpenAI-compatible)**:
- `text` — input text (required)
- `voice_mode` — `"predefined"` or `"clone"` (default: `"predefined"`)
- `predefined_voice_id` — one of 28 voices, **MUST include `.wav` extension** (e.g., `"Alice.wav"`, `"Elena.wav"`)
- `output_format` — `"wav"`, `"opus"`, or `"mp3"` (default: `"wav"`)
- `split_text` — boolean, auto-splits long text (default: true)
- `chunk_size` — character limit per chunk (50-500, default: 120)

**Available voices**: Abigail, Adrian, Alexander, Alice, Austin, Axel, Connor, Cora, Elena, Eli, Emily, Everett, Gabriel, Gianna, Henry, Ian, Jade, Jeremiah, Jordan, Julian, Layla, Leonardo, Michael, Miles, Olivia, Ryan, Taylor, Thomas

### Check Voices

```bash
curl http://127.0.0.1:8004/v1/audio/voices
curl http://127.0.0.1:8004/api/model-info
```

### Health Check

```bash
curl http://127.0.0.1:8004/  # Returns Web UI HTML
```

## Option B: travisvn/chatterbox-tts-api (NOT RECOMMENDED)

Known issue: model loads on CUDA but crashes with HTTP 000 (empty reply) on TTS requests.

### Pull and Run

```bash
docker run -d --name yt-anim-chatterbox \
  --gpus all \
  -p 8082:5123 \     # ← CRITICAL: internal port is 5123, NOT 8080
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=compute,utility \
  --restart unless-stopped \
  travisvn/chatterbox-tts-api:latest
```

### First Load

First startup takes 2-3 minutes to initialize on CUDA:
```
Initializing Chatterbox TTS model...
✓ Model initialized successfully on cuda
INFO:     Application startup complete.
```

### API (OpenAI-compatible format — unreliable):

```bash
curl -X POST http://127.0.0.1:8082/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{"input": "Text here.", "voice": "default", "response_format": "wav"}' \
  -o output.wav
```

## Pipeline Integration

In `create_video_v2.py` the ChatterboxTTS class defaults to port 8004 (devnen build):

```python
tts = ChatterboxTTS(api_url="http://127.0.0.1:8004", voice="Alice.wav")
```

The config file (`config/pipeline_v2.json`) has:
```json
{
  "tts": "chatterbox",
  "chatterbox_url": "http://127.0.0.1:8004",
  "chatterbox_voice": "Alice.wav"
}
```

## Expected Audio Output

- Format: PCM 16-bit WAV
- Sample rate: 24kHz
- Mono channel
- ~384 kbps bitrate
