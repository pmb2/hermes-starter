# V2 Voiceover-First Pipeline Decisions

Captured 2026-06-10 during session where the operator redirected from Spacebar deployment to overhauling the animation pipeline.

## Why V2 Exists

The legacy v1 pipeline (AnimateDiff/LTX-2.3 + Fish Speech) produces inconsistent output because:
- ComfyUI Docker had **zero model weights** loaded (all model dirs empty) — the actual root cause of "garbled, jumbled garbage"
- Video generation is heavy, slow, and hard to review per-frame
- AI TTS voices risk demonetization on YouTube

## Design Decisions

1. **Voiceover-first**: Record real voice (or hire a voice actor) → transcribe → timestamp frames. This is the Danny Why playbook adapted for FOSS.
2. **Frame-by-frame**: One image per timestamp, saved with timestamp filenames for review. the operator reviews all frames before assembly.
3. **MS Paint simple illustration style**: Easy for any model to produce consistently. Swappable via prompt files.
4. **Ken Burns pan/zoom**: Still images → animated video via FFmpeg zoompan. Avoids AnimateDiff/LTX complexity.
5. **External SRT, not burned in**: Subtitles as separate file for flexibility.
6. **Script cascade**: OpenCodeGo (deepseek-v4-flash) → OpenRouter → Ollama, so no single point of failure.
7. **Styling swappable**: Prompts in `prompts/` directory, style guide in `prompts/style_guide.txt`. Change prompt = change visual style.

## API Endpoint Reference

### Chatterbox TTS (travisvn/chatterbox-tts-api)
- Image: `travisvn/chatterbox-tts-api:latest`
- Internal port: **5123** (NOT 8080)
- Start: `docker run -d --gpus all -p 8082:5123 travisvn/chatterbox-tts-api:latest`
- Health: `GET /health` returns 200
- TTS: `POST /v1/audio/speech`
  - Body: `{"model":"chatterbox","input":"text","voice":"default","response_format":"wav"}`
  - Response: raw WAV binary
- Takes ~2 min to load model on first startup (CUDA initialization)
- Used by `ChatterboxTTS` class in `create_video_v2.py`

### OpenCodeGo Script Generation
- Endpoint: `https://opencode.ai/zen/go/v1/chat/completions`
- Auth: `Authorization: Bearer <OPENCODE_GO_API_KEY>`
- Model: `deepseek-v4-flash`
- Response: OpenAI-compatible chat completions format
- Key in `.env`: `OPENCODE_GO_API_KEY=sk-...`

### ComfyUI + FLUX.1-schnell
- Workflow: `workflows/flux_text_to_image.json`
- Model: `flux1-schnell-fp8.safetensors` (from `Comfy-Org/flux1-schnell`)
- Requires: CLIP-L + T5XXL encoders in `models/clip/`
- Template variables: `{{MODEL_NAME}}`, `{{POSITIVE_PROMPT}}`, `{{NEGATIVE_PROMPT}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{SEED}}`, `{{STEPS}}`, `{{CFG}}`

## File Location Quirk

On this Windows host (git-bash via MSYS), there's a write_file vs terminal path discrepancy:
- write_file resolves `E:/path` to `C:\e\path`
- Terminal `${MY_REPOS}/...` maps to the actual E: drive
- Cross-reference: use `ls ${MY_REPOS}/...` for terminal, `${MY_REPOS}/...` for write_file
- Solution: write to one, `cp` via terminal to the other

## Model Download Best Practice

Use Python inside the container to avoid MSYS path corruption:

```python
# From host, pipe Python into container
docker exec yt-anim-comfyui python3 -c "
from huggingface_hub import hf_hub_download
import os
target = '/workspace/ComfyUI/models/checkpoints/flux1-schnell-fp8.safetensors'
path = hf_hub_download('Comfy-Org/flux1-schnell', 'flux1-schnell-fp8.safetensors')
os.link(path, target)
"
```

DO NOT use `hf download` inside `docker exec` — MSYS translates `--local-dir` paths.
DO NOT use deprecated `huggingface-cli` — the `hf` CLI replaces it.
`hf_hub_download` in v1.14+ auto-resumes (no `resume` param).
