# PULSE.md — Per-Agent Persistent Log

**Used by:** qa-lead, dev-lead, skills-lead, integration-lead, docs-lead, and other cron agents.
**Location:** `~/AppData/Local/hermes/profiles/<agent>/PULSE.md`
**Purpose:** Persistent heartbeat log of every pulse run. Provides continuity between cycles (each pulse reads the last entry before running) and an audit trail that survives agent restarts.

## Format

Each entry follows this structure:

```
## Pulse @ YYYY-MM-DD HH:MM UTC
- **Status**: 🟢 Nominal / 🟡 Attention Needed / 🔴 Issue Found
- **Focus**: [what was investigated this cycle — specific and concise]
- **Findings**:
  - ✅ or 🟢 for passing/healthy items
  - 🟡 for warnings or changes noted
  - 🔴 for failures or regressions
  - Use compact one-line-per-item, `backticks` for filenames/commands
  - Group related findings with bullet indent
- **Next Action**: [one concrete thing to do next cycle]
```

### File-level header

The file begins with a static preamble:

```
# PULSE.md — <agent-name>

> Continuous heartbeat log for the <agent-name> agent.
> Each pulse is the agent running its domain-specific work on schedule.
> Appended by <cron-job-name> (every 4h).
```

No additional formatting or index — just sequential append.

## Entry Rules

1. **Timestamp is UTC** — always `YYYY-MM-DD HH:MM UTC` (not local time, not EST).
2. **Separator between entries** — a line of three dashes between each pulse:
   ```
   ---
   ```
3. **Status must be one of three**: 🟢 Nominal / 🟡 Attention Needed / 🔴 Issue Found. Do not invent variants like 🟢 All Clear; the three canonical tags are enforced for machine-parseability.
4. **Findings are bullet points** — `- ` prefix, one item per line, no blank lines between items. Group logically but keep compact.
5. **Next Action** — singular, concrete, actionable. Not a wishlist. If the issue is out of the agent's control (e.g., push blocked by 403), say so explicitly.
6. **Consistency across cycles** — maintain the same tracked metrics across consecutive pulses (e.g., test counts, divergence behind origin, working tree diff). This enables trend detection.

## Workflow

On each pulse run:

1. **Read the file** — open the last 50-60 lines (the most recent 2-5 entries) for context on what was tracked last time.
2. **Re-run same metrics** — measure whatever was measured in the previous pulse (test suites, git divergence, etc.) so the delta is meaningful.
3. **Append new entry** — write the new entry at the end of the file following the format above.
4. **Summarize to digest** — call `append-digest.py` with a condensed version of key findings (not the full PULSE.md entry).

## Example

```markdown
## Pulse @ 2026-07-09 08:59 UTC
- **Status**: 🟢 Nominal
- **Focus**: 13th-cycle verification — approval/tirith/context-reliance suites, divergence tracking
- **Findings**:
  - ✅ **Approval + Tirith + Deny**: 412/412 passed (24.35s) — pipeline ordering + platform autouse holding
  - ✅ **Context refs**: 17/17 passed (3.72s) — USERPROFILE monkeypatch intact
  - 🟡 **Divergence**: 2 ahead, **97 behind** origin/main (was 42 behind @cycle 12) — upstream active
  - 🟡 **Push still blocked** (403) — fixes survive only on local HEAD
- **Next Action**: Continue monitoring; cycle 14 will detect same pattern unless push access restored.

---
```

## Relation to Other Systems

| System | Purpose | When It Runs |
|--------|---------|-------------|
| **PULSE.md** | Per-agent persistent full log | Every pulse (agent-local) |
| **`append-digest.py`** | Condensed summary to daily digest | Every pulse (shared digest) |
| **Discord delivery** | Final output to user | Every pulse (if waking hours) |

PULSE.md is the source of truth for the agent's own history. The digest is a cross-agent summary for the morning brief. Delivery is the user-facing report.
