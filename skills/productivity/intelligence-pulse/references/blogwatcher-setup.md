# Blogwatcher Setup — Windows (MSYS2/Git Bash)

Blogwatcher-cli is a Go-based RSS/Atom feed reader. Installed and configured May 30, 2026.

## Installation

```bash
go install github.com/JulienTant/blogwatcher-cli/cmd/blogwatcher-cli@latest
```

Binary lands at `~/go/bin/blogwatcher-cli`. Add to PATH or use full path.

## Database

SQLite DB at `~/.blogwatcher-cli/blogwatcher-cli.db`

Tables:
- `blogs` — id, name, url, feed_url, scrape_selector, last_scanned
- `articles` — id, blog_id, title, url, published_date, discovered_date, is_read, categories

## Feed Management

```bash
# Add feed
blogwatcher-cli add "Name" https://site.com --feed-url https://site.com/feed.xml

# List blogs
blogwatcher-cli blogs

# Scan all feeds
blogwatcher-cli scan

# Remove failing feed
blogwatcher-cli remove "Name" --yes
```

## Quick SQLite3 CLI Queries for Pulse

Column notes (confirmed Jun 2026): the DB uses `b.name` (not `b.title`), `a.published_date` (not `a.published_at`), `a.is_read` (not `a.read`), and `a.categories` (text column with comma-separated tags). These differ from what you might expect — use these exact names:

```bash
# Unread articles by blog (last 2 days)
sqlite3 "${USER_HOME}/.blogwatcher-cli/blogwatcher-cli.db" \
  "SELECT b.name AS blog, COUNT(*) AS unread FROM articles a JOIN blogs b ON a.blog_id = b.id WHERE a.is_read = 0 AND a.published_date > datetime('now', '-2 days') GROUP BY b.name ORDER BY unread DESC;"

# Recent unread articles with URLs (for pulse picks)
sqlite3 "${USER_HOME}/.blogwatcher-cli/blogwatcher-cli.db" \
  "SELECT a.published_date, b.name AS blog, substr(a.title,1,70) AS title, a.url FROM articles a JOIN blogs b ON a.blog_id = b.id WHERE a.is_read = 0 AND a.published_date > datetime('now', '-24 hours') ORDER BY a.published_date DESC LIMIT 15;"

# Feed freshness (last scan time per blog)
sqlite3 "${USER_HOME}/.blogwatcher-cli/blogwatcher-cli.db" \
  "SELECT name, last_scanned FROM blogs ORDER BY name;"

# Wired coupon noise filter — check recent Wired articles
sqlite3 "${USER_HOME}/.blogwatcher-cli/blogwatcher-cli.db" \
  "SELECT a.published_date, substr(a.title,1,70), a.categories FROM articles a JOIN blogs b ON a.blog_id = b.id WHERE b.name = 'Wired' AND a.is_read = 0 AND a.published_date > datetime('now', '-2 days') ORDER BY a.published_date DESC;"
```

The `blogwatcher-cli articles` CLI command also works for reading fresh articles by feed, but raw sqlite3 gives you direct control over filters and avoids CLI pagination.

## Reading Articles for Pulse (Python approach)

Pulse reads the DB directly via SQL (no CLI needed):

```python
import sqlite3
from pathlib import Path

db = str(Path.home() / ".blogwatcher-cli" / "blogwatcher-cli.db")
conn = sqlite3.connect(db)
cur = conn.cursor()

# New articles since last check
cur.execute("""
    SELECT a.id, a.title, a.url, a.published_date, a.discovered_date,
           a.categories, b.name AS blog_name
    FROM articles a
    JOIN blogs b ON a.blog_id = b.id
    WHERE a.discovered_date > ?
    ORDER BY a.discovered_date DESC
    LIMIT 50
""", (last_check,))
```

## Feed Roster (May 30, 2026)

Active (8 feeds, all working):
1. Ars Technica AI — `https://feeds.arstechnica.com/arstechnica/index`
2. Hacker News — `https://hnrss.org/frontpage`
3. Krebs on Security — `https://krebsonsecurity.com/feed/`
4. MIT Tech Review AI — `https://www.technologyreview.com/topic/artificial-intelligence/feed/`
5. Manufacturing Dive — `https://www.manufacturingdive.com/feeds/news/`
6. TechCrunch AI — `https://techcrunch.com/category/artificial-intelligence/feed/`
7. The Verge — `https://www.theverge.com/rss/index.xml`
8. Wired — `https://www.wired.com/feed/rss`

Replaced (failed):
- Automation World (404)
- BleepingComputer (403)
- O'Reilly Radar (301)
- The Register (302)
- The Verge AI-specific feed (404)
- Wired Security-specific feed (404)

## Cron Job

Silent watchdog cron: `Blogwatcher Feed Scan` — every 240m, no_agent mode.
Script: `~/AppData/Local/hermes/scripts/blogwatcher-scan.sh`

```bash
#!/usr/bin/env bash
BW="$HOME/go/bin/blogwatcher-cli"
if [ ! -x "$BW" ]; then
    echo "[BLOGWATCHER] blogwatcher-cli not found"
    exit 1
fi
OUTPUT=$("$BW" scan 2>&1) || { echo "[BLOGWATCHER] Scan failed"; exit 1; }
FAILURES=$(echo "$OUTPUT" | grep -c "Error:" || true)
SUCCESSES=$(echo "$OUTPUT" | grep -c "Source: RSS" || true)
if [ "$FAILURES" -gt 0 ] && [ "$SUCCESSES" -eq 0 ]; then
    echo "[BLOGWATCHER] All feeds failed"
    exit 1
fi
exit 0  # silent on partial/complete success
```
