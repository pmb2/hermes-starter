#!/usr/bin/env python3
"""
Buzz Channel Scanner — queries all relay channels for recent activity.

Usage:
    python buzz_scan_channels.py

Output:
    - Prints all kind 9, 1, and 7 events from the last N hours
    - Groups by channel, sorted by most recent
    - Flags urgent keywords, @Chief mentions, stalled conversations
    - Prints "URGENT=YES" or "URGENT=NO" on last line

Config:
    Edit RELAY_URL, SECRET_KEY_HEX, and CHANNEL_UUIDS at the top of main()
    or import from buzz_keys.json / buzz_channels.json.

Dependencies:
    pip install nostr-protocol websocket-client
"""
import json
import time
import websocket
import nostr_protocol as np

# === CONFIG ===
RELAY_URL = "ws://localhost:3000"
NOW = int(time.time())
WINDOW_SECONDS = 14400  # 4 hours
FOUR_HOURS_AGO = NOW - WINDOW_SECONDS

# Load CoS key from buzz_keys.json
COS_KEY = None
try:
    import json as _json
    with open("buzz_keys.json") as _f:
        _kd = _json.load(_f)
    COS_KEY = _kd.get("chief-of-staff", {}).get("secret_key")
except Exception:
    pass

SECRET_KEY_HEX = COS_KEY or "<relay-pubkey-hex>"

# Load channel map from buzz_channels.json
CHANNEL_UUIDS = {}
try:
    with open("buzz_channels.json") as _f:
        CHANNEL_UUIDS = json.load(_f)
except Exception:
    # Fallback minimal set
    CHANNEL_UUIDS = {
        "admin": "86d52a2d-5180-4894-9afa-3db6e372812e",
        "general": "71f00d9c-ee58-5c2e-be3a-546536fa1ed7",
        "engineering": "77392233-6f07-4817-b58f-30453485ef7f",
        "devops": "24443fd6-7f24-446d-8644-591ed38f384e",
        "monitoring": "ad19186a-7fd0-47b2-8732-4bef10f47dd5",
    }

UUID_TO_CHANNEL = {v: k for k, v in CHANNEL_UUIDS.items()}

# Load agent pubkey map from buzz_keys.json
AGENT_KEY_MAP = {}
try:
    with open("buzz_keys.json") as _f:
        _kd = json.load(_f)
    AGENT_KEY_MAP = {v["public_key"]: name for name, v in _kd.items()}
except Exception:
    pass


def resolve_author(pubkey_hex):
    return AGENT_KEY_MAP.get(pubkey_hex, pubkey_hex[:12] + "...")


