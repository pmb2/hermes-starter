# Metadata.Hermes Audit Methodology

Systematic scan for skills lacking `metadata.hermes` blocks, run during Skillmate pulses.

## Quick Count

```bash
cd ~/AppData/Local/hermes/skills

# Count active skills (excluding .archive)
active_skills=$(find . -maxdepth 3 -path './.archive' -prune -o -name SKILL.md -type f -print | wc -l)

# Count skills WITH metadata.hermes
meta_skills=$(find . -maxdepth 3 -path './.archive' -prune -o -name SKILL.md -type f -print0 | xargs -0 grep -l "metadata\.hermes" 2>/dev/null | wc -l)

# Count skills without
without_meta=$((active_skills - meta_skills))

echo "Active: $active_skills | With metadata.hermes: $meta_skills | Without: $without_meta ($(( without_meta * 100 / active_skills ))%)"
```

> **Note:** `grep -l` checks the entire file, not just frontmatter. A skill that mentions `metadata.hermes` in its body text (e.g. as a reference) will be counted as having it. Cross-check with the YAML-based scan (Section 7a) for precise results.

## Full Metadata Gap Scan (YAML-Aware)

Run the Section 7a detection script from SKILL.md to distinguish:
- **No metadata.hermes at all** — needs full block
- **Has metadata.hermes but no triggers** — needs triggers only
- **Clean** — has both

## Historical Baseline (2026-07-13)

| Metric | Value |
|--------|-------|
| Active skills | 302 |
| With `metadata.hermes` block | 302 (100%) |
| Without | 0 |
| Largest skill | market-lead/land-wholesaling, productivity/intelligence-pulse, gstack-ship, gstack-plan-devex-review, gstack-plan-design-review (92KB each) |
| Skills over 95KB | 0 |
| Name/directory mismatches (non-gstack) | 7 — 4 job-agent, 3 mlops — flagged 2026-07-13 by Section 7c scan |
| Gstack naming convention mismatches | 53 — deliberate, not a bug |

### Previous Baseline (retired 2026-07-13)

Prior to the Jul 13 frontmatter audit blitz, the baseline was:

| Metric | Value |
|--------|-------|
| Active skills | 291 |
| With `metadata.hermes` block | 3 (skill-library-maintenance, gstack-hermes-upgrade, hermes-agent-skill-authoring) |
| Without | 288 (99%) |
| Largest skill | gstack-plan-design-review (93.5KB) |
| Skills over 95KB | 0 |
| NO_TRIGGERS (has metadata.hermes but no triggers) | 0 — resolved Jul 13 (`thread-continuity-recovery` patched) |

## When to Run

- Every Skillmate pulse check
- After any external agent activity (curator passes, multi-agent editing)
- After installing new skills from hub or external dirs

## Recommended Action Levels

| Without count | Severity | Action |
|--------------|----------|--------|
| 0 | 🟢 None | All clear |
| 1-10 | 🟡 Low | Individual fixes during pulse |
| 10-50 | 🟡 Medium | Phased backfill by category |
| 50+ | 🔴 High | Bulk backfill script (Section 10) |
