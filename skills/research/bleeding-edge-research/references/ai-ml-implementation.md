# AI/ML Ecosystem Implementation

This reference documents the specific AI/ML-focused implementation of the bleeding-edge research scanning methodology, including the scoring/tier system, auto-action handler, and FOSS gap tracking patterns built into the operator's Hermes agent.

## Scoring Keywords (Per Category)

These keyword lists are used for relevance scoring (0.0-1.0) in `ai_ecosystem_scan.py`:

```python
CATEGORY_KEYWORDS = {
    "agent_frameworks": [
        "agent", "tool-calling", "tool calling", "orchestration", "MCP", "A2A",
        "function calling", "multi-agent", "agentic", "tool use", "tool-use",
        "agent framework", "agent platform", "reasoning agent", "code agent"
    ],
    "llm_reasoning": [
        "reasoning", "chain-of-thought", "chain of thought", "reinforcement learning",
        "RL", "test-time compute", "test time compute", "self-play", "self play",
        "CoT", "system 2", "thinking", "deep search", "monte carlo tree search",
        "MCTS", "process reward", "PRM", "outcome reward", "ORM", "verifier"
    ],
    "fine_tuning": [
        "GRPO", "DPO", "RLHF", "preference optimization", "fine-tuning", "fine tuning",
        "SFT", "reward model", "reinforcement learning from human", "PPO",
        "direct preference", "constitutional AI", "instruction tuning"
    ],
    "model_architecture": [
        "mixture of experts", "MoE", "sparse", "quantization", "distillation",
        "efficient", "attention", "transformer", "diffusion", "state space",
        "Mamba", "hybrid", "multi-modal", "multimodal", "embedding"
    ],
    "context_inference": [
        "context window", "inference optimization", "KV cache", "token compression",
        "speculative decoding", "prompt compression", "inference speed",
        "model serving", "batch inference", "continuous batching", "prefix caching",
        "attention optimization", "long context", "context length"
    ],
    "ai_coding": [
        "code generation", "code agent", "program repair", "software engineering",
        "SWE-bench", "coding agent", "code review", "code completion",
        "repository", "pull request", "issue resolution", "debug"
    ],
    "multi_agent": [
        "multi-agent", "multiagent", "agent collaboration", "agent communication",
        "swarm", "agent society", "agent protocol", "cooperative", "delegation",
        "agent coordination", "agent network", "agent-to-agent"
    ],
    "safety_alignment": [
        "alignment", "safety", "jailbreak", "red teaming", "adversarial",
        "guardrail", "constitutional", "harmlessness", "bias", "fairness",
        "evaluation", "benchmark", "interpretability", "mechanistic interpretability"
    ],
}
```

## arXiv Search Queries (8 Frontier Categories)

| # | Category | Query |
|---|----------|-------|
| 1 | Agent Frameworks | `cat:cs.AI+AND+ti:agent+OR+ti:tool+OR+ti:orchestration+ANDNOT+ti:medical+ANDNOT+ti:robotic+ANDNOT+ti:health` |
| 2 | LLM Reasoning & RL | `ti:reasoning+AND+ti:language+model+OR+ti:reinforcement+learning+AND+cat:cs.LG` |
| 3 | Fine-Tuning (GRPO/DPO/RLHF) | `ti:fine-tuning+AND+ti:RL+OR+ti:DPO+OR+ti:GRPO+OR+ti:preference+AND+cat:cs.LG` |
| 4 | Model Architecture (MoE/Sparse) | `ti:mixture+of+experts+OR+ti:sparse+OR+ti:quantization+OR+ti:distillation+AND+cat:cs.LG` |
| 5 | Context & Inference | `ti:context+AND+ti:window+OR+ti:inference+AND+ti:optimization+AND+cat:cs.CL` |
| 6 | AI Coding & SE | `ti:code+generation+AND+ti:agent+OR+ti:program+repair+OR+ti:software+engineering+AND+cat:cs.SE` |
| 7 | Multi-Agent Systems | `ti:multi-agent+OR+ti:multiagent+AND+cat:cs.AI+AND+cat:cs.MA` |
| 8 | Safety & Alignment | `ti:safety+AND+ti:alignment+OR+ti:jailbreak+OR+ti:red+teaming+AND+cat:cs.AI` |

## Auto-Action Handler Architecture

The companion `auto_action_handler.py` runs as a `no_agent=true` cron job every 6 hours:

### Input Sources
- `ai_ecosystem_findings.json` — scored findings from the ecosystem scanner
- `latest.json` + `history.jsonl` — monitoring pipeline findings (FL land, GovCon, opportunities)

### Tier-Based Processing
- **TIER 1:** Clone repos → `git clone --depth=1` to `${MY_REPOS}/Documents/github/` + pip install
- **TIER 1:** Download papers → `curl` to `${MY_REPOS}/Documents/research/papers/`
- **TIER 1:** Log opportunities to `research/opportunities.md`
- **TIER 2:** Research notes to `research/ai_ecosystem_notes.md`
- **TIER 3:** Ignored

### State Management
- `auto_action_state.json` tracks `actioned_fps` (last 1000) and `noted_fps` (last 200)
- Dedup prevents re-executing already-handled findings
- Empty stdout = silent (nothing actionable)

## FOSS TIER 1 Tracker

Tracked in `${MY_REPOS}/Documents/github/hermes-config/docs/FOSS_TIER1_TRACKER.md`:

### Structure
```
| Finding | Source | FOSS Available? | Built into Hermes? | Gap/Notes |
```
- **✅ Built:** FOSS repo exists and was cloned to ${MY_REPOS}/Documents/github/
- **🔍 Gap:** arXiv paper with no FOSS implementation — logged with priority ranking
- **🚫 Gap:** Paper with no clear build path (domain-specific, requires infrastructure)

### High-Priority Build Recommendations (from Jun 25 scan)
1. Autodata-style synthetic data agent — build as Hermes skill
2. Cross-Lingual Token Arbitrage — context compression script
3. Adaptive Multi-Agent Scaffolding — orchestration for Codex/Claude Code
4. Bayesian Control for Coding Agents — probabilistic tool-use decisions

## Scripts

- `ai_ecosystem_scan.py` — Full scanner with scoring/tier system (8 categories + GitHub + new repos)
- `auto_action_handler.py` — TIER 1 executor consuming scored JSON

## Cron Jobs

| ID | Name | Schedule | Type | Purpose |
|----|------|----------|------|---------|
| 880cccff88fe | AI/ML Ecosystem Pulse | every 6h | LLM-driven | Runs scanner + synthesizes brief + FOSS gap tracking |
| 9843a00bd786 | Auto-Action Handler | every 6h | no_agent | Silent TIER 1 executor (clone, download, log) |
