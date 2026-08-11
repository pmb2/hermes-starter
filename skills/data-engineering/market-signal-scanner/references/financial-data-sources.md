# Keyless financial data sources (verified 2026-08)

All endpoints verified working without API keys. Re-probe with curl before wiring new scans — feeds drift.

## Reddit (public JSON)
- Endpoints: `https://www.reddit.com/r/{sub}/{listing}.json?limit=N&raw_json=1` (also `old.reddit.com`, `api.reddit.com` as fallbacks)
- **403 without a browser-like User-Agent** — use a full Chrome UA string, not a bot identifier
- Listings: `hot`, `rising`, `new`; skip `stickied` posts
- Public JSON is unauthenticated and rate-limited; PRAW script creds (`REDDIT_CLIENT_ID/SECRET`) lift the ceiling
- No `praw` dependency needed for v1 — requests + JSON is enough

## StockTwits (keyless)
- Trending: `GET https://api.stocktwits.com/api/2/trending/symbols.json?limit=20`
  - Returns `symbols[]` with `symbol`, `watchlist_count`, `trends.summary` — great confirmation layer
- Streams: `GET https://api.stocktwits.com/api/2/streams/symbol/{SYMBOL}.json?limit=20`
  - Returns `messages[]` with `body` (cashtag-formatted), `likes.total`, `replies`, `user.username`, `created_at` (ISO)
- **Crypto pollution**: symbols end `.X` (e.g. `CRO.X`) — filter `endswith('.X')` for equity watchlists
- No auth headers needed; plain UA fine

## RSS news feeds
- **Working** (verified):
  - MarketWatch top stories: `https://feeds.content.dowjones.io/public/rss/mw_topstories`
  - Investing.com: `https://www.investing.com/rss/news.rss`
  - Yahoo Finance index: `https://finance.yahoo.com/news/rssindex`
- **Dead** (verified 2026-08 — do not use):
  - `https://feeds.finance.yahoo.com/rss/2.0/headline?s=...` → returns sad-panda HTML page
  - Benzinga `https://www.benzinga.com/feed` → empty body
- parse with `feedparser`; send a browser UA; treat feeds as non-critical (never fail the scan on feed errors)
- Filter by `published_parsed` age; dedupe on entry id/link

## yfinance (keyless market confirmation)
- `ticker.fast_info` → `last_price`, `previous_close`, `open`, `day_high`, `day_low`, `market_cap` — **no volume here**
- `ticker.history(period='10d')` → DataFrame with `Close`, `Volume` — compute change%, volume vs 5-day avg, gap% from these
- `ticker.calendar` → dict with `'Earnings Date': [date, ...]` (list of `datetime.date`); compute days-until-earnings for swing-option risk flags
- **Cache aggressively** (15 min quotes, 6 h earnings) — each call is ~1-2s; batch only top N (10-12) signals per scan
- Wrap in try/except + `available()` flag so scans work when yfinance is missing

## YouTube (no API key)
- Channel RSS: `https://www.youtube.com/feeds/videos.xml?channel_id=UC...`
- Search RSS: `https://www.youtube.com/feeds/videos.xml?search_query=...` (URL-encoded) — works without API key
- Transcripts: `youtube-transcript-api` python package; falls back to title+description on block
- Resolve channel IDs via yt-dlp search (`yt-dlp "ytsearch1:..." --print channel_id`) when only a handle is known

## Optional LLM distillation (OmniRoute, env-gated)
- Local gateway: `http://localhost:20128/v1` (OpenAI-compatible), key `omniroute-local` or `OMNIROUTE_API_KEY`
- Gate with `STOCK_SNIFFER_LLM_ENABLED=1`; model e.g. `gpt-5.6-sol`; default OFF so scans work without it
- Use `response_format: {"type": "json_object"}` for structured `{tickers, summary}` output
