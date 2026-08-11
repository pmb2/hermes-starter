# Engine Status Log — dated observations

Per-engine access behavior observed across sweep sessions. Update with each
session that changes a status. Blocks are per-session/per-fingerprint — a
"blocked" entry means blocked in THAT session, not permanently.

## 2026-08-04 (Legal Watchdog daily sweep, 23:00 ET)

| Source | Backend | Result |
|--------|---------|--------|
| Federal Register API (articles.json) | curl | ✅ Working — but 2 of ~10 queries returned `JSONDecodeError: Expecting value` (empty body); both succeeded on single retry after `sleep 2-3` |
| WY SOS wyobiz.wyo.gov FilingSearch.aspx | curl | HTTP 200 page but form unusable from curl |
| WY SOS | Playwright MCP browser | Form rendered clean, refs obtained, filled + clicked → ASP.NET "Loading..." postback hang → reload → visual CAPTCHA ("What code is in the image?", "Your support ID is:") |
| WY SOS DOM | Playwright evaluate | Element IDs randomized per load: textbox id=`ans`, submit button id=`jar`. `MainContent_*` IDs absent. Detect CAPTCHA via `document.body.innerText` (a11y snapshot missed it) |
| DDG Lite | curl | HTTP 202, no result links (challenge state) |
| DDG Lite | Playwright browser | ✅ Rendered results, 0 console errors. Extraction: `document.body.innerText` slice from first `"1."`; `.result`/`.result-link` selectors returned empty |
| Bing | Playwright browser | ❌ Challenge-gated: "One last step — Please solve the challenge below to continue" |
| Mojeek | curl | Empty results (0 links) |
| OpenCorporates | curl | 1.5KB stub page — JS-gated/blocked |
| Built-in browser_navigate (CDP) | — | ❌ "CDP WebSocket connect failed: target machine actively refused" |

## 2026-08-07 (Legal Watchdog daily sweep, 01:15 ET)

| Source | Backend | Result |
|--------|---------|--------|
| Federal Register API | curl | ✅ Working consistently — all 8 queries parsed clean (FTC 192, DOL 271, SBA 468, GSA 210, OFPP 184, privacy term, all-agency AI). Individual article JSON `/api/v1/articles/<doc>.json` returned title/type/comments_close_on in one call |
| WY SOS FilingSearch.aspx | Playwright MCP | Form rendered clean on first load (NO CAPTCHA), filled "the company" → ASP.NET "Loading..." postback hang → reload → visual CAPTCHA w/ support ID <discord-channel-id>5 (visible in a11y snapshot this time, not just innerText) |
| DDG Lite | curl | First query ✅ 8 result links, then subsequent queries CAPTCHA'd — per-query rate limiting, not a full-session block |
| Bing | Playwright MCP | ❌ Challenge-gated "One last step — Please solve the challenge below" |
| Bing | curl | Page loads (~74KB) but no parseable `<h2>`/b_algo results — JS-layout variant; not usable via grep |
| Mojeek | curl (desktop Chrome UA) | ✅ WORKING — parseable links `grep -oP '<a class="ob" href="\K[^"]+'` + titles `class="title"`. Name queries returned unrelated hits (MN "Backus" town / Saint the operator noise — shallow index). Rate-limited on 4th rapid query (space w/ `sleep 2`). `site:` operator returned nothing |
| Yandex | curl | JS-gated, no extractable links/titles — not usable |
| FTC press releases | Playwright MCP | ✅ Rendered clean, no CAPTCHA; `snapshot(target="main")` + `?page=N` pagination worked; newest item Jul 31, 2026 |
| Built-in browser_navigate (CDP) | — | ❌ "CDP WebSocket connect failed: ... actively refused" (same as Aug 4) |

## 2026-08-08 (Legal Watchdog daily sweep, 03:05 UTC / Aug 7 23:05 ET)

| Source | Backend | Result |
|--------|---------|--------|
| Federal Register API | curl | ✅ Working — all agency sweeps parsed clean (FTC 192, DOL 271, SBA 468, GSA 210, OFPP 184); FTC AI Accuracy doc 2026-13628: comments closed 7/31, no final rule yet (status None) |
| DDG Lite | curl | ❌ ALL 7 queries blocked with "anomaly" marker (unlike Aug 7 01:15 where the first query worked) — per-session variability reconfirmed |
| DDG HTML (html.duckduckgo.com/html/) | Playwright MCP | ✅ NEW: renders clean, ZERO CAPTCHA; `.result`/`a.result__a`/`.result__snippet` selectors work for browser_evaluate extraction (title \|\| href \|\| snippet per line). Used for all 7 name/entity queries. `site:sos.wyo.gov "the company"` → 0 results (registry data not indexed — index gap, not absence) |
| WY SOS FilingSearch.aspx | Playwright MCP | Form clean on first load → "the company" (Contains radio) → ASP.NET "Loading..." hang → reload → visual CAPTCHA (support ID <discord-channel-id>0) — same sequence as Aug 4/7, reconfirmed; `site:` fallback is a dead end |
| Built-in browser_navigate (CDP) | — | ❌ "CDP WebSocket connect failed: ... actively refused" (third consecutive session) |

