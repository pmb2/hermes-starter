#!/usr/bin/env python3
"""
PIM Ingestion Runner Template — Two-phase stealth + console-paste fallback.

Phase 1: Start Firefox + apply 22 StealthEngine measures via ultimate-firefox-mcp
Phase 2: PIM connector connects (preload scripts persist across sessions)
Fallback: For Cloudflare-protected sites, use console-paste approach (see Layer 6)

Usage:
  # Stealth mode (non-Cloudflare sites)
  python pim-ingest-runner.py

  # Harvester mode (Cloudflare sites — paste console scripts manually)
  python pim-harvester.py
"""

import asyncio
import json
import logging
import os
import subprocess
import socket
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pim-ingest")

PIM_DIR = os.path.expandvars(r"${MY_REPOS}/git-mcp/services/personal-intelligence-mcp")  # set MY_REPOS env
FF_ULITMATE_DIR = r"C:\\Users\\<you>\\ultimate-firefox-mcp"
# Use the PATCHED Firefox binary (xul.dll patched, navigator.webdriver=undefined)
FIREFOX_EXE = r"C:\\Users\\<you>\\firefox-portable\\firefox.exe"
PROFILE_PATH = os.path.expandvars(r"%APPDATA%\\Mozilla\\Firefox\\Profiles\\<profile-id>.default-release-1")
BIDI_PORT = int(os.environ.get("PIM_BIDI_PORT", "9239"))

firefox_proc = None


def port_open(p: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=1):
            return True
    except (OSError, socket.timeout):
        return False


async def start_firefox():
    global firefox_proc
    if port_open(BIDI_PORT):
        raise RuntimeError(f"Port {BIDI_PORT} already in use. Use a fresh port or wait for TIME_WAIT.")

    logger.info("Starting Firefox (profile: <profile-id>, port: %d)", BIDI_PORT)
    firefox_proc = subprocess.Popen(
        [FIREFOX_EXE, "--remote-debugging-port", str(BIDI_PORT), "--no-remote", "--profile", PROFILE_PATH],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for i in range(60):
        if port_open(BIDI_PORT):
            break
        await asyncio.sleep(1)
    else:
        raise RuntimeError("Firefox did not start")

    logger.info("Firefox ready (PID %d)", firefox_proc.pid)
    await asyncio.sleep(5)  # session restore


def stop_firefox():
    global firefox_proc
    if firefox_proc:
        firefox_proc.terminate()
        try:
            firefox_proc.wait(timeout=15)
        except Exception:
            firefox_proc.kill()
        firefox_proc = None


async def apply_stealth():
    """Phase 1: Apply 22 StealthEngine measures then disconnect session."""
    sys.path.insert(0, FF_ULITMATE_DIR)
    from ultimate_firefox_mcp.stealth import StealthEngine
    from ultimate_firefox_mcp.browser import FirefoxBrowser as BiDiBrowser

    logger.info("Applying stealth via ultimate-firefox-mcp StealthEngine...")
    browser = BiDiBrowser(host="127.0.0.1", port=BIDI_PORT, timeout=30)
    await browser.connect()

    engine = StealthEngine()
    script_ids = await engine.apply(browser)
    logger.info("Applied %d/22 stealth measures", len(script_ids))

    # Disconnect — preload scripts persist at Firefox runtime level
    await browser.disconnect()
    logger.info("Stealth applied. Preload scripts remain active.")
    return len(script_ids)


async def run_ingestion(source: str, **kwargs):
    """Phase 2: Run PIM connector (new BiDi session, preload scripts active)."""
    os.environ["PIM_BIDI_PORT"] = str(BIDI_PORT)
    sys.path.insert(0, PIM_DIR)

    if source == "chatgpt":
        from app.connectors.chatgpt import ChatGPTConnector
        connector = ChatGPTConnector()
    elif source == "grok":
        from app.connectors.grok import GrokConnector
        connector = GrokConnector()
    else:
        raise ValueError(f"Unknown source: {source}")

    from app.db import AsyncSessionLocal, init_db
    await init_db()
    async with AsyncSessionLocal() as session:
        result = await connector.ingest(session, kwargs)
    return result


async def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--assume-running", action="store_true",
                        help="Skip Firefox start/stop — assume it's already on PIM_BIDI_PORT")
    parser.add_argument("--source", choices=["chatgpt", "grok", "both"], default="both")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info("PIM Ingestion (Two-Phase Stealth)")
    logger.info("=" * 50)

    if not args.assume_running:
        try:
            await start_firefox()
            await apply_stealth()
        except Exception as e:
            logger.error("Setup failed: %s", e)
            sys.exit(1)

    results = {}
    sources = ["chatgpt", "grok"] if args.source == "both" else [args.source]
    try:
        for source in sources:
            logger.info("")
            logger.info("--- %s ---", source.upper())
            result = await run_ingestion(source, max_conversations=50, scroll_pause=2000)
            results[source] = result
            logger.info("%s: %s", source, json.dumps(result, indent=2))
    except Exception as e:
        logger.error("Ingestion error: %s", e)
        results["error"] = str(e)
    finally:
        if not args.assume_running:
            stop_firefox()

    print(json.dumps({"results": results, "status": "done"}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
