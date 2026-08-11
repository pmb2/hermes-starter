#!/usr/bin/env python3
"""
Firefox Cookie Import for Camoufox — with graceful Camoufox-down handling.
Patched June 21, 2026: previously the script exited with code 1 and errored
the cron job every cycle when Camoufox wasn't running. Now it attempts to
start Camoufox first, and exits cleanly if the browser can't be reached.

Key pattern: watchdog scripts that run as no_agent cron jobs should NOT
sys.exit(1) when their dependency is unavailable — they should either
start the dependency or exit 0 with a log message. Otherwise the cron
system marks the job as errored even though the condition is expected.
"""
import json
import os
import sqlite3
import urllib.request
import sys

PROFILE = os.path.expanduser(
    "~/AppData/Roaming/Mozilla/Firefox/Profiles/<profile-id>.default-release-1"
)
CAMOFOX_URL = "http://localhost:9377"
USER_ID = "the operator"

def get_firefox_cookies():
    """Extract all cookies from Firefox profile."""
    db_path = os.path.join(PROFILE, "cookies.sqlite")
    if not os.path.exists(db_path):
        print(f"ERROR: Cookie database not found at {db_path}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{db_path}?immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT name, value, host, path, expiry, isSecure, isHttpOnly, sameSite
        FROM moz_cookies
        WHERE expiry > strftime('%s', 'now')
        ORDER BY lastAccessed DESC
    """)

    cookies = []
    for row in cursor.fetchall():
        domain = row["host"].lstrip(".")
        cookie = {
            "name": row["name"],
            "value": row["value"],
            "domain": domain,
            "path": row["path"],
            "expires": -1 if row["expiry"] <= 0 else int(row["expiry"] / 1000),
            "httpOnly": bool(row["isHttpOnly"]),
            "secure": bool(row["isSecure"]),
            "sameSite": ["Strict", "Lax", "None"][min(row["sameSite"] or 0, 2)],
        }
        if cookie["expires"] == 0:
            cookie["expires"] = -1
        cookies.append(cookie)

    conn.close()
    return cookies

def import_to_camofox(cookies, batch_size=100):
    """Import cookies into Camofox session via REST API."""
    total = len(cookies)
    imported = 0
    for i in range(0, total, batch_size):
        batch = cookies[i : i + batch_size]
        data = json.dumps({"cookies": batch}).encode()
        req = urllib.request.Request(
            f"{CAMOFOX_URL}/sessions/{USER_ID}/cookies",
            data=data, method="POST",
        )
        req.add_header("Content-Type", "application/json")
        try:
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read())
            count = result.get("count", 0)
            imported += count
            print(f"  Batch {i//batch_size + 1}: {count} cookies imported")
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:200]
            print(f"  Batch {i//batch_size + 1} FAILED: HTTP {e.code}: {body}")
    return imported

if __name__ == "__main__":
    print("=== Firefox Cookie Import for Camoufox ===\n")

    print(f"Reading cookies from: {PROFILE}")
    cookies = get_firefox_cookies()
    print(f"Found {len(cookies)} unexpired cookies\n")

    # Check Camofox health — attempt to start it if not running
    try:
        health = json.loads(
            urllib.request.urlopen(f"{CAMOFOX_URL}/health", timeout=5).read()
        )
        engine = health.get("engine", "?")
        print(f"Camofox status: engine={engine}, connected={health.get('browserConnected')}\n")
    except Exception as e:
        print(f"Camofox not running: {e}")
        print("Attempting to start Camofox via stealth-browser watchdog...")
        start_script = os.path.expanduser(
            "~/AppData/Local/hermes/scripts/start-stealth-browser.sh"
        )
        if os.path.exists(start_script):
            ret = os.system(f"bash '{start_script}'")
            if ret == 0:
                print("Camofox started. Retrying cookie import...")
                try:
                    health = json.loads(
                        urllib.request.urlopen(f"{CAMOFOX_URL}/health", timeout=5).read()
                    )
                    print(f"Camofox now running: {health.get('engine')}\n")
                except Exception as e2:
                    print(f"Camofox still not available: {e2}")
                    print("Will retry next cycle. Exiting cleanly.")
                    sys.exit(0)
            else:
                print(f"Start script returned {ret}. Exiting cleanly.")
                sys.exit(0)
        else:
            print(f"Start script not found. Exiting cleanly.")
            sys.exit(0)

    print(f"Importing {len(cookies)} cookies...")
    imported = import_to_camofox(cookies)
    print(f"\nTotal imported: {imported} cookies\n")
    print("=== IMPORT COMPLETE ===")
