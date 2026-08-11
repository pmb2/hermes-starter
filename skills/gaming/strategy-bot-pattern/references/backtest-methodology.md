# 5-Week Strategy Backtest Methodology

## Overview

Run N strategy bots against M weeks of historical odds data, each trial
probabilistically resolving unmatched games to produce averaged results.

## Key Parameters

| Parameter | Typical Value | Description |
|-----------|---------------|-------------|
| `LOOKBACK_DAYS` | 35 (5 weeks) | Window of historical data to replay |
| `NUM_TRIALS` | 5 | Number of randomized runs per bot |
| `BOT_CLASSES` | 10 | Strategy implementations loaded from registry |

## Data Flow

```
SQLite games table
  │  SELECT all games, sorted by commence_time DESC
  ▼
Filter to LOOKBACK_DAYS window (timestamps)
  │  Split by challenge week
  ▼
For each bot, for each trial:
  ├── bot.decide(games_by_sport, bankroll) → decisions
  ├── match_game(decision, flat_games) → game (or None)
  ├── settle_decision(decision, game) → (result, P/L)
  └── bankroll += P/L
  ▼
Aggregate: average W/L/P, final bankroll, ROI across all trials
  ▼
Save to data/backtest_results.json
```

## Probabilistic Settlement

Not all historical games have real scores. For games without scores
(common with the-odds-api free tier), use implied probability from
the **home moneyline odds**:

```python
def implied_prob(american_odds):
    if american_odds is None:
        return 0.5  # coin flip
    if american_odds > 0:
        return 100 / (american_odds + 100)
    return abs(american_odds) / (abs(american_odds) + 100)

def settle_decision(decision, game):
    team_key = pick_team_key(decision, game)
    winner = determine_winner(game)  # from real scores, or None

    if winner and winner != "push":
        same = team_key == winner
    elif winner == "push":
        return ("P", 0.0)
    else:
        # No real scores — simulate via implied probability
        if team_key == "home":
            prob = implied_prob(game.get("home_ml"))
        else:
            prob = implied_prob(game.get("away_ml"))
        same = random.random() < prob

    if same:
        # Calculate payout
        if decision.odds > 0:
            payout = decision.wager * (1 + decision.odds / 100)
        else:
            payout = decision.wager * (1 + 100 / abs(decision.odds))
        return ("W", round(payout - decision.wager, 2))
    return ("L", round(-decision.wager, 2))
```

## Wager Sizing

Two modes based on whether the bot is already at its weekly target:

```python
target = week_target(cw)
gap = max(0, target - bankroll)

if gap > 0 and dec.odds != 0:
    # Calibrated sizing: wager enough to close the gap
    n = len(decisions)
    needed = gap / max(n, 1)
    if dec.odds > 0:
        wager = needed / (dec.odds / 100)
    else:
        wager = needed / (100 / abs(dec.odds))
    wager = min(wager, bankroll)
    wager = max(wager, 1.0)
else:
    # Default: 5% of bankroll
    wager = bankroll * 0.05
```

## Results Format

```json
{
  "date": "2026-07-09",
  "lookback_days": 35,
  "num_trials": 5,
  "total_games": 42,
  "games_with_scores": 18,
  "season_start": "2026-07-01",
  "active_weeks": [1, 2, 3, 4, 5],
  "results": [
    {
      "username": "strat_ds",
      "display_name": "Ds",
      "avg_wins": 2,
      "avg_losses": 0,
      "avg_pushes": 0,
      "total_bets": 2,
      "win_pct": 100.0,
      "final_bankroll": 102.47,
      "net_pl": 2.47,
      "roi_pct": 2.5,
      "avg_weeks": 5
    }
  ]
}
```

## API Endpoints

### GET — Read Latest Results

```python
@app.get("/api/strategies/backtest")
def get_backtest_results():
    results_path = ROOT / "data" / "backtest_results.json"
    if results_path.exists():
        return json.loads(results_path.read_text())
    return {"results": [], "message": "No backtest data yet."}
```

### POST — Run Backtest + Sync to DB

Trigger the backtest script via subprocess, persist results and sync to `challenge_participants` table so the strategy engine picks them up on next refresh:

```python
@app.post("/api/strategies/backtest/run")
def run_backtest_and_sync():
    script_path = ROOT / "scripts" / "backtest_5week.py"
    subprocess.run([sys.executable, str(script_path)], capture_output=True, timeout=120, cwd=ROOT)
    
    # Read results
    bt = json.loads((ROOT / "data" / "backtest_results.json").read_text())
    
    # Append to history file (keep last 50)
    history_path = ROOT / "data" / "backtest_history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    history.append({"date": datetime.now().isoformat(), "results": bt["results"], "games_analyzed": bt["total_games"]})
    history = history[-50:]
    history_path.write_text(json.dumps(history, indent=2))
    
    # Sync to challenge_participants table
    for r in bt["results"]:
        conn.execute("""
            INSERT INTO challenge_participants (user_id, display_name, current_units, wins, losses, week_reached)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                current_units=excluded.current_units, wins=excluded.wins,
                losses=excluded.losses, week_reached=excluded.week_reached
        """, (r["username"], r["display_name"], r["final_bankroll"], r["avg_wins"], r["avg_losses"], r.get("avg_weeks", 1)))
    conn.commit()
    
    return {"success": True, "results": bt["results"], "history_id": len(history) - 1}
```

