#!/usr/bin/env python3
"""
verify-stealth.py — End-to-end Firefox BiDi stealth verification.

Connects to a running Firefox instance on a given port, applies StealthEngine,
creates a tab, navigates, and verifies anti-detection measures are active.

Usage:
    python verify-stealth.py                         # port 9239 (default)
    python verify-stealth.py --port 9239 --visible   # non-headless Firefox

Exit code: 0 = all checks pass, 1 = failures
"""

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("verify-stealth")


def _port_open(port: int) -> bool:
    import socket
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=3):
            return True
    except (OSError, socket.timeout):
        return False


def ensure_firefox(port: int = 9239, headless: bool = True):
    """Launch portable Firefox with automation profile if not already running."""
    if _port_open(port):
        log.info(f"Firefox already running on port {port}")
        return port

    binary = r"${USER_HOME}\firefox-portable\firefox.exe"
    profile = r"${USER_HOME}\AppData\Local\hermes\firefox-profile"

    if not os.path.exists(binary):
        log.error(f"Portable Firefox not found: {binary}")
        sys.exit(1)

    cmd = [binary, "--remote-debugging-port", str(port), "--no-remote", "--profile", profile]
    if headless:
        cmd.insert(1, "--headless")

    log.info(f"Launching Firefox on port {port} (headless={headless})")
    log.info(f"  Profile: {profile}")
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if _port_open(port):
            log.info(f"Firefox ready on port {port}")
            return port
        time.sleep(1)

    log.error("Firefox did not start within 30s")
    sys.exit(1)


async def verify_stealth(port: int = 9239):
    """Connect, apply stealth, create tab, verify measures."""
    import websockets
    from ultimate_firefox_mcp.stealth import StealthEngine

    # Phase 1: BiDi WebSocket connection
    log.info("\n=== Phase 1: BiDi Connection ===")
    ws = await websockets.connect(
        f"ws://127.0.0.1:{port}/session",
        max_size=10 * 1024 * 1024,
        close_timeout=5,
    )
    await ws.send(json.dumps({
        "id": 1, "method": "session.new",
        "params": {"capabilities": {"alwaysMatch": {"webSocketUrl": True}}},
    }))
    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    sid = resp.get("result", {}).get("sessionId", "")
    assert sid, f"Session creation failed: {resp}"
    log.info(f"  ✅ BiDi session: {sid[:20]}...")

    # Phase 2: StealthEngine
    log.info("\n=== Phase 2: StealthEngine ===")
    engine = StealthEngine()
    combined = await engine.get_preload_script()
    assert combined, "StealthEngine returned empty script"
    log.info(f"  ✅ StealthEngine loaded: {len(engine.all_measure_names)} measures")
    log.info(f"     Measures: {', '.join(engine.all_measure_names)}")
    log.info(f"     Preload script: {len(combined):,} chars")

    # Register preload script
    await ws.send(json.dumps({
        "id": 2, "method": "script.addPreloadScript",
        "params": {"functionDeclaration": combined},
    }))
    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    assert "result" in resp, f"Preload registration failed: {resp}"
    log.info("  ✅ Preload script registered (all future pages get stealth)")

    # Phase 3: Create tab + navigate
    log.info("\n=== Phase 3: Tab Creation ===")
    await ws.send(json.dumps({
        "id": 3, "method": "browsingContext.create",
        "params": {"type": "tab"},
    }))
    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
    ctx = resp.get("result", {}).get("context", "")
    assert ctx, f"Tab creation failed: {resp}"
    log.info(f"  ✅ Tab created: {ctx[:20]}...")

    # Navigate to about:blank
    await ws.send(json.dumps({
        "id": 4, "method": "browsingContext.navigate",
        "params": {"context": ctx, "url": "about:blank", "wait": "complete"},
    }))
    resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
    log.info(f"  ✅ Navigation complete")

    # Phase 4: Verify stealth measures
    log.info("\n=== Phase 4: Stealth Verification ===")
    checks = [
        ("navigator.webdriver",
         "JSON.stringify(Object.getOwnPropertyDescriptor(navigator, 'webdriver'))",
         lambda v: v and v.get("value") is None),
        ("navigator.plugins length",
         "navigator.plugins.length",
         lambda v: isinstance(v, (int, float)) and v > 0),
        ("navigator.languages",
         "JSON.stringify(navigator.languages)",
         lambda v: isinstance(v, str) and "en-US" in v),
        ("navigator.hardwareConcurrency",
         "navigator.hardwareConcurrency",
         lambda v: isinstance(v, (int, float)) and v > 1),
    ]

    passed = 0
    failed = 0
    for name, expr, validator in checks:
        cid = 10 + checks.index((name, expr, validator))
        await ws.send(json.dumps({
            "id": cid, "method": "script.evaluate",
            "params": {
                "expression": expr,
                "target": {"context": ctx},
                "awaitPromise": True,
                "resultOwnership": "root",
            },
        }))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=10))
        eval_result = resp.get("result", {}).get("result", {})
        rtype = eval_result.get("type")
        rval = eval_result.get("value")

        try:
            if rtype == "string":
                parsed = json.loads(rval)
                ok = validator(parsed)
            elif rtype == "number":
                ok = validator(rval)
            elif rtype is None:
                ok = validator(None)
            else:
                ok = validator(rval)
        except Exception:
            ok = False

        if ok:
            log.info(f"  ✅ {name}")
            passed += 1
        else:
            log.warning(f"  ❌ {name} (value={rval})")
            failed += 1

    # Phase 5: Cleanup
    log.info("\n=== Phase 5: Cleanup ===")
    await ws.send(json.dumps({"id": 99, "method": "session.end"}))
    await ws.close()
    log.info("  ✅ Session ended, WebSocket closed")

    # Results
    log.info(f"\n{'='*50}")
    log.info(f"RESULTS: {passed} passed, {failed} failed out of {len(checks)} checks")
    log.info(f"{'='*50}")
    return failed == 0


async def main():
    parser = argparse.ArgumentParser(description="Verify Firefox BiDi stealth")
    parser.add_argument("--port", type=int, default=9239, help="Firefox debug port")
    parser.add_argument("--visible", action="store_true", help="Non-headless Firefox")
    args = parser.parse_args()

    # Ensure Firefox is running
    ensure_firefox(port=args.port, headless=not args.visible)
    await asyncio.sleep(2)

    success = await verify_stealth(port=args.port)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
