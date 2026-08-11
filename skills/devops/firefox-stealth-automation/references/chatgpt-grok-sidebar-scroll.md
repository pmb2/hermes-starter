# ChatGPT / Grok Sidebar Scroll Pattern

Both ChatGPT and Grok use lazy-loading sidebars that only render ~10-15 conversation links visible at a time. Scrolling the sidebar container triggers additional items to load. This document describes the async JS scroll pattern used by the PIM connectors to discover ALL conversations.

## The Pattern

Run the entire scroll loop **inside the page** via a single `evaluate()` call. This avoids BiDi round-trip latency on each scroll step.

```javascript
(async () => {
    const seen = new Set();
    const conversations = [];

    const extractLinks = (container) => {
        const links = container.querySelectorAll('a[href*="/c/"]');
        links.forEach(link => {
            const href = link.getAttribute('href') || '';
            const m = href.match(/\/c\/([a-f0-9-]+)/);
            if (m && !seen.has(m[1])) {
                seen.add(m[1]);
                const title = (link.textContent || '').trim() || 'Untitled';
                conversations.push({
                    id: m[1],
                    title: title.substring(0, 200),
                    url: href.startsWith('http') ? href : window.location.origin + href,
                });
            }
        });
    };

    // Step 1: Find the sidebar container
    const sidebars = document.querySelectorAll(
        'nav, [class*="sidebar"], [class*="history"], aside, [class*="chat-list"]'
    );
    let sidebar = null;
    for (const s of sidebars) {
        if (s.querySelector('a[href*="/c/"]')) {
            sidebar = s;
            break;
        }
    }
    if (!sidebar) sidebar = document.body;

    // Step 2: Find the scrollable child
    let scrollEl = sidebar;
    for (const child of sidebar.querySelectorAll('div, section, ul, ol')) {
        try {
            const style = window.getComputedStyle(child);
            if ((style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                child.scrollHeight > child.clientHeight) {
                scrollEl = child;
                break;
            }
        } catch(e) {}
    }

    // Step 3: Scroll loop
    extractLinks(sidebar);
    let stale = 0;
    const MAX_STALE = 3;    // stop after 3 empty scrolls
    const MAX_SCROLLS = 100; // hard cap

    for (let i = 0; i < MAX_SCROLLS && stale < MAX_STALE; i++) {
        const before = conversations.length;
        scrollEl.scrollTop = scrollEl.scrollHeight;
        await new Promise(r => setTimeout(r, 2500));
        extractLinks(sidebar);
        if (conversations.length === before) {
            stale++;
        } else {
            stale = 0;
        }
    }

    return JSON.stringify(conversations);
})();
```

## Key Details

- **Dedup by UUID:** The `seen` Set prevents duplicate conversation entries across scroll iterations.
- **URL construction:** Uses the `href` from the DOM link. If relative, prepends `window.location.origin`.
- **Title:** `link.textContent` works for both ChatGPT and Grok. Falls back to `'Untitled'`.
- **Scroll element detection:** Not all sidebar containers are scrollable. The code tries `getComputedStyle().overflowY` to find the actual scrollable child. If none found, scrolls the sidebar itself.
- **Stop condition:** 3 consecutive scrolls with zero new items → sidebar is fully loaded.

## Platform Differences

| Aspect | ChatGPT | Grok |
|--------|---------|------|
| Sidebar tag | `<nav>` (React sidebar) | `[class*="sidebar"]` or `[class*="history"]` |
| URL pattern | `https://chatgpt.com/c/{uuid}` | `https://grok.com/c/{uuid}` |
| Wait time | 6s (heavy React rendering) | 2.5s normally |
| Scroll container | `nav > div` with overflow-y:auto | `div[class*="sidebar"]` child |

## Integration with BiDi Client

In `app/connectors/_firefox_bidi.py`, the JS is sent via `script.evaluate` with `awaitPromise: True`:

```python
raw = await ff.evaluate(SCROLL_AND_EXTRACT_LIST_JS)
conversations = json.loads(raw) if isinstance(raw, str) else raw
```

The page must have an active browsing context (tab) and the user must be logged in. The JS runs in the page context and returns a JSON string of all discovered conversations.

## Sidebar Scroll vs API Pagination

Sidebar scroll is a **last resort** pattern — it's DOM-based, fragile if ChatGPT/Grok change their HTML structure, and slow (2.5s per scroll iteration).

If the site exposes an API endpoint for conversation history (e.g., `GET /backend-api/conversations?offset=N&limit=20`), prefer that. API pagination is faster, more reliable, and doesn't consume BiDi session capacity for navigation.

ChatGPT has a `GET /backend-api/conversations?offset=0&limit=30` endpoint that returns JSON with conversation IDs, titles, and timestamps. Use that instead when available.
