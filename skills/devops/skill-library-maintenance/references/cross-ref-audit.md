# Cross-Reference Integrity Scan

## Purpose
Verify every `related_skills` entry in every SKILL.md resolves to an actual directory containing SKILL.md on disk. Catches stale refs from removed/renamed skills.

## Methodology

### 1. Build canonical skill name set
Walk all directories under `skills/` (excluding `.archive` and `.curator_backups`) to collect every skill name that has a SKILL.md.

### 2. Scan all SKILL.md frontmatter for related_skills
For each SKILL.md not in `.archive`, extract the YAML frontmatter and search for `related_skills: [...]`. Parse the list.

### 3. Compare against canonical set
Any referenced name not in the canonical set is a dead ref.

### 4. Remediate
- **Replace** with the correct existing skill name if one semantically fits
- **Remove** the entry if no equivalent skill exists
- **Fix archived skills** too — dead refs in `.archive` are cosmetic but should be cleaned on discovery

## Audit History

### 2026-07-11 — First full scan
- **331 SKILL.md files scanned** across all categories (active + .archive)
- **37 skills** with `related_skills` declared
- **112 unique cross-references** resolved
- **4 dead references found and fixed:**
  | Source Skill | Dead Ref | Fix |
  |---|---|---|
  | `computer-use` | `browser` (no exact match) | → `hermes-browser-internals` |
  | `local-website-prospecting` | `website-landlord-lead-gen` | removed (no equivalent) |
  | `.archive/open-source-prep` | `codebase-hardening` | removed (no equivalent) |
  | `.archive/foss-first-engineering` | `open-source-tool-research` | removed (no equivalent) |
- **Result**: 100% of active-skill related_skills now resolve.

### 2026-07-12 AM — Subdirectory symlink investigation (colliding skills)
- Attempted to fix 3 unresolvable subdirectory skills (`hermes-agent-skill-authoring`, `writing-plans`, `plan`) by creating top-level symlinks via `mklink /D`
- Symlinks resolved file access but **created name collisions** with skills in external_dirs at the same relative path — error shifted from "not found" to "ambiguous", skill remained unloadable
- Conclusion: external-dir collisions must be fixed by removing the duplicate (Option A or B), not by adding symlinks
- Documented as formal pitfalls in `skill-library-maintenance` v1.3.0

### 2026-07-12 PM — Subdirectory symlink audit (non-colliding skills resolved)
- 4 additional subdirectory skills identified as referenced via `related_skills` but lacking root-level access:
  | Skill | Category | related_skills refs |
  |---|---|---|
  | `subagent-driven-development` | `software-development/` | 13 |
  | `systematic-debugging` | `software-development/` | 20 |
  | `project-documentation-standards` | `software-development/` | 11 |
  | `native-mcp` | `mcp/` | 12 |
- **3 safe to symlink** — `subagent-driven-development`, `systematic-debugging`, `native-mcp` have no external-dir collision, symlinks resolve cleanly
- **1 risk case** — `project-documentation-standards` IS in the external-dir collision table (Step 8); symlink created anyway and verified resolving — monitor for ambiguous-skill errors
- **Result**: All 4 symlinks accessible. 30 total symlinks now in skills root (26 external + 4 local).
