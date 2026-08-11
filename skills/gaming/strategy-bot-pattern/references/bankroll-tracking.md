# Bankroll Tracking & Settlement Reference

Full algebraic proof and multi-scenario verification for strategy bot
bankroll accounting. Every formula here is verified against standard
sports betting math.

## The Settlement Function

```python
def settle_bet(wager: float, odds: int, won: bool, pushed: bool = False) -> float:
    if pushed:
        return 0.0
    if not won:
        return -wager
    if odds > 0:
        profit = wager * odds / 100           # +200: $50 * 2 = $100
    else:
        profit = wager * 100 / abs(odds)      # -130: $32.50 * 0.769 = $25
    return round(profit, 2)
```

## Algebraic Proof

```
Given:
  payout = wager + profit
  profit = settle_bet() returns on a win

Identity:
  bankroll + profit = bankroll + (payout - wager)
                    = bankroll - wager + payout
```

The left side is the implicit approach (just add profit).
The right side is the explicit approach (deduct wager, add full payout).
They are identical. No stake is "missing."

## Single-Bet Scenarios

### Scenario 1: Win at -130

```
Start bankroll:   $100.00
Wager:            $32.50
Odds:             -130
Payout:           $32.50 × (1 + 100/130) = $57.50  (stake + profit)
Profit:           $57.50 - $32.50 = $25.00

Method A (implicit):  $100.00 + $25.00 = $125.00
Method B (explicit):  $100.00 - $32.50 + $57.50 = $125.00
```

### Scenario 2: Win at +200

```
Start bankroll:   $100.00
Wager:            $50.00
Odds:             +200
Payout:           $50.00 × (1 + 200/100) = $150.00
Profit:           $150.00 - $50.00 = $100.00

Method A:  $100.00 + $100.00 = $200.00
Method B:  $100.00 - $50.00 + $150.00 = $200.00
```

### Scenario 3: Loss at -130

```
Start bankroll:   $100.00
Wager:            $32.50
Profit/Loss:      -$32.50

Method A:  $100.00 + (-$32.50) = $67.50
Method B:  $100.00 - $32.50 + $0 = $67.50
```

### Scenario 4: Push

```
Start bankroll:   $100.00
Wager:            $20.00
P/L:              $0.00

Method A:  $100.00 + $0.00 = $100.00
Method B:  $100.00 - $20.00 + $20.00 = $100.00
```

## Multi-Bet Sequential Settlement

When a bot settles N bets sequentially in the same cycle, the implicit
method stays consistent because the bankroll feeds forward:

```python
# Round 1 (2 bets, same week)
bankroll = 100.0

# Bet 1: $50 at -110 → WIN
pl1 = 50.0 * 100/110 = 45.45          # profit
bankroll = 100.0 + 45.45 = 145.45     # implicit

# Bet 2: $7.27 at +150 → WIN (wager based on $145.45 bankroll)
pl2 = 7.27 * 150/100 = 10.91          # profit
bankroll = 145.45 + 10.91 = 156.36    # implicit

# Verify with explicit method:
# Bet 1: 100 - 50 + (50 + 45.45) = 145.45
# Bet 2: 145.45 - 7.27 + (7.27 + 10.91) = 156.36
# ✅ Same
```

## Verification Script

```python
# Paste this into any Python shell to verify:
test_cases = [
    # (wager, odds, won, pushed, expected_pl, expected_bankroll)
    (32.50, -130, True, False, 25.00, 125.00),
    (50.00, 200,  True, False, 100.00, 200.00),
    (32.50, -130, False, False, -32.50, 67.50),
    (20.00, 200,  False, True,  0.00,   100.00),
]

for wager, odds, won, pushed, exp_pl, exp_br in test_cases:
    if pushed:
        pl = 0.0
    elif not won:
        pl = -wager
    else:
        pl = wager * odds / 100 if odds > 0 else wager * 100 / abs(odds)
        pl = round(pl, 2)
    br = round(100.0 + pl, 2)  # start at $100
    
    status = "✅" if (pl == exp_pl and br == exp_br) else "❌"
    print(f"{status} wager=${wager} odds={odds} won={won} push={pushed}: "
          f"pl=${pl} br=${br} (expected pl=${exp_pl} br=${exp_br})")
```
