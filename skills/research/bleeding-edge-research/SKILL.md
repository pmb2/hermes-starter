---
name: bleeding-edge-research
description: "Systematic scanning of academic sources (arXiv, Semantic Scholar), open-source repositories (GitHub API), and curated research venues to surface cutting-edge papers, models, tools, and frameworks before they become widely known."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [research, arxiv, semantic-scholar, github, papers, academic, bleeding-edge, frontier]
    triggers: [bleeding-edge, cutting-edge, research-papers, frontier-research, whats-new-in-ai, new-papers, arxiv-scan]
    related_skills: [arxiv, intelligence-pulse, gpt-researcher]
---

# Bleeding-Edge Research

**Purpose:** Discover cutting-edge developments in any technical field by systematically scanning academic preprints, open-source repositories, and research venue blogs — before they reach mainstream awareness.

## When to Load

- A cron pulse needs to monitor frontier research (AI, ML, agents, systems, security, etc.)
- The user asks "what's new in X" or "anything interesting on arXiv" or "what papers came out this week on Y"
- You need to assess the state of the art for a specific niche (e.g., "what's the latest on multi-agent orchestration")
- The user wants to know what open-source tools or repos are gaining traction

## Source Hierarchy (use in order)

### Tier 1: arXiv API (primary source for preprints)
arXiv has papers within hours of submission. Use the REST API — no key needed, ~1 req/3s rate limit.

**General formula:**
```bash
curl -s "https://export.arxiv.org/api/query?search_query=SEARCH_QUERY&sortBy=submittedDate&sortOrder=descending&max_results=N"
```

**Parse with (use `python` not `python3` on Windows):**
```bash
curl -s "URL" | python -c "
import sys, xml.etree.ElementTree as ET
ns = {'a': 'http://www.w3.org/2005/Atom'}
root = ET.parse(sys.stdin).getroot()
for e in root.findall('a:entry', ns):
    title = e.find('a:title', ns).text.strip().replace(chr(10), ' ')[:120]
    aid = e.find('a:id', ns).text.strip().split('/abs/')[-1]
    pub = e.find('a:published', ns).text[:10]
    authors = ', '.join(a.find('a:name', ns).text.split()[-1] for a in e.findall('a:author', ns))[:80]
    print(f'  [{pub}] {title}')
    print(f'   {authors}')
    print(f'   https://arxiv.org/abs/{aid}')
"
```

**Category prefixes:**
- `cat:cs.AI` — Artificial Intelligence
- `cat:cs.LG` — Machine Learning
- `cat:cs.CL` — Computation and Language (NLP)
- `cat:cs.CV` — Computer Vision
- `cat:cs.SE` — Software Engineering
- `cat:cs.CR` — Cryptography/Security
- `cat:cs.MA` — Multi-Agent Systems

**Field prefixes:** `ti:` (title), `au:` (author), `abs:` (abstract), `all:` (all fields)

**Boolean:** `AND` (default with +), `OR`, `ANDNOT`, quoted phrases with `+`

**Targeted queries for frontier topics:**
- Agent frameworks: `cat:cs.AI+AND+ti:agent+OR+ti:tool+OR+ti:orchestration+ANDNOT+ti:medical+ANDNOT+ti:robotic`
- LLM reasoning: `ti:reasoning+AND+ti:language+model+OR+ti:reinforcement+learning+AND+cat:cs.LG`
- Fine-tuning (GRPO/DPO): `ti:fine-tuning+AND+ti:RL+OR+ti:DPO+OR+ti:GRPO+AND+cat:cs.LG`
- MoE/sparse/efficient: `ti:mixture+of+experts+OR+ti:sparse+OR+ti:quantization+AND+cat:cs.LG`
- Context/inference: `ti:context+AND+ti:window+OR+ti:inference+AND+ti:optimization+AND+cat:cs.CL`
- AI coding: `ti:code+generation+AND+ti:agent+OR+ti:program+repair+AND+cat:cs.SE`
- Multi-agent: `ti:multi-agent+OR+ti:multiagent+AND+cat:cs.AI+AND+cat:cs.MA`
- Safety/alignment: `ti:safety+AND+ti:alignment+OR+ti:jailbreak+OR+ti:red+teaming+AND+cat:cs.AI`

