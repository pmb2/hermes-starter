# LaTeX on Windows — MiKTeX for AI Scientist

## Installation

MiKTeX is the standard LaTeX distribution for Windows. On this machine it's installed at:

```
${USER_HOME}\AppData\Local\Programs\MiKTeX\miktex\bin\x64\
```

Version: MiKTeX 25.12, MiKTeX-pdfTeX 4.23

## Available Tools

All confirmed working:
- `pdflatex.exe` — Main LaTeX → PDF compiler
- `bibtex.exe` — Bibliography management
- `xelatex.exe` — Unicode-aware LaTeX
- `chktex.exe` — LaTeX syntax checker
- `latexmk.exe` — Auto-compilation wrapper
- `lualatex.exe` — Lua-based LaTeX

## PATH Issue

MiKTeX is installed in the user's AppData (not Program Files), so it's NOT in the system PATH. `shutil.which('pdflatex')` returns `None`, which causes the AI Scientist's `check_latex_dependencies()` to return `False`.

## Fix: PATH Injection in MCP Config

The Hermes MCP server config injects MiKTeX into PATH via the `env:` block:

```yaml
mcp_servers:
  ai-scientist:
    env:
      PATH: ${USER_HOME}/AppData/Local/Programs/MiKTeX/miktex/bin/x64;${PATH}
```

This ensures subprocesses started by the MCP server (e.g., `pdflatex`, `bibtex`, `chktex`) are found. If running `launch_scientist.py` directly from the terminal, run:

```bash
export PATH="${USER_HOME}/AppData/Local/Programs/MiKTeX/miktex/bin/x64:$PATH"
```

Or better — set the user PATH via Windows System Properties → Environment Variables.

## Chocolatey Lock Issue

If re-installing via choco, a stale lock file at `C:\ProgramData\chocolatey\lib\cf918a7f408d34c7b350efbd0199760c621e100a` may prevent installation. Needs admin: `rm "C:\ProgramData\chocolatey\lib\cf918a7f408d34c7b350efbd0199760c621e100a"` then retry.