## 2026-08-08 (Reputation Monitor, Sat 14:00 UTC)

| Source | Backend | Result |
|--------|---------|--------|
| DDG HTML (html.duckduckgo.com/html/) | Playwright MCP | ✅ Still clean (3rd session). Same `.result`/`a.result__a`/`.result__snippet` evaluate extraction. **NEW pitfall: navigate and evaluate issued in the SAME parallel batch → evaluate returns the PREVIOUS page's results. Always navigate, then evaluate in a separate call.** |
| allrecentarrests.org main domain | curl | 404 — page gone (removal stuck/expired). But **state subdomains still live**: ny.allrecentarrests.org, ny.alljailsearch.org, www.alljailsearch.org all HTTP 200 serving same false claim ID 1649468. `alljailsearch.com` root dead (000/connection refused). **Main-domain 404 ≠ resolved — probe state subdomains and sibling TLDs.** |
| inmateaid.com/inmate-profiles/the operator-backus | curl | ✅ 200 — generic path LIVE with false claim ("incarcerated in Schenectady County Correctional Facility"); the /1649468/ ID path 404s. Check the generic listing path, not just the ID URL. |
| Data broker sweep | curl | beenverified.com 200 (JS-rendered, no text via grep), spokeo.com 200, radaris.com 404 on /~the operator-Backus (site Cloudflare-blocked), familytreenow.com 403, peoplefinders.com 403 |
| `/tmp` file persistence | terminal | ⚠️ `curl -o /tmp/x.html` reported size but file GONE by next terminal call (grep: No such file). `/tmp` is ephemeral/per-call on this MSYS host. **Pipe fetch→parse in one command** (`curl ... | grep -oP` / `| python3 -c`). |

## Recurring patterns to remember

- Bing open in Jul 2026 sweeps, challenge-gated Aug 4 AND Aug 7 2026 — never assume; treat Bing as unreliable now.
- DDG Lite via browser has been the reliable fallback both times curl was blocked; curl→DDG may still work for the FIRST query (per-query rate limit).
- Mojeek curl: empty Aug 4 → WORKING Aug 7 WITH desktop Chrome UA header. Send the UA — that is the difference.
- session_search for last-confirmed entity status worked well as registry baseline
  when WY SOS was blocked (found "ACTIVE per Aug 1 Reputation Monitor run").
- WY SOS: first load can render clean (no CAPTCHA); the CAPTCHA appears on RELOAD after the ASP.NET postback hang. Record the support ID for the manual-check report.
- DDG HTML via Playwright is the best browser search path (verified Aug 7-8): standard `.result` selectors work, richer results than Lite, no CAPTCHA — prefer it over Lite for extraction-heavy sweeps. `site:` on registry domains (wyobiz) returns zero — an index gap, never evidence of absence.
- CDP/built-in browser_navigate has been down three consecutive sessions (Aug 4, 7, 8) — treat Playwright MCP as the default browser backend for now, not the fallback.
- **Playwright evaluate/navigate sequencing:** never batch `browser_navigate` and `browser_evaluate` in the same parallel batch — the evaluate runs against the PREVIOUS page. Navigate, then evaluate in a separate call (confirmed Aug 8 2026).
- **MSYS /tmp is ephemeral per terminal call:** `curl -o /tmp/x.html` can report a size yet the file is gone in the next call. Always pipe fetch→parse in one command (`curl ... | grep -oP` / `| python3 -c`); never save to /tmp for a later read.
- **Syndicated arrest-site networks: a main-domain 404 ≠ resolved.** allrecentarrests.org main page 404'd but ny.allrecentarrests.org, ny.alljailsearch.org, www.alljailsearch.org all still served the same claim (ID 1649468); `alljailsearch.com` (dead) vs `alljailsearch.org` (live) differ by TLD. Probe state subdomains and sibling TLDs, and check generic listing paths (inmateaid.com/inmate-profiles/the operator-backus works while /1649468/ 404s).
