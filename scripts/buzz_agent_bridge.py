#!/usr/bin/env python3
"""Buzz Agent Bridge — dedup'd, loop-free, auto-reconnect. Uses OmniRoute for AI.

Fixes applied (2026-08-01):
  - Writes own PID file (logs/buzz_bridge.pid) so watchdogs can check liveness
  - No global socket.setdefaulttimeout (was poisoning other threads)
  - Reply uses content only, falls back to reasoning when content is empty
  - Timestamped logging to logs/buzz_bridge.log
  - Hardened reconnect loop with exponential backoff
"""
import json, time, sys, re, os, socket, threading, http.client, logging
from pathlib import Path

ROOT = Path(__file__).parent
HERMES_HOME = Path(os.environ.get("HERMES_HOME") or Path.home() / "AppData" / "Local" / "hermes")
# Relay target: LOCAL relay is now primary (2026-08-01 migration).
# Override with BUZZ_RELAY_URL env var if ever needed.
HOSTED = os.environ.get("BUZZ_RELAY_URL", "ws://localhost:3000")
PIDFILE = HERMES_HOME / "logs" / "buzz_bridge.pid"
LOG = HERMES_HOME / "logs" / "buzz_bridge.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.FileHandler(LOG, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger("buzz-bridge")

KEYS = json.loads((ROOT / "buzz_keys.json").read_text())
CHANS = json.loads((ROOT / "buzz_channels.json").read_text())
CNAMES = {v: k for k, v in CHANS.items()}
# Channel representative mapping — which agent responds automatically in each channel
REPS = json.loads((ROOT / "channel_reps.json").read_text()) if (ROOT / "channel_reps.json").exists() else {}

# Ensure scripts dir is on sys.path so model_identity can be imported
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

AGENT_PUBKEYS = set()
for slug, data in KEYS.items():
    if slug != "the operator" and "public_key" in data:
        AGENT_PUBKEYS.add(data["public_key"])

ALIASES = {
    "chief-of-staff": ["Chief", "chief", "CoS", "cos"],
    "development-lead": ["Dev", "dev", "Architect", "architect"],
    "intelligence-lead": ["Intel", "intel", "Oracle", "oracle"],
    "operations-lead": ["Ops", "ops", "Pulse", "pulse"],
    "security-lead": ["Security", "security", "Vigil", "security-lead"],
    "creative-lead": ["Creative", "creative", "Muse", "creative-lead"],
    "research-lead": ["Research", "research", "Nova", "nova"],
}
REV = {}
for slug, names in ALIASES.items():
    for n in names:
        REV[n.lower()] = slug

# Per-agent personas fed to OmniRoute as the system prompt. This gives each
# agent real role context so replies are useful, not generic.
PERSONAS = {
    "chief-of-staff": "You are Chief, the Chief of Staff for the operator's AI ecosystem. You coordinate all agents, track the operation, and report up to the operator. Concise, decisive, mission-aware.",
    "development-lead": "You are Architect, the Development Lead. You manage the dev team and system health. Technical answers with specifics.",
    "intelligence-lead": "You are Oracle, the Intelligence Lead. You manage intel digests and cross-reference data with URLs.",
    "operations-lead": "You are Pulse, the Operations Lead. You track system health, containers, and automation. Metrics-driven.",
    "security-lead": "You are Vigil, the Security Lead. You monitor threats, review vulnerabilities, and recommend hardening. Serious and precise.",
    "creative-lead": "You are Muse, the Creative Lead. You brainstorm ideas, write compelling copy, and bring creative direction.",
    "research-lead": "You are Nova, the Research Lead. You deliver deep, well-sourced research briefs with structure and citations where possible.",
}
SEEN = set()


def write_pid():
    try:
        PIDFILE.parent.mkdir(parents=True, exist_ok=True)
        PIDFILE.write_text(str(__import__("os").getpid()))
    except Exception as e:
        log.warning("pid write failed: %s", e)


def omni_llm(display, query, slug=None):
    """Call OmniRoute and return AI response text (content preferred).

    Uses model_identity to resolve the active model for this agent.
    Falls back to the hardcoded workhorse model if identity module is missing.
    """
    try:
        # Resolve active model from model_identity
        model = "oc/deepseek-v4-flash-free"
        try:
            from model_identity import resolve_for_agent
            m = resolve_for_agent(slug) if slug else resolve_for_agent("chief-of-staff")
            model = m.get("omniroute_model") or model
        except Exception:
            pass

        persona = PERSONAS.get(slug) or f"You are {display}. Be concise."
        body = json.dumps({"model":model,"stream":True,
            "messages":[{"role":"system","content":persona},{"role":"user","content":query}],
            "max_tokens":200,"temperature":0.7})
        conn = http.client.HTTPConnection("localhost", 20128, timeout=40)
        conn.request("POST", "/v1/chat/completions", body, {"Content-Type":"application/json"})
        resp = conn.getresponse()
        raw = resp.read().decode()
        conn.close()
        reply = ''
        for line in raw.split("\n"):
            if line.startswith("data: ") and "DONE" not in line:
                try:
                    d = json.loads(line[6:]).get("choices",[{}])[0].get("delta",{})
                    c = d.get("content") or ""
                    r = d.get("reasoning_content") or ""
                    if c: reply += c
                    elif r and not reply: reply += r
                except: pass
        reply = reply.strip()[:1000] if reply else "On it."
        # Strip spurious leading "The" artifact (grok-4.5 prepends "The" to
        # short replies: "TheTANGERINE", "The**I am Nova..."). Only when
        # directly followed by uppercase or markdown — real sentences have a space.
        if reply.startswith("The") and len(reply) > 3 and reply[3] in "*ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            reply = reply[3:]
        return reply
    except Exception as e:
        log.warning("omni_llm error: %s", str(e)[:80])
        return ""


