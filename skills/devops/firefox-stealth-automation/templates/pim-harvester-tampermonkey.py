#!/usr/bin/env python3
"""
PIM Conversation Harvester — Tampermonkey-based (no remote debugging).
Receives conversation data from GM_xmlhttpRequest and writes to PIM.

Usage:
  python pim-harvester-tampermonkey.py
  (starts HTTP server on port 8897)
"""
import json, logging, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("pim-harvester")

PIM_DIR = r"${MY_REPOS}\Documents\github\git-mcp\services\personal-intelligence-mcp"
PORT = 8897
batches = []

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        global batches
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length)
        try:
            msg = json.loads(body)
            source = msg.get('source', '?')
            convs = msg.get('conversations', [])
            logger.info("Received %d convos from %s", len(convs), source)
            for c in convs[:3]:
                msgs = c.get('messages', [])
                logger.info("  - %s (%d msgs)", c.get('title','?')[:40], len(msgs))
            if convs:
                batches.append(msg)
                self.server.needs_write = True
            self._ok({"ok": True, "count": len(convs)})
        except Exception as e:
            logger.error("Error: %s", e)
            self._ok({"error": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        n = sum(len(b.get('conversations',[])) for b in batches)
        msg = "PIM Harvester active\nBatches: %d\nConvos: %d\n" % (len(batches), n)
        self.wfile.write(msg.encode())

    def _ok(self, obj):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def log_message(self, *args): pass

class Svr(HTTPServer):
    needs_write = False
    allow_reuse_address = True

def write_to_pim():
    global batches
    if not batches:
        return
    sys.path.insert(0, PIM_DIR)
    import asyncio as aio
    from app.db import AsyncSessionLocal, init_db
    from app.core.pipeline import process_item

    loop = aio.new_event_loop()
    aio.set_event_loop(loop)

    async def _do():
        await init_db()
        total = 0
        async with AsyncSessionLocal() as session:
            for batch in batches:
                source = batch['source']
                for c in batch['conversations']:
                    msgs = c.get('messages', [])
                    full_text = ""
                    if msgs and len(msgs) > 0:
                        parts = []
                        for m in msgs:
                            role = m.get('role', 'unknown')
                            content = m.get('content', '')
                            if content:
                                parts.append("**" + role.title() + ":** " + content)
                        full_text = "\n\n---\n\n".join(parts)
                    try:
                        await process_item(
                            session=session,
                            source_type=source,
                            source_id=c['id'],
                            title=c.get('title', 'Untitled'),
                            source_url=c.get('url', ''),
                            full_text_override=full_text,
                        )
                        total += 1
                    except Exception as e:
                        logger.warning("Item %s: %s", c.get('id','?'), e)
        logger.info("Wrote %d items to PIM", total)

    loop.run_until_complete(_do())
    loop.close()
    batches.clear()

def main():
    s = Svr(('127.0.0.1', PORT), Handler)
    logger.info("PIM Harvester on http://127.0.0.1:%d", PORT)
    logger.info("Waiting for Tampermonkey data...")
    try:
        while True:
            s.handle_request()
            if s.needs_write:
                s.needs_write = False
                write_to_pim()
    except KeyboardInterrupt:
        if batches:
            write_to_pim()

if __name__ == "__main__":
    main()
