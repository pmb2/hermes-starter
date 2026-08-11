# MLB Stats API Reference

Free, no-key-required API from MLB for schedule, scores, and player data. Useful as a fallback data source when primary odds providers (DraftKings, Odds API) are inaccessible or during off-season/All-Star break.

## Base URL

```
https://statsapi.mlb.com/api/v1/
```

## Useful Endpoints

### Schedule — check what games exist on a given date

```
GET /schedule?sportId=1&date=YYYY-MM-DD&hydrate=probablePitcher,linescore
```

Returns all MLB games for that date with team names, scores, status, probable pitchers, venue, and linescore.

**Quick check via curl + inline Python:**

```bash
curl -s "https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-07-14&hydrate=probablePitcher,linescore" | \
  python -c "import json,sys; d=json.load(sys.stdin); print(f'Games: {d[\"totalItems\"]}'); [(lambda g: print(f'  {g[\"teams\"][\"away\"][\"team\"][\"name\"]} @ {g[\"teams\"][\"home\"][\"team\"][\"name\"]} — {g[\"status\"][\"detailedState\"]}'))(g) for g in (d.get('dates',[{}])[0].get('games',[]) if d.get('dates') else [])]"
```

**Compact view (no hydrate)** — faster, less data, good for just checking existence/status:

```bash
curl -s "https://statsapi.mlb.com/api/v1/schedule?date=2026-07-22&sportId=1" | \
  python -c "
import sys, json
data = json.load(sys.stdin)
for d in data.get('dates', []):
    for g in d.get('games', []):
        status = g['status']['detailedState']
        away = g['teams']['away']['team']['name']
        home = g['teams']['home']['team']['name']
        print(f'{away} @ {home} | Status: {status}')
"
```

### Single game live feed (full pitch-by-pitch)

```
GET /game/{gamePk}/feed/live
```

Full pitch-by-pitch data for in-progress or completed games. Contains `gameData.status.detailedState` and `gameData.status.codedGameState` for checking finality.

**Usage for bet-resolution checking:**

```python
# Check if game is final
import requests, json
data = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{gamePk}/feed/live").json()
gs = data['gameData']['status']
is_final = gs['codedGameState'] in ('F', 'FT', 'FO')
print(f"Status: {gs['detailedState']} — coded: {gs['codedGameState']}")
```

### Linescore (current score + inning-by-inning)

```
GET /game/{gamePk}/linescore
```

Returns current inning, inning state (Top/Bottom), runs/hits/errors per team, and a per-inning breakdown array. Use this for lightweight status checks without downloading the full live feed.

**Output fields:**

| Field | Type | Description |
|-------|------|-------------|
| `currentInning` | int | Current inning number |
| `inningState` | string | `"Top"` or `"Bottom"` |
| `isTopInning` | bool | True = away batting |
| `teams.home.runs` | int | Home team total runs |
| `teams.away.runs` | int | Away team total runs |
| `teams.home.hits` | int | Home team total hits |
| `teams.home.errors` | int | Home team total errors |
| `innings[]` | array | Per-inning array with `num`, `home.runs`, `away.runs` |

**Quick score check:**

```bash
curl -s "https://statsapi.mlb.com/api/v1/game/{gamePk}/linescore" | \
  python -c "
import sys, json
data = json.load(sys.stdin)
inn = data.get('currentInning', '?')
state = data.get('inningState', '?')
ar = data.get('teams', {}).get('away', {}).get('runs', 0)
hr = data.get('teams', {}).get('home', {}).get('runs', 0)
print(f'Inning: {inn} {state} — Away {ar}, Home {hr}')
"
```

### Team info

```
GET /teams?sportId=1
```

All 30 MLB teams with IDs, names, venue, league, division.

### People (player) info

```
GET /people/{playerId}
```

Player details: name, position, stats, handedness.

## Game State Codes

Seen in `status.codedGameState` from the schedule or live-feed endpoint:

| Code | Meaning |
|------|---------|
| `P` | Pre-game / scheduled |
| `W` | Warmup |
| `I` | In Progress (live) |
| `F` | Final |
| `FT` | Final (tie) |
| `FO` | Final (forfeit) |
| `D` | Delayed |
| `PPD` | Postponed |

`status.detailedState` gives the human-readable version ("In Progress", "Final", "Scheduled", "Warmup", "Pre-Game").

## Critical Observations

- **No auth required** — zero rate limits observed (free public API).
- **All-Star Game days** (typically mid-July): `totalItems=1` with teams "American League All-Stars" / "National League All-Stars". No regular season games that day or the next day.
- **Post All-Star break restart**: first regular season game back is usually the host team (e.g., Mets @ Phillies on July 16). Full 15-game slate resumes on July 17.
- **Schedule endpoint works for any date** (past, present, future) — dates with no games return `{"dates":[],"totalItems":0,"totalGames":0}`.
- **hydrate=probablePitcher** includes pitcher names. **hydrate=linescore** includes inning-by-inning runs/hits/errors plus current score.
- **gameType**: "R" = regular season, "A" = All-Star Game, "S" = spring training, "P" = postseason, "D" = divisional series, "L" = league championship, "W" = world series.
- **linescore endpoint returns early innings even when score is 0-0** — each inning object has `{num, home: {runs, hits, errors, leftOnBase}, away: {runs, hits, errors, leftOnBase}}`. Empty innings are omitted.
- **The live-feed endpoint v1.1** (`/api/v1.1/game/{pk}/feed/live`) is the most comprehensive but heaviest. Use `/api/v1/game/{pk}/linescore` for quick status checks and the schedule endpoint for multi-game overviews.
- **Doubleheaders**: both games appear in the schedule under the same date. Distinguish by `gameDate` timestamp — common patterns: Game 1 at 17:05 UTC (1:05 PM ET), Game 2 at 23:05 UTC (7:05 PM ET).

## When to Use

| Situation | Recommended Endpoint |
|-----------|---------------------|
| Check if any games exist today | `/schedule?sportId=1&date=TODAY` |
| Get probable pitchers for analysis | Add `&hydrate=probablePitcher` |
| Check final scores | Add `&hydrate=linescore` + check `status.detailedState` = "Final" |
| Both pitchers + scores | `&hydrate=probablePitcher,linescore` |
| Verify a game is officially final | Check `status.codedGameState` — `"F"` / `"FT"` / `"FO"` = final |
| Quick in-game score check (lightweight) | `GET /game/{gamePk}/linescore` — returns current inning, state, score |
| Full resolution check before settling a bet | `GET /game/{gamePk}/feed/live` — use `gameData.status.codedGameState` |
| Multi-game overview (no extra data) | `GET /schedule?sportId=1&date=TODAY` (no hydrate) |
