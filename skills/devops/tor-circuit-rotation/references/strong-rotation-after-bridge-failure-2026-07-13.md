# Strong Rotation After Bridge NEWNYM Failure — July 13, 2026

A rotation cycle where the initial bridge `browser_new_identity()` did **not** change
the exit IP, escalating to strong rotation (close all BUILT circuits + NEWNYM) via
raw socket control protocol, which succeeded.

This is distinct from:
- **Normal rotation** (Jul 12, Jul 13 00:09 UTC) — single NEWNYM via bridge worked
- **Hung daemon recovery** — daemon was unresponsive
- **Zero circuits recovery** — daemon had no usable circuits
- **Cookie-missing deadlock** — no cookie on disk prevented auth

Here the daemon was healthy (9 BUILT circuits, SOCKS5 responsive), the bridge sent
NEWNYM successfully, but the exit IP remained unchanged after 25s. Strong rotation
via control protocol immediately fixed it.

## Session Profile

| Attribute | Value |
|-----------|-------|
| **Available tools** | `mcp_tor_camoufox_bridge_*` (discovered via `tool_search` — not directly visible) |
| **Bridge state** | `tor_browser: {status: "configured"}`, `camoufox: {status: "running"}` |
| **Active engine** | tor |
| **Initial rotation** | `browser_new_identity()` — returned `"NEWNYM requested"` |
| **Escalation** | Raw socket strong rotation (close 9 BUILT circuits + NEWNYM + 30s wait) |
| **Prev cycle** | Jul 13 00:09 UTC — normal rotation, 0 orphans, 46 stale dirs |

## Exit IP Timeline

| Step | Result |
|------|--------|
| **Pre-rotation (SOCKS5)** | `185.220.100.249` (Tor exit, via `check.torproject.org/api/ip` ✅) |
| **Bridge NEWNYM** | `"NEWNYM requested for Tor circuit rotation"` |
| **After 25s wait** (sleep exit 0) | `185.220.100.249` **unchanged** |
| **Strong rotation** | Closed 9 BUILT circuits (8 succeeded, 1 already gone) → NEWNYM `250 OK` |
| **After 30s rebuild** | `149.202.79.129` ✅ **changed** |
| **Non-Tor reference IP** | `74.76.35.96` (via direct `api.ipify.org`) |

**Key observations:**
- Bridge NEWNYM returned success but did not change the exit IP within 25s
- `sleep 25` completed without interruption (exit code 0) — the cron sleep pitfall
  is intermittent, not deterministic
- Strong rotation via raw socket worked on first attempt: 9 circuits closed,
  8 confirmed successful, 1 already transitioned
- 6 fresh BUILT circuits established within 30s (grew to 8 by next check ~60s later)

## Post-Rotation Checks

### xul.dll Stealth Patch
```
PATCHED=True (webdriver:0, WEBDRIVER_BIDI:0) ✅
```

### Circuits (after strong rotation + 30s)
```
GENERAL_PURPOSE_BUILT=8
TOTAL_BUILT=8
```
Exit relays across fresh circuits: VaginaDick, wokestaywokestay, DFRI40, NTH52R5, bauruine
— all different from pre-rotation exit. Guard nodes also rotated (confidential, code9n).

### Orphan Processes
| Process | Count | Action |
|---------|-------|--------|
| `firefox.exe` | **10** | All confirmed orphans (PowerShell: empty window titles) → killed ✅ |
| `geckodriver.exe` | **0** | None |
| `tor.exe` | Normal count | Healthy |

**Note:** 10 orphans is in the recovery range (down from the 25-83 peak), suggesting
the GFX crash auto-recovery patches are reducing but not eliminating crash frequency.

### Stale Session Directory Cleanup
| Metric | Value |
|--------|-------|
| **Pre-cleanup count** | 37 `torbrowser-driver-*` directories |
| **Successfully cleaned** | 35 |
| **Remaining** | 2 (active session + 1 locked) |
| **Active session dir** | `torbrowser-driver-6hw1yw9f/` |
| **Cleanup method** | `rm -rf` via bash `for` loop (preserving newest) |

**Accumulation rate context:** 46 stale dirs at Jul 13 00:09 UTC → cleaned to 3 →
37 at Jul 13 ~06:00 UTC. Net accumulation of ~34 dirs in 6 hours when the system
has no crashes but MCP restarts produce fresh sessions. This is ~5-6 dirs/hour
during normal operation (vs 10+/hour during crash cycles).

## Health Summary

```
Bridge Status     → tor: configured, camoufox: running
Initial NEWNYM    → IP unchanged after 25s ⚠️
Strong Rotation   → 185.220.100.249 → 149.202.79.129 ✅
Stealth Patch     → webdriver:0, WEBDRIVER_BIDI:0 ✅
SOCKS5            → reachable on :9250 ✅
Orphans           → 10 killed (all confirmed orphans) ✅
Stale Dirs        → 37 → 2 (35 cleaned) ✅
Recovery Actions  → strong rotation via raw socket, orphan kill, stale dir cleanup
```

## What This Means

The bridge's `browser_new_identity()` is not 100% reliable even on a healthy daemon.
A ~16% failure rate estimate (1 failure in ~6 observed cycles across all references)
is consistent with available data. The raw socket strong rotation is the reliable
fallback and should be preferred whenever the bridge NEWNYM doesn't change the exit IP
within 25-30s. Do NOT assume the daemon is hung or degraded — just escalate to
strong rotation immediately.

**Comparison with failing scenarios:**

| Scenario | SOCKS5 Reachable | Control Port Responsive | Circuits | Fix |
|----------|------------------|------------------------|----------|-----|
| **Bridge NEWNYM failed (this run)** | ✅ | ✅ | 9 BUILT | Strong rotation via raw socket |
| **Hung daemon** | ❌ (timeout) | ❌ (PROTOCOLINFO hangs) | N/A | Kill + auto-recovery |
| **Zero circuits** | ⏳ (timeout) | ✅ | 0 GP BUILT | NEWNYM + 30s wait |
| **Cookie-missing deadlock** | ✅ | ✅ (but can't auth) | N/A | Wait for interactive session |

The diagnostic that differentiates this case from "zero circuits" is the healthy
pre-rotation circuit count (9 BUILT vs 0). The fix that differentiates from
"hung daemon" is that strong rotation works immediately without a daemon kill.
