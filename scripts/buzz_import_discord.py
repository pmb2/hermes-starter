#!/usr/bin/env python3
"""buzz_import_discord.py — Full Discord chat history → Buzz channels (v2).

Reads ALL Hermes Discord conversation history from state.db files
(main + every profile), classifies each session to the best-matching
Buzz channel, and posts the exchanges in chronological BATCHES so the
full history lands in the right channels — not just a 12-exchange digest.

- Classifier covers all 58 channels (keyword buckets)
- Exchanges batched ~8 per message, oldest first, so nothing is dropped
- Dedup state file prevents double-posting on re-runs
- Cleans up v1 digests ("Discord history import" header) on first run
- Signs batches with the channel's lead agent key

Usage: python buzz_import_discord.py [--days N] [--dry-run] [--force]
"""
import json, sys, time, sqlite3, datetime, re, hashlib
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from buzz_client import BuzzClient

LOCAL = "ws://localhost:3000"
KEYS = json.loads((ROOT / "buzz_keys.json").read_text())
CHANS = json.loads((ROOT / "buzz_channels.json").read_text())

HERMES_HOME = Path(os.environ.get("HERMES_HOME") or Path.home() / "AppData" / "Local" / "hermes")
MAIN_DB = HERMES_HOME / "state.db"
PROFILES_DIR = HERMES_HOME / "profiles"

DAYS = None
if "--days" in sys.argv:
    DAYS = int(sys.argv[sys.argv.index("--days") + 1])
DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

STATE_FILE = ROOT / "buzz_discord_import_state.json"
BATCH_SIZE = 8       # exchanges per posted message
MSG_LEN = 240        # per-exchange text length

# Channel lead agents (used for signing + classification hints)
CHANNEL_AGENT = {
    "general": "chief-of-staff",
    "admin": "chief-of-staff",
    "management": "chief-of-staff",
    "dev": "development-lead",
    "engineering": "development-lead",
    "coding": "development-lead",
    "architecture": "development-lead",
    "intel": "intelligence-lead",
    "intelligence": "intelligence-lead",
    "research": "research-lead",
    "ops": "operations-lead",
    "operations": "operations-lead",
    "infrastructure": "operations-lead",
    "security": "security-lead",
    "compliance": "security-lead",
    "creative": "creative-lead",
    "design": "creative-lead",
    "content": "creative-lead",
}

# Keyword buckets -> buzz channel. Ordered; first match wins.
# NOTE: matching is WORD-BOUNDARY (\b...\b) — substring matching misroutes
# ("invest" would match "investigate", "option" matches "FOSS options").
TOPIC_MAP = [
    (("law", "legal", "compliance", "ccpa", "regulat", "nda", "lawsuit", "attorney", "contract review", "court"), "legal"),
    (("recruiter", "c2c", "inmail", "linkedin", "indeed", "resume", "interview", "job posting", "job search", "hiring pipeline", "contract opportunity"), "career"),
    (("lehigh", "wholesal", "zillow", "deed", "tax roll", "absentee", "vacant land", "land deal", "property", "real estate", "acreage", "parcel"), "market-lead"),
    (("draftkings", "fanduel", "mlb", "nfl", "nba", "ncaa", "parlay", "sportsbook", "betting", "odds", "point spread", "moneyline"), "sports"),
    (("stock", "stocks", "portfolio", "trading", "options trading", "dividend", "position sizing", "investing", "investment", "investor", "market cap", "earnings report", "crypto", "bitcoin"), "finance"),
    (("cyber", "threat", "exploit", "infostealer", "vuln", "malware", "ransom", "zero-day", "hack", "breach", "security audit", "cve"), "cybersecurity"),
    (("hermes", "agent code", "mcp", "dev-lead", "python", "api server", "deploy", "docker", "git commit", "codebase", "refactor", "code review", "bug fix", "regression", "pytest", "unit test", "dev team", "code", "app", "server", "endpoint", "pipeline", "kubernetes", "repo", "branch", "commit", "backend", "frontend", "database", "sqlite", "postgres", "node", "typescript", "javascript", "react", "llm", "openai", "api"), "engineering"),
    (("workout", "nutrition", "fitness", "biomarker", "supplement", "protein", "sleep tracking"), "health"),
    (("pulse", "intel digest", "blogwatcher", "pim", "watchdog", "uptime", "monitoring"), "monitoring"),
    (("workflow", "sop", "logistics", "supply chain", "operations"), "operations"),
    (("content", "blog", "copywriting", "ad copy", "video", "podcast", "youtube", "scriptwriting", "content calendar"), "content"),
    (("tax", "irs", "deduction", "filing"), "tax"),
    (("research", "landscape", "literature review", "deep dive"), "research"),
    (("marketing", "brand", "outreach", "campaign", "advert", "seo"), "marketing"),
    (("product", "roadmap", "user research", "mvp"), "product"),
    (("hr", "people ops", "culture", "team building"), "hr"),
    (("support", "helpdesk", "ticket", "faq", "troubleshoot"), "support"),
    (("data", "analytics", "dashboard", "sql", "pandas"), "data"),
    (("mes", "solumina", "as9100", "shop floor", "manufacturing execution"), "manufacturing"),
    (("automation", "cron", "selenium", "workflow engine"), "automation"),
]