def main():
    print(f"🔍 Buzz Channel Scan — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}")
    print(f"   Window: last {WINDOW_SECONDS//3600}h (since {time.strftime('%H:%M UTC', time.gmtime(FOUR_HOURS_AGO))})")
    print(f"   Relay: {RELAY_URL}")
    print(f"   Channels: {len(CHANNEL_UUIDS)}")

    keys = np.Keys.parse(SECRET_KEY_HEX)
    ws = websocket.WebSocket()
    ws.settimeout(8)
    ws.connect(RELAY_URL)
    print(f"✅ Connected")

    # NIP-42 AUTH
    challenge = None
    try:
        msg = json.loads(ws.recv())
        if msg[0] == "AUTH":
            challenge = msg[1]
    except Exception as e:
        print(f"⚠️ init: {e}")
        ws.close()
        return

    if challenge:
        ev = np.EventBuilder.auth(challenge, RELAY_URL).to_event(keys)
        ws.send(json.dumps(["AUTH", json.loads(ev.as_json())]))
        try:
            resp = json.loads(ws.recv())
            if resp[0] == "OK" and resp[2] is True:
                print(f"🔐 AUTH OK")
            else:
                print(f"🔐 AUTH: {resp}")
        except Exception as e:
            print(f"⚠️ auth: {e}")

    # Query kind 9, 1, 7
    all_events = []
    for k, sub in [(9, "s9"), (1, "s1"), (7, "s7")]:
        filt = {"kinds": [k], "since": FOUR_HOURS_AGO, "limit": 500}
        ws.send(json.dumps(["REQ", sub, filt]))
        end = time.time() + 5
        while time.time() < end:
            try:
                msg = json.loads(ws.recv())
                if msg[0] == "EVENT" and msg[1] == sub:
                    all_events.append(msg[2])
                elif msg[0] == "EOSE" and msg[1] == sub:
                    break
            except websocket.WebSocketTimeoutException:
                break
            except Exception:
                break
        ws.send(json.dumps(["CLOSE", sub]))

    ws.close()
    print(f"📊 Events in window: {len(all_events)}")

    if not all_events:
        print("NOEVENTS")
        return

    # Group by channel
    ch_events = {}
    for ev in all_events:
        cuuid = None
        for t in ev.get("tags", []):
            if t and t[0] == "h" and len(t) > 1:
                cuuid = t[1]
                break
        ch = UUID_TO_CHANNEL.get(cuuid, "unk")
        ch_events.setdefault(ch, []).append(ev)
        ev["_channel"] = ch

    for ch in ch_events:
        ch_events[ch].sort(key=lambda e: e.get("created_at", 0), reverse=True)

    active = sorted(ch_events.items(),
                    key=lambda kv: kv[1][0].get("created_at", 0),
                    reverse=True)

    # Analyze
    urgent_kw = ["urgent", "crisis", "emergency", "critical", "🚨", "🔴",
                 "down", "broken", "outage", "blocker", "p0", "P0",
                 "fire", "asap", "ASAP", "failing", "failed"]
    urgent, mentions, threads, stalls = [], [], [], []
    stalled_cutoff = NOW - 7200

    for ch, evs in active:
        for ev in evs:
            c = ev.get("content", "")
            cl = c.lower()
            who = resolve_author(ev.get("pubkey", ""))
            if any(k in cl for k in urgent_kw):
                urgent.append(f"#{ch} {who}: {c[:130]}")
            if "@chief" in cl or "@cos" in cl or "@aegis" in cl:
                mentions.append(f"#{ch} {who}: {c[:130]}")
        first = evs[0]
        if not any(t and t[0] == "e" for t in first.get("tags", [])):
            threads.append(f"#{ch} {resolve_author(first.get('pubkey', ''))}: {first.get('content', '')[:80]}")
        if FOUR_HOURS_AGO <= first.get("created_at", 0) < stalled_cutoff:
            stalls.append(f"#{ch} last {int((NOW - first.get('created_at', 0))/60)}m by {resolve_author(first.get('pubkey', ''))}")

    if urgent:
        print(f"\n🔴 URGENT ({len(urgent)}):")
        for x in urgent[:6]:
            print(f"  {x}")
    if mentions:
        print(f"\n📢 @Chief/CoS ({len(mentions)}):")
        for x in mentions[:6]:
            print(f"  {x}")
    if threads:
        print(f"\n🆕 New threads ({len(threads)}):")
        for x in threads[:12]:
            print(f"  {x}")
    if stalls:
        print(f"\n⏸️ Stalled ({len(stalls)}):")
        for x in stalls[:6]:
            print(f"  {x}")

    print(f"\n📋 Active channels ({len(active)}):")
    for ch, evs in active:
        e0 = evs[0]
        ts = time.strftime('%H:%M', time.gmtime(e0.get('created_at', 0)))
        who = resolve_author(e0.get('pubkey', ''))
        n = len(evs)
        print(f"  #{ch} [{ts}] {who}: {e0.get('content', '')[:55]} ({n} msg)")

    if urgent or mentions:
        print("\nURGENT=YES")
    else:
        print("\nURGENT=NO")


if __name__ == "__main__":
    main()