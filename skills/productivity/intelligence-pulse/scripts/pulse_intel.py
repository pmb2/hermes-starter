#!/usr/bin/env python3
"""
Pulse Intelligence Check — run from the heartbeat cron.

Checks all data sources for NEW content since the last check,
cross-references against active project priorities, and outputs
a structured report.

Usage:
    python pulse_intel.py [--last-check TIMESTAMP] [--output json|text]

Outputs to stdout. Pipe to the Pulse cron for inclusion in the heartbeat.

KNOWN ISSUE: Firefox places.sqlite is locked when Firefox is running.
The bookmark check will hang (silent timeout). If no bookmarks appear,
Firefox is likely open — check pim.db instead (it already ingests bookmarks).

DUAL-TRACKING NOTE: This script maintains its own last_check.json independent
of intelligence_collector.py's .last_intelligence_check file. When the collector
runs between pulse_intel.py calls, items may appear under the PIM source in
both tools. This is expected — pulse_intel.py is a fallback for when the
collector times out, not a replacement.
"""

import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
HOME = Path.home()
BOOKMARKS_DB = HOME / "AppData/Roaming/Mozilla/Firefox/Profiles/<profile-id>.default-release-1/places.sqlite"
GITMCP_DB = Path("${MY_REPOS}/git-mcp/services/github-star-intelligence-mcp/gitmcp.db")
PIM_DB = Path("${MY_REPOS}/git-mcp/services/personal-intelligence-mcp/pim.db")
LAST_CHECK_FILE = Path(__file__).parent / "last_check.json"

# ── Active Project Keywords ────────────────────────────────────────────────
PROJECT_KEYWORDS = {
    "P0: Engineering": ["deploy", "ci", "pipeline", "refactor", "regression", "test", "release"],
    "P1: AI & Agents": ["agent", "llm", "mcp", "fine-tune", "rag", "inference", "context window"],
    "P1: Open Source": ["opensource", "github", "stars", "repository", "maintainer", "contributor"],
    "P2: DevSecOps": ["vulnerability", "cve", "hardening", "threat", "zero-day", "incident"],
}


def load_last_check():
    """Load last-check timestamps from file."""
    if LAST_CHECK_FILE.exists():
        return json.loads(LAST_CHECK_FILE.read_text())
    return {"bookmarks": 0, "github_stars": "2000-01-01T00:00:00Z", "pim": "2000-01-01T00:00:00Z"}


def save_last_check(stamps):
    LAST_CHECK_FILE.write_text(json.dumps(stamps, indent=2))


def check_bookmarks(last):
    """
    Check Firefox bookmarks for new entries.

    NOTE: This hangs indefinitely if Firefox is running (places.sqlite lock).
    Returns an error entry in that case so callers can fall back to PIM DB.
    """
    if not BOOKMARKS_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(BOOKMARKS_DB))
        cur = conn.cursor()
        cur.execute("""
            SELECT b.title, p.url, b.dateAdded / 1000000
            FROM moz_bookmarks b
            JOIN moz_places p ON b.fk = p.id
            WHERE b.type = 1 AND b.dateAdded / 1000000 > ?
            ORDER BY b.dateAdded DESC
            LIMIT 20
        """, (last,))
        results = [{"title": r[0] or "(untitled)", "url": r[1], "date": r[2]} for r in cur.fetchall()]
        conn.close()
        return results
    except sqlite3.OperationalError as e:
        # Likely "database is locked" — Firefox is running
        return [{"error": f"lock: {e}", "hint": "Firefox is open — use pim.db fallback"}]
    except Exception as e:
        return [{"error": str(e)}]


