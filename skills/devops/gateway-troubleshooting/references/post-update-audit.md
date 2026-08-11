# Post-Update Audit Checklist

After `hermes update` runs (especially when it reports "Restoring local changes..."), verify the custom stack survived. The update stashes local modifications, pulls upstream, and re-applies — that restore can drop patches, leave `.orig` conflict leftovers, or reset config.

the operator expects this audit proactively after any update. Do not wait to be asked.

### Custom Fork Commit Check (pmb2)

After every update, custom features from the `pmb2` fork that live on origin's `main` but NOT on `origin/main` may be lost. The local repo tracks `origin/main` by default, but the operator's custom commits live on `pmb2/main`. Identify and re-apply them:

```bash
cd ~/AppData/Local/hermes/hermes-agent
git fetch pmb2 main
git log pmb2/main --not origin/main --oneline
```

Each listed commit is a custom feature that needs cherry-picking. Known pmb2 custom commits:

| Hash | Feature | File |
|------|---------|------|
| `243aaf36a7` | 🔄 reaction re-prompt (`on_raw_reaction_add` handler) | `plugins/platforms/discord/adapter.py` |

Apply:
```bash
git cherry-pick <hash>
```

If cherry-pick conflicts arise, resolve with `git mergetool` or manual edit, then `git cherry-pick --continue`. The commit author message already identifies itself — no need to reword.

## 1. Repo state — did custom patches survive?

```bash
cd ~/AppData/Local/hermes/hermes-agent
git status --short
git stash list          # anything stuck in stash = lost patch
find . -name "*.orig" -not -path "./node_modules/*"   # conflict leftovers
grep -rl "<<<<<<< " --include="*.py" . | head -5      # unresolved conflicts
```

Known custom patches to verify by name:
- `HERMES_ONE_MODEL_LIBRARY_COMPAT_V1` in `hermes_cli/web_server.py` (model library endpoints for Hermes One desktop). Verify with:
  ```bash
  grep -c "HERMES_ONE" hermes_cli/web_server.py   # expect ~15+ hits
  ```

Clean up junk the update leaves behind: `.orig` files, `.coverage`, `.playwright-mcp/`, stray pytest artifacts.

## 2. Config diff against timestamped backups

The updater writes `config.yaml.bak.YYYYMMDD_HHMMSS` before touching config. Diff semantically (not textually — key order changes):

```bash
cd ~/AppData/Local/hermes
diff <(python -c "import yaml; print(yaml.safe_dump(yaml.safe_load(open('config.yaml.bak.<NEWEST>')), sort_keys=True))") \
     <(python -c "import yaml; print(yaml.safe_dump(yaml.safe_load(open('config.yaml')), sort_keys=True))")
```

Expected diffs: intentional model/provider changes only. Anything else missing = restore it.

## 3. MCP servers, cron jobs, scripts

```bash
python -c "
import yaml, json
c = yaml.safe_load(open(r'${USER_HOME}\AppData\Local\hermes\config.yaml'))
print(len(c.get('mcp_servers', {})), 'MCP servers')
print(sorted(c.get('providers', {}).keys()), 'providers')
j = json.load(open(r'${USER_HOME}\AppData\Local\hermes\cron\jobs.json'))
print(len(j.get('jobs', j if isinstance(j, list) else [])), 'cron jobs')
"
ls ~/AppData/Local/hermes/scripts/{cron-guardian.py,hermes_model.py,workflow_runner.py,jippity_bridge.py,daily_brief.py}
cat ~/AppData/Local/hermes/model_config.json   # centralized model config for scripts
```

## 4. Gateway process reality check

`hermes gateway status` can report a STALE PID (the pidfile outlives the process). Verify the real listener:

```bash
netstat -ano | grep -i listen | grep 8642
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter 'ProcessId=<pid>' | Select ProcessId,CreationDate,CommandLine | Format-List"
curl -s http://localhost:8642/health   # expect {"status":"ok",...,"version":"..."}
```

## 5. Missed messages during downtime

Discord does not replay gateway events. Anything sent while the gateway was down is lost — voice messages show up later only as "(attachment)" in history backfill. Check log timestamps around the update window and warn the user to re-send anything from that window. See `references/discord-voice-message-transcription.md`.

## 6. Report

Deliver a compact table: component / status. Flag anything restored or still missing. the operator's standing expectation: custom functionality (patches, MCP servers, cron, scripts) survives updates — if it didn't, restore it from git stash, `.bak` files, or the feature branch, then commit.
