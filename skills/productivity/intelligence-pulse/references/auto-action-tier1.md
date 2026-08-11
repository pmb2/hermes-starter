# references/auto-action-tier1.md

## Auto-Action on TIER 1 Findings

When a monitoring or intelligence finding scores TIER 1 (>= 0.70 or equivalent), execute the appropriate action automatically.

### Script: `auto_action_handler.py`

Located at `${USER_HOME}/AppData/Local/hermes/scripts/auto_action_handler.py`

A no_agent cron script that:
1. Reads findings from the monitoring pipeline (latest.json + history.jsonl)
2. Pattern-matches URLs and keywords against action templates
3. Executes the appropriate action (clone, download, log)
4. Dedups via state file (auto_action_state.json)
5. Reports what was done

**Action patterns:**
- GitHub URL → `git clone --depth=1` to `${MY_REPOS}/Documents/github/` + `pip install -e` if applicable
- arXiv URL → download PDF to `${MY_REPOS}/Documents/research/papers/<id>.pdf`
- GovCon/FL Land opportunity keywords → log to `${MY_REPOS}/Documents/research/opportunities.md`
- Tool/package name → pip install + import smoke test

### For LLM-Driven Pulses (AI Ecosystem)

When the LLM identifies a TIER 1 finding during synthesis, it should execute the action using terminal tools directly — not wait for the handler script.

### Dedup

Track by fingerprint (`action_type:target`) in `auto_action_state.json`. Never re-execute.

### Cron

Registered as `Auto-Action Handler — TIER 1 finding executor` (every 360m, no_agent).
