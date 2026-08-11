# Cron model pin — CLI only (2026-08-07)

## Problem
Config-drift spend-guard blocks unpinned agent cron jobs after global provider/model change. Error text may suggest pinning via the agent `cronjob` tool.

## What fails
In-agent:
```
cronjob(action='update', job_id=..., provider=..., model=...)
```
→ **"No updates provided."** (provider/model not accepted through that tool surface on this host).

## What works
```bash
hermes cron edit <job_id> --provider custom --model gpt-5.6-sol
```

Verify in `jobs.json`: `provider` and `model` fields set (not only `*_snapshot`).

## Related path fixes
MSYS `.sh` cron failures: use `.py` stdin wrappers + `MSYS2_ARG_CONV_EXCL=*` (skill `windows-cron-msys-path-fix`). That skill is **user-owned** — autonomous curator cannot patch it; user can `hermes curator adopt windows-cron-msys-path-fix` to opt in.

## Jobs pinned this way (example set, 2026-08-07)
- 5f9f140c2c05 nationwide-daily-build
- d8629516eb8c radicle-github-sync
- d40d13453914 legal-data-privacy-weekly
- 54d45f82670d fitness accountability
- 9bba2fd6f89d jailai-status
- fe4bfe713da9 jailai-watchdog
