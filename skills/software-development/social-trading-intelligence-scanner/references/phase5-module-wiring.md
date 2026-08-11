# Phase 5 Module Wiring Pattern

How to add a new intelligence module to the stock-sniffer pipeline without breaking anything.

## Steps (in order)

### 1. Create the module

```python
# src/stocksniffer/<module>.py
def do_thing(signals, *, config=None, **kwargs) -> result:
    """Stateless; takes signals, returns enriched data."""
    ...
    return result

def format_thing_discord(result) -> str:
    """Returns Discord-formatted block or empty string."""
    ...
```

### 2. Update models if needed

- Add new fields to `SourceKind` in `models.py` if adding a source
- Add `extras` fields to `Signal` if enriching signals

### 3. Add config toggle in `sources.yaml`

```yaml
<module>:
  enabled: true
  # module-specific knobs
```

### 4. Wire into `pipeline.py`

```python
from .<module> import do_thing, format_thing_discord

# In run_scan():
mod_cfg = cfg.get("<module>") or {}
if mod_cfg.get("enabled", True):
    try:
        result = do_thing(signals, config=mod_cfg)
        block = format_thing_discord(result)
        if block:
            extra_blocks.append(block)
    except Exception:
        pass  # optional module failures are non-fatal
```

### 5. Update `format_discord()` signature

```python
def format_discord(result, *, ..., extra_blocks: list[str] | None = None):
    ...
    if extra_blocks:
        for block in extra_blocks:
            if block:
                lines.append("")
                lines.append(block)
```

### 6. Add CLI command

```python
# In cli.py
def cmd_<module>(args):
    ...
    return 0

# In build_parser():
mod_cmd = sub.add_parser("<module>", help="...")
mod_cmd.set_defaults(func=cmd_<module>)
```

### 7. Add tests

Offline tests only. No network, no yfinance live calls. Use `Signal` dataclass fixtures.

### 8. Update docs

- `docs/architecture.md` — add module to table
- `docs/operations.md` — add CLI command
- `AGENTS.md` — add module to canonical layout

## Pitfalls

- **Gateway handler order**: Define `_handle_*` functions BEFORE the `COMMANDS` list that references them, or get `NameError`.
- **Dataclass optional fields**: Always pass `field=None` explicitly in tests for fields with `| None` type.
- **SourceKind**: Every new source MUST be added to `SourceKind` Literal in `models.py`, `sources/__init__.py` exports, and `SOURCE_NAMES` in `pipeline.py`.
- **extra_blocks**: The `format_discord()` function needs the `extra_blocks` parameter added before modules can inject blocks.