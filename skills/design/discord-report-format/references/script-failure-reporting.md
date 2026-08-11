# Script Failure Reporting

How to format a report when the primary data-collection script fails. Covers single failures AND consecutive (escalating) failures across multiple cron runs.

## Single Failure (first occurrence)

Surface it prominently in the RECAP section with the script path and error. Do not bury it.

```
📊 **RECAP**
- `daily_brief.py` | ❌ FAILED | Not found at `C:\path\to\scripts\daily_brief.py`
- Other work | ✅ completed satisfactorily
```

## Second Consecutive Failure

Escalate to ⚠️. Note that this is a repeat. Include the previous occurrence date.

```
📊 **RECAP**
- `daily_brief.py` | ⚠️ FAILED (2nd consecutive) | First occurred Jun 19. Script not found at same path.
```

## Third+ Consecutive Failure

Escalate to 🔴. Name the specific error pattern. Include a concrete fix recommendation.

```
📊 **RECAP**
- `daily_brief.py` | 🔴 FAILED (3rd consecutive) | Same error: `scripts/scripts/daily_brief.py` double-nested path.
  Fix: resolve `scripts/scripts/` nesting in cron job script_path config.
```

## General Formatting Rules

- Always include the script path in backticks so the user knows exactly which file failed
- Always note the error/exit reason (not just "script failed" — say "not found", "exit code 1", "syntax error", etc.)
- At ⚠️ and 🔴 levels, include a **one-line fix recommendation** in the RECAP or Recommended Actions section
- If the data-collection script failed but the agent manually gathered data from fallback sources, indicate this:

```
📊 **RECAP**
- `daily_brief.py` | ❌ FAILED | Not found. Report compiled from fallback sources: git scan, BizDev MCP, session_search.
```

- Do NOT suppress the failure just because you successfully gathered data from other sources. The user needs to know the pipeline is broken.
