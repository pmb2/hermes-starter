# v6 Scene-Based Pipeline (I2V Edition)

**Evolved from v5 flipbook** — Each scene gets 4-5 distinct FLUX images (different shot angles, NOT seed variations), then the best image feeds into Wan2.1 I2V for a real video clip. **No Ken Burns/zoom-pan** — user explicitly rejected slideshow effects. Only real video generation is acceptable.

## Architecture

```
run_scene_pipeline.py (orchestrator)
├── scripts/pipeline_utils.py — ComfyUI API + Wan2.1 I2V + ffmpeg helpers
├── scripts/scene_generator.py — Per-scene FLUX images + I2V video clip gen
└── scripts/scene_assembler.py — I2V clip speed-ramping + concat + audio mux
```

## File Locations

All under `${MY_REPOS}/Documents/github/yt-animations/`:
- `run_scene_pipeline.py` — Orchestrator (CLI flags: `--scene N`, `--skip-generation`, `--skip-assembly`, `--preset`)
- `scripts/pipeline_utils.py` — Shared utilities (`comfyui_submit`, `generate_flux_image`, `generate_i2v_video`)
- `scripts/scene_generator.py` — Image/video generation (30 scenes x 4-5 images + 1 I2V each)
- `scripts/scene_assembler.py` — Video-only assembly (speed-ramp via setpts, concat demuxer, audio mux)
- `workflows/wan_i2v_1_3B.json` — I2V workflow template (string-based `{{...}}` replacement, not JSON injection)
- `workflows/flux_dev_text_to_image.json` — FLUX T2I (used for first shot per scene, no input image needed)
- `workflows/flux_dev_img2img.json` — FLUX I2I (used for shots with prior input image, denoise 0.65)

## I2V Model Download

The Wan2.1 I2V model must be downloaded into the ComfyUI Docker models volume. Two methods:

**Method A — curl inside container (worked):**
```bash
# T5 encoder (10.5GB)
curl -L -o /workspace/ComfyUI/models/text_encoders/umt5-xxl-enc-bf16.safetensors \
  https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/umt5-xxl-enc-bf16.safetensors

# I2V 14B fp8 model (15.8GB)
curl -L -o /workspace/ComfyUI/models/diffusion_models/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors \
  https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors

# VAE (243MB)
curl -L -o /workspace/ComfyUI/models/vae/Wan2_1_VAE_bf16.safetensors \
  https://huggingface.co/Kijai/WanVideo_comfy/resolve/main/Wan2_1_VAE_bf16.safetensors
```

**Method B — hf download CLI (container):**
```bash
hf download Kijai/WanVideo_comfy Wan2_1_VAE_bf16.safetensors \
  --local-dir /workspace/ComfyUI/models/vae
```

**Required models**:
| File | Size | Location | Source |
|------|------|----------|--------|
| `Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors` | 15.8GB | `models/diffusion_models/` | Kijai/WanVideo_comfy |
| `umt5-xxl-enc-bf16.safetensors` | 10.5GB | `models/text_encoders/` | Kijai/WanVideo_comfy |
| `Wan2_1_VAE_bf16.safetensors` | 243MB | `models/vae/` | Kijai/WanVideo_comfy |

**Existing compatible models**: `clip_vision_h.safetensors` (in `models/clip-vit-large-patch14/`) and the FLUX CLIP models (`t5xxl_fp16.safetensors`, `clip_l.safetensors` in `models/clip/`) are already present from the FLUX setup.

## I2V Workflow Template

`workflows/wan_i2v_1_3B.json` uses string-based template replacement (`{{INPUT_IMAGE}}`, `{{MODEL_NAME}}`, `{{POSITIVE_PROMPT}}`, `{{WIDTH}}`, `{{HEIGHT}}`, `{{NUM_FRAMES}}`, `{{STEPS}}`, `{{CFG}}`, `{{SEED}}`). Replacement happens before JSON parsing — the template has unquoted int placeholders so it's not valid JSON until substituted.

**Key nodes**: LoadImage → WanVideoVAELoader → WanVideoModelLoader → CLIPVisionLoader → WanVideoClipVisionEncode → WanVideoTextEncode → WanVideoImageToVideoEncode → WanVideoSampler → WanVideoDecode → VHS_VideoCombine.

**Important**: The `WanVideoSampler` node receives reference connections from the model, VAE, text encode, image-to-video embeds, and VRAM management nodes via input IDs (`["4_MODEL_LOADER", 0]`, `["3_VAE_LOADER", 0]`, `["7_TEXT_ENCODE", 0]`, `["8_I2V_ENCODE", 0]`, `["9_VRAM_MGMT", 0]`). The negative prompt comes from `["7_TEXT_ENCODE", 1]` (the second output of the text encode node).