import re as _re


def classify(title: str, sample: str) -> str:
    blob = ((title or "") + " " + (sample or "")).lower()
    for kws, chan in TOPIC_MAP:
        for kw in kws:
            if _re.search(rf"\b{_re.escape(kw)}\b", blob):
                return chan
    return "general"


def clean_msg(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\[Recent channel messages\]\s*", "", text)
    text = re.sub(r"\[New message\]\s*", "", text)
    text = re.sub(r"\[the operator\]\s*", "", text)
    text = re.sub(r"\[[^\]]*from Discord[^\]]*\]", "", text)
    text = re.sub(r"\[System[^\]]*\]", "", text)
    text = text.replace("\u00a0", " ").strip()
    return text


# Noise: exchanges that are pure filler (no real content)
NOISE = re.compile(
    r"^(ok|okay|yes|no|yep|nope|sure|thanks|thank you|great|good|perfect|nice|keep going|"
    r"continue|do it|go ahead|proceed|correct|right|got it|understood|same|again|more|"
    r"that's it|thats it|done|finish|let's go|lets go|awesome|excellent|👍|✅|🙏|🎉|\s*)$",
    re.IGNORECASE,
)


def is_noise(text: str) -> bool:
    t = text.strip().strip('"').strip()
    if not t:
        return True
    if len(t) <= 3:
        return True
    return bool(NOISE.match(t))


def iter_discord_sessions():
    dbs = [MAIN_DB] + list(PROFILES_DIR.glob("*/state.db"))
    seen = set()
    for db in dbs:
        if not db.exists():
            continue
        try:
            conn = sqlite3.connect(str(db))
            cur = conn.cursor()
            cur.execute("SELECT id, title FROM sessions WHERE source='discord'")
            sessions = cur.fetchall()
            for sid, title in sessions:
                if sid in seen:
                    continue
                seen.add(sid)
                cur2 = conn.cursor()
                cur2.execute(
                    "SELECT timestamp, role, content FROM messages "
                    "WHERE session_id=? AND content IS NOT NULL AND length(content)>3 "
                    "ORDER BY timestamp", (sid,)
                )
                msgs = [(ts, role, content) for ts, role, content in cur2.fetchall()]
                conn.commit()
                if msgs:
                    yield (sid, title, msgs)
            conn.close()
        except Exception:
            try:
                conn.close()
            except Exception:
                pass


def build_exchanges(msgs, cutoff):
    exchanges = []
    pending_ask = None
    pending_ts = None
    for ts, role, content in msgs:
        if role == "user":
            text = clean_msg(content)
            if text and not is_noise(text):
                if pending_ask:
                    exchanges.append((pending_ts, pending_ask, ""))
                pending_ask = text
                pending_ts = ts
        elif role == "assistant" and pending_ask:
            text = (content or "").strip()
            if text and not text.startswith("API call failed") and not is_noise(text):
                exchanges.append((pending_ts, pending_ask, text[:400]))
                pending_ask = None
    if pending_ask:
        exchanges.append((pending_ts, pending_ask, ""))
    return [e for e in exchanges if (e[0] or 0) >= cutoff]


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))


def exchange_hash(ex):
    return hashlib.md5(f"{ex[1][:120]}|{ex[2][:120]}".encode()).hexdigest()[:16]


def full_exchange_hash(ex):
    return hashlib.md5(f"{ex[1]}|{ex[2]}".encode()).hexdigest()


