# Python Package Corruption: Duplicate Dist-Info Directories

A common cause of sudden cron job failures after package upgrades.

## Symptom

```
ImportError: cannot import name 'getcurrent' from 'greenlet' (unknown location)
```

## Root Cause

Two or more `greenlet` dist-info directories exist simultaneously in
site-packages. The C extension (`.pyd`) loads from one version while the
Python module is found in another, causing `(unknown location)`.

## Detection

```bash
# Check for duplicate dist-info directories
ls /path/to/site-packages/ | grep -i greenlet

# With duplicates:
#   greenlet-3.2.4.dist-info     ← old
#   greenlet-3.5.2.dist-info     ← new (conflict)
```

## Fix

```bash
pip uninstall greenlet -y
rm -rf site-packages/greenlet-3.2.4.dist-info site-packages/greenlet-3.5.2.dist-info
rm -rf site-packages/greenlet
pip install greenlet
python -c "import greenlet; print(greenlet.__version__, hasattr(greenlet, 'getcurrent'))"
```

## Broader Pattern

Affects any C-extension package: `cryptography`, `numpy`, `psutil`,
`grpcio`, `orjson`, `pydantic-core`. Detect duplicates:
```bash
ls site-packages/ | grep "[0-9].*\.dist-info" | sed 's/-.*//' | sort | uniq -c | sort -rn | head -10
```

Count > 1 on any package = potential version conflict.
