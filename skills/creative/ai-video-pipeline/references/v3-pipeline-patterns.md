# V3 Pipeline Internal Patterns

## Three Modes of Operation

| Mode | Flags | Use Case |
|------|-------|----------|
| Standard | `--topic "..."` | LLM generates script from scratch |
| Script Breakdown | `--topic "..." --script-file script.md` | LLM adds timestamped visual prompts to existing script |
| Trailer | `--topic "..." --script-file script.md --trailer` | LLM condenses full script into ~5min thriller trailer |
| Pre-built JSON | `--topic "..." --script-json file.json` | Skip LLM entirely, use previously saved breakdown |

## Required Boilerplate When Creating a Pipeline Script

Three helper functions must exist for the v3 script to work:
- `_load_api_key()` — resolves OPENCODE_GO_API_KEY from env → Hermes .env → ~/.hermes/.env
- `_call_llm()` — tries providers in cascade (opencode-go → openrouter → ollama)
- `concat_videos()` — uses FFmpeg concat demuxer for scene-to-scene assembly (xfade crashes on 10+ clips with gyan.dev Windows build)

These are in `create_video_v3.py` at predictable locations. If rewriting or forking the script, include them.

## Known Pitfalls (This Session)

- **concat_videos() was missing from v3**: The initial v3 commit didn't include a `concat_videos()` function — only `build_xfade_chain()` existed. When the assembly code was patched to use concat instead of xfade, `NameError: name 'concat_videos' is not defined` crashed the pipeline. Always verify helper functions exist after patching assembly strategy.
- **Background process accumulation**: Three background processes accumulated from repeated failed runs. Each had a different log file name. Kill all before restarting: `ps aux | grep create_video_v3 | grep -v grep | awk '{print $2}' | xargs kill -9`
- **model config nesting**: `pipeline_v2.json` stores model under `models.flux.model_name` but `sv()` does flat key lookup for `"model"`. Always pass `--model` explicitly on command line.
- **First YouTube upload opens browser**: OAuth flow starts a local server on port 8080. User must be at the machine to authenticate. Token is cached as `token.pickle` afterwards.
