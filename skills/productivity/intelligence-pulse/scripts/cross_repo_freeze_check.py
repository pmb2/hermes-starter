#!/usr/bin/env python3
"""
cross_repo_freeze_check.py — Multi-repo stall detection for pulse delivery.

Walks all git repos under GITHUB_BASE (default: ${MY_REPOS}/),
extracts last-commit date + message + author for each, then detects two patterns:

  1. Multi-repo same-date stalls: >=3 repos with the SAME last-commit date AND
     that date is >3 days ago. A systemic abandonment signal.
  2. Pre-migration freeze: same as above but commit messages contain
     "pre-migration" or "prep:" — the user hit a migration wall
     and froze everything simultaneously.

Output: human-readable report + JSON blob for programmatic use.

Usage:
    python scripts/cross_repo_freeze_check.py
    python scripts/cross_repo_freeze_check.py --hours 7  # custom stall threshold
    python scripts/cross_repo_freeze_check.py --json      # JSON-only output
    python scripts/cross_repo_freeze_check.py --full      # include per-repo detail
"""

import os
import subprocess
import sys
import json
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

_default_base = os.environ.get("GITHUB_BASE", "")
if not _default_base:
    # Windows-native path required for git subprocess compatibility
    for candidate in ["${MY_REPOS}/Documents/github", "${MY_REPOS}"]:
        if Path(candidate).is_dir():
            _default_base = candidate
            break
    if not _default_base:
        _default_base = "${MY_REPOS}/Documents/github"
GITHUB_BASE = _default_base
STALL_DAYS_DEFAULT = 3  # repos older than this are "cold"
FREEZE_KEYWORDS = ["pre-migration", "prep:", "prep "]


def get_last_commit(repo_path: Path) -> dict | None:
    """Return {date, message, author} for the last commit, or None if no commits."""
    git_dir = repo_path / ".git"
    if not git_dir.is_dir():
        # Check if .git is a file (worktree)
        git_file = repo_path / ".git"
        if not git_file.exists():
            return None

    try:
        # Date
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", "-1", "--format=%as"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode != 0:
            return None
        date_str = result.stdout.strip()
        if not date_str:
            return None

        # Message
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", "-1", "--format=%s"],
            capture_output=True, text=True, timeout=10
        )
        msg = result.stdout.strip() if result.returncode == 0 else ""

        # Author
        result = subprocess.run(
            ["git", "-C", str(repo_path), "log", "-1", "--format=%an"],
            capture_output=True, text=True, timeout=10
        )
        author = result.stdout.strip() if result.returncode == 0 else ""

        return {"date": date_str, "message": msg, "author": author}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def days_since(commit_date: str) -> int | None:
    """Return days since this commit date, or None if unparseable."""
    try:
        d = datetime.strptime(commit_date, "%Y-%m-%d").date()
        return (date.today() - d).days
    except ValueError:
        return None


def main():
    stall_days = int(sys.argv[sys.argv.index("--hours") + 1]) if "--hours" in sys.argv else STALL_DAYS_DEFAULT
    output_json = "--json" in sys.argv
    full_detail = "--full" in sys.argv

    repos = {}
    base_path = Path(GITHUB_BASE)
    for d in sorted(base_path.iterdir()):
        if not d.is_dir() or d.name.startswith("."):
            continue
        info = get_last_commit(d)
        if info is not None:
            repos[d.name] = info

    # Group by last-commit date
    by_date: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    # (repo_name, author, message)
    for repo, info in repos.items():
        by_date[info["date"]].append((repo, info["author"], info["message"]))

    # Filter: dates with >=3 repos AND older than stall_days
    stall_dates = {}
    pre_migration_dates = {}
    today = date.today()
    for commit_date, repo_list in sorted(by_date.items()):
        try:
            d = datetime.strptime(commit_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        age = (today - d).days
        if age > stall_days and len(repo_list) >= 3:
            # Check for pre-migration pattern
            pre_migration_count = sum(
                1 for _, _, msg in repo_list
                if any(kw in msg.lower() for kw in FREEZE_KEYWORDS)
            )
            stall_dates[commit_date] = {
                "count": len(repo_list),
                "age_days": age,
                "repos": [{"name": r, "author": a, "message": m} for r, a, m in repo_list],
                "pre_migration_count": pre_migration_count,
                "is_pre_migration_freeze": pre_migration_count >= 3,
            }

    if output_json:
        print(json.dumps({
            "total_repos_checked": len(repos),
            "stall_dates": stall_dates,
            "has_stall": len(stall_dates) > 0,
            "has_pre_migration": any(
                sd["is_pre_migration_freeze"] for sd in stall_dates.values()
            ),
        }, indent=2))
        return

    # Human-readable output
    print(f"=== Cross-Repo Freeze Check ===")
    print(f"Repo base: {GITHUB_BASE}")
    print(f"Repos checked: {len(repos)}")
    print(f"Stall threshold: {stall_days}+ days, >=3 repos\n")

    if not stall_dates:
        print("✅ No multi-repo stalls detected.")
        return

    for commit_date, sd in sorted(stall_dates.items()):
        label = "🔴 PRE-MIGRATION FREEZE" if sd["is_pre_migration_freeze"] else "📌 MULTI-REPO STALL"
        print(f"{label} — {sd['count']} repos frozen since {commit_date} ({sd['age_days']} days ago)")

        if full_detail:
            for r in sd["repos"]:
                msg_short = r["message"][:80]
                print(f"  • {r['name']}: \"{msg_short}\" [{r['author']}]")
        else:
            names = ", ".join(r["name"] for r in sd["repos"])
            print(f"  Repos: {names}")

        if sd["is_pre_migration_freeze"]:
            print(f"  ⚠️  {sd['pre_migration_count']}/{sd['count']} repos have 'pre-migration' in commit message")
            print(f"  → User hit a migration wall and abandoned all at once")
        print()

    # Also show any repos with recent human activity (for absence detection)
    recent_human = []
    for repo, info in repos.items():
        days = days_since(info["date"])
        if days is not None and days <= 2:
            is_autogit = "autogit" in info["message"].lower()
            if not is_autogit:
                recent_human.append((repo, info))
    if recent_human and full_detail:
        print("\nRecent human commits (last 48h, non-autogit):")
        for repo, info in recent_human:
            print(f"  • {repo} ({info['date']}): {info['message'][:80]} [{info['author']}]")


if __name__ == "__main__":
    main()
