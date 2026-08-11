# TubeFlow Research — Concepts Adopted

TubeFlow (github.com/wnstify/tubeflow) is a Claude Code-native YouTube content pipeline focused on pre-production research and post-production social promotion. It doesn't handle video generation (TTS, FLUX, assembly) — it covers the text/content strategy phases.

## Concepts Adopted

| Concept | Implementation |
|---------|---------------|
| Parallel research agents | `scripts/research_topic.py` — 4 searches (topic, competitors, SEO, community) via DuckDuckGo |
| Channel voice guide | `prompts/channel-voice.md` — tone, pacing, sentence patterns, word choice table |
| Social post generation | `scripts/generate_social.py` — LinkedIn/Twitter/Facebook from manifest.json |
| Script template with hooks | Integrated into `prompts/script_generation_prompt.txt` with `{{VOICE_GUIDE}}` and `{{RESEARCH_CONTEXT}}` |

## Not Adopted (Claude Code-specific)
- Full `.claude/` directory structure (agents/skills/commands) — incompatible with Hermes
- GitHub Issues community voting — low priority
- The "film yourself" pipeline stage — irrelevant (our pipeline automates visuals)
