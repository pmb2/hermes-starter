# Worked Example: E: Clone Skills Retirement — Restore (2026-08-02)

## Incident

Scribe pulse (2026-08-02 01:43 UTC) found the E: hermes-config clone (`vps-hybrid`
branch, stale at `ce9b1d0`) with **76 uncommitted deleted files / 17,012 lines**
in its working tree. The `skills/` tree had been `mv`'d into untracked
`skills.retired-2026-08-02/` (39 SKILL.md files) by an unknown process — an
uncommitted retirement move, not data loss.

Danger: the retired set included **unique live skills with NO local copy**:
`hermes-agent-skill-authoring`, `writing-plans`, `subagent-driven-development`,
`test-driven-development`, `systematic-debugging`, `requesting-code-review`,
`project-documentation-standards`, `plan`, `github-auth`, `github-pr-workflow`,
`github-project-documentation`, `personal-knowledge-ingestion`, `github-issues`,
`github-repo-management`, `codebase-hardening`, `codebase-inspection`,
`portfolio-documentation`, `mcp-service-extension`. These are the exact
Jul 31 loader-failure class — if the deletion had been committed and synced to
the canonical clone, the skill loader would have skipped them.

## Diagnostic Sequence (what worked)

```bash
# 1. Establish clone topology FIRST
cd ${USER_HOME}/Documents/github/hermes-config   # canonical (external_dirs, master)
git branch --show-current && git log --oneline -2 && git status --short | head
# -> CLEAN at c22cc68. Incident is NOT here.

cd ${MY_REPOS}/hermes-config  # stale (vps-hybrid)
git status --short | grep '^ D' | wc -l          # 76 deleted
git status --short | grep '^??'                  # untracked retirement dir exists
# -> skills.retired-2026-08-02/ = the moved files. Nothing lost.

# 2. Check for local copies before restoring (unique-live-skill test)
for s in hermes-agent-skill-authoring writing-plans subagent-driven-development \
         plan mcp-service-extension; do
  find ${USER_HOME}/AppData/Local/hermes/skills -name "$s" -type d 2>/dev/null \
    || echo "NO-LOCAL-COPY: $s"
done

# 3. Restore ONLY deleted tracked files
cd ${MY_REPOS}/hermes-config
git diff --name-only --diff-filter=D | xargs git checkout --

# 4. Verify
git status --short | grep -c '^ D'               # -> 0
for f in skills/software-development/hermes-agent-skill-authoring/SKILL.md \
         skills/software-development/writing-plans/SKILL.md \
         skills/software-development/subagent-driven-development/SKILL.md \
         skills/README.md; do
  [ -f "$f" ] && echo "OK: $f" || echo "MISSING: $f"
done
```

## Key Decisions

- **Restored** the ` D` files instead of committing the retirement — the move was
  uncommitted, included unique live skills, and the canonical C: clone still
  served them. Restoring to HEAD is the conservative documentation-integrity fix.
- **Left the retirement archive untouched** (`skills.retired-2026-08-02/` stayed
  untracked) — nothing lost either way, and the archive is evidence for the
  ownership decision.
- **Left in-flight work untouched** — untracked memory-layer docs
  (`docs/architecture/HERMES_MEMORY_ENHANCEMENT_PLAN.md`, `PGGRAPH_INTEGRATION.md`,
  `infra/pggraph/`, `config/memory/`, `scripts/pggraph-mcp/`) were recent (48h)
  and not Scribe's scope to commit.

## Outcome

- E: `skills/` back to HEAD; 0 deletions remaining; canonical C: verified clean.
- Flagged for team: retire the E: clone entirely (C: master is canonical);
  memory-layer work needs an ownership decision (commit vs discard).
- Next-Action pattern: when a clone shows mass uncommitted deletions, check the
  canonical clone first and look for an untracked retirement dir before
  concluding data loss.
