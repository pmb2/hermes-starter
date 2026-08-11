# Auto-Action Handler Gap Analysis

Observed during the 2026-07-11 morning briefing cycle.

## Gap 1: Missing Infrastructure Crash Keywords

**Symptoms:** Gateway crash in watchdog.log (63 occurrences, Tier 1, score 0.6) was only `intel_logged` — never got a `hardening_note`.

**Root Cause:** `resolve_actions()` in `cyber_auto_actions.py` routes actions via keyword matching on headline + description:

```python
# Breach/leak — gets hardening + intel
if "breach" in hl_lower or "leak" in hl_lower or "dump" in hl_lower:
    actions.append(("hardening", finding))
    actions.append(("log_intel", finding))

# Patch signals — gets patch + hardening
if "patch" in hl_lower or "cve" in hl_lower or "vulnerability" in hl_lower or "exploit" in hl_lower:
    actions.append(("patch", finding))
    actions.append(("hardening", finding))

# Infrastructure signals — missing!
# No block for "crash"|"segfault"|"panic"|"watchdog"|"timeout"
```

**Fix:** Add an infrastructure signal block:

```python
# Infrastructure signals
if "crash" in hl_lower or "segfault" in hl_lower or "panic" in hl_lower or \
   "watchdog" in hl_lower or "timeout" in hl_lower:
    actions.append(("hardening", finding))
    actions.append(("patch", finding))
```

## Gap 2: Duplicate Finding Processing

**Symptoms:** The same breach finding (fingerprint `cyber:1a865bf6`) appeared twice in `cyber_intel_findings.json` — once per scan date — and both entries were processed independently. Resulted in duplicate hardening note and duplicate intel log entry.

**Root Cause:** Each entry in the JSON array has the same `fingerprint` but different `url` and `date` fields. The state tracking uses `action_type:fingerprint` as the dedup key, but since both entries have the same fingerprint but appear at different array positions, both get routed.

**Fix:** Deduplicate findings by fingerprint before routing:

```python
# Before the routing loop
seen_fps = set()
unique_findings = []
for f in findings:
    fp = f.get("fingerprint", "")
    if fp in seen_fps:
        continue
    seen_fps.add(fp)
    unique_findings.append(f)
findings = unique_findings
```

## Audit Trail

| File | Evidence |
|------|----------|
| `cyber_actions_log.jsonl` | Line 1: hardening_note, Line 2: intel_logged for finding (breach). Lines 3+: same finding again |
| `cyber_hardening_notes.md` | grep shows 2 identical entries for the same breach finding |
| `cyber_intel_findings.json` | Fingerprint `cyber:1a865bf6` appears twice (different scan timestamps) |
| `cyber_intel_log.md` | Only 1 entry for the breach finding (handler skipped duplicate for intel_log on second pass due to state being saved mid-run) |
