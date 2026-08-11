#!/usr/bin/env python3
"""
Firefox BiDi Page Extractor — reusable template for scraping content from pages
via Firefox BiDi WebSocket protocol.

Key patterns demonstrated:
  1. session.new({"capabilities": {}}) — NOT empty params
  2. script.callFunction result parsing: resp["result"]["result"]["value"]
  3. Page-text fallback: when DOM selectors fail, extract innerText and parse
  4. Always session.end before ws.close to free session slots (max 5)

Usage:
  python bidi-page-extractor.py

Requirements:
  pip install websockets
  Firefox running with --remote-debugging-port 9239
"""
import asyncio
import json
import re
import websockets

BIDI_PORT = 9239
BIDI_URL = f"ws://127.0.0.1:{BIDI_PORT}/session"

class BiDiClient:
    """Minimal Firefox BiDi client for page extraction."""

    def __init__(self):
        self.ws = None
        self.ctx = None
        self._mid = 0

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, *args):
        await self.close()

    async def connect(self):
        self.ws = await websockets.connect(BIDI_URL)
        # session.new REQUIRES {"capabilities": {}} — empty {} fails
        await self._send("session.new", {"capabilities": {}})
        resp = await self._send("browsingContext.create", {"type": "tab"})
        self.ctx = resp["result"]["context"]
        print(f"[OK] Session ready | tab={self.ctx[:16]}...", flush=True)

    async def navigate(self, url, wait_sec=4):
        print(f"  -> {url[:80]}", flush=True)
        await self._send("browsingContext.navigate", {
            "context": self.ctx, "url": url, "wait": "complete"
        })
        await asyncio.sleep(wait_sec)

    async def eval_js(self, js_expression):
        """Evaluate JS and return the value. Handles string/number/bool."""
        resp = await self._send("script.callFunction", {
            "target": {"context": self.ctx},
            "functionDeclaration": f"() => {{ return {js_expression}; }}",
            "awaitPromise": True,
            "resultOwnership": "root"
        })
        # Result is at resp["result"]["result"]["value"]
        inner = resp.get("result", {}).get("result", {})
        t = inner.get("type")
        if t == "string":
            return inner.get("value", "")
        if t == "number":
            return str(inner.get("value", ""))
        if t == "boolean":
            return str(inner.get("value", ""))
        # null/undefined/object — return raw snippet
        return f"RAW<{t}>: {json.dumps(inner)[:200]}"

    async def get_page_text(self, max_chars=8000):
        """Get visible page text via document.body.innerText."""
        return await self.eval_js(
            f"(document.body?.innerText || '').substring(0, {max_chars})"
        )

    async def get_title(self):
        return await self.eval_js("document.title")

    async def close(self):
        try:
            await self._send("session.end", {})
            await self.ws.close()
        except Exception:
            pass

    async def _send(self, method, params):
        self._mid += 1
        msg = {"id": self._mid, "method": method, "params": params}
        await self.ws.send(json.dumps(msg))
        while True:
            raw = await self.ws.recv()
            resp = json.loads(raw)
            if resp.get("id") == self._mid:
                if "error" in resp:
                    raise RuntimeError(
                        f"BiDi error [{resp['error']}]: {resp.get('message','')}"
                    )
                return resp


# ══════════════════════════════════════════════════════════════
# Example: Page-text extraction with fallback parsing
# This pattern works when JS DOM selectors fail (React SPAs,
# dynamic class names, obfuscated markup). Instead of fragile
# querySelector chains, dump innerText and parse heuristically.
# ══════════════════════════════════════════════════════════════

async def extract_job_listings_example():
    """
    Example: scrape Indeed for AI jobs using page-text fallback.
    
    When document.querySelector('.jobTitle') returns nothing because
    Indeed changes their CSS class names, fall back to parsing
    document.body.innerText with line-by-line heuristics.
    """
    async with BiDiClient() as bidi:
        await bidi.navigate("https://www.indeed.com/q-remote-ai-jobs.html")
        text = await bidi.get_page_text()

        # Heuristic line-by-line parsing
        jobs = []
        lines = text.split('\n')
        noise_words = ["Skip to", "Home", "Company reviews", "Employers",
                       "Start of main", "Keyword", "Search", "Pay", "Remote",
                       "Job Type", "Date posted", "Sort by"]

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or len(line) < 5 or any(line.startswith(n) for n in noise_words):
                i += 1
                continue

            # Check if the next lines contain company/salary info
            company = ""
            salary = ""
            j = i + 1
            while j < min(i + 6, len(lines)):
                l = lines[j].strip()
                if l.startswith('$') and '(' not in l:
                    salary = l
                elif ("DataAnnotation" in l or "Loom Security" in l
                      or "Omada Health" in l or "Remote in" in l):
                    if "Remote in" in l:
                        pass  # location
                    else:
                        company = l
                j += 1

            if company or salary:
                jobs.append({"title": line, "company": company, "salary": salary})
                i = j
                continue
            i += 1

        print(f"\n[Extracted] {len(jobs)} job listings via text fallback:")
        for j in jobs[:5]:
            print(f"  {j['title']} @ {j['company']}  {j['salary']}")


if __name__ == "__main__":
    asyncio.run(extract_job_listings_example())