def delete_agent_msgs(matched, akey, evt):
    """Send NIP-09 deletions for agent's recent messages in channel."""
    try:
        sys.path.insert(0, str(ROOT))
        from buzz_client import BuzzClient
        chan = next((t[1] for t in evt.get("tags", []) if t[0] == "h"), "")
        ac = BuzzClient(akey, relay_url=HOSTED)
        if not ac.connect():
            log.warning("  del auth failed for %s", matched)
            return
        ac.ws.settimeout(10)
        sid = "d" + str(int(time.time()))
        ac.ws.send(json.dumps(["REQ", sid, {"kinds":[9],"authors":[ac.pubkey],"#h":[chan],"limit":10}]))
        ac.ws.settimeout(4)
        to_del = []
        deadline = time.time() + 4
        while time.time() < deadline:
            try:
                dr = json.loads(ac.ws.recv())
                if dr[0] == "EVENT": to_del.append(dr[2]["id"])
            except: break
        for eid in to_del:
            ac.send_event(5, "", [["e", eid]])
        if to_del:
            ac.send_event(9, "Deleted " + str(len(to_del)) + " messages.", [["e", evt.get("id","")], ["h", chan]])
        ac.close()
        log.info("deleted %d messages for %s", len(to_del), matched)
    except Exception as e:
        log.warning("del err: %s", str(e)[:60])


def run():
    delay = 1
    while True:
        try:
            sys.path.insert(0, str(ROOT))
            from buzz_client import BuzzClient

            client = BuzzClient(KEYS["the operator"]["secret_key"], relay_url=HOSTED)
            if not client.connect():
                raise Exception("auth failed")
            client.ws.settimeout(15)

            uuids = list(CHANS.values())
            for i, uuid in enumerate(uuids):
                client.ws.send(json.dumps(["REQ", str(i), {"kinds":[9], "#h":[uuid], "limit":0}]))

            client.ws.settimeout(5)
            drained = 0
            deadline = time.time() + 10
            while drained < len(uuids) and time.time() < deadline:
                try:
                    r = json.loads(client.ws.recv())
                    if r[0] == "EOSE": drained += 1
                except: break

            log.info("Bridge: %d ch, %d agents, %d EOSE", len(uuids), len(REV), drained)
            delay = 1

            last_beat = time.time()
            while True:
                client.ws.settimeout(25)
                try:
                    r = json.loads(client.ws.recv())
                    last_beat = time.time()
                except Exception:
                    try:
                        client.ws.send(json.dumps(["REQ", "ka", {"kinds":[9], "limit":0}]))
                    except Exception:
                        raise Exception("connection dead")
                    continue

                if r[0] != "EVENT": continue
                evt = r[2]; evt_id = evt.get("id",""); content = evt.get("content",""); pk = evt.get("pubkey","")

                if evt_id in SEEN: continue
                SEEN.add(evt_id)
                if len(SEEN) > 10000: SEEN.clear()
                if pk in AGENT_PUBKEYS: continue
                if not content: continue

                c = content.lower()
                matched = None
                # 1. Check @mention first (the operator explicit targeting)
                for alias, slug in REV.items():
                    if "@" + alias in c: matched = slug; break
                if not matched:
                    # 2. No @mention — check for channel representative
                    cn = CNAMES.get(next((t[1] for t in evt.get("tags",[]) if t[0]=="h"),""), "?")
                    chan_key = "#" + cn
                    rep = REPS.get(chan_key)
                    if rep and rep in KEYS:
                        matched = rep

                cn = CNAMES.get(next((t[1] for t in evt.get("tags",[]) if t[0]=="h"),""), "?")
                display = ALIASES[matched][0]
                log.info("@%s #%s: %s", display, cn, content[:60])

                akey = KEYS.get(matched, {}).get("secret_key")
                if not akey: continue

                query = re.sub(r"@\S+\s*", "", content).strip()
                if not query: continue

                tags = [["e", evt_id], ["p", pk]]
                for t in evt.get("tags", []):
                    if t[0] == "h": tags.append(t)

                # Delete command?
                if query.lower().startswith("delete"):
                    qt = threading.Thread(target=delete_agent_msgs, args=(matched, akey, evt), daemon=True)
                    qt.start()
                    continue

                # AI reply in background thread
                def do_reply(slug, display, akey, evt_id, pk, query, tags):
                    reply = omni_llm(display, query, slug) or "On it."
                    try:
                        ac = BuzzClient(akey, relay_url=HOSTED)
                        if not ac.connect():
                            log.warning("  reply auth failed for %s", display)
                            return
                        ac.ws.settimeout(10)
                        ac.send_event(9, reply, tags)
                        ac.close()
                        log.info("  replied: %s", reply[:40])
                    except Exception as e:
                        log.warning("  reply err: %s", str(e)[:60])

                t = threading.Thread(target=do_reply, args=(matched, display, akey, evt_id, pk, query, tags), daemon=True)
                t.start()

        except Exception as e:
            log.warning("X %s", str(e)[:80])
            time.sleep(delay)
            delay = min(delay * 2, 30)


if __name__ == "__main__":
    write_pid()
    log.info("=== Buzz Agent Bridge started (pid %s) ===", __import__("os").getpid())
    run()