def check_github_stars(last):
    """Check GitHub stars for new entries."""
    if not GITMCP_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(GITMCP_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        # The star DB table is 'github_repos' (not 'starred_repos')
        cur.execute("""
            SELECT full_name, owner, name, html_url, description,
                   stars_count, forks_count, primary_language, topics,
                   created_at AS repo_created_at, starred_at
            FROM github_repos
            WHERE starred_at > ?
            ORDER BY stars_count DESC
            LIMIT 20
        """, (last,))
        results = []
        for r in cur.fetchall():
            results.append({
                "title": r["name"],
                "full_name": r["full_name"],
                "description": r["description"] or "",
                "url": r["html_url"],
                "date": r["starred_at"],
                "lang": r["primary_language"] or "",
            })
        conn.close()
        return results
    except Exception as e:
        return [{"error": str(e)}]


def check_pim(last):
    """
    Check Personal Intelligence DB for new items.
    
    Uses the `saved_items` table. This is the canonical source after ingestion
    — it contains bookmarks, github_stars, youtube, and email items.
    """
    if not PIM_DB.exists():
        return []
    try:
        conn = sqlite3.connect(str(PIM_DB))
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT id, source_type, title, source_url, full_text,
                   tags, created_at, ingested_at
            FROM saved_items
            WHERE ingested_at > ?
            ORDER BY ingested_at DESC
            LIMIT 30
        """, (last,))
        results = []
        for r in cur.fetchall():
            results.append({
                "title": r["title"] or "(untitled)",
                "url": r["source_url"] or "",
                "source": r["source_type"],
                "summary": (r["full_text"] or "")[:200],
                "tags": r["tags"] or "[]",
                "date": r["ingested_at"],
            })
        conn.close()
        return results
    except Exception as e:
        return [{"error": str(e)}]


def classify_item(title, summary="", tags=""):
    """Determine which active project(s) an item relates to."""
    text = f"{title} {summary} {tags}".lower()
    matches = []
    for project, keywords in PROJECT_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text:
                matches.append(project)
                break
    return matches if matches else ["uncategorized"]


def main():
    stamps = load_last_check()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    
    new_stamps = dict(stamps)
    items = []

    # Phase 1: Collect — try Firefox first, fall back silently
    bookmarks = check_bookmarks(stamps.get("bookmarks", 0))
    if bookmarks and "error" not in bookmarks[0]:
        for b in bookmarks:
            items.append({"source": "bookmark", "title": b["title"], "url": b["url"], "date": str(b["date"])})
        if bookmarks:
            new_stamps["bookmarks"] = max(b["date"] for b in bookmarks)

    github = check_github_stars(stamps.get("github_stars", "2000-01-01T00:00:00Z"))
    if github and "error" not in github[0]:
        for g in github:
            items.append({"source": "github_star", "title": g["title"], "url": g["url"],
                          "description": g["description"], "date": g["date"] or now_iso})
        if github:
            new_stamps["github_stars"] = github[0]["date"] or now_iso

    pim = check_pim(stamps.get("pim", "2000-01-01T00:00:00Z"))
    if pim and "error" not in pim[0]:
        for p in pim:
            items.append({"source": p["source"], "title": p["title"], "url": p["url"],
                          "summary": p["summary"], "tags": p["tags"], "date": p["date"]})
        if pim:
            new_stamps["pim"] = pim[0]["date"]

    # Phase 2: Classify
    classified = {"P0": [], "P1": [], "P2": [], "P3": [], "uncategorized": []}
    for item in items:
        matches = classify_item(item.get("title", ""), item.get("summary", ""), item.get("tags", ""))
        for m in matches:
            if m.startswith("P0"):
                classified["P0"].append(item)
            elif m.startswith("P1"):
                classified["P1"].append(item)
            elif m.startswith("P2"):
                classified["P2"].append(item)
            elif m.startswith("P3"):
                classified["P3"].append(item)
            else:
                classified["uncategorized"].append(item)

    # Phase 3: Report
    total = len(items)
    if total == 0:
        last_check_time = stamps.get("pim", stamps.get("bookmarks", "unknown"))
        if isinstance(last_check_time, str) and last_check_time != "unknown":
            # Check how recent the last successful ingestion was
            # (datetime is already imported at module level — no re-import needed)
            try:
                last_dt = datetime.fromisoformat(last_check_time.rstrip("Z"))
                delta = datetime.now(timezone.utc) - last_dt.replace(tzinfo=timezone.utc)
                if delta.total_seconds() < 300:  # < 5 min
                    print(f"[INTEL] No new items — last check was {int(delta.total_seconds())}s ago. Pipeline is alive but recently checked.")
                else:
                    print(f"[INTEL] No new items since {last_check_time[:19]} ({int(delta.total_seconds()/60)}m ago).")
            except Exception:
                print(f"[INTEL] No new items since last check ({last_check_time}).")
        else:
            print("[INTEL] No new items since last check.")
        save_last_check(new_stamps)
        return

    print(f"🧠 Intelligence Check — {total} new items")
    print()

    for priority in ["P0", "P1", "P2", "P3"]:
        if classified[priority]:
            label = {"P0": "🔴 ACTIVE WORK", "P1": "🟡 IMPORTANT", "P2": "🟢 LATER", "P3": "🔵 BLOCKED"}[priority]
            print(f"=== {label} ===")
            for item in classified[priority][:5]:
                title = item.get("title", "?")
                url = item.get("url", "")
                src = item.get("source", "?")
                desc = item.get("description", item.get("summary", ""))[:120]
                print(f"  • {title}")
                if desc:
                    print(f"    {desc}")
                print(f"    [{src}] {url}")
            print()

    if classified["uncategorized"]:
        print("=== ⚪ UNCATEGORIZED ===")
        for item in classified["uncategorized"][:5]:
            title = item.get("title", "?")
            src = item.get("source", "?")
            print(f"  • {title} [{src}]")
        print()

    save_last_check(new_stamps)


if __name__ == "__main__":
    main()
