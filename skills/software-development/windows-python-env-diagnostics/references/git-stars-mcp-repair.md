# git-stars MCP Server Repair — Session Detail (2026-07-31)

Weaver pulse case study for `windows-python-env-diagnostics` sections 2b/2c.
`github-star-intelligence-mcp` failed to connect in Hermes. Three stacked root
causes, each masking the next — diagnose in this order.

## Symptom Chain

1. **`ModuleNotFoundError: No module named 'pydantic_core._pydantic_core'`** —
   config.yaml + `start-mcp.bat` used bare `python`. On this box bare `python`
   resolves to `hermes-agent\.venv` (a BROKEN venv — broken pydantic_core), NOT
   the project venv or system Python. The healthy interpreter is
   `hermes-agent\venv` (no dot) or system `Python311\python.exe`.
2. **`McpError: Invalid request parameters`** on `list_tools` — after switching
   the client to system Python311: system-wide `fastmcp 3.4.2 + mcp 1.26.0` is a
   known-bad combo (native-mcp skill: pin `fastmcp>=0.4,<1.0` + `mcp>=1.0,<1.2`).
3. **Even the fresh project `.venv` imported the wrong `fastmcp`** — `import
   fastmcp` resolved to `C:\...\Python311\fastmcp` (base interpreter ROOT, not
   site-packages) because (a) stale `fastmcp` 3.4.2 dir sat in the Python root,
   and (b) global `PYTHONPATH` injected hermes-agent site-packages ahead of the
   venv's own.

## Fix Recipe (applied)

```bash
cd ${MY_REPOS}/git-mcp/services/github-star-intelligence-mcp
# 1. Fresh venv with pinned known-good combo
"${USER_HOME}\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
env -u PYTHONPATH ./.venv/Scripts/python.exe -m pip install \
  "fastmcp>=0.4,<1.0" "mcp>=1.0,<1.2" "pydantic>=2.10,<2.14" \
  "pydantic-settings>=2.0,<2.7" uvicorn anyio httpx "sqlalchemy[asyncio]" aiosqlite asyncpg python-dotenv
# 2. Rename stale base-root shadow
cd ${USER_HOME}/AppData/Local/Programs/Python/Python311
mv fastmcp fastmcp.renamed && mv fastmcp-3.4.2.dist-info fastmcp-3.4.2.dist-info.renamed
# 3. config.yaml: git-stars command -> E:\...\.venv\Scripts\python.exe (never bare python)
```

Verified: `fastmcp 0.4.1 | pydantic 2.13.4 | uvicorn 0.52.0`, `app.main` imports
OK under clean env.

## Verification Pattern

Transport tests (`stdio_client` + `list_tools`) repeatedly died on
`OSError: [WinError 10106]` at `import asyncio` (`_overlapped` / Winsock LSP
flake — intermittent under `env -u PYTHONPATH`; plain `import asyncio` in a fresh
shell works). This is a HOST quirk, not a server defect. Fall back to in-process
verification:

```bash
cd <project> && env -u PYTHONPATH ./.venv/Scripts/python.exe -c \
  "import sys; sys.path.insert(0,'.'); import app.main; print('APP.MAIN OK')"
```

Also mirror the clean env in the transport-test client:
```python
env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
params = StdioServerParameters(command=r'E:\...\.venv\Scripts\python.exe',
                               args=['-m', 'app.main'], env={**env, 'DATABASE_URL': 'sqlite+aiosqlite:///./gitmcp.db'})
```

## Residual

- `start-mcp.bat` (auto-restart wrapper) still uses bare `python` — needs the
  same venv-python update; flagged, not changed.
- Retry `WinError 10106` 3-5x before concluding anything about the server.
