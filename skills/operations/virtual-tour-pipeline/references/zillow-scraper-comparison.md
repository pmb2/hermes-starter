# Zillow Scraper Comparison

## 1. Zillow Scraper API (zillowscraperapi.com)
**URL:** https://zillowscraperapi.com/
**Data:** Full property JSON, photos, agent, floor plan
**Pricing:**
- Free: 1,000 requests, no card needed
- Vibe: $19/mo (27K requests)
- Pro: $49/mo (82K requests, $0.60/1K)
- Pay-as-you-go: $0.90/1K
**Anti-bot:** Built-in residential proxies + PerimeterX handling
**Status:** Recommended for our scale. Free tier covers months of dev.

## 2. Apify Zillow Actors
**URL:** https://apify.com/maxcopell/zillow-scraper
**Actors:** Zillow Scraper, Zillow Search Scraper, Zillow Property Images Fetcher
**Pricing:** ~$2/1K results, $5 free monthly credits
**Pros:** Can run on cron schedule, pay-per-result
**Cons:** Need Apify account

## 3. Bright Data Zillow Scraper
**URL:** https://brightdata.com/products/web-scraper/zillow
**Pricing:** $1.50/1K requests, 5K free/mo, 98.44% success rate
**Pros:** Enterprise-grade, 400M+ residential IPs
**Cons:** Overkill for our volume, $250 minimum on dataset

## 4. HasData
**URL:** https://hasdata.com/apis/zillow-api
**Pricing:** Pay-per-request (less transparent)
**Unique:** Has MCP server — could wire directly as Hermes tool

## 5. APIllow
**URL:** https://zillapi.com/
**Pricing:** Free tier (100 credits), paid from $54/yr
**Cons:** Limited data fields, no agent email

## 6. DIY Playwright (NOT viable alone)
Search pages load. Detail pages blocked by PerimeterX. Use only for initial URL discovery then feed to paid API.

---

**Verdict:** Zillow Scraper API free tier for dev → Pro ($49/mo) at scale.
