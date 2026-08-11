# Cron Job Auto-Fix Pattern: Proactive Scanning + Self-Healing

When a periodic cron job finds issues (broken scripts, config drift, erroring jobs,
stale state), it should **fix them immediately** rather than just reporting them.

This pattern extends the self-healing pulse from infrastructure (services/containers)
into the Hermes configuration layer itself — cron jobs, scripts, profiles, and configs.

## Pattern

```
EACH RUN:
  PHASE 1: SCAN — Find every issue
    - cronjob(action='list') → look for error/gone-missing jobs
    - session_search() over recent sessions → look for unresolved issues
    - Read scripts referenced by erroring jobs → identify the bug
    - Check configs for drift (stub configs, missing fields)

  PHASE 2: FIX — Repair everything possible
    - Patch broken scripts (MSYS path issue → Python stdin wrapper)
    - Fix config drift (missing fallback providers, MCP servers)
    - Fill in stub configs with sensible defaults
    - Update cron job references (bad path → correct relative path)
    - Test each fix with cronjob(action='run', job_id=...)

  PHASE 3: REPORT — What was fixed, what remains
    - List each fix: what was wrong, what was changed, test result
    - List remaining issues: why they couldn't be fixed (blocker)
    - Prioritize: urgent (security/breakage) vs routine (optimization)

  PHASE 4: ESCALATE — Things that need the user
    - Token/key exposure (report, don't rotate)
    - Architectural decisions (fleet size, redundancies)
    - Environment dependencies that can't be fixed in a cron sandbox
```

## What to Auto-Fix vs What to Report

### Auto-Fix (no permission needed)
| Issue | Fix |
|-------|-----|
| Cron job script not found (MSYS path) | Create Python stdin wrapper, update cron reference |
| Script exits on expected condition (service down) | Patch to exit 0 gracefully instead of sys.exit(1) |
| Config drift (missing fallback, MCP servers) | Add missing sections with sensible defaults |
| Stub agent configs (placeholder directives) | Fill with domain-specific directives from context |
| CRLF line endings in bash scripts | `sed -i 's/\r$//'` |
| Overlapping pulse jobs doing same work | Pause redundant jobs, note consolidation needed |
| Silent failures (deliver=local + error) | Change delivery to origin so user sees the failure |

### Report Only (flag to user)
| Issue | Why Not Auto-Fix |
|-------|------------------|
| Token/key exposure in env files | Changing credentials breaks running services |
| Infrastructure architecture (fleet size, provider choice) | Needs user decision |
| Environment dependencies (E: drive, missing binaries) | Can't be fixed from cron sandbox |
| Strategic decisions (stop doing X, start doing Y) | Needs user context |
| PR-level code changes | Needs review |

## User Preference: Proactive Fix

When the user has said "fix it, don't just tell me about it" (the operator:
"if there are developer things you can fix, fix them"), this preference
overrides the default "report and wait" posture.

Embed this in every scan-and-fix pulse prompt:
- If you can fix it with available tools, DO IT — don't ask
- If a fix fails after 3 attempts, stop and report the blocker honestly
- If the fix would touch credentials, secrets, or production data paths, STOP and report
- Test each fix before declaring it done
- Always report what was fixed so the user knows what changed

## Example: Cron Job Fix Workflow

```python
# 1. Scan for broken jobs
result = cronjob(action='list')
for job in result.jobs:
    if job.last_status == 'error':
        # 2. Read the script
        script = read_script(job.script)
        # 3. Identify the bug
        if 'MSYS path' in error:
            # 4. Create Python wrapper
            write_wrapper_script(job.name, script.path)
            # 5. Update cron reference
            cronjob(action='update', job_id=job.id, script='wrapper.py')
            # 6. Test
            cronjob(action='run', job_id=job.id)
        elif 'expected condition':
            # Make it graceful
            patch_script_to_exit_0_gracefully(script.path)
```

## Anti-Patterns

- **Don't rotate secrets** — flag exposure, never change credentials
- **Don't delete cron jobs** — pause them instead (they're recoverable)
- **Don't rewrite entire scripts** — targeted patches only
- **Don't fire-and-forget** — always test after fixing
- **Don't report "nothing to report"** — stay silent when all is well
