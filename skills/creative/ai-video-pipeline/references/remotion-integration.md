# Remotion Integration

Remotion (remotion.dev, 49.8k ★) is a React-based framework for creating videos programmatically. It replaces the FFmpeg/Pillow assembly phase in the pipeline — handling text overlays, transitions, audio sync, captions, and encoding with pixel-perfect React/CSS.

## Architecture

```
Script (LLM) → FLUX Keyframes (ComfyUI) → TTS (Chatterbox) → Remotion Render → MP4
```

FLUX generates images, Remotion assembles the final video. Best of both worlds.

## When to Use Remotion vs FFmpeg Assembly

| Feature | Remotion | FFmpeg |
|---------|----------|--------|
| Text quality | Perfect (CSS) | Poor (drawtext) |
| Animations | CSS/Spring transitions | Complex filter chains |
| Preview | Hot-reload Studio | Full rebuild |
| Subtitles | Built-in SRT/WebVTT | Manual |
| Complexity | Setup needed | Zero deps |

Use Remotion anytime the video needs text, transitions, or subtitles. Use FFmpeg for simple hard-cut concatenation (faster, fewer deps).

## MCP Integration

Two MCP servers wired into Hermes config:

1. **remotion-docs** — Official Remotion MCP (`npx -y @remotion/mcp@latest`). Provides documentation context for AI assistants via CrawlChat vector index.

2. **remotion-render** — Custom MCP server at `mcp/remotion_mcp/server.py`. Wraps renderMedia, renderStill, listCompositions, renderWithProps, getVideoMetadata as MCP tools.

## Project Structure

```
remotion-studio/
├── package.json          # React + Remotion + @remotion/renderer + @remotion/captions
├── tsconfig.json
├── remotion.config.ts
├── src/
│   ├── index.ts          # registerRoot(Root)
│   └── Root.tsx          # Composition registry (SycamoreTrailer, etc.)
├── public/
│   ├── frames/           # FLUX keyframes go here
│   └── audio/            # TTS narration files
└── remotion.config.ts
```

## Key Remotion Packages

- `remotion` — Core framework + CLI
- `@remotion/renderer` — Node.js SSR API (renderMedia, getCompositions)
- `@remotion/captions` — SRT/WebVTT subtitle generation
- `@remotion/mcp` — Official MCP server for docs assistance

## Installation

```bash
npm install remotion @remotion/renderer @remotion/captions
```

Or create a new project:
```bash
npx create-video@latest remotion-studio --template blank
```

## Rendering (in Python pipeline)

```python
import subprocess
subprocess.run(["node", "scripts/remotion-render.mjs",
    "--composition", "SycamoreTrailer",
    "--output", "outputs/trailer.mp4",
    "--props", json.dumps({"scenes": scenes})
], check=True)
```

Or use the MCP server tool `render_media`.

## Pitfalls

- Chrome needs ~2GB+ RAM during rendering. Close other browser instances on Windows.
- `@remotion/mcp` is in test phase — may be rate-limited later.
- Commercial license required if company >$1M revenue or non-open-source.
- Set MCP timeout to 600s+ for long renders in Hermes config.
