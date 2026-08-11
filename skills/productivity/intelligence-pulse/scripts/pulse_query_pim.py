#!/usr/bin/env python3
"""
pulse_query_pim.py — Direct PIM DB queries for pulse delivery.
Avoids dependency on intelligence_collector.py (which can hang on Firefox DB lock).
Call this when the collector times out or you need fast results.

Usage:
    python pulse_query_pim.py                    # New items (last 4 hours) by source
    python pulse_query_pim.py --hours 24         # Custom window
    python pulse_query_pim.py --recent           # Recent item titles
    python pulse_query_pim.py --sources          # Source freshness
    python pulse_query_pim.py --all              # Full summary (all modes)
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta, timezone

PIM_DB = os.environ.get(
    "PIM_DB_PATH",
    "${MY_REPOS}/Documents/github/git-mcp/services/personal-intelligence-mcp/pim.db"
)


def connect():
    if not os.path.exists(PIM_DB):
        print(f"[PIM] ERROR: DB not found at {PIM_DB}")
        sys.exit(1)
    return sqlite3.connect(PIM_DB)


def new_items_by_source(hours=4):
    """Count new items grouped by source type."""
    conn = connect()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    cursor = conn.execute(
        """SELECT source_type, COUNT(*) as count
           FROM saved_items
           WHERE ingested_at > ?
           GROUP BY source_type
           ORDER BY count DESC""",
        (cutoff,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print(f"[PIM] 0 new items in the last {hours}h across all sources")
        return 0

    total = sum(r[1] for r in rows)
    print(f"[PIM] {total} new items in the last {hours}h:")
    for source, count in rows:
        print(f"  \u2022 {source}: {count}")
    return total


def recent_items(limit=15):
    """Show most recent items with titles and URLs."""
    conn = connect()
    cursor = conn.execute(
        """SELECT source_type, title, source_url, ingested_at
           FROM saved_items
           ORDER BY ingested_at DESC
           LIMIT ?""",
        (limit,),
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        print("[PIM] No items found")
        return

    print(f"[PIM] {len(rows)} most recent items:")
    for source, title, url, ts in rows:
        title_short = (title or "Untitled")[:70]
        print(f"  \u2022 [{source}] {title_short}")
        if url:
            print(f"    {url}")


def source_freshness():
    """When each source last ingested and total counts."""
    conn = connect()
    cursor = conn.execute(
        """SELECT source_type, MAX(ingested_at) as last_ingested, COUNT(*) as total
           FROM saved_items
           GROUP BY source_type
           ORDER BY last_ingested DESC"""
    )
    rows = cursor.fetchall()
    conn.close()

    print("[PIM] Source freshness:")
    now = datetime.now(timezone.utc)
    for source, last_ts, total in rows:
        try:
            dt = datetime.fromisoformat(last_ts)
            hours_ago = (now - dt).total_seconds() / 3600
            if hours_ago < 6:
                status = "\u2705"
            elif hours_ago < 24:
                status = "\u26a0\ufe0f"
            else:
                status = "\u274c"
            print(f"  {status} {source}: {hours_ago:.0f}h ago ({total} total)")
        except Exception:
            print(f"  \u2753 {source}: last={last_ts} ({total} total)")


def full_summary():
    """Combined output for a quick pulse check."""
    print("=" * 50)
    print("PIM Pulse Summary")
    print("=" * 50)
    new_items_by_source(4)
    print()
    source_freshness()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "--all" in args:
        full_summary()
    elif "--sources" in args:
        source_freshness()
    elif "--recent" in args:
        limit = 15
        for a in args:
            if a.startswith("--limit="):
                limit = int(a.split("=")[1])
        recent_items(limit)
    elif "--hours" in args:
        idx = args.index("--hours")
        hours = int(args[idx + 1]) if idx + 1 < len(args) else 24
        new_items_by_source(hours)
    else:
        new_items_by_source(4)
