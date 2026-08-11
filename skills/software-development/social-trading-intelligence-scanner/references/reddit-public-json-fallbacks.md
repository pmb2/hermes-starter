# Reddit public JSON fallbacks

## Problem

From agent/cron hosts, `https://www.reddit.com/r/{sub}/{listing}.json` often returns:

```
403 Client Error: Blocked
```

even with a custom User-Agent.

## Working fallback chain

Try in order with the same params (`limit`, `raw_json=1`):

1. `https://www.reddit.com/r/{sub}/{listing}.json`
2. `https://old.reddit.com/r/{sub}/{listing}.json`
3. `https://api.reddit.com/r/{sub}/{listing}` (no `.json` suffix)

Headers that helped:

```
User-Agent: Mozilla/5.0 ... Chrome/124 ... stock-sniffer/0.1
Accept: application/json,text/html;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.9
```

Polite delay ~0.6s between public listing requests.

## Better long-term

Script app via PRAW when `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` are set. Mode `auto` should prefer PRAW when creds exist.

## Reporting

If all Reddit hosts fail but YouTube works, still emit a report (do not hard-fail the whole scan). Note Reddit empty in risk/notes; only use `❌` for total operational failure when policy requires.
