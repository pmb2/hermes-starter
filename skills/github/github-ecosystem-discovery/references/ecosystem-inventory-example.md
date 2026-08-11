# Ecosystem Inventory Reference

> **Concrete output from the `github-ecosystem-discovery` workflow**  
> Generated: 2026-07-26  
> Source parent directory: `${MY_REPOS}\Documents\github\` + additional workspaces

## Scope

Repos discovered across:
- `${MY_REPOS}\Documents\github\` — 130 directories (main workspace)
- `${USER_HOME}\buzz\` — block/buzz (Nostr/AT social platform)
- `${USER_HOME}\OmniRoute\` — Free AI gateway
- `${USER_HOME}\AppData\Local\hermes\hermes-agent\` — NousResearch upstream + pmb2 fork

## Categorization

| Category | Count |
|----------|-------|
| Owned repos (pmb2/*) | ~42 |
| Third-party repos | ~95 |
| Local-only (no remote) | ~15 |
| **Total** | **152** |

## Owner Breakdown

| Owner | Count | Key Projects |
|-------|-------|-------------|
| **pmb2** (the operator) | 42 | hermes-config, agent-fleet, agent-universe, OSINT-agent, legal-team, GHL, solumina-agent, website-landlord, the planning repo |
| **NousResearch** | 1 | hermes-agent (upstream) |
| **Microsoft** | 1 | playwright-mcp |
| **OpenAI** | 1 | openai-agents-python |
| **GitHub** | 1 | github-mcp-server |
| **langchain-ai** | 2 | langchain, langgraph |
| **Others** | ~60+ | Various starred/exploratory forks |
| **Local-only** | ~15 | Configs, experiments, WIP |

## Key Categories

### Core Infra
- hermes-agent, hermes-config, model-gateway, 9router-v2, OmniRoute, Hermes-router
### Multi-Agent
- agent-fleet, agent-universe, AI-Scientist, PraisonAI, SuperAGI, MetaGPT
### OSINT/Security
- OSINT-agent, legal-team, hexstrike-ai, spiderfoot, relay-pool
### Business
- solumina-agent, auto-resume, GHL, website-landlord, legal-team
### Service Sites
- constructManage, mobile-mechanic, car-detailing
### the planning repo
- the planning repo, councilOS
### Content
- yt-animation, bookends, ComfyUI

## Key Remote Extraction Commands Used

```bash
# Batch all remotes at once
for d in ${MY_REPOS}/*/; do
  echo "=== $(basename "$d") ==="
  (cd "$d" && git remote -v 2>/dev/null | head -2)
  echo
done

# README skim
cat /path/to/repo/README.md 2>/dev/null | head -10
```

## Notes

- `_docs/` is a large local documentation archive (NOT a git repo) containing 90+ tool evaluations, research notes, architecture docs
- Several directories (logs/, scripts/, sales/) are config-only, not repos
- `bch-lotto` repo has dual remotes: `origin` = `pmb2/BurnBounty`, `legacy-bch-collections` = `pmb2/bch-collections`