**VRAM management**: The 14B model at 480P needs ~20-22GB VRAM on a 24GB 3090. The workflow uses `WanVideoVRAMManagement` (autodetect=1) and `WanVideoBlockSwap` (blocks_to_swap=10) to fit. This is tight on WDDM — expect 2-5 min per video.

## Video Output Download

The `VHS_VideoCombine` node saves videos to the ComfyUI output directory (not standard image output). After the workflow completes, the pipeline searches for files matching the prefix in the output directory via `docker exec find`. Alternative: use the `/view` endpoint with the filename from ComfyUI's history.

## Generation Strategy

### Per-Scene Image Prompts
- **Scenes 1-17**: Hand-crafted 4-5 visual descriptions in `SCENE_VISUALS` dict within `scene_generator.py`
- **Scenes 18+**: Falls back to `script.json` shot prompts (`scene["shots"][][\"prompt\"]`)
- All prompts include MS Paint style prefix for visual consistency

### FLUX Image Generation (4 steps, not 20!)
- **Steps MUST be 4 for FLUX.1-schnell** — 20 steps causes VRAM exhaustion on 24GB 3090
- **CFG MUST be 1.0** — FLUX schnell is guidance-free; any other value produces garbage
- **Negative prompt check**: Compare `node_id` (not `class_type`) for negation — both CLIPTextEncode nodes have the same class_type, so `"neg" in node_id.lower()` is the correct check
- First image per scene: T2I via `flux_dev_text_to_image.json` (denoise=1.0)
- Subsequent images: T2I with different seeds (each is a distinct prompt, not img2img)

### I2V Video Generation
- Picks the middle image from each scene's generated set as the best representative
- Generates 81 frames at 16fps (~5s) of video with real motion
- Videos are speed-ramped via `ffmpeg setpts` to match TTS scene timing
- Scene timing estimated from narration char-count ratio of total audio duration

### fal.ai Alternative
- Endpoint: `fal-ai/wan-t2v` (confirmed working)
- Requires funded FAL_KEY balance
- Currently **balance exhausted** — top up at fal.ai/dashboard/billing
- Much faster than local I2V (~1 min vs 2-5 min per video)

## Scene Assembly (No Ken Burns)
1. Each scene's I2V video clip is loaded
2. Speed-ramped via setpts PTS multiplier to match scene duration
3. If video is shorter than scene, freeze-frame last frame via `tpad=stop_mode=clone`
4. All scene clips concatenated with `concat` demuxer (never xfade — gyan.dev crash)
5. Audio muxed from pre-existing TTS WAV
6. If visuals shorter than audio, ffmpeg trims to shortest

## Pitfalls

### I2V workflow JSON parsing fails
**Symptom**: `Expecting property name enclosed in double quotes` when loading the workflow
**Cause**: Template has unquoted `{{WIDTH}}` etc. that aren't valid JSON before substitution
**Fix**: Use string-based substitution BEFORE `json.loads()`. Replace all `{{...}}` placeholders with their actual string/int values on the raw text, then parse.

### I2V model download fails (15 bytes)
**Symptom**: Downloaded .safetensors is 15 bytes — contains "Not Found" error text
**Cause**: Wrong URL for the model file. The 1.3B I2V model `Wan2_1-I2V-1_3B_fp16.safetensors` does NOT exist in the Kijai/WanVideo_comfy repo. Use `Wan2_1-I2V-14B-480P_fp8_e4m3fn.safetensors` (14B fp8, ~16GB) instead.
**Fix**: Verify the filename exists with `curl -sI` before downloading. Check the repo listing at `https://huggingface.co/api/models/Kijai/WanVideo_comfy`.

### I2V image upload fails
**Symptom**: ComfyUI LoadImage node returns "Is a directory" error
**Cause**: Empty `image` field sent to LoadImage — it tries to read the ComfyUI input directory as a file
**Fix**: Only use img2img workflow when an actual input image is available. For the first image of each scene, use text-to-image workflow (no LoadImage node).

### Template variable order of operations
The `generate_i2v_video` function must upload the input image to ComfyUI BEFORE loading/parsing the workflow template. The `input_filename` is generated during upload and used in template substitution. Move the upload step before workflow loading.

## Key Files Created
| File | Purpose |
|------|---------|
| `outputs/sycamore-v2/images/sNNN/` | Per-scene FLUX images (PNGs) |
| `outputs/sycamore-v2/videos/sNNN/` | Per-scene I2V video clips (MP4s) |
| `outputs/sycamore-v2/assembly/sNNN/` | Built scene clips (temporaries) |
| `outputs/sycamore-v2/final/sycamore-v2.mp4` | Final assembled video |
| `outputs/sycamore-v2/generation_checkpoint.json` | Checkpoint for resume |
