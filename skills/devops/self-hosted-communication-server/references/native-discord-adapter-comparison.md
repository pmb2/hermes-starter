# Native Discord Adapter vs spacebar-gateway.py — Redundancy Analysis

**Date:** 2026-06-07 (updated after commit 538fb4496)
**Author:** Hermes Agent (diagnostic pass + port)

## Bottom Line

**All 16 patches have been ported into the Discord adapter.** The old
`spacebar-gateway.py` wrapper is fully redundant as of commit `538fb4496`
on branch `feat/spacebar-native-support`.

The native adapter at `plugins/platforms/discord/adapter.py` has an
`_apply_spacebar_patches()` method that applies all patches conditionally
when `extra.base_url` is set in the platform config.

## Per-Patch Port Status

| # | Patch | Status | Where |
|---|-------|--------|-------|
| 1 | API version v9 | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 2 | Route.BASE → Spacebar URL | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 3 | DEFAULT_GATEWAY → Spacebar WS | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 4 | compress=False | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 5 | Custom identify payload | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 6 | Raw token auth (no 'Bot ') | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 7 | Command API methods | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 8 | Custom login (HTTP /users/@me) | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 9-11 | Raw*Event null guild_id | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 12 | _fill_overwrites null guard | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 13 | dispatch _MissingSentinel guard | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 14 | msvcrt.locking noop | ✅ Ported (lock path) | `adapter.py` → `_apply_spacebar_patches()` |
| 15 | Lock path → .spacebar | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 16 | Bulk Raw*Event null guild_id | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 17 | received_message null guild_id | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |
| 18 | TextChannel._update safe_data | ✅ Ported | `adapter.py` → `_apply_spacebar_patches()` |

## Additional Fixes in the Adapter

| Fix | Description |
|-----|-------------|
| `_is_spacebar_mode()` helper | Module-level Spacebar detection for standalone code |
| `_standalone_send` raw auth | Uses raw token (no `Bot` prefix) when Spacebar mode active |
| `_discord_api_url()` env fallback | Falls back to `SPACEBAR_API_BASE` env var when adapter not loaded |

## Deployment Comparison

### Old Way (Deprecated)
1. Start fleet-core.py from agent-fleet repo
2. Fleet-core launches spacebar-gateway.py per profile
3. Each wrapper patches discord.py, starts Hermes gateway
4. Fleet-core monitors and restarts on crash
5. Death loop from cleanup-kill signal confusion

### New Way (Current)
1. hermes gateway run (or hermes -p profile gateway run)
2. Adapter detects SPACEBAR_API_BASE env var
3. _apply_spacebar_patches() applies all 16 patches before Bot creation
4. Gateway connects to Spacebar natively
5. No wrapper, no fleet-core, no death loop

## File Locations
- Native adapter: hermes-agent/plugins/platforms/discord/adapter.py
- Old wrapper: agent-fleet/scripts/spacebar-gateway.py (deprecated)