### Tier 2: Semantic Scholar (citations, impact, recommendations)
Provides citation counts, influential citations, related papers, and author profiles. Free, no key, 1 req/s.

- Paper details: `https://api.semanticscholar.org/graph/v1/paper/arXiv:ID?fields=title,citationCount,influentialCitationCount`
- Citations (who cited it): `https://api.semanticscholar.org/graph/v1/paper/arXiv:ID/citations?fields=title,year&limit=10`
- References (what it cites): `https://api.semanticscholar.org/graph/v1/paper/arXiv:ID/references?fields=title,citationCount&limit=10`
- Search: `https://api.semanticscholar.org/graph/v1/paper/search?query=TOPIC&limit=5`
- Author search: `https://api.semanticscholar.org/graph/v1/author/search?query=NAME`

Use Semantic Scholar to assess impact — a paper with 0 citations 2 weeks out may be a dud; one with 50+ citations on day 1 is a breakout.

### Tier 3: GitHub API (trending repos and new projects)
The search API catches fresh repos that academic sources miss.

```bash
# Most-starred in topic
curl -s "https://api.github.com/search/repositories?q=ai+agent+framework&sort=stars&order=desc&per_page=10"

# New repos this week with traction
curl -s "https://api.github.com/search/repositories?q=created:>YYYY-MM-DD+topic:ai&sort=stars&order=desc&per_page=10"
```

### Tier 4: Research Venue Blogs
Check for publications, model cards, and technical blog posts:

