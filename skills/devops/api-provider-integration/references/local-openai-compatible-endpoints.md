# Local OpenAI-Compatible Inference Endpoints (faster-whisper, Qwen3TTS)

Proven 2026-08-04 on the agency voice stack (RTX 3090, Docker). These are
self-hosted OpenAI-compatible endpoints; the same 5-step discovery methodology
from SKILL.md applies, plus these product-specific quirks.

## faster-whisper (STT)

- Endpoint: `POST /v1/audio/transcriptions` (port 8178 in the stack).
- **Auth is REQUIRED even locally**: `Authorization: Bearer $FASTER_WHISPER_API_KEY`
  (64-char key from .env). Without it you get `{"detail":"invalid_api_key"}`,
  NOT a 401/403 — easy to misread as an endpoint problem.
- Body: multipart `file=@audio.wav`, `model=large-v3`, `response_format=json`.
- Response: `{"text":"...","model":"large-v3","language":"en","duration":N,"segments":[...]}`.
- **First boot downloads the model (~3.1GB) into the HF cache volume**; the
  container can sit "unhealthy" for 10-30+ min while it downloads (healthcheck
  start_period shorter than the download). HF throttles hard (~700KB/s); a
  `docker restart` resumes from the `.incomplete` blob at full speed. Check
  progress: `du -sh /models` + count `*.incomplete` blobs. No volume for the
  cache = re-download every recreate.

## Qwen3TTS (tts-qwen service)

- Endpoint: `POST /v1/audio/speech` (port 8000), OpenAI-compatible.
- **Model id is `qwen3-tts` (dash), NOT `qwen3tts`** — guessing the obvious
  name returns 400. Default voice is `Vivian` (not `default`). Discover both
  from `GET /v1/models` / `GET /v1/voices` or the app's own
  `tests/test_api.py` when docs are absent.
- Body: `{"model":"qwen3-tts","input":"text","voice":"Vivian","response_format":"wav"}`.
- **First request triggers a ~7GB model download** — the request times out;
  that's normal. Watch the container log for `Loading '1.7B-CustomVoice' ...`
  and `du -sh ~/.cache/huggingface` until `.incomplete` count hits 0, then retry.
- **Image has NO curl** (that's why its healthcheck can't use curl) — use
  python `urllib.request` inside the container or host curl to the traefik route.
- Nested-quote hell: `docker exec ... python3 -c "..."` with JSON payloads
  breaks in bash — write the probe to a file, `docker cp` it in, run it.

## Round-trip verification pattern (prove the loop)

The cheapest proof the whole audio chain works — synthesize then transcribe:

1. TTS: synthesize a known sentence -> wav (443KB for ~9s speech).
2. Copy the wav into the whisper container.
3. STT: transcribe it back; expect near-verbatim text (ASR may drop a word —
   "leads system" -> "lead system" is normal variance, not a failure).

This validates text->audio->text on the GPU with zero cloud and no phone call.

## General gotchas for local OpenAI-compatible services

- Healthcheck/readiness passing does NOT mean models are loaded — first real
  request pays the model-load/download cost. Always budget a warm-up call.
- `invalid_api_key` / `400` on a service that "is running" = check the auth
  header and the exact model id BEFORE suspecting the endpoint.
- Containers in this stack frequently lack curl/wget: use python urllib, or
  node fetch from a node-based sibling container, or host-side curl to the
  traefik-published hostname.
