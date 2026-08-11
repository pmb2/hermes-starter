# genmedia CLI on Windows — Installation & Quirks

## What It Is

[genmedia](https://github.com/fal-ai-community/genmedia-cli) is the agent-first CLI for fal.ai — search, inspect schemas, and run 600+ generative AI models. Published as `@fal-ai/genmedia-cli`, compiled with Bun into a standalone binary.

## Windows Installation

**Cannot install via npm** — `npm install -g genmedia-cli` and `npm install -g @fal-ai/genmedia-cli` both fail:

| Attempt | Result |
|---------|--------|
| `npm install -g genmedia` | ✅ found but **os not supported** (`darwin,linux` only) |
| `npm install -g @fal-ai/genmedia-cli` | ❌ 404 (scoped package not published to registry) |
| `npm install -g genmedia-cli` | ❌ 404 |

**Solution:** Run directly from source via [Bun](https://bun.sh):

```bash
# Clone the repo
git clone --depth 1 https://github.com/fal-ai-community/genmedia-cli.git

# Run via bun
bun run /path/to/genmedia-cli/src/index.ts -- --help
```

## Wrapper Script

A Python wrapper at `~/.hermes/scripts/genmedia.py` provides a consistent CLI:

```python
# Uses bun.exe at its canonical Windows location
BUN = r"${USER_HOME}\.bun\bin\bun.exe"
GENMEDIA_SRC = r"${MY_REPOS}\Documents\github\genmedia-cli\src\index.ts"
cmd = [BUN, "run", GENMEDIA_SRC] + sys.argv[1:]
subprocess.run(cmd)
```

Usage:
```bash
python ~/.hermes/scripts/genmedia.py -- models --query "text-to-video"
python ~/.hermes/scripts/genmedia.py -- run fal-ai/kling-video/v3/pro/text-to-video
```

## API Key

Set the key via:
```bash
export FAL_KEY="59b4c4b3-..."
bun run /path/to/genmedia-cli/src/index.ts -- setup --non-interactive --api-key="$FAL_KEY"
```

The config is stored encrypted at `~/.genmedia/config.json`. The key also works as `FAL_KEY` env var at runtime (genmedia reads it).

## Skills (fal.ai Community)

The `genmedia skills install` command downloads SKILL.md bundles from the fal.ai registry:

```bash
bun run /path/to/genmedia-cli/src/index.ts -- skills install <name> --targets claude,agents-md
```

Installed skills land in `~/.claude/skills/<name>/` (when run from home) or the cwd's `.claude/skills/`. Copy them to `~/.claude/skills/` afterward for global Claude Code availability.

For Hermes Agent, copy SKILL.md files into `~/.hermes/skills/<category>/<name>/`.

## Key Quirks

- **bun.exe location:** `C:\Users\<user>\.bun\bin\bun.exe`, not the npm shim at `C:\Users\<user>\AppData\Roaming\npm\bun` (which is a POSIX script, not runnable from Windows subprocess)
- **No Windows binary:** The pre-compiled binary from npm is macOS/Linux only. Running via bun from source works on Windows (bun cross-compiles).
- **Config path:** `~/.genmedia/config.json` on Windows resolves to `C:\Users\<user>\.genmedia\config.json`
- **Skills install cwd-dependent:** The command installs into the current working directory's `.claude/skills/`, not the user home. Always copy afterward.
