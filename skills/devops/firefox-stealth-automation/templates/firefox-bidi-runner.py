#!/usr/bin/env python3
"""
Firefox BiDi Runner — Start, connect, navigate, extract, cleanup.
For use with non-Cloudflare sites where stealth BiDi works.
"""

import asyncio
import json
import logging
import socket
import subprocess
import sys
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bidi-runner")

FIREFOX_EXE = r"C:\Program Files\Mozilla Firefox\firefox.exe"
HEADLESS = os.environ.get("FIREFOX_HEADLESS", "1") == "1"  # default headless for cron
PROFILE_NAME = "default-release-1"  # the operator's real profile (<profile-id>)
PIM_DIR = r"${MY_REPOS}\Documents\github\git-mcp\services\personal-intelligence-mcp"
BIDI_PORT = int(os.environ.get("PIM_BIDI_PORT", "9223"))

sys.path.insert(0, PIM_DIR)
os.environ["PIM_BIDI_PORT"] = str(BIDI_PORT)


def port_open(p: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", p), timeout=1):
            return True
    except:
        return False


async def run():
    from app.connectors._firefox_bidi import FirefoxBiDiClient

    # Kill any existing Firefox (ensures fresh headless instance, cleans orphaned sessions)
    subprocess.run(["taskkill", "/F", "/IM", "firefox.exe"], capture_output=True)
    await asyncio.sleep(2)

    # Build launch command: headless by default, visible if FIREFOX_HEADLESS=0
    cmd = [FIREFOX_EXE, "--remote-debugging-port", str(BIDI_PORT), "--no-remote"]
    if HEADLESS:
        cmd.insert(1, "--headless")
    cmd.extend(["-P", PROFILE_NAME])

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )

    # Wait for port with timeout
    for i in range(60):
        if port_open(BIDI_PORT):
            break
        await asyncio.sleep(1)

    await asyncio.sleep(3)

    # Connect BiDi (stealth applied auto in _apply_stealth)
    ff = FirefoxBiDiClient()
    await ff.connect()
    logger.info("Connected. New tab...")

    await ff.new_tab("https://example.com")
    await asyncio.sleep(3)
    title = await ff.evaluate("document.title")
    logger.info("Page title: %s", title)

    await ff.close()
    proc.terminate()
    proc.wait()
    logger.info("Done")


asyncio.run(run())
