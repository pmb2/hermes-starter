# Enhancement System: Extending the AI Ecosystem Pulse to PIM Content

## Current Architecture

The AI Ecosystem Pulse system (at `hermes-config/docs/AI_ECOSYSTEM_PULSE_ARCHITECTURE.md`) scans arXiv + GitHub for AI/ML developments every 6h using two cron jobs:

- **`ai_ecosystem_scan.py`** (ID: 880cccff88fe, every 6h, LLM-driven) — Searches 8 arXiv frontier categories + GitHub trending, scores findings 0.0–1.0
- **`auto_action_handler.py`** (ID: 9843a00bd786, every 6h, no_agent) — Reads scored findings, auto-executes Tier 1 actions (clone repos, download papers, log opportunities)

### Tier System

| Tier | Score | Action |
|------|-------|--------|
| Tier 1 | ≥ 0.40 | Auto-execute: clone repo + pip install, download arXiv PDF, log opportunity |
| Tier 2 | ≥ 0.20 | Log research note only |
| Tier 3 | < 0.20 | Ignored entirely |

### Key Files

| File | Path |
|------|------|
| Scanner script | `${USER_HOME}/AppData/Local/hermes/scripts/ai_ecosystem_scan.py` |
| Auto-action handler | `${USER_HOME}/AppData/Local/hermes/scripts/auto_action_handler.py` |
| Scored findings | `${USER_HOME}/trumpian-accounting-kb/monitoring/findings/ai_ecosystem_findings.json` |
| FOSS Tier 1 Tracker | `${MY_REPOS}/Documents/github/hermes-config/docs/FOSS_TIER1_TRACKER.md` |
| Clone target dir | `${MY_REPOS}/Documents/github/` |

## Current Gap: PIM Content Not Scanned

The system ONLY scans arXiv + GitHub. It does NOT process content from the PIM ingestion pipeline (ChatGPT conversations, Grok conversations, YouTube transcripts, emails, bookmarks, GitHub stars).

### Why This Matters

The PIM pipeline ingests ~32 Grok conversations + thousands of YouTube items per run. These contain:
- Tool recommendations (like AnythingMCP) that should be auto-evaluated
- Enhancement ideas from AI conversations that could improve Hermes Agent
- Research leads that never get surfaced through arXiv/GitHub scanning

## Planned Extension

The `auto_action_handler.py` already has a modular architecture with `analyze_scored_finding()` that dispatches by tier. To extend it to PIM content:

1. Add a `load_pim_findings()` function that queries `pim.db` for recent items
2. For each item, run relevance scoring (reuse the keyword-based scoring from `ai_ecosystem_scan.py`)
3. Classify by tier using the same thresholds
4. Execute Tier 1 actions (the existing fetch-intercept can now identify repos/URLs from PIM content)

### "Review This" MCP Server (Future)

Create a new MCP server (or skill) that exposes:

- `evaluate_source(url, content_type)` — fetches content, runs tier grader, returns scored findings
- Trigger triggers: "review this [URL]", "check out [tool]", "enhancement scan"
- Auto-inference via SOUL.md patterns added to Hermes Agent + Chief of Staff

## AnythingMCP Analysis (Jul 10 2026)

[anythingmcp](https://github.com/HelpCode-ai/anythingmcp) is a self-hosted MCP gateway that converts REST/SOAP/GraphQL/Database APIs into MCP tools. It has 175+ pre-built adapters, a Knowledge Graph for cross-connector data relationships, AI Skills from usage patterns, and full auth/audit/RBAC.

**Integration potential:** Would serve as a secondary MCP gateway alongside the existing PIM, exposing the PIM database and external APIs as queryable MCP tools. Its Knowledge Graph would let Hermes chain calls across systems. Lower priority than building out the PIM enhancement extension.

**Build order (per the operator):**
1. Extend AI Ecosystem Pulse to scan PIM content (baseline)
2. Build "review this" MCP server (trigger)
3. Auto-implement Tier 1 enhancements (code changes, not just clones)
4. Wire Hermes inference (SOUL.md triggers)
5. Deploy AnythingMCP (gateway layer, lowest urgency)
