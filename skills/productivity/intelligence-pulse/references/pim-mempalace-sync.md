# PIM → MemPalace Sync Pipeline

> Established: May 29, 2026
> Sync cadence: Every 3 hours (after each unified PIM pipeline run)

## Architecture

```
YouTube extraction ─┐
GitHub stars    ────┤
Firefox bookmarks ──┤
PIM ingest (ChatGPT)─┤── cron job (every 180m) ──→ PIM DB ──→ mempalace mine ──→ MemPalace (personal-intelligence wing)
ChatGPT         ────┤
Grok            ────┘
```

Two systems that were previously disconnected:
- **PIM (Personal Intelligence Manager)** — SQLite DB at `personal-intelligence-mcp/pim.db`. Stores 1,500+ ingested items (bookmarks, stars, emails, ChatGPT/Grok conversations, YouTube saves). Source-specific connectors via Firefox BiDi extraction.
- **MemPalace** — Local memory store at `~/.mempalace/palace/`. 10k+ drawers across wings/rooms. Used by all agents for persistent memory.

The bridge exports new PIM items as markdown files and mines them into MemPalace via `mempalace mine`.

## Sync Script

Location: `${USER_HOME}/AppData/Local/hermes/scripts/pim_sync_mempalace.py`

What it does:
1. Queries PIM DB (`saved_items`) for items from last 7 days
2. Groups by `source_type` (chatgpt, grok, bookmark, github_star, email, youtube)
3. Writes one markdown file per source type with: title, URL, author, tags, AI summary, key points
4. Runs `mempalace mine <file> --wing personal-intelligence` per source type
5. Stores per-item in MemPalace under `personal-intelligence / general` room

Key fields preserved per drawer:
- PIM ID (for cross-referencing back to PIM DB)
- Source type + URL
- Tags (if available)
- LLM summary (Copilot API generated)
- Key points (list)

## Consolidated Pipeline: `PIM Ingestion & Sync — every 3h`

**Cron job ID:** `b0490179124c`
**Schedule:** `every 180m` (3 hours)
**Enabled toolsets:** `terminal`, `file`, `browser`

The old separate `Weekly Extraction — YT, GitHub, Bookmarks` was eliminated — everything now runs in one pipeline:

1. **YouTube** — cd `${USER_HOME}/FireFox-Phantom-MCP` && run `python yt_extract.py`. This navigates YouTube Library (`youtube.com/feed/library`), scans for ALL playlist links (including system playlists: **Liked Videos=LL**, **Watch Later=WL**, **Favorites=FL**), then iterates each playlist scrolling up to 30x to extract every video. Then `python yt_transcripts.py` fetches transcripts for new videos via youtube-transcript-api. Outputs JSON: `youtube_temp.json` + `youtube_transcripts.json`.
2. **GitHub stars** — Run `github_stars_extractor.py` from `${MY_REPOS}/git-mcp/`
3. **Firefox bookmarks** — cd `${USER_HOME}/FireFox-Phantom-MCP` && run `python extract_bookmarks.py` or `python bookmark_checker.py`
4. **ChatGPT** — `python ~/AppData/Local/hermes/scripts/pim_chatgpt.py` (uses Firefox on port 9223)
5. **Grok** — `python ~/AppData/Local/hermes/scripts/pim_grok.py` (uses Firefox on port 9223)
6. **MemPalace sync** — `python ~/AppData/Local/hermes/scripts/pim_sync_mempalace.py`
7. **Report** — Summary of what was ingested per source

### Key changes from previous setup:
- **Cadence:** Every 3 hours (was 4h ChatGPT/Grok + weekly YT/GitHub/bookmarks)
- **Firefox port:** 9223 (was 9239) — Firefox is expected to already be running. DO NOT start a new instance.
- **YT/GitHub/bookmarks** absorbed from their own weekly cron into the unified pipeline
- **pim_sync_mempalace.py** runs as the final step every time, not just after ChatGPT/Grok

## Patched Firefox

- **Location:** `${USER_HOME}/firefox-portable/firefox.exe`
- **Profile:** `<profile-id>.default-release-1` (logged into ChatGPT + Grok)
- **Port:** 9223 (BiDi WebSocket) — expected to already be running before the pipeline triggers
- **Auto-start:** NOT handled by the pipeline. The cron prompt should NOT start a new Firefox instance. If Firefox is down, the pipeline reports it as a source failure and continues with other sources.
- **Lock handling:** Run `rm -f` on the parent.lock file before starting Firefox (for manual restarts only)

## MemPalace Lock Contention

`mempalace mine` requires an exclusive lock on the palace DB. If the MemPalace MCP server (`mempalace mcp`) is running simultaneously, CLI mine commands will fail. The cron prompt sequences ingestion before sync to avoid this.
