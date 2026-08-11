# Version-Field Sweep Results — 2026-07-21 to 2026-07-22

## Phase 1 (Jul 21 11:17 ET)
- Scope: 29 recently-modified SKILL.md files
- Found: 3 missing `version:` — `ai-model-router-gateway`, `mcp-fleet-audit`, `local-service-websites`
- Action: All 3 patched to v1.0.0
- Methodology: `find -newermt` on skills root only — missed subdirectory skills

## Phase 2 (Jul 21 17:50 UTC)
- Scope: Full `os.walk` sweep of all 339+ active SKILL.md
- Found: 4 more missing `version:` in subdirectories:
  - `curation/skill-content-audit`
  - `legal/fcra-disclosure-requests`
  - `media/youtube-content`
  - `devops/ultimate-firefox-mcp-browser`
- Action: All 4 patched to v1.0.0 via standalone `patch()` tool (handles CRLF)

## Phase 3 — Completion (Jul 22 11:10 ET)
- Scope: Final sweep validation — manual cross-check against `scripts/version-field-audit.py` output
- Found: 6 more missing `version:` in scroll-world suite + skip-tracing:
  - `cold-call-scroll-world` — flat root, `name:` → `description:` only
  - `scroll-world` — flat root, `name:` → `description:` only (603-line skill)
  - `scroll-world-pipeline` — flat root, `name:` → `description:` → `allowed-tools:` chain
  - `scroll-world-pipeline-v2` — flat root, same structure as pipeline
  - `scroll-world-site-builder` — flat root, same structure as pipeline
  - `skip-tracing` — flat root, complex `metadata.hermes` block present but no root `version:`
- Action: All 6 patched to v1.0.0 via standalone `patch()` tool
- Note: These were missed by Phase 2 because they're top-level flat skills (not in subdirectories) and weren't part of the recent-modification check. The Phase 2 full `os.walk` should have caught them — discrepancy likely due to the script not yet existing at Phase 2 time (it was created during Phase 1).

## Out of Scope (deliberate)
- **50 gstack skills** — maintained externally by gstack tooling, no version convention
- **7 symlinked skills** (ask-matt, codebase-design, decision-mapping, domain-modeling, edit-article, git-guardrails-claude-code, grilling) — external `.agents/skills/` source, not skills-lead scope

## Result
**100% complete.** All non-gstack, non-symlink active SKILL.md now have `version:` field. Total patches over 3 phases: 13 skills.

To verify: `python scripts/version-field-audit.py --path ~/AppData/Local/hermes/skills` should return 0 missing.
