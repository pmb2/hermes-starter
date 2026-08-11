# Safe System Reclaim Playbook (archive-first)

## Policy

1. Archive/move → verify sizes → only then remove source.
2. Do not stop revenue/runtime stacks without explicit OK.
3. Do not delete named Docker volumes, live DBs, dirty clones, or credentials casually.
4. Prefer park (`stop` + `restart=no`) over delete for runtime clutter.
5. Write plans under `~/AppData/Local/hermes/plans/system-tidy-YYYY-MM-DD/` with restore map.

## Cold store

```
${MY_REPOS}\Archives\hermes\
  YYYY-MM-DD\ logs\ backups\ skills-curator\
${MY_REPOS}\Archives\repos\
```

Local hot:

```
~/AppData/Local/hermes/data/land/
~/AppData/Local/hermes/.env.bak-*
~/AppData/Local/hermes/scripts/rotate-hermes-logs.py
```

## Sequence

### Stabilize

- Backup and dedupe `.env` (last non-empty wins).
- Pin drift: `hermes cron edit <id> --provider ... --model ...`
- MSYS path jobs: Python wrappers with explicit Git bash, PATH, `MSYS2_ARG_CONV_EXCL=*`
- Native EXEs from bash: `C:/...` or `E:/...` paths only

### Logs

1. Gzip to E:; truncate in place.
2. Re-stat high-volume logs at end of session.
3. If ModuleNotFoundError: install into project venv from config.yaml.
4. Cron rotate every 6h via `rotate-hermes-logs.py`.
5. Docker log-opts need Desktop restart.

### Data / archives

- Move tax rolls and similar out of `scripts/` into `data/`.
- Patch consumers for env override + legacy fallback.
- Move multi-GB backups, curator backups, installer zips, corrupt configs to E:.
- Use pathlib/shutil if robocopy path-doubles under MSYS.

### Host / Docker park

- Attribute ports by PID → process path before stopping services.
- Example: `:5432` may be host PostgreSQL, not Gigabyte.
- Park half-dead Temporal or idle yt-anim/duplicate TTS only after inventory.
- Keep named volumes (Comfy models especially).
- Safe prune only: container/image/builder.

### Clones

- Clean + older + non-canonical: zip to Archives/repos, then remove.
- Pack lock: rename `_STALE_<name>_DELETE_OK_<date>`, retry later.
- Never auto-delete dirty clones.

## Restore

```powershell
Set-Service tvnserver -StartupType Automatic; Start-Service tvnserver
docker update --restart=unless-stopped <names>; docker start <names>
copy $env:LOCALAPPDATA\hermes\.env.bak-YYYYMMDD-tidy $env:LOCALAPPDATA\hermes\.env
```

## Metrics honesty

Report both archived GB on E: and C: free-space delta. VHDX lag means they often disagree.