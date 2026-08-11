# Selects MCP (Cutback) — capability analysis & FOSS alternatives

Source: https://cutback.video/selects/mcp (fetched 2026-08-04).
Product: proprietary MCP server connecting AI agents (Claude Code/Desktop,
Codex, OpenClaw) to real footage; exports structured projects to Premiere,
Final Cut Pro, DaVinci Resolve. SOC 2 Type II, cloud-based analysis.

## Advertised capabilities

1. Pre-indexed project: every angle, audio track, scene change indexed before
   the first prompt
2. Transcription + word-level timing
3. Speaker diarization / speaker-based camera switching
4. Scene/topic chunking, color labels, drop-bad-takes
5. Visual search ("man in red shirt", emotional beats, @person smiling)
6. Transcript search
7. Multicam sync of N angles
8. Silence removal, filler-word removal
9. Selects reels + batch shorts ("back catalog → 100 shorts")
10. Content-aware graphics (host says "Sony A7IV" → product image + live
    pricing dropped in; lower thirds, topic cards)
11. Instant preview; parallel edits; 10ms cut precision claim
12. Export: Premiere / Final Cut / DaVinci Resolve projects

## FOSS alternatives evaluated (2026-08)

| Project | Stars | Verdict |
|---|---|---|
| burningion/video-editing-mcp | 284 | Thin wrapper around COMMERCIAL Video Jungle API — engine proprietary. UX reference only. |
| FireRedTeam/FireRed-OpenStoryline | 3182 | Full AI video editing agent; heavyweight, generation-oriented. Inspirational. |
| Breakthrough/PySceneDetect | 5066 | Adopt directly for scene detection. |
| Aseiel/VideoHighlighter | 67 | Local AI video analyzer w/ visual search + highlights; no NLE export. Closest concept. |
| hetpatel-11/Adobe_Premiere_Pro_MCP | 428 | Deep Premiere control via ExtendScript; needs running Premiere. Complementary. |
| DareDev256/fcp-mcp-server | ~100 | FCPXML timeline editing. Complementary for FCP-native finishing. |
| Jumper (getjumper.io) | — | Closest commercial alternative; local media, agentic selects, XML export. |
| Eddie AI (heyeddie.ai) | — | Interview/podcast rough cuts, MCP endpoint, handoff to NLEs. |
| TwelveLabs MCP | — | Semantic video search/analysis; pairs with an editing MCP for cutting. |

Conclusion (2026-08): NO complete FOSS Selects equivalent existed → built
`pmb2/open-selects-mcp` wiring faster-whisper + pyannote + PySceneDetect +
open_clip + SQLite FTS5 + OTIO/ffmpeg into one FastMCP server.

## Honest gaps vs Selects (as of initial build)

- No built-in preview player (agent renders clips and shares files)
- Diarization needs HF token for gated pyannote models
- No content-aware graphics drop-in (needs per-NLE effect templates)
- CLIP ViT-B/32 weaker than proprietary vision on fine-grained queries
- Multicam sync assumes shared audio; silent/music-only angles need manual offsets
