#!/usr/bin/env python3
"""
PIM Harvester — WebSocket receiver for CSP-restricted sites (Grok, ChatGPT).
Works where HTTP fetch is blocked by Content-Security-Policy.

Usage:
  1. python pim-harvester.py
  2. Open chatgpt.com or grok.com in your normal Firefox
  3. F12 -> Console -> paste the one-liner that prints
  4. Data flows via WebSocket to PIM

CSP bypass: Sites that block connect-src to http://127.0.0.1 often ALLOW
ws://127.0.0.1:* (as Grok's CSP does). WebSocket avoids the CSP violation.
"""
import asyncio, json, logging, os, sys
import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pim-harvester")

PIM_DIR = r"${MY_REPOS}\Documents\github\git-mcp\services\personal-intelligence-mcp"
WS_PORT = 8898
received = []


async def handler(ws):
    global received
    async for raw in ws:
        try:
            msg = json.loads(raw)
            source = msg.get("source", "?")
            convs = msg.get("conversations", [])
            logger.info("Received %d convos from %s", len(convs), source)
            if convs:
                received.append(msg)
                await ws.send(json.dumps({"ok": True, "count": len(convs)}))
                await process_to_pim()
            else:
                await ws.send(json.dumps({"ok": True, "count": 0, "note": "no convos found in sidebar DOM"}))
        except Exception as e:
            logger.error("Handler error: %s", e)
            await ws.send(json.dumps({"error": str(e)}))


async def process_to_pim():
    global received
    if not received:
        return
    sys.path.insert(0, PIM_DIR)
    from app.db import AsyncSessionLocal, init_db
    from app.core.pipeline import process_item
    await init_db()
    total = 0
    async with AsyncSessionLocal() as session:
        for batch in received:
            source = batch["source"]
            for c in batch["conversations"]:
                try:
                    await process_item(
                        session=session, source_type=source,
                        source_id=c["id"], title=c.get("title", "Untitled"),
                        source_url=c.get("url", ""),
                    )
                    total += 1
                except Exception as e:
                    logger.warning("Item %s: %s", c.get("id", "?"), e)
    logger.info("Stored %d items in PIM", total)
    received = []


async def main():
    logger.info("=" * 50)
    logger.info("PIM Harvester (WebSocket) — CSP-safe")
    logger.info("Port: %d", WS_PORT)
    logger.info("=" * 50)
    logger.info("")
    logger.info("CHATGPT console paste (open chatgpt.com, F12 -> Console):")
    logger.info("")
    logger.info(
        'var ws=new WebSocket("ws://127.0.0.1:%d");'
        "ws.onopen=function(){"
        "var c=[];"
        "document.querySelectorAll('a[href*=\"/c/\"]').forEach(function(a){"
        "var m=a.href.match(/\\/c\\/([a-f0-9-]+)/);"
        "if(m&&!c.find(function(x){return x.id===m[1]}))"
        "c.push({id:m[1],title:(a.textContent||'').trim()||'Untitled',url:a.href})"
        "});"
        "ws.send(JSON.stringify({source:'chatgpt',conversations:c}));"
        "console.log('Sent '+c.length+' convos');"
        "ws.onmessage=function(e){console.log('PIM:',e.data)}"
        "};" % WS_PORT
    )
    logger.info("")
    logger.info("GROK console paste (open grok.com, F12 -> Console):")
    logger.info("")
    logger.info(
        'var ws=new WebSocket("ws://127.0.0.1:%d");'
        "ws.onopen=function(){"
        "var c=[];"
        "document.querySelectorAll('a[href*=\"/chat/\"]').forEach(function(a){"
        "var m=a.href.match(/\\/chat\\/([a-f0-9-]+)/);"
        "if(m&&!c.find(function(x){return x.id===m[1]}))"
        "c.push({id:m[1],title:(a.textContent||'').trim()||'Untitled',url:a.href})"
        "});"
        "ws.send(JSON.stringify({source:'grok',conversations:c}));"
        "console.log('Sent '+c.length+' convos');"
        "ws.onmessage=function(e){console.log('PIM:',e.data)}"
        "};" % WS_PORT
    )
    logger.info("")
    logger.info("Waiting for data...")
    async with websockets.serve(handler, "127.0.0.1", WS_PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