### GET — Backtest History

Return all past runs (newest first) for frontend < > navigation:

```python
@app.get("/api/strategies/backtest/history")
def get_backtest_history():
    history_path = ROOT / "data" / "backtest_history.json"
    if history_path.exists():
        return json.loads(history_path.read_text())[::-1]  # newest first
    return []
```

## Frontend: Strategy Table Columns

The strategy table should display each bot's current week and deadline countdown:

| Column | Source | Example |
|--------|--------|---------|
| Week | `bot.week_reached` | Wk 3 |
| Deadline | `7 - (week_reached % 7)` | 4d |

Add `week_reached` to `BaseStrategy.get_status()`:
```python
"week_reached": getattr(self, "week_reached", 1),
```
And load it from the DB in the engine:
```python
bot.week_reached = r.get("week_reached", 1)
```

### Frontend < > History Navigation

Store the history array and an index, render → apply on arrow click:

```javascript
async function loadBacktestHistory() {
  const data = await API.backtestHistory();
  _btHistory = Array.isArray(data) ? data : [];
  _btIdx = 0;
  updateBacktestNav();
}

function prevBacktest() {
  if (_btIdx > 0) { _btIdx--; applyBacktestRun(_btHistory[_btIdx]); updateBacktestNav(); }
}

function nextBacktest() {
  if (_btIdx < _btHistory.length - 1) { _btIdx++; applyBacktestRun(_btHistory[_btIdx]); updateBacktestNav(); }
}

function applyBacktestRun(run) {
  const bots = run.results.map(r => ({
    username: r.username, display_name: r.display_name,
    wins: r.avg_wins || 0, losses: r.avg_losses || 0,
    total_bets: (r.avg_wins || 0) + (r.avg_losses || 0),
    bankroll: r.final_bankroll || 100,
    roi_pct: r.roi_pct || 0, week_reached: r.avg_weeks || 1,
  }));
  renderStrategyTable(bots);
}
```

## Common Pitfalls

- **Games without scores = most of the data.** On free-tier Odds API,
  games rarely have real scores. The backtest relies heavily on
  probabilistic simulation. Run 5+ trials and average to smooth variance.
- **Season timing matters.** If the challenge just started (week 1-2),
  there's only 1-2 weeks of data, giving thin results. Let the season
  accumulate before taking backtest rankings seriously.
- **Bots with preconditions may place zero bets.** A bot that only bets
  -400+ favorites will sit out weeks where no such favorite exists.
  Zero bets = $100 final bankroll = 0% ROI = flat on every trial.
- **Seeded RNG.** Use `random.seed(42 + trial)` so results are
  reproducible. Different seeds produce different win/loss distributions
  for simulated games, which is why averaging across trials matters.
- **Multiple trials are essential** — a single run can be lucky/unlucky.
  With 5 trials and the majority of games simulated, averaged results
  are far more meaningful than any single trial.

### Timezone Naive-vs-Aware Crash

`datetime.now()` returns a **timezone-naive** datetime. DB dates stored
via `datetime.fromisoformat(ct.replace("Z", "+00:00"))` are **timezone-aware**.
Comparing them raises `TypeError: can't compare offset-naive and offset-aware`.

**If the comparison is inside a bare `try/except (ValueError, TypeError): pass`,
the error is silently swallowed** and the game excluded from the window — the
backtest thinks it has zero games.

**Fix:**
```python
now = datetime.utcnow()  # naive UTC
for g in all_games:
    ct = g.get("commence_time", "")
    if ct:
        try:
            ct_dt = datetime.fromisoformat(ct.replace("Z", "+00:00"))
            ct_naive = ct_dt.replace(tzinfo=None)  # strip tz
            if lookback_start <= ct_naive <= lookback_end:
                filtered.append(g)
        except (ValueError, TypeError):
            pass
```

### Max Wager Cap (Base Class Pattern)

Without a hard cap, bots with 90%+ win rates go bust on 100% bankroll bets.

Add to `BaseStrategy.__init__`:
```python
self.max_wager_pct = 0.15  # never bet more than 15% of bankroll
```
Enforce in each `decide()`: `wager = min(wager, round(bankroll * self.max_wager_pct, 2))`.

### The 90/10 Wager Trap

90% win rate still busts with 100% bankroll bets. Caps prevent this.

**Rule of thumb:** 8-15% per bet × 3-5 bets/week beats large bets + low volume.

### Strategy Tuning Loop

1. Run backtest → baseline
2. Identify over/under-betting: busting? cut max wager. Zero bets? lower thresholds.
3. Change ONE parameter at a time
4. Retest, compare deltas
5. Know when to stop — some strategies are fundamentally wrong regardless of params

### Lookback Window

DB with only future games: widen window to include all games.
```python
lookback_end = now + timedelta(days=365)
```

### Chart History Minimum Points

Remove `current != start` condition so flat-trajectory bots get ≥2 points:
```python
elif week_reached >= 1:
    for w in range(1, week_reached + 1):
        bankroll = start if current == start else ...
        result.append({"week": w, "bankroll": bankroll})
```
