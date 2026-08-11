# v3 Multi-Shot Pipeline Reference

## Architecture Change from v2

| Aspect | v2 | v3 |
|--------|----|----|
| Images per scene | 1 | 2-4 (shots) |
| Transitions | Hard cut (concat demuxer) | Crossfade (xfade within scenes), concat between scenes |
| Scene structure | `scenes[].{narration, visual_prompt}` | `scenes[].{narration, shots[].{prompt, shot_description, duration_hint_sec}}` |
| Outputs | 1 image per scene | N images (total_shots = scenes × shots_per_scene) |
| Total images (12 scenes) | ~12 | ~36-48 |
| YouTube | Manual | `--upload` flag |
| Script input | Topic only | Topic, script file, pre-built JSON |

## Script Promotion Flow (v3 only)

The `_call_llm()` helper routes through OpenCodeGo → OpenRouter → Ollama cascade, same strategy as `generate_script()` but designed for free-form prompts (not just topic→script generation).

## Operating Modes

### Standard (`--topic "..."`)
Generates script from scratch. Uses `prompts/script_generation_v3_prompt.txt`.

### Script Breakdown (`--topic "..." --script-file script.md`)
Loads a pre-existing script file, feeds it to the LLM with instructions to produce timestamped scenes and detailed FLUX visual prompts. Uses default prompt built into `create_video_v3.py`.

### Trailer (`--topic "..." --script-file script.md --trailer`)
Loads a full script and uses `prompts/trailer_breakdown_prompt.txt` to condense it into a thrilling 5-minute trailer. First 10-15 seconds are the hook. Each scene gets energy_level (hook/build/peak/release). 8-12 scenes produced.

### Pre-Built JSON (`--topic "..." --script-json path/to/script.json`)
Skip the LLM entirely. Load a previously-generated script JSON directly. Useful when:
- The LLM occasionally generates malformed JSON — save a good output and retry
- You have a pre-written scene breakdown from a previous session
- The script is complex and you want to keep it stable across rebuilds

## Prompt Files

| File | Purpose |
|------|---------|
| `prompts/script_generation_v3_prompt.txt` | Standard v3 — instructs LLM to produce `scenes[].shots[]` with 2-4 shots per scene |
| `prompts/trailer_breakdown_prompt.txt` | Trailer mode — takes full script text, produces timestamped thriller breakdown |

## XFade Assembly Details

The `build_xfade_chain()` function chains N video clips using the FFmpeg `xfade=transition=fade` filter.

For N clips, the filter graph looks like:
```
[0:v][1:v]xfade=transition=fade:duration=0.5:offset={clip0_dur-0.5}[s1];
[s1][2:v]xfade=transition=fade:duration=0.5:offset={clip0_dur+clip1_dur-0.5}[s2];
...
```

### Gyan.dev xfade Crash (Complex Chains)

**Symptom**: Assembly crashes with exit code 4294967274 (0xFFFEFFFA) when chaining 5+ videos with the `xfade` filter. Intra-scene xfade (2-4 clips) works fine; inter-scene xfade (8-10 clips) crashes.

**Root cause**: Gyan.dev FFmpeg 8.1 Windows build has a filtergraph size limitation. Complex xfade chains with many inputs trigger a libavfilter crash (same root cause as the drawtext crash — fontconfig/Freetype linkage issue in the gyan.dev binary).

**Fix**: 
- Intra-scene (shots within a scene): Keep xfade — works fine with 2-4 clips
- Inter-scene (scene-to-scene): Use `concat` demuxer instead. The v3 pipeline does this automatically via `concat_videos()`.

## Known Quirks

### DeepSeek Reasoning Eats Token Budget
- Symptom: "No JSON in LLM output" with long prompts + voice guide loaded
- Root cause: deepseek-v4-flash exposes `reasoning_content` which consumes 30-40K tokens on complex prompts. At `max_tokens=8192`, content comes back empty.
- Fix: `max_tokens=16384` minimum. Increase to 32768 for very long scripts (>10K chars).
- Scope: OpenCodeGo deepseek-v4-flash only. OpenRouter and Ollama don't exhibit this.

