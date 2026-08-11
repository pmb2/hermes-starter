# AI Ecosystem Scanning — Bleeding-Edge Research via arXiv + GitHub

## Purpose

When generic web searches return SEO-optimized marketing content (old, well-known, surface level), use academic and open-source APIs for genuine bleeding-edge signal. This applies to any monitoring pulse that tracks AI/ML developments.

## Source Hierarchy

### Tier 1: arXiv (Academic Papers)
arXiv returns actual research — not blog posts. Papers appear 24-48h after submission. Use the REST API with targeted search queries per frontier area.

**Script:** `${USER_HOME}/AppData/Local/hermes/scripts/ai_ecosystem_scan.py`
- Self-contained Python stdlib (no pip deps)
- Searches 8 frontier categories per run
- Respects arXiv rate limits (1 req / 3.5s)
- Each query sorted by `submittedDate` descending

**8 frontier search categories:**
1. Agent Frameworks & Tool Calling — `cat:cs.AI+AND+ti:agent+OR+ti:tool+OR+ti:orchestration+ANDNOT+ti:medical+ANDNOT+ti:robotic`
2. LLM Reasoning & RL — `ti:reasoning+AND+ti:language+model+OR+ti:reinforcement+learning+AND+cat:cs.LG`
3. Fine-Tuning (GRPO/DPO/RLHF) — `ti:fine-tuning+AND+ti:RL+OR+ti:DPO+OR+ti:GRPO+OR+ti:preference+AND+cat:cs.LG`
4. Model Architecture (MoE/Sparse) — `ti:mixture+of+experts+OR+ti:sparse+OR+ti:quantization+OR+ti:distillation+AND+cat:cs.LG`
5. Context & Inference Optimization — `ti:context+AND+ti:window+OR+ti:inference+AND+ti:optimization+AND+cat:cs.CL`
6. AI Coding & Software Engineering — `ti:code+generation+AND+ti:agent+OR+ti:program+repair+OR+ti:software+engineering+AND+cat:cs.SE`
7. Multi-Agent Systems — `ti:multi-agent+OR+ti:multiagent+AND+cat:cs.AI+AND+cat:cs.MA`
8. Safety & Alignment — `ti:safety+AND+ti:alignment+OR+ti:jailbreak+OR+ti:red+teaming+AND+cat:cs.AI`

### Tier 2: GitHub Trending API
GitHub's search API returns actual trending repos sorted by stars. Catches tools before blog posts exist.

Query: `https://api.github.com/search/repositories?q=ai+llm+agent+framework&sort=stars&order=desc&per_page=10`

### Tier 3: Research Institution Blogs (LLM-driven pulse only)
When an LLM is synthesizing the output, check at least 2 of:
- Hacker News (front page for AI/ML titles)
- LMSys blog (model rankings, Chatbot Arena)
- OpenAI Research blog
- Simon Willison's AI tag (practical tool coverage)

### Tier 4: Targeted Web Search (last resort)
Only for things the above sources miss (pricing changes, closed-source releases).

## Scoring & Tiering

Apply Boss Radar rubric (see `boss-radar-scoring.md`):
- 0.70+ TIER 1 — Directly applicable. Auto-execute (clone repo, download paper, install tool).
- 0.40-0.69 TIER 2 — Worth watching. Flag in delivery.
- Below 0.40 — Skip entirely.

**Calibration note:** arXiv papers lack name-bonus keywords that inflate Trump/KB scores. A paper at 0.65 is roughly equivalent to a Trump finding at 0.85. Adjust thresholds accordingly.

## Rate Limits

| API | Limit | Notes |
|-----|-------|-------|
| arXiv | 1 req / 3s | Returns XML. No auth needed. |
| GitHub (unauthed) | 60 req / hr | Use `User-Agent` header. |
| Semantic Scholar | 1 req / s | 100 req/s with API key. |

## Key Technique: script over inline-prompt

Do NOT embed long Python parsing snippets inside cron prompts — they break on special characters, newlines, and quote nesting. Instead:
1. Write a standalone Python script (`ai_ecosystem_scan.py`) with all parsing logic
2. Reference the script path in the cron prompt
3. The cron job runs `python <path>` and gets clean output
4. The LLM (if present) synthesizes the output rather than dumping it raw

## References

- arXiv API docs: https://info.arxiv.org/help/api/index.html
- GitHub Search API: https://docs.github.com/en/rest/search
- Skill's script: `${USER_HOME}/AppData/Local/hermes/scripts/ai_ecosystem_scan.py`
