# Shared Dependency Version Skew — Worked Diagnosis (OpenBB + MCP servers)

Symptom pattern: a Python MCP server **connects and registers tools**, but every tool call
returns `N/A`, empty results, or an `ImportError` from a Python library the server depends
on. The server process is healthy — its shared package install is broken. One broken
package typically takes down **every** server that imports it (this case: both
`trading-signals` and `openbb-finance` broke at the same import line).

## The OpenBB case (Aug 2026)

- `openbb` 4.7.2/4.7.1/4.6.0 meta-package ships a **generated** `package/equity.py` that does
  `from openbb_core.app.provider_interface import OBBject_EquityInfo, OBBject_EquityScreener, ...`
- `openbb-core` 1.6.13 (latest on PyPI) does **NOT** statically export those names. It creates
  them dynamically at runtime: `ProviderInterface._generate_return_annotations()` builds 181
  `OBBject_*` classes (incl. `EquityInfo`) via pydantic `create_model`, stores them in the
  singleton's `return_annotations` dict, and never injects them into the module namespace.
- Result: `from openbb import obb; obb.equity` → `ImportError: cannot import name 'OBBject_EquityInfo'`.

### Why the clean-venv control test is decisive

Same versions (openbb 4.6.0 + openbb-core 1.6.13) in a fresh venv → `obb.equity` works and
returns live quotes (SPY bid 744.11). On the polluted system Python, even deleting the
generated `openbb/package/*.py` files and reinstalling regenerates the SAME broken import.
Cause of the divergence: editable-install `.pth` finders / PYTHONPATH pollution
pre-register extensions before `auto_build()` runs, so the builder emits the specific
`OBBject_*` imports instead of generic `OBBject`. **Version was never the problem — the
environment was.**

### Reproduce the import failure standalone
```bash
python -c "from openbb import obb; print(hasattr(obb, 'equity'))"
# ImportError: cannot import name 'OBBject_EquityInfo' from 'openbb_core.app.provider_interface'
```

### Prove install integrity (installed == official wheel)
```bash
pip download openbb-core==1.6.13 --no-deps -d "C:/tmp/obbc"
unzip -o -q openbb_core-1.6.13-py3-none-any.whl -d whl
md5sum whl/openbb_core/app/provider_interface.py \
        /c/Users/<user>/AppData/Local/Programs/Python/Python311/Lib/site-packages/openbb_core/app/provider_interface.py
# identical hashes → environment pollution, not corruption
grep -c "__getattr__" whl/openbb_core/app/provider_interface.py   # 0 — no PEP 562 fallback
```

### Check version constraints before downgrading
```bash
python -c "import importlib.metadata as md; print(md.requires('openbb'))"
# openbb-core (>=1.6.10,<2.0.0) — 1.6.13 satisfies it; pip index confirms 1.6.13 is latest
```

## The durable fix: per-server venv (not a temp dir)

Temp dirs die on reboot. Use a stable path and point the MCP config at it:

```bash
python -m venv "C:/Users/<user>/AppData/Local/hermes/venvs/<server-name>"
"C:/Users/<user>/AppData/Local/hermes/venvs/<server-name>/Scripts/python.exe" \
  -m pip install "openbb==4.6.0" "mcp==1.28.1"
```

Then in `config.yaml` under `mcp_servers:<server>:` set
`command: C:/Users/<user>/AppData/Local/hermes/venvs/<server-name>/Scripts/python.exe`
(keep `args:` pointing at the server script).

**Verify BEFORE the restart** (a config edit that points at a broken venv wastes a restart cycle):
```bash
# 1. Compile the server script under the venv
venv-python -m py_compile "E:/.../mcp/trading-signals-mcp.py"
# 2. Import the server module and confirm tools register
venv-python -c "
import importlib.util
spec = importlib.util.spec_from_file_location('srv', r'E:\...\mcp\trading-signals-mcp.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
print(len(mod.mcp._tool_manager._tools))  # 4 tools
"
# 3. Confirm the shared lib actually returns data
venv-python -c "from openbb import obb; r = obb.equity.price.quote('SPY'); print(r.results[0].bid)"
```

## Ghost-package quirk (fresh venvs)

After creating a venv, `pip list` may show a package (e.g. `mcp 1.28.1`) that `import mcp`
cannot find — pip resolved it from the base interpreter's metadata, not the venv's
site-packages. Fix:
```bash
venv-python -m pip install --force-reinstall --no-deps "mcp==1.28.1"
venv-python -c "from mcp.server.fastmcp import FastMCP; print('ok')"
```

## Windows pitfalls that bit during this diagnosis

- `python -m venv /c/tmp/foo` (MSYS path) silently creates nothing → always use `C:/tmp/foo`.
- `pip download -d /c/tmp/...` mangles the MSYS path (files land somewhere unexpected) →
  pass `-d "C:/tmp/..."`.
- `python ${MY_REPOS}/.../script.py` becomes `C:\e\...` under MSYS → use literal
  `${MY_REPOS}/...` Windows paths for Python invocations.
- The `openbb/package/src` entry appearing at the front of `sys.path` is the openbb builder's
  own source dir — don't chase it as pollution; the real divergence is extension
  pre-registration at build time.
