#!/usr/bin/env python3
"""buzz_presence.py — Post agent presence intros into each agent's channels.

One-time setup: for each agent, post a short presence/intro message into
each of its assigned channels (signed with the agent's own key), so every
agent is visibly "in" its chats on the Buzz relay. Idempotent — checks the
relay for existing presence messages from that agent in that channel
before posting.

Usage: python buzz_presence.py [--force]
"""
import json, sys, time, datetime
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from buzz_client import BuzzClient

LOCAL = "ws://localhost:3000"
KEYS = json.loads((ROOT / "buzz_keys.json").read_text())
CHANS = json.loads((ROOT / "buzz_channels.json").read_text())

FORCE = "--force" in sys.argv

INTROS = {
    "chief-of-staff": "🛡️ Chief online — cross-agent coordination. Report here.",
    "development-lead": "🔧 Architect online — dev lead. Working core & engineering.",
    "intelligence-lead": "🔬 Oracle online — intel digests & cross-referencing.",
    "research-lead": "📚 Nova online — deep research & exploration.",
    "operations-lead": "📡 Pulse online — infrastructure & monitoring.",
    "security-lead": "🔒 Vigil online — security monitoring & hardening.",
    "creative-lead": "🎨 Muse online — creative direction & content.",
}


def main():
    sk = KEYS["the operator"]["secret_key"]
    probe = BuzzClient(sk, relay_url=LOCAL)
    if not probe.connect():
        print("FATAL: cannot authenticate")
        return 1

    posted = skipped = failed = 0
    for name, data in sorted(KEYS.items()):
        if name == "the operator" or not isinstance(data, dict):
            continue
        akey = data.get("secret_key")
        apk = data.get("public_key")
        if not akey or not apk:
            continue
        intro = INTROS.get(name)
        if not intro:
            continue
        for chan in data.get("channels", []):
            ch_uuid = CHANS.get(chan)
            if not ch_uuid:
                continue
            if not FORCE:
                # Idempotence: has this agent already posted a presence msg here?
                existing = probe.query(
                    {"kinds": [9], "authors": [apk], "#h": [ch_uuid], "limit": 5}, timeout=6
                )
                if existing:
                    skipped += 1
                    continue
            ac = BuzzClient(akey, relay_url=LOCAL)
            if not ac.connect():
                failed += 1
                continue
            eid = ac.send_channel_message(ch_uuid, intro)
            ac.close()
            if eid:
                posted += 1
            else:
                failed += 1
            time.sleep(0.2)

    probe.close()
    print(f"DONE: {posted} presence messages posted, {skipped} already present, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
