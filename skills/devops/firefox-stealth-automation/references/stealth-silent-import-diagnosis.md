# Diagnosing Silent Stealth Import Failures

## Problem

The PIM connector (`_firefox_bidi.py`) imports StealthEngine from ultimate-firefox-mcp:

```python
from ultimate_firefox_mcp.stealth import StealthEngine
```

If this import fails (ImportError), the except block catches it silently and logs:
```
WARNING  root:ultimate-firefox-mcp not available, skipping stealth
```

**No error is raised. Extraction proceeds normally with ZERO anti-detection.** Every visited site sees an automated browser (navigator.webdriver=true, missing plugins, detectable canvas/WebGL fingerprints, etc.).

## Root Causes

### 1. package not pip-installed
`ultimate-firefox-mcp` lives at `${USER_HOME}\ultimate-firefox-mcp\` as raw source. If `pip install -e .` was never run (or failed due to build backend issues), the package is not on sys.path.

**Check:**
```bash
pip list | grep ultimate-firefox-mcp
# If empty -> not installed
```

**Fix:**
```bash
cd ${USER_HOME}\ultimate-firefox-mcp
pip install -e .
```

**Common failure:** `pyproject.toml` has `build-backend = "setuptools.backends._legacy:_Backend"` which doesn't exist in modern setuptools. Fix:
```toml
[build-system]
requires = ["setuptools>=64.0", "wheel"]
build-backend = "setuptools.build_meta"
```

### 2. sys.path doesn't include the source directory
Even without pip install, the import can work if the source directory is on sys.path. The PIM cron job runs from `${MY_REPOS}\Documents\github\git-mcp\services\personal-intelligence-mcp`, and `sys.path` doesn't include `${USER_HOME}\ultimate-firefox-mcp`.

**Belt-and-suspenders fix** (added to both `_apply_stealth()` and `_apply_cdp_stealth()`):
```python
import sys
ultimate_path = r"${USER_HOME}\ultimate-firefox-mcp"
if ultimate_path not in sys.path:
    sys.path.insert(0, ultimate_path)
from ultimate_firefox_mcp.stealth import StealthEngine
```

### 3. The import only fails in cron context
The ultimate-firefox-mcp MCP server works from its workdir because Python adds the workdir to sys.path automatically when running `python -m ultimate_firefox_mcp.main` from `${USER_HOME}\ultimate-firefox-mcp`. But the PIM cron job runs from a different directory.

## Detection

```bash
# Check if stealth is actually being applied in PIM logs
grep -i "stealth.*applied\|stealth.*skip\|ultimate.*not.*available" ${HERMES_HOME}/logs/agent.log | tail -20

# Expected: "Applied 22/22 stealth measures via StealthEngine"
# Bad: "ultimate-firefox-mcp not available, skipping stealth"
```

## Verification

```bash
# From any working directory:
python -c "from ultimate_firefox_mcp.stealth import StealthEngine; e = StealthEngine(); print('OK')"
# If this fails -> package not installed or path not set
```
