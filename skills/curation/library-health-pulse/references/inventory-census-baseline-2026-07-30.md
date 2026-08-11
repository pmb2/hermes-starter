# Inventory Census Baseline — July 30, 2026

Full-library census produced during a dedicated skills audit session.
Use as baseline for future Sweep K rounds.

## Top-Level Counts

| Metric | Count |
|--------|-------|
| Total skill directories on disk (all depths) | ~250+ |
| Top-level skill dirs | 94 |
| Skills with SKILL.md (active skills) | ~70+ |
| Category containers (no SKILL.md, contain sub-skills) | ~20 |
| Symlinked from `~/.agents/skills/` (imported) | 30 |
| Bundled per manifest (Apple platform) | 4 |
| Internal symlinks (within skills dir) | 6 |
| Skills with version numbers | ~40 |

## Source-Provenance Breakdown

### Symlinked from `~/.agents/skills/` (30 skills)
ask-matt, codebase-design, decision-mapping, design-an-interface, domain-modeling,
edit-article, git-guardrails-claude-code, grilling, improve-codebase-architecture,
request-refactor-plan, resolving-merge-conflicts, scaffold-exercises,
setup-matt-pocock-skills, setup-pre-commit, teach, to-issues, to-prd,
ubiquitous-language, writing-beats, writing-fragments, writing-shape,
migrate-to-shoehorn, svg-icon-best-practice, obsidian-vault,
higgsfield-game-generation, higgsfield-generate, higgsfield-marketplace-cards,
higgsfield-product-photoshoot, higgsfield-soul-id, higgsfield-video-explainer,
higgsfield-websites

### Bundled (per `.bundled_manifest`)
apple-notes, apple-reminders, findmy, imessage

### Internal Symlinks (within skills dir)
hermes-agent-skill-authoring -> software-development/hermes-agent-skill-authoring
native-mcp -> mcp/native-mcp
plan -> software-development/plan
project-documentation-standards -> software-development/project-documentation-standards
subagent-driven-development -> software-development/subagent-driven-development
systematic-debugging -> software-development/systematic-debugging
writing-plans -> software-development/writing-plans

## Domain Distribution

| Domain | Sub-skills | Notes |
|--------|-----------|-------|
| Software Development | ~62 | Largest domain. Under `software-development/` |
| DevOps & Infrastructure | ~50 | Under `devops/`. Includes cron, Docker, MCP, Firefox, backup, CI/CD |
| Security & OSINT | ~20 | Under `security/`. Full suite: cyber, OSINT, facial, property, social |
| Creative & Media | ~30 | Under `creative/` + `media/` |
| Website Building / Service Sites | ~15 | Scroll-world, Astro, home-service builders |
| Scroll-World (Higgsfield Pipeline) | ~7 | Dedicated scroll-world skills |
| Operations | ~11 | Under `operations/` |
| MLOps & Data Science | ~10 | Under `mlops/`, `data-science/` |
| Curation & Library Maintenance | ~4 | Under `curation/` |
| GitHub & VCS | ~6 | Under `github/` |
| Business & Lead Generation | ~12 | Under `business-development/`, `lead-generation/` |
| Real Estate & Land | ~9 | Under `market-lead/` |
| Legal | ~5 | Under `legal/` |
| Job Agent | ~10+ | Under `job-agent/` |
| FAL.ai Media Generation | ~5 | Under `fal-ai/` |
| MCP Servers | ~4 | Under `mcp/` |
| Productivity | ~18 | Under `productivity/` |
| Gaming | ~3 | Under `gaming/` |
| Research | ~13 | Under `research/` |
| Social Media | ~3 | Under `social-media/` |

## Quality Findings

### Curator State
- Last run: 2026-07-30T07:24:15 UTC
- Duration: 241s
- Run count: 9
- Last summary: "auto: 2 reactivated; llm: skipped (consolidation off)"
- `.bundled_manifest` contains only 4 Apple platform entries

### Known Cross-Reference Issues
- **Gstack dead links**: ~148 dead `related_skills` across 54 gstack-* skills — bare peer names without `gstack-` prefix
- **Consolidation dead links**: Old spacebar-*, mcp-server-onboarding → native-mcp, github-repo-management/codebase-inspection/codebase-hardening → github

### Versioning
- ~40 skills have explicit version numbers in frontmatter (range v1.0.0 to v3.11.3)
- ~30+ skills lack version fields entirely
- Most sub-skills in category containers lack versions

### Empty / Category-Only Directories
These directories exist as category containers with only DESCRIPTION.md (no SKILL.md):
data-engineering/, data-science/, design/, devops/, email/, finance/, media/,
mlops/, note-taking/, productivity/, market-lead/, research/, sales/, smart-home/,
ui-ux-pro-max/, site-generation/, autonomous-ai-agents/, business-development/