### FLUX Steps: 4 Not 20
- Symptom: Scene 1 works, then all subsequent FLUX prompts fail with ConnectionResetError
- Root cause: schnell is designed for 1-4 steps. Using 20 steps fills VRAM and causes connection drops.
- Fix: `--steps 4` for FLUX.1-schnell. Quality difference is negligible.
- Better quality alternative: `--model flux1-dev-fp8.safetensors --steps 20`

### Config Nesting — sv() Flat Lookup vs pipeline_v2.json Nested Structure
- `pipeline_v2.json` stores model name under `models.flux.model_name` and resolution as a dict `{"width":1920,"height":1080}`.
- The pipeline's `sv(args, cfg, key, fallback)` does a **flat key lookup** in `cfg`. It does NOT traverse nested dicts.
- **Symptom**: Setting `"model_name": "flux1-schnell-fp8/AiAF/..."` under `models.flux` has no effect. Pipeline reads `cfg["model"]` → not found → falls back to `args.model` default (`flux1-schnell-fp8.safetensors`). All FLUX images fail with "clip input is invalid: None" because the root-level file is UNet-only.
- **Fix A**: Always pass model explicitly via `--model "flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors"`.
- **Fix B**: Add the model at the flat key level: `"model": "flux1-schnell-fp8/AiAF/..."` in pipeline_v2.json.
- **Same issue**: Resolution (dict vs string `1920x1080`), TTS URL, workflow path.

### Resolution Config Format
- `pipeline_v2.json`: `"resolution": {"width": 1920, "height": 1080}` (dict)
- CLI `--resolution`: `"1920x1080"` (string)
- Code must handle both: `isinstance(res, dict)` check

### API Key Auto-Loading
- The `_load_api_key()` function resolves OPENCODE_GO_API_KEY from:
  1. `os.getenv("OPENCODE_GO_API_KEY")`
  2. `$HERMES_HOME/.env` (line ~453)
  3. `~/.hermes/.env`
- No manual export needed in new sessions
- New scripts should copy this same fallback pattern

### write_file Path Resolution (Windows)
- `write_file("E:/path")` resolved to `C:\e\path\` — WRONG (write_file handles E: directly now if you use absolute Windows path)
- Terminal's `${MY_REPOS}/...` maps to actual E: drive
- For writing files to yt-animations project, use terminal/Python:
  ```bash
  python -c "pathlib.Path('create_video_v3.py').write_text(content)"
  ```
- `patch` tool also resolves paths through the same mechanism — it works when paths exist

### FLUX Model Variants — AiAF vs Root-Level
There are two `flux1-schnell-fp8` paths in the ComfyUI checkpoints directory:

| Path | Size | CLIP | VAE | Works with |
|------|------|------|-----|-----------|
| `flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors` | 17GB | ✅ 198 keys | ✅ 244 keys | Standard workflow (CheckpointLoaderSimple) |
| `flux1-schnell-fp8.safetensors` (root) | 11-12GB | ❌ 0 keys | ❌ 0 keys | Dev workflow (UNETLoader + DualCLIPLoader + VAELoader) |

**Always use the AiAF path** — it's the full model with embedded CLIP+VAE. Pass it as:
```
--model "flux1-schnell-fp8/AiAF/flux1-schnell-fp8.safetensors"
```

The root-level file is a UNet-only fp8 conversion that requires the separate dev workflow.

## YouTube Upload Workflow

1. User creates Google Cloud project, enables YouTube Data API v3
2. Downloads OAuth desktop credentials as `client_secret.json` in project root
3. First run: browser opens for OAuth consent -> `token.pickle` cached
4. Pipeline: `--upload --privacy unlisted` generates youtu.be link
5. Review cycle: phone review -> delete via `python scripts/youtube_manager.py delete <id>` -> rebuild -> re-upload
6. Final: upload as public when approved

CLI standalone:
```bash
python scripts/youtube_manager.py upload output.mp4 --title "DRAFT" --privacy unlisted
python scripts/youtube_manager.py delete <video_id>
python scripts/youtube_manager.py list
```
