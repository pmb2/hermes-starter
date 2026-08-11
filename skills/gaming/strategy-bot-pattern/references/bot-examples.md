# Strategy Bot Examples — 10 Common Approaches

These are concrete strategy implementations for the $100→$10M 25% Weekly
Challenge format. Each one represents a different approach to bankroll
management and selection.

## 1. Heavy Favorite (all-in)

**Logic:** Find the single heaviest favorite (-400 or worse moneyline). Bet 100%
of bankroll on it. One bet per week maximum.

```python
for sport, games in odds_data.items():
    for g in games:
        for side, field, team in [("home","home_ml",g["home_team"]),
                                   ("away","away_ml",g["away_team"])]:
            ml = g.get(field)
            if ml and ml <= -400 and ml < best_odds:
                best = {"team": team, "odds": ml, ...}

if best:
    return [StrategyDecision(wager=bankroll, ...)]
```

**Risk:** Extreme — one loss = bust. Fast growth when it hits.

## 2. Value Hunter (Kelly Criterion)

**Logic:** Calculate implied probability from market odds, estimate true
probability with a 5% edge adjustment. Bet only when edge > 5%. Size via
full Kelly: `kelly = edge / (decimal_odds - 1)`.

```python
implied = abs(ml) / (abs(ml) + 100)  # for negative odds
estimated = implied * 0.95  # favorites are overbet
edge = estimated - implied
if edge > 0.05:
    kelly = edge / (decimal - 1)
    wager = bankroll * min(kelly, 0.3)
```

**Risk:** Moderate — Kelly naturally sizes bets down for risky picks.

## 3. Underdog Special

**Logic:** Bet all underdogs at +150 or higher. Fixed 5% of bankroll per bet.
High volume (5-10 bets). Dogs win less often but pay out big when they do.

```python
for game in games:
    for field, team in [("home_ml", home), ("away_ml", away)]:
        ml = game.get(field)
        if ml and ml >= 150:
            decisions.append(StrategyDecision(wager=bankroll * 0.05, ...))
```

**Risk:** High — long losing streaks are common.

## 4. Conservative Grinder

**Logic:** Only -200+ favorites, 10% fixed sizing. Steady compounding.

```python
for game in games:
    for field, team in [("home_ml", home), ("away_ml", away)]:
        ml = game.get(field)
        if ml and ml <= -200:
            decisions.append(StrategyDecision(wager=bankroll * 0.10, ...))
```

**Risk:** Low — favorites at -200 win ~67%+.

## 5. Arbitrage Bot

**Logic:** Find games where the sum of inverse decimal odds on both sides
is < 1 (guaranteed profit regardless of outcome).

```python
home_dec = 1 + 100/abs(home_ml) if home_ml < 0 else 1 + home_ml/100
away_dec = 1 + 100/abs(away_ml) if away_ml < 0 else 1 + away_ml/100
arb_pct = (1/home_dec) + (1/away_dec)
if arb_pct < 0.98:  # 2%+ return
    # Bet both sides proportionally for risk-free profit
```

**Risk:** Near zero — guaranteed profit if arb is real.

## 6. Momentum Trader

**Logic:** In live games, bet the team that's leading. In upcoming games,
bet home favorites as a momentum proxy.

```python
if status == "live" and int(home_score) > int(away_score) + 3:
    bet on home team
elif status == "scheduled" and home_ml <= -150:
    bet on home team (home field momentum)
```

**Risk:** Moderate — momentum can reverse.

## 7. Martingale

**Logic:** Base unit = 2% of starting bankroll. After each loss, double the
next wager. After a win, reset to base. Only bet -150+ favorites.

```python
multiplier = 2 ** consecutive_losses
wager = min(base_unit * multiplier, bankroll * 0.5)  # cap at 50%
```

**Risk:** Very high — 5-loss streak = 32x base unit.

## 8. Kelly Criterion (25% fractional)

**Logic:** Same as Value Hunter but with a 2% edge minimum and 25%
fractional Kelly to reduce variance.

```python
full_kelly = edge / (decimal - 1)
kelly_pct = full_kelly * 0.25  # 25% fractional
wager = bankroll * min(kelly_pct, 0.25)
```

**Risk:** Low-moderate — fractional Kelly controls variance.

## 9. Parlay King

**Logic:** Combine 2-3 heavy favorites (-250+ each) into a parlay. Higher
combined odds while keeping individual leg probabilities high.

```python
from itertools import combinations
for combo in combinations(candidates[:8], 2):
    product = c1["decimal"] * c2["decimal"]
    # American odds of parlay
    parlay_odds = int(round((product - 1) * 100))
```

**Risk:** High — all legs must hit.

## 10. Data Scientist

**Logic:** Multi-factor model scoring each game on:
1. Favorite strength (moneyline magnitude)
2. Home field advantage (+2 pts)
3. Market confidence (strong vs moderate favorite)
4. Long dog penalty (-2 pts for +200+ dogs)
5. Live game momentum if applicable

Take top 20% of scored games. Size proportionally to score.

```python
score = 0
if ml < 0: score += min(10, abs(ml) / 50)
if side == "home": score += 2.0
if ml <= -200: score += 3.0
top_n = max(2, len(all_scored) // 5)
```

**Risk:** Moderate — model-driven, systematic.