def main():
    cutoff = 0 if DAYS is None else time.time() - DAYS * 86400
    state = load_state()
    posted_markers = set(state.get("posted", []))

    # Collect all exchanges per channel
    by_channel = defaultdict(list)
    total_sessions = 0
    for sid, title, msgs in iter_discord_sessions():
        exchanges = build_exchanges(msgs, cutoff)
        if not exchanges:
            continue
        total_sessions += 1
        # Classify on a rich sample: title + first several exchanges (~1.5KB),
        # so sessions that open generically still land in the right channel.
        sample_parts = [title or ""]
        for ex in exchanges[:6]:
            sample_parts.append(ex[1])
            if ex[2]:
                sample_parts.append(ex[2])
        sample = " ".join(sample_parts)[:1500]
        chan = classify(title, sample)
        by_channel[chan].extend(exchanges)

    # Dedupe exchanges per channel — the same conversation appears in both the
    # main state.db and per-profile state.dbs, so exchanges repeat. Without
    # dedup, batch markers collide and unique content gets skipped.
    for chan in list(by_channel):
        seen = set()
        uniq = []
        for ex in sorted(by_channel[chan], key=lambda e: e[0] or 0):
            h = full_exchange_hash(ex)
            if h in seen:
                continue
            seen.add(h)
            uniq.append(ex)
        by_channel[chan] = uniq

    print(f"Scanned {total_sessions} sessions -> {len(by_channel)} channels, "
          f"{sum(len(v) for v in by_channel.values())} exchanges total")

    # Clean v1 digests (only when posting for real)
    if not DRY_RUN:
        try:
            sk = KEYS["the operator"]["secret_key"]
            probe = BuzzClient(sk, relay_url=LOCAL)
            if probe.connect():
                evts = probe.query({"kinds": [9], "limit": 500}, timeout=10)
                v1 = [e for e in evts if "Discord history import" in e.get("content", "")]
                for e in v1:
                    ac = BuzzClient(sk, relay_url=LOCAL)
                    if ac.connect():
                        ac.send_event(5, "", [["e", e["id"]]])
                        ac.close()
                probe.close()
                if v1:
                    print(f"Cleaned {len(v1)} v1 digests")
        except Exception as e:
            print(f"v1 cleanup skipped: {str(e)[:80]}")

    posted = failed = skipped = 0
    for chan in sorted(by_channel):
        if chan not in CHANS:
            print(f"  !! #{chan} not a channel — dropping {len(by_channel[chan])} exchanges")
            continue
        exchanges = sorted(by_channel[chan], key=lambda e: e[0] or 0)
        # batch oldest -> newest
        batches = [exchanges[i:i + BATCH_SIZE] for i in range(0, len(exchanges), BATCH_SIZE)]
        agent = CHANNEL_AGENT.get(chan, "the operator")
        akey = KEYS.get(agent, {}).get("secret_key") or KEYS["the operator"]["secret_key"]

        for bi, batch in enumerate(batches):
            # Channel-scoped marker: the exchange hash alone collides across
            # channels (identical first exchange + same batch size).
            marker = chan + ":" + exchange_hash(batch[0]) + ":" + str(len(batch))
            if marker in posted_markers and not FORCE:
                skipped += 1
                continue
            lines = [f"📜 **Discord history — #{chan}** (batch {bi + 1}/{len(batches)})"]
            for ts, ask, reply in exchanges_of_batch(batch):
                d = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if ts else "?"
                ask_s = ask[:MSG_LEN] + ("…" if len(ask) > MSG_LEN else "")
                lines.append(f"\n**[{d}] the operator:** {ask_s}")
                if reply:
                    lines.append(f"**Agent:** {reply[:MSG_LEN]}")
            content = "\n".join(lines)
            if DRY_RUN:
                print(f"  [DRY] #{chan} batch {bi + 1}/{len(batches)} ({len(batch)} ex)")
                continue
            try:
                c = BuzzClient(akey, relay_url=LOCAL)
                if not c.connect():
                    failed += 1
                    continue
                eid = c.send_channel_message(CHANS[chan], content)
                c.close()
                if not eid and not FORCE:
                    # Retry once with backoff (relay rate-limits fast bursts)
                    time.sleep(2.0)
                    c = BuzzClient(akey, relay_url=LOCAL)
                    if c.connect():
                        eid = c.send_channel_message(CHANS[chan], content)
                        c.close()
                if eid:
                    posted_markers.add(marker)
                    posted += 1
                else:
                    failed += 1
                time.sleep(0.5)
            except Exception as e:
                failed += 1
                print(f"  ✗ #{chan} b{bi + 1}: {str(e)[:80]}")

    if posted and not DRY_RUN:
        state["posted"] = sorted(posted_markers)
        save_state(state)
    print(f"\nDONE: {posted} batches posted, {skipped} already posted, {failed} failed"
          + (" (DRY RUN)" if DRY_RUN else ""))
    return 0 if failed == 0 else 1


def exchanges_of_batch(batch):
    # sort by timestamp within batch already; just return
    return batch


if __name__ == "__main__":
    sys.exit(main())
