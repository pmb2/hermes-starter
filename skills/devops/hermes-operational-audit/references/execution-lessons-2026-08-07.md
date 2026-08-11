# Execution lessons — system tidy reclaim (2026-08-07)

Companion to `safe-reclaim-playbook.md` and `the operator-audit-2026-08-07-metrics.md`.

## User policy (encode as default)
When the operator says: consolidate / tidy **without losing anything critical** and **without interrupting or breaking anything**:
- Archive/move → verify sizes → then remove source
- Leave revenue stacks up (agency-stack, BookEnds, hermes-pggraph, buzz, gateway)
- No named Docker volume deletes
- No bulk git clone deletes without dirty check
- Write `07-EXECUTION-LOG.md` + restore map

## Techniques that worked
1. **.env collapse** — last non-empty wins; 131 KB → ~9 KB; keep backup `.env.bak-YYYYMMDD-tidy` on C: and E:
2. **Cron pins** — `hermes cron edit` CLI only (`references/cron-model-pin-cli.md`)
3. **Path jobs** — add `cos-channel-awareness.py` / `ai-sharp-data-commit.py` wrappers; retarget jobs to `.py`
4. **Tax data** — `data/land/` not `scripts/`; Windows-native paths for python.exe in `.sh`
5. **Logs** — gzip to E:, truncate in place; **re-check mcp-stderr at end** (regrows during tidy)
6. **Large trees** — Python `pathlib`/`shutil.move` when robocopy path-doubles under MSYS
7. **Docker** — container/image/builder prune only; stop if rmi says image in use
8. **Reporting** — always pair "archived to E: (GB)" with "C: free delta" (vhdx lag)

## Do not claim as free unless OS shows it
Docker builder prune (~8 GB inside vhdx) may not increase `df` free on C:. Still valuable; explain vhdx.

## Protected skills note
`windows-cron-msys-path-fix` is user-owned — cannot autonomous-patch. Recommend adopt if pin docs still wrong there.
`project-inventory` may live under hermes-config external — refresh counts (116 not 126) via adopt/user edit.
