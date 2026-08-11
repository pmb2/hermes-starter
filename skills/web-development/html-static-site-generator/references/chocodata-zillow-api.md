# ChocoData Zillow API Reference

**Base URL:** `https://api.chocodata.com/api/v1/zillow`
**API key format:** `cd_live_XXXXXXXXXXXXX`
**Free tier:** 1,000 requests, no credit card
**Pro tier:** $49/mo for 82,000 requests ($0.60/1K)
**Pay-as-you-go:** $0.90/1K successful

## Property Endpoint

```
GET /property?api_key={key}&zpid={zpid}&country=us
```

### Key fields returned

| Field | Type | Example |
|-------|------|---------|
| `name` | str | `"451 Ballston Road, your city, NY, 12302"` |
| `description` | str | Full MLS description |
| `images` | list[str] | `["https://photos.zillowstatic.com/fp/abc-p_d.jpg", ...]` |
| `main_image` | str | `"https://photos.zillowstatic.com/fp/abc-p_d.jpg"` |
| `listing_agent` | str | `"Christine M Serafini, Miranda Real Estate Group Inc"` |
| `trade_info` | list[dict] | `[{"price":"399900","beds":4,"baths":2,"living_area":1880}]` |
| `rooms` | list[dict] | `[{"room_type":"bedroom","count":4},{"room_type":"bathroom","count":2}]` |
| `lot_size` | str | Sqft as string: `"14810"` |
| `url` | str | Full Zillow URL |
| `year_built` | int | `1939` |
| `home_status` | str | `FOR_SALE`, `FOR_RENT`, `SOLD` |
| `property_type` | str | `apartment`, `single_family`, `condo`, etc. |
| `latitude` / `longitude` | float | Coordinates |
| `parcel_id` | str | Tax parcel ID |

### Image note

Images come as raw URL strings with `_d.jpg` suffix. DO NOT try to upgrade to `_bd.jpg` — that variant 404s for most listings. Use `_d.jpg` directly:
```python
url = url.replace("_bd.jpg", "_d.jpg")  # strip broken HD variant
```

### Agent parsing

`listing_agent` is `"Name, Brokerage"`. Split on `", "`:
```python
parts = listing_agent.split(", ")
agent_name = parts[0]  # "Christine M Serafini"
agent_broker = parts[1]  # "Miranda Real Estate Group Inc"
```

## Search Endpoint

```
GET /search?api_key={key}&location={zip}&status=for_sale|for_rent|sold&country=us
```

**Returns:** `{"query":..., "location":..., "total_results":N, "results_count":N, "results": [{"zpid": 12345}, ...]}`

Results contain ONLY the `zpid` field. You must call the property endpoint for each ZPID to get full data.

### Rate limiting
Allow ~300ms between detail-lookup calls. The API auto-retries transient failures (502 `target_unreachable`).

### Location quirk
`"your city,NY"` as the location may return Westchester County (Irvington/Tarrytown, ~145mi away). Use zip code `"12302"` for the actual your city/Schenectady area. Zip searches return 40+ results for active zip codes.

### Photo count distribution (your city 12302, July 2026)
Test of 41 listings in 12302: 33 of 41 (80%) have 20+ photos. 11 listings have 50 photos. Typical listings have 20-50 photos. The `images` array is reliably populated for active for-sale listings.

## Pricing (zillowscraperapi.com)

| Plan | Cost | Requests/mo | Per 1K |
|------|------|-------------|--------|
| Free | $0 | 1,000 | — |
| Vibe | $19/mo | 27,000 | $0.70 |
| Pro | $49/mo | 82,000 | $0.60 |
| Custom | $100+/mo | 200k-4M+ | $0.50 |
| Pay-as-you-go | top-up | — | $0.90 |

## Error handling

- **502 Bad Gateway / target_unreachable:** Transient — retry. You are NOT charged for failed requests.
- **403:** The API's anti-bot pool couldn't handle the request. Retry later.
- **Missing images:** Some listings have 0 photos even when the listing exists (typically recently added or expired).
