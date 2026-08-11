# Search Coverage Design — Domain Categories & Expansion Framework

> Extracted from `intelligence-pulse` SKILL.md Appendix to reduce file size. Referenced in the parent skill's ## Workflow section.

## Principle: Domain Categories, Not Strategic Buckets

**the operator's explicit preference (June 2026):** Don't lock search categories into rigid strategic-track silos. Name categories by the **domain they describe** (e.g., `fl_land_intel`, `govcon_c2c_intel`), not by which strategic bucket they serve. This keeps the monitoring flexible — findings can inform whatever the operator is working on today, and categories don't need renaming when priorities shift.

**Always include a wildcard catch-all category** (e.g., `opportunity_signals`) for things that don't fit predefined boxes. Rigid categories miss the most interesting signals — the curveball that doesn't match any existing search pattern but could accelerate things. The catch-all ensures every monitoring system has a "nothing fits here but it's interesting" escape valve.

## Audit Pattern: Inventory -> Categorize -> Expand

When asked to "expand search coverage" across an existing monitoring ecosystem:

1. **Inventory everything.** Run `cronjob(action='list')` to see ALL current jobs. Identify which ones do web searching (web_search in prompt, "web" in enabled_toolsets, gpt-researcher in skills, or explicit search queries in the prompt). Note each job's schedule, loaded skills, and toolsets.

2. **Identify gaps** by comparing current coverage against what the user cares about. Cross-reference each pipeline's search terms against stated priorities. Flag categories with zero coverage, not just thin coverage. Look for adjacent domains that connect naturally (e.g., FAR monitoring → GovCon/FedRAMP/SBIR).

3. **Every expansion gets three layers:** new domain queries (adjacent unsearched territories), sub-sector queries (deeper within existing categories), and explicit query examples in the prompt. Never just say "search for more" — specify the actual search strings so the next run has concrete direction.

4. **Rename rigid category labels.** If a pipeline uses "Track A"/"Track B"/"Pillar X" framing, rename categories to describe the **domain** being searched. Update the cron prompt to match. The weekly summary should report by what the findings ARE, not by what bucket they serve.

5. **Add the wildcard.** Every monitoring system needs one catch-all `opportunity_signals` category with broad, high-reach queries spanning: emerging tech, creative finance, grant funding, new consulting niches, AI automation plays, market gaps. No minimum relevance threshold — if it's interesting and doesn't fit elsewhere, it lands here.

## Pipeline Expansion Checklist

When updating a specific cron pipeline's search coverage:
- [ ] Read the current full prompt
- [ ] Identify what domains it currently covers
- [ ] List adjacent unsearched domains (at least 3-5 new query clusters)
- [ ] Write explicit web_search queries for each new cluster
- [ ] Add a wildcard category if one doesn't exist
- [ ] Update the delivery format to reflect new categories
- [ ] Add "No change = stay silent" if not already present
- [ ] Bump enabled_toolsets to include "web" if new queries need web_search
- [ ] Verify with session_search against past outputs to confirm freshness
- [ ] Verify config loads cleanly (dry-run for script-based monitors)

## Reference
- `references/search-coverage-expansion.md` — Full session transcript detailing a real expansion across 7 monitoring pipelines
