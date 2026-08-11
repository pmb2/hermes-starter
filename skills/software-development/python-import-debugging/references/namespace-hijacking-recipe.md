# Namespace Package Hijacking — Reproduction & Fix

Discovered during Sentry pulse (2026-07-28) on the Hermes Agent codebase.

## Symptom

```
tests/scripts/test_build_skills_index_health.py:23: in <module>
    import scripts.build_skills_index as build_mod
E   ModuleNotFoundError: No module named 'scripts.build_skills_index'
```

Despite `hermes-agent/scripts/build_skills_index.py` existing on disk.

## Diagnosis

```python
import scripts
print(scripts.__path__)
# → ['E:\\yourdata\\Documents\\github\\finance-team\\insider-trading\\src\\scripts']
```

The `scripts` namespace resolved to `finance-team/insider-trading/src/scripts` because:
1. That directory's `src/` was on sys.path (via editable install `.pth` file)
2. Neither `hermes-agent/scripts/` nor `finance-team/.../scripts/` had `__init__.py`
3. Python's namespace package resolution picked the first match on sys.path

## Fix

Added `__init__.py` to `hermes-agent/scripts/`:

```python
# Hermes Agent utility scripts — each module is a standalone entry point.
```

This forces `scripts` to resolve as a regular package, giving priority to the local copy over the contaminated namespace.

## Verification

```bash
cd /path/to/hermes-agent
python -m pytest tests/scripts/test_build_skills_index_health.py -q
# → 2 passed in 2.37s
```

## Broader Context

The `finance-team/insider-trading/src` was on sys.path because of an editable install (`pip install -e`). The `sys.path` also contained other development projects (`deal-finder`, `healthy-food-filter`, `local-biz-scanner`, `website-landlord`, `openloop`, `tradingagents`, `haystack`, `ai-hedge-fund`, etc.). Each contributes to potential namespace conflicts if they share top-level directory names with other projects.

## Prevent Recurrence

- Any project with a `scripts/` directory containing importable modules should have an `__init__.py` (even empty).
- Editable installs of multiple projects with same-named package directories (especially generic names like `scripts`, `tools`, `utils`, `config`) will eventually collide.
- To audit all namespace-prone directories on the current sys.path:

```python
import sys, os
for p in sys.path:
    d = os.path.join(p, 'scripts')
    if os.path.isdir(d) and not os.path.exists(os.path.join(d, '__init__.py')):
        print(f"Bare 'scripts' namespace at: {d}")
```
