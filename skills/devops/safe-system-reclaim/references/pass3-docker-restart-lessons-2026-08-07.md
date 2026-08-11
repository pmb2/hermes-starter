# Pass 3 lessons — post Docker restart (2026-08-07)

Validated while finishing system tidy after user restarted Docker Desktop.

## Compose restart durability

Symptom: parked containers (`docker update --restart=no` + `stop`) come back **Up** after Docker Desktop restart.

Cause: project `docker-compose.yml` still has `restart: unless-stopped` (or similar). Docker Desktop / compose project reconciliation re-applies policies.

Durable park checklist:

1. `docker update --restart=no <names>`
2. `docker stop <names>`
3. `docker compose down` (never `-v` if volumes must stay)
4. `docker rm` any leftovers
5. Patch compose `restart: unless-stopped` → `restart: "no"` with comment + `.bak` of original
6. Verify `docker ps -a` shows none of the parked project after another Docker restart

## daemon.json log rotation ≠ fleet-wide immediately

After writing `~/.docker/daemon.json` with `max-size` / `max-file` and restarting Docker:

- New containers pick up daemon defaults (or explicit LogConfig).
- Long-lived containers often keep previous LogConfig (`json-file` empty opts or `local` with own caps).
- Full inheritance requires recreate/redeploy of those services.

Do not claim “all container logs are capped” after daemon.json alone.

## Large volume backup before delete

Target example: `yt-animations_comfyui-models` ≈ **196 GB**.

What failed / was too slow:

- `docker run --rm -v VOL:/src:ro -v DEST:/dest alpine cp -a . /dest/` progressed only ~17 GB after ~15+ minutes and risked hang.
- Stopping mid-copy is OK **only if** volume remains; write `BACKUP-INCOMPLETE.txt` in the archive directory.

Safer sequencing for future reclaim:

1. Park compose permanently (section above)
2. Full archive with a streaming method (`tar c | tar x`, dedicated disk tool, or relocate Docker data-root to E:)
3. Byte-count / file-count verify archive ≈ source
4. Only then `docker volume rm ...`
5. Then VHDX compact maintenance window

Never start `wsl --shutdown` / Optimize-VHD while a volume archive is running.

## MCP project venv isolation (job-agent / bizdev)

Broken Hermes `mcp-stderr.log` multi-GB growth often comes from stdio MCP crash loops.

Working pattern:

1. Create project `.venv` under the MCP project (not Hermes agent venv).
2. Install deps with **that** interpreter: `PYTHONPATH= PYTHONHOME= .venv/Scripts/python.exe -m pip install ...`
3. Force MCP into the venv when pip resolves to global site-packages: `--ignore-installed --no-cache-dir mcp==...`
4. Point `config.yaml` `mcp_servers.<name>.command` at `.venv/Scripts/python.exe`.
5. Set env on the MCP entry:
   - `PYTHONPATH: ""`
   - `PYTHONNOUSERSITE: "1"`
   - correct `DATABASE_URL` (sqlite async needs `sqlite+aiosqlite://...`; postgres needs `asyncpg` installed if URL is postgresql+asyncpg)
6. Verify: `DATABASE_URL=... .venv/Scripts/python.exe -c "import mcp_server"`
7. Config backup before edit: `config.yaml.bak-YYYYMMDD-passN`

Hermes agent venv contamination symptoms:

- Import resolves under `...\hermes-agent\venv\Lib\site-packages\...` while using a different executable
- `ModuleNotFoundError: pywintypes` / `mcp` path mismatch

## Other broken MCPs that flood stderr

Even after job-agent fix, module-style servers can spam:

- `agent-replay` → `agent_replay.mcp_server` missing
- `personal-intelligence` → `app.main` needs correct workdir/venv
- `healthy-food-filter` → package not on Hermes python path
- `ultimate-firefox-mcp` → package not found / wrong workdir

Audit action: disable (`enabled: false`) or fix workdir+command before leaving them in the always-on fleet. Tail `logs/mcp-stderr.log` for `starting MCP server` + `ModuleNotFoundError` pairs.

## Host Ollama vs agency Ollama

If Docker `agency-stack-agency-ollama-1` is healthy and is the intended provider:

- Stop host `ollama.exe serve` to free RAM/ports
- Leave Docker ollama + proxy running
- Confirm no Run-key autostart; user may still relaunch desktop Ollama app later

## Cron model pins

Config-drift spend-guard jobs need explicit pin via CLI:

```text
hermes cron edit <id> --provider custom --model gpt-5.6-sol
```

Agent `cronjob update` may reject provider/model fields (“No updates provided”).

## Portfolio archive

- Clean stale clone: zip to `${MY_REPOS}\Archives\repos\`, then remove or rename.
- If `.git/objects/pack` is locked: rename to `_STALE_<name>_DELETE_OK_<date>`, delete after unlock/reboot.
- Merge-temp dirs: zip + move folder to Archives even if clean.

## Report pack locations (this pass family)

`~/AppData/Local/hermes/plans/system-tidy-2026-08-07/`

- `00`–`06` audit/plan
- `07`–`09` execution logs (pass 1–3)

Mirror: `hermes-config/docs/findings/system-tidy-2026-08-07/`
