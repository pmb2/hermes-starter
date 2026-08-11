# Safe System Reclaim Playbook (archive-first)

Use when the operator (or ops) asks to tidy / consolidate / free disk **without losing critical data** and **without breaking running systems**.

## Policy (non-negotiable)

1. Archive or move → **verify sizes** → only then remove source.
2. Do not stop revenue/runtime stacks (agency-stack core, BookEnds while launching, hermes-pggraph, buzz-prod, Hermes gateway) without explicit OK.
3. Do not delete **named** Docker volumes (model weights, postgres data) without an explicit named decision.
4. Do not bulk-delete git clones until `git status` shows clean or uncommitted work is committed/stashed.
5. Write `plans/system-tidy-YYYY-MM-DD/07-EXECUTION-LOG.md` with a **restore map**.

## Cold store layout

```
${MY_REPOS}\Archives\hermes\
  YYYY-MM-DD\          # .env.bak, installers, one-shot dumps
  logs\                # gzipped rotated logs
  backups\             # state.db backups, pre-update zips
  skills-curator\      # moved .curator_backups trees
```

Local hot data (keep on C: under Hermes):

```
~/AppData/Local/hermes/data/land/     # tax rolls, large CSVs (not scripts/)
~/AppData/Local/hermes/.env.bak-*     # env backups
~/AppData/Local/hermes/config-backups/
```

## Phase order

### A. Stabilize (before reclaim)

| Step | How |
|------|-----|
| Backup `.env` | `cp .env .env.bak-YYYYMMDD-tidy` (+ copy to E: Archives) |
| Dedupe `.env` | Python: last non-empty wins per key; keep ~unique KEY= lines; expect ~5–15 KB |
| Pin drift crons | `hermes cron edit <id> --provider custom --model <current>` (CLI; agent tool cannot pin) |
| Fix MSYS path jobs | `.py` wrappers that `bash -s` stdin + PATH + `MSYS2_ARG_CONV_EXCL=*` — see `windows-cron-msys-path-fix` |

### B. Logs

1. Stream-gzip large files to E: (`gzip -c` or Python gzip).
2. Truncate **in place** so open writers keep the path (`: > file` / `open(path,'wb').close()`).
3. At end of session, **re-stat `logs/mcp-stderr.log`** — it often refills multi-GB during MCP activity; truncate again.
4. Old agent `gateway-*.log` files (>5 MB and age >7d): archive+truncate safely.

### C. Data-out-of-scripts

1. `cp -a` or Python copy tree to `data/land/` (or E: data).
2. Compare total bytes (walk both trees).
3. Only if match (or dst ≥ src for dirs with identical content): `rmtree` / unlink source.
4. Update refresh scripts to Windows-native paths for `python.exe` calls.

### D. Hermes bulk cold moves

Safe movers (typical):

- `backups/pre-update-*.zip`, `state.db.backup-*`, temp multi-GB db copies → E: `backups/`
- `skills/.curator_backups` → E: `skills-curator/` (use Python pathlib if robocopy path-doubles)
- Root installer zips (`camoufox-win64.zip`) → E: installers
- `config.yaml.corrupt.*` → `config-backups/archive/` (keep ~3 newest real `.bak`)

**Never casually move/delete live `state.db`.**

### E. Docker (safe band)

```text
docker container prune -f      # exited only
docker image prune -f          # dangling layers
docker builder prune -f        # build cache
# optional later: docker volume prune -f  # dangling anonymous only — still review first
```

Stop if `docker rmi` says image is used by a running container.

**Not safe without approval:** deleting `*_comfyui-models` (or any large named volume), parking Temporal/TTS/Ollama stacks, relocating Docker data-root, vhdx compact (needs WSL shutdown window).

### F. Verify

- `df -h` C: and E: — report both archived bytes and OS free delta separately.
- `docker ps` spot-check: bookends, hermes-pggraph, agency critical services healthy.
- Confirm `.env` still has Discord/OmniRoute/browser keys non-empty.

## Restore map template

```markdown
## Restore
- .env → copy .env.bak-YYYYMMDD-tidy .env
- logs → gunzip from E:\...\Archives\hermes\logs\
- state backups → copy from E:\...\Archives\hermes\backups\
- leepa data → already at hermes/data/land/ (or reverse move)
- curator skills → move back under skills/.curator_backups
```

## What “done” means

- Critical services still up
- Redundant bulk data lives on E: or under `data/`, not in `scripts/`
- Execution log exists with sizes and destinations
- User told honestly if C: free GB did not move as much as archived GB (vhdx)