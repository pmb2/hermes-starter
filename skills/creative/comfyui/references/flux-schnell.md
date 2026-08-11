# FLUX.1-schnell ComfyUI Reference

## Critical Parameters

| Parameter | Value | Why |
|-----------|-------|-----|
| CFG | `1.0` | FLUX uses guidance-free training. Setting CFG > 1.0 (e.g., 3.5, 7.0) produces solid-color garbage — always 1 unique color per frame, different shade per seed. |
| Steps | `4` (schnell) or `20–50` (dev) | FLUX.1-schnell is distilled for 4-step generation. More steps don't improve quality and waste compute. |
| Sampler | `euler` | Works well with FLUX.1-schnell. Other samplers may be tested. |
| Scheduler | `simple` | Standard choice for FLUX. |
| Resolution | `1024×1024` (native) | FLUX was trained at 1024×1024. Using other resolutions may produce suboptimal results. `1280×720` also works for video pipelines. |

## Recommended ComfyUI Workflow Structure

```
CheckpointLoaderSimple → CLIPTextEncode (positive)
                       → CLIPTextEncode (negative)
EmptyLatentImage
KSampler → VAEDecode → SaveImage
```

**Node connections:**
- `CheckpointLoaderSimple` output 0 (model) → KSampler model input
- `CheckpointLoaderSimple` output 1 (clip) → both CLIPTextEncode clip inputs
- `CheckpointLoaderSimple` output 2 (vae) → VAEDecode vae input
- KSampler output 0 (latent) → VAEDecode samples input
- VAEDecode output 0 (image) → SaveImage images input

**Important:** The VAE is embedded inside the checkpoint file (at least for `Comfy-Org/flux1-schnell-fp8.safetensors`). The separate `ae.safetensors` in models/vae/ is NOT used by CheckpointLoaderSimple — output index 2 provides the VAE from the checkpoint itself. A corrupt or missing `ae.safetensors` (e.g., 140-byte stub from a gated repo) is harmless if the checkpoint has a valid embedded VAE.

## Template Replacement Variables

When using a parameterized workflow template for programmatic generation:

| Variable | Value | Notes |
|----------|-------|-------|
| `{{MODEL_NAME}}` | `flux1-schnell-fp8.safetensors` | Exact filename, case-sensitive |
| `{{POSITIVE_PROMPT}}` | Full prompt text | Include style prefix if applicable |
| `{{NEGATIVE_PROMPT}}` | Negative prompt | Short is fine: "blurry, low quality" |
| `{{WIDTH}}`, `{{HEIGHT}}` | `1024` × `1024` | FLUX native |
| `{{SEED}}` | Random int 1–2³¹ | Pass `-1` or random per run |
| `{{STEPS}}` | `4` | FLUX.1-schnell |
| `{{CFG}}` | `1.0` | **CRITICAL — must be 1.0 for FLUX** |

## Model Sizes (Comfy-Org/flux1-schnell fp8)

| File | On-disk Size | Contents |
|------|-------------|----------|
| `flux1-schnell-fp8.safetensors` | 6.1 GB (disk), 16.1 GB (decompressed weights) | Diffusion model + VAE + CLIP-L + T5XXL all-in-one |

The checkpoint has 1,438 weight keys. The model dtype is `torch.float8_e4m3fn` with manual cast to `bfloat16` for stable computation.

## Video Pipeline Integration

When integrating FLUX.1-schnell into a script→TTS→frames→video pipeline:

1. **One image per scene** — Generate one FLUX image per timestamped scene
2. **Ken Burns effect** — Apply zoompan on each image to create motion:
   ```
   ffmpeg -loop 1 -i frame.png -t DURATION -vf \
     "fps=24,scale=2560:1440:flags=lanczos,zoompan=z='min(zoom+0.015,1.15)':d=2400:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720,format=yuv420p"
   ```
3. **Audio sync** — Scene duration matches voiceover segment length
4. **Missing image fallback** — When FLUX fails (e.g., OOM), detect the error (not a solid-color frame) rather than silently substituting colored placeholders

## Known Issues

- **CFG=3.5+ produces garbage** — Always verify CFG=1.0 in both the workflow JSON template and the instantiation code
- **Docker + Windows GPU hangs** — `--normalvram` with saturated VRAM can freeze the container. Prefer `--lowvram` in Windows Docker Desktop environments
- **WDDM VRAM reporting** — `nvidia-smi` on Windows shows inflated VRAM usage from desktop compositor and hardware-accelerated apps. Actual free memory may be 0–500 MB out of 24 GB
- **LOWVRAM mode speed** — On RTX 3090 with `--lowvram`: 2–5 min per 1024×1024 image. With `--normalvram` and free VRAM: 10–15 seconds per image
