#!/usr/bin/env python3
"""Buzz Test-Message Cleanup — deletes stray/test messages from the hosted relay.

Deletes NIP-29 channel messages (kind 9) that match test/stray patterns:
  - "@Forge test connection", "bridge test", "OmniRoute test hello"
  - "@Forge: Received. Processing..." spam (40+ identical messages)
  - "Thinking. 1. **Analyze the Request:**" reasoning-dump spam
  - "reporting for duty", "online and watching", "connected via Buzz Desktop"

Deletion is done via NIP-09 kind-5 events signed with the ORIGINAL AUTHOR's
key (relay requires deletion events to be authored by the event owner).

Usage: python buzz_cleanup.py [--dry-run] [--limit N]
"""
import json, sys, time, datetime
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from buzz_client import BuzzClient

HOSTED = "ws://localhost:3000"  # LOCAL relay is primary (2026-08-01 migration)
KEYS = json.loads((ROOT / "buzz_keys.json").read_text())
CHANS = json.loads((ROOT / "buzz_channels.json").read_text())
REV = {v: k for k, v in CHANS.items()}

TEST_PATTERNS = [
    "test connection", "bridge test", "omniroute test", "multi-channel test",
    "test working", "test hello", "test message", "testing", "self-test",
    "received. processing", "processing...", "reporting for duty",
    "online and watching", "connected via buzz desktop", "in the building",
    "thinking. 1.  **analyze the request",
    "is this thing on", "hello?", "ping test", "can you hear me",
]

# Channel intro/description messages (emoji + **X Channel** — description).
# These legitimately contain words like "testing" (Testing Channel intro) and
# must NEVER be deleted as stray test messages.
CHANNEL_INTRO_RE = "channel** —"


def is_test(content: str) -> bool:
    low = content.lower()
    # Channel intros are legitimate — never treat as test spam
    if CHANNEL_INTRO_RE in low:
        return False
    return any(p in low for p in TEST_PATTERNS)


DRY_RUN = "--dry-run" in sys.argv
LIMIT = None
if "--limit" in sys.argv:
    try:
        LIMIT = int(sys.argv[sys.argv.index("--limit") + 1])
    except Exception:
        LIMIT = None


def main():
    sk = KEYS["the operator"]["secret_key"]
    client = BuzzClient(sk, relay_url=HOSTED)
    if not client.connect():
        print("FATAL: could not authenticate to hosted relay")
        return 1

    evts = client.query({"kinds": [9], "limit": 500}, timeout=12)
    print(f"Fetched {len(evts)} kind-9 events")

    # Group by author so we can sign deletions with the right key
    by_author = {}
    for e in evts:
        by_author.setdefault(e["pubkey"], []).append(e)

    # Identify test events
    test_evts = [e for e in evts if is_test(e.get("content", ""))]
    # Drop events we can't delete (author key unknown / not in KEYS)
    deletable = []
    skipped_unknown_author = 0
    for e in test_evts:
        author = e.get("pubkey")
        author_name = next((k for k, v in KEYS.items() if v.get("public_key") == author), None)
        if author_name and "secret_key" in KEYS[author_name]:
            deletable.append((e, author_name))
        else:
            skipped_unknown_author += 1

    print(f"Test/stray events: {len(test_evts)} | deletable: {len(deletable)} | "
          f"skipped (unknown author): {skipped_unknown_author}")

    if LIMIT:
        deletable = deletable[:LIMIT]

    if DRY_RUN:
        for e, aname in deletable[:30]:
            h = next((t[1] for t in e.get("tags", []) if t[0] == "h"), "?")
            ts = datetime.datetime.utcfromtimestamp(e.get("created_at", 0)).strftime("%m-%d %H:%M")
            print(f"  [DRY] would delete [{REV.get(h, h[:8])}] {ts} by {aname} :: {e.get('content','')[:60]!r}")
        print(f"\nDRY RUN: {len(deletable)} deletions would be sent.")
        client.close()
        return 0

    # Send NIP-09 deletions grouped per author
    deleted = 0
    failed = 0
    for author_pk, group in by_author.items():
        group_tests = [e for e, an in deletable if e["pubkey"] == author_pk]
        if not group_tests:
            continue
        author_name = next((k for k, v in KEYS.items() if v.get("public_key") == author_pk), author_pk[:8])
        ask = KEYS.get(author_name, {}).get("secret_key")
        if not ask:
            continue
        try:
            ac = BuzzClient(ask, relay_url=HOSTED)
            if not ac.connect():
                print(f"  auth failed for {author_name}, skipping {len(group_tests)} deletions")
                failed += len(group_tests)
                continue
            for e in group_tests:
                eid = e["id"]
                # kind 5 = deletion, tag e = target event
                ok = ac.send_event(5, "", [["e", eid]])
                if ok:
                    deleted += 1
                else:
                    failed += 1
            ac.close()
            print(f"  {author_name}: deleted {len(group_tests)} messages")
        except Exception as ex:
            print(f"  {author_name}: ERROR {str(ex)[:80]}")
            failed += len(group_tests)

    client.close()
    print(f"\nDONE: {deleted} deleted, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
