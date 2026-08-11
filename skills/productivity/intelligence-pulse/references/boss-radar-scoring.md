# Boss Radar Scoring & Action Tiers

**Purpose:** Consistent scoring and tiering system across all monitoring and intelligence pipelines. Every finding gets a relevance score and action tier so the operator can triage at a glance.

## Relevance Score (0.0 - 1.0)

Scored per-finding based on direct applicability to the operator's stack, current projects, pain points, or cash generation.

| Range | Label | Criteria |
|-------|-------|----------|
| 0.70 - 1.0 | **TIER 1 (ACT NOW)** | Directly applicable right now. A tool to install, a model to try, a technique solving a known problem, an opportunity with immediate ROI. Requires action or decision. |
| 0.40 - 0.69 | **TIER 2 (WATCH)** | Relevant but not urgent. Worth monitoring. New framework, promising paper, pricing change, emerging trend. Action not needed yet. |
| < 0.40 | **TIER 3 (NOTE)** | Background signal. Industry context, incremental improvements, noise. Never surfaced in delivery. |

## Action Tiers

| Tier | Label | Behavior |
|------|-------|----------|
| TIER 1 | **ACT NOW** | Surface prominently. Flag for immediate action. Can trigger alert bridge delivery. |
| TIER 2 | **WATCH** | Include in next digest. Mention in pulse body. Track over time. |
| TIER 3 | **NOTE** | Skip entirely. Not delivered. Used only for internal dedup state. |

## Threshold Calibration by Category Group

Different category types score differently due to keyword bias. Calibrate per group:

### Trump/KB Categories (nyag_civil, criminal, trump_org, forbes, djt, real_estate, regulatory)
- Algorithmic scoring via keyword matching (run_monitor.py)
- Trump name bonus: +0.25 — inflates scores across the board
- TIER 1: >= 0.75 | TIER 2: 0.50 - 0.74 | TIER 3: < 0.50
- Alert bridge threshold: 0.60

### Business Intelligence Categories (fl_land_intel, govcon_c2c_intel)
- Algorithmic scoring via keyword matching (run_monitor.py)
- No name bonus — scores naturally cluster 0.25 - 0.60
- TIER 1: >= 0.55 | TIER 2: 0.30 - 0.54 | TIER 3: < 0.30
- Alert bridge threshold: 0.40

### Opportunity Signals / Wildcard
- Algorithmic scoring — broad queries, naturally low precision
- TIER 1: >= 0.50 | TIER 2: 0.25 - 0.49 | TIER 3: < 0.25
- Alert bridge threshold: 0.40

### AI/ML Ecosystem Research
- LLM-assigned scoring during synthesis (not algorithmic)
- Scored by reasoning over paper/repo content and the operator's stack
- TIER 1: >= 0.70 | TIER 2: 0.40 - 0.69 | TIER 3: < 0.40
- Delivery: only TIER 1 and TIER 2. Silent if nothing >= 0.60.

## Output Format

All delivery channels use the same format:

```
[0.85] [TIER 1] Finding headline — why it matters
   https://source.url
[0.55] [TIER 2] Another finding
   https://source.url
```

## Implementation

### Automated (no_agent scripts)
Works with any scoring that produces 0-1 values:

```python
def score_to_tier(score, category_group="default"):
    thresholds = {
        "default":      [(0.70, "TIER 1"), (0.40, "TIER 2")],
        "trump":        [(0.75, "TIER 1"), (0.50, "TIER 2")],
        "business_intel": [(0.55, "TIER 1"), (0.30, "TIER 2")],
        "opportunity":  [(0.50, "TIER 1"), (0.25, "TIER 2")],
    }
    th = thresholds.get(category_group, thresholds["default"])
    for threshold, tier in th:
        if score >= threshold:
            return tier
    return "TIER 3"
```

### LLM-Assigned (cron agent synthesizing)
The cron prompt defines the rubric and instructs the agent to assign scores/tiers during synthesis. The LLM has better context than keyword matching for nuanced findings.

## Alert Bridge Integration

The alert bridge (no_agent cron, every 4h) uses category-specific thresholds:

- Trump/KB cats: 0.60
- Business intel cats: 0.40
- AI research: 0.40 (when using algorithmic scores), or LLM-decided

State tracking: each alert bridge maintains a small JSON state file tracking the last-alerted fingerprint to prevent re-alerting the same item.

## Daily Digest Integration

The daily digest groups findings by category, ranks by relevance score descending, and formats with score + tier inline. Only TIER 1 and TIER 2 are surfaced. The digest maintains its own state file of reported fingerprints to avoid re-reporting across days.