- [Hacker News](https://news.ycombinator.com/) — scan front page for relevant keywords
- [LMSys Blog](https://lmsys.org/blog/) — Chatbot Arena rankings, model evaluations
- [OpenAI Research](https://openai.com/research/) — new papers, model cards
- [Anthropic Research](https://anthropic.com/research) — safety, alignment, new models
- [Simon Willison's AI](https://simonwillison.net/tags/ai/) — practical AI tool coverage
- [Stratechery](https://stratechery.com/) — AI business model analysis
- Field-specific venues (e.g., for CV check PapersWithCode, for NLP check ACL Anthology)

## How to Build a Scanning Cron Job

A complete bleeding-edge pulse cron prompt:

1. **Primary:** Run a field-specific scanner script that queries arXiv across N targeted sub-topics + GitHub trending
2. **Secondary:** `web_extract` 2-3 research venue blogs for things the scanner misses
3. **Score + Tier:** Each finding gets a relevance score 0.0-1.0 via keyword matching, then classified into TIER 1 (≥0.40, actionable), TIER 2 (≥0.20, notable), TIER 3 (<0.20, skip)
4. **Auto-Action on TIER 1:** Clone GitHub repos (`git clone --depth=1`), download arXiv PDFs, install pip packages, log opportunities. TIER 2 gets research notes.
5. **FOSS Gap Tracking:** For each TIER 1 paper without a FOSS implementation, log the gap in a tracker file (see FOSS_TIER1_TRACKER.md pattern)
6. **Output JSON:** Write structured JSON to a findings file so downstream `no_agent` cron jobs can consume it without re-scanning
7. **Deliver:** Only surface TIER 1 and TIER 2 human-readable summary. Silent if nothing actionable.

### Scoring Methodology

Score each finding 0.0-1.0 using category-specific keyword matching:

```
def score_finding(title, category_keywords):
    title_lower = title.lower()
    matches = sum(1 for kw in category_keywords if kw.lower() in title_lower)
    return min(1.0, matches / max(1, len(category_keywords) * 0.15))
```

**Keyword lists per category** (store as a dict in the scanner script):

| Category | Example Keywords |
|----------|-----------------|
| Agent Frameworks | `agent`, `tool-calling`, `orchestration`, `MCP`, `A2A`, `multi-agent`, `function calling`, `agentic` |
| LLM Reasoning | `reasoning`, `chain-of-thought`, `reinforcement learning`, `RL`, `test-time compute`, `self-play` |
| Fine-Tuning | `GRPO`, `DPO`, `RLHF`, `preference optimization`, `fine-tuning`, `SFT`, `reward model` |
| Model Architecture | `mixture of experts`, `MoE`, `sparse`, `quantization`, `distillation`, `state space` |
| Context/Inference | `context window`, `inference optimization`, `KV cache`, `token compression`, `speculative decoding` |
| AI Coding | `code generation`, `code agent`, `SWE-bench`, `coding agent`, `program repair` |
| Multi-Agent | `multi-agent`, `multiagent`, `agent collaboration`, `swarm`, `agent protocol` |
| Safety/Alignment | `alignment`, `safety`, `jailbreak`, `red teaming`, `guardrail`, `adversarial` |

### TIER Thresholds

- **TIER 1 (≥0.40):** Auto-execute — clone repos, download papers, install packages, log opportunities
- **TIER 2 (≥0.20):** Research note only — log for review, don't execute
- **TIER 3 (<0.20):** Skip entirely

**GitHub popularity boost:** Repos with 2000+ stars and partial relevance get TIER 1 automatically. NEW repos (<7 days) with 100+ stars get TIER 2, with 500+ stars get TIER 1.

### Structured JSON Output Format

Write scored findings to a JSON file consumable by `no_agent` cron jobs:

```json
{
  "fingerprint": "arxiv:2606.20529v1",
  "headline": "LedgerAgent: Structured State for Policy-Adherent Tool-Calling Agents",
  "url": "https://arxiv.org/abs/2606.20529v1",
  "date": "2026-06-18",
  "category": "agent_frameworks",
  "relevance_score": 0.85,
  "tier": 1,
  "source": "arxiv",
  "authors": "Uddin, Saeidi, Blanco, Baral"
}
```

Same structure for GitHub repos with `source: "github"` and additional fields like `stars` and `language`. Maintain a history JSONL file for dedup.

### Auto-Action Handler Pattern

Build a companion `no_agent` silent cron that reads the scored JSON and executes TIER 1 actions:

1. **Clone repos:** `git clone --depth=1 <url> /path/to/github/` + try `pip install -e .` if setup.py exists
2. **Download papers:** `curl -o /path/to/papers/<id>.pdf https://arxiv.org/pdf/<id>`
3. **Log opportunities:** Append to `opportunities.md` with tier/score attribution
4. **Research notes:** Log TIER 2 findings to a notes file
5. **State management:** Track `actioned_fps` and `noted_fps` in a JSON state file to prevent re-execution
6. **Dedup:** Check already-actioned fingerprints before executing — skip if already done

The handler stays silent (no stdout) when nothing is actionable. Reports only when actions were taken.

### FOSS Gap Tracking

After scanning, for each TIER 1 paper that is arXiv-only (no GitHub implementation):

1. Search GitHub for the paper's technique/keywords
2. If a FOSS implementation exists, clone it
3. If none exists, log the gap in a FOSS_TIER1_TRACKER.md with priority ranking
4. The cron prompt should include this as a mandatory step (update the prompt when adding tracking)

### Source Priority Rules
- arXiv papers > blog posts (papers are original research, blogs are commentary)
- GitHub repos with traction > repos without (stars/week as proxy)
- Today's papers > this week's papers (each day's arXiv dump resets the frontier)
- Open source > proprietary (the operator can try/use open source now)

### Pitfalls
- **arXiv rate limit:** ~1 request per 3 seconds. Batch queries with a 3.5s sleep between them. The API returns HTTP 429 if you exceed this.
- **python3 vs python:** On Windows (git-bash), `python3` is often unavailable. Use `python`.
- **GitHub API rate limit:** 60 req/hr unauthenticated, 5000 req/hr with token. For cron use, add a `GITHUB_TOKEN` env var.
- **arXiv ID versioning:** The API returns the latest version URL (e.g., `2606.20529v1`). For citations, preserve the version suffix to prevent citation drift.
- **Withdrawn papers:** Always check the `<summary>` field for withdrawal/retraction notices before treating a paper as valid.
- **Semantic Scholar latency:** Sometimes slow (5-10s). Use 15s timeout and skip gracefully on failure.
- **Latest.json overwrite:** If scanning multiple sub-topics one at a time, each run replaces the output file. Either run all queries in a single script (like ai_ecosystem_scan.py does) or aggregate from history files.

## Script

`scripts/ai_ecosystem_scan.py` — A complete AI/ML ecosystem scanner that runs 8 targeted arXiv queries + 1 GitHub search with rate-limit handling and XML parsing. Runs in ~60s. Copy and modify for other fields (change arXiv categories and GitHub search queries).
