# Pulse Data Source Queries

## Firefox Bookmarks

```sql
-- Profile path: ~/AppData/Roaming/Mozilla/Firefox/Profiles/<profile>/places.sqlite
-- Profile name: <profile-id>.default-release-1

-- Get all bookmarks created after a timestamp
SELECT 
  b.id,
  b.title,
  b.dateAdded / 1000000 AS date_added_unix,
  p.url,
  p.id AS place_id,
  (SELECT title FROM moz_bookmarks WHERE id = b.parent) AS folder
FROM moz_bookmarks b
JOIN moz_places p ON b.fk = p.id
WHERE b.type = 1  -- bookmarks only (not folders)
  AND b.dateAdded / 1000000 > :last_check_unix_epoch
ORDER BY b.dateAdded DESC;
```

## GitHub Stars (gitmcp.db)

```sql
-- DB: ${MY_REPOS}/git-mcp/services/github-star-intelligence-mcp/gitmcp.db

-- Get recently starred repos
SELECT 
  id, name, full_name, description, 
  html_url, language, stargazers_count,
  starred_at, topics, owner_login
FROM starred_repos
WHERE starred_at > :last_check_iso
ORDER BY starred_at DESC;

-- Check if DB has any data at all
SELECT COUNT(*) AS total_stars FROM starred_repos;
SELECT MIN(starred_at) AS oldest, MAX(starred_at) AS newest FROM starred_repos;
```

## YouTube Videos

**Option A: PostgreSQL** (if the extraction pipeline has DB access)

```sql
-- DB: bookmarks_data (PostgreSQL, host=127.0.0.1, user=postgres, pass=postgres)

SELECT 
  video_id, title, url, channel, playlist,
  has_transcript, segment_count, duration_sec
FROM youtube_videos
WHERE id > :last_known_id
ORDER BY id ASC;
```

**Option B: JSON export file** (from yt_extract.py)

```bash
# Check for new JSON exports
ls -la ${USER_HOME}/FireFox-Phantom-MCP/youtube_*.json 2>/dev/null
# Parse with jq
jq '.videos[] | select(.video_id | IN($new_ids[]))' youtube_export.json
```

## Personal Intelligence DB (pim.db)

```sql
-- DB: ${MY_REPOS}/git-mcp/services/personal-intelligence-mcp/pim.db
-- Table: saved_items
-- Schema (verified):
--   id TEXT PRIMARY KEY, source_type TEXT, source_id TEXT,
--   title TEXT, author TEXT, source_url TEXT,
--   full_text TEXT, full_text_length INTEGER,
--   tags TEXT, ingestion_status TEXT, retry_count INTEGER,
--   created_at TEXT, updated_at TEXT, ingested_at TEXT
-- UNIQUE(source_type, source_id)

-- Quick count
SELECT COUNT(*) AS total_items FROM saved_items;

-- Get items ingested after last check (canonical query)
SELECT 
  id, source_type, title, source_url AS url,
  full_text AS summary, tags, created_at, ingested_at
FROM saved_items
WHERE ingested_at > :last_check_iso
ORDER BY ingested_at DESC
LIMIT 30;

-- Count by source type
SELECT source_type, COUNT(*) AS cnt FROM saved_items
WHERE ingested_at > :last_check_iso
GROUP BY source_type;

-- Get tag distribution for a time window
SELECT tags, COUNT(*) AS cnt FROM saved_items
WHERE ingested_at > datetime('now', '-48 hours', 'utc')
GROUP BY tags ORDER BY cnt DESC;

-- Get most recent items with project tags only (non-empty tags)
SELECT title, source_type, tags, ingested_at
FROM saved_items
WHERE tags != '[]'
ORDER BY ingested_at DESC
LIMIT 10;
```

## Cross-Reference: Map Items to Active Projects

```sql
-- Uses the `tags` column (pre-computed by intelligence_collector.py) instead
-- of ad-hoc text matching. Tags are already set per-project during ingestion.
-- Examples: '["agent-ecosystem"]', '["twitch-farm","agent-ecosystem"]', '["construct-manage"]'

-- All items tagged to a specific project in a time window
SELECT id, source_type, title, source_url, tags, ingested_at
FROM saved_items
WHERE json_extract(tags, '$') LIKE '%"construct-manage"%'
  AND ingested_at > :last_check_iso
ORDER BY ingested_at DESC;

-- Count by project tag (workaround for SQLite json)
SELECT
  CASE
    WHEN tags LIKE '%"bookends"%' THEN 'P0: Bookends'
    WHEN tags LIKE '%"construct-manage"%' THEN 'P0: Construct Manage'
    WHEN tags LIKE '%"twitch-farm"%' THEN 'P1: Twitch Farm'
    WHEN tags LIKE '%"yt-animation"%' THEN 'P1: YT Animation'
    WHEN tags LIKE '%"agent-ecosystem"%' THEN 'P1: Agent Ecosystem'
    WHEN tags LIKE '%"mes-solumina"%' THEN 'P3: Solumina Agent'
    ELSE 'uncategorized'
  END AS project,
  COUNT(*) AS items,
  GROUP_CONCAT(title, ' | ') AS sample_titles
FROM saved_items
WHERE ingested_at > :last_check_iso
GROUP BY project
ORDER BY items DESC;
```

## Tracking Last-Check Timestamps

Store in a simple JSON file or SQLite table:

```json
{
  "bookmarks": 1779760000,
  "youtube": 1779760000,
  "github_stars": "2026-05-26T00:00:00Z",
  "pim": "2026-05-26T00:00:00Z"
}
```

Location: `~/.hermes/skills/productivity/intelligence-pulse/last_check.json`
