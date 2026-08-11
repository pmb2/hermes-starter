# the operator Hermes metrics snapshot — 2026-08-07

Companion to the full tidy plans under  
`~/AppData/Local/hermes/plans/system-tidy-2026-08-07/`  
and hermes-config `docs/findings/system-tidy-2026-08-07/`.

## Fleet (pre-tidy)

| Metric | Value |
|--------|-------|
| Cron jobs | 97 total / 68 enabled |
| last_status | 66 ok / 8 error / 9 unknown / 14 scheduled |
| Config-drift spend-guard | 6 jobs |
| MCP servers in config.yaml | 39 |
| Local SKILL.md | 526 (~1.4 GB skills tree; ~902 MB `.curator_backups`) |
| Scripts dir | ~247 entries / ~386 MB (leepa data dominated) |
| `.env` | 131 KB, 1615 lines, **34 unique keys**, CAMOFOX/AGENT_BROWSER **378×** each |
| state.db | ~4.7 GB; ~7065 sessions; ~271k messages; dual FTS |
| logs | ~4.8 GB; mcp-stderr alone ~4.1 GB |
| backups on C: | ~15.4 GB multi-GB state/pre-update artifacts |
| Local git repos (unique) | ~187 |
| pmb2 GitHub | 116 (10 archived) |
| Docker | ~98–101 running; images ~163 GB; volumes ~290 GB |
| Volume hotspot | `yt-animations_comfyui-models` **~196 GB** |
| C: | 85% used, ~145–146 GB free |
| E: | 24% used, ~677 GB free |
| Host RAM | ~65 GB; ~9 GB free under full stack |

## Safe reclaim results (same day)

| Action | Result |
|--------|--------|
| `.env` dedupe | ~131 KB → ~9 KB (backup retained) |
| Drift crons pinned | 6 jobs → custom / gpt-5.6-sol via CLI |
| Path jobs | py wrappers for cos-channel + ai-sharp commit |
| Logs | archived to E: + truncated (mcp-stderr needed 2nd pass) |
| leepa | moved to `data/land/` after size match |
| curator_backups | ~902 MB → E: archives |
| Hermes backups | ~15.4 GB → E: archives |
| Docker | container/image/builder prune only; named volumes untouched |
| Services | bookends + hermes-pggraph remained healthy |

## C: free space note

OS free rose only ~12 GB while ~17+ GB landed on E: — expected with Docker sparse vhdx non-shrink. Report both numbers.

## Still parked after pass

- VNC 0.0.0.0:5800/5900; GigabyteUpdateService on :5432
- ComfyUI volume decision; Temporal half-dead stack; TTS/Ollama triples
- Docker data-root / vhdx compact maintenance window
- Duplicate clone cleanup after dirty review
- `project-inventory` skill counts (126) vs live 116 — skill refresh owed (hermes-config / external)

## Plans pack files

- `00-EXECUTIVE-SUMMARY.md` … `07-EXECUTION-LOG.md`