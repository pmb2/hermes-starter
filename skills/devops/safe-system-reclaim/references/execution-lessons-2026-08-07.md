# Execution lessons — system tidy reclaim (2026-08-07)

## User policy

If the operator says consolidate/tidy without losing critical data or interrupting services, then "get started" / "keep going" means execute the safe archive-first path, not re-plan forever.

## Pass 1

1. `.env` 131KB → ~9KB after last-non-empty collapse.
2. Cron pins need `hermes cron edit` CLI; agent cronjob update can return "No updates provided."
3. Path jobs: `.py` stdin wrappers, retarget off `.sh`.
4. Tax data: `data/land/leepa_2025/`; NAL file must exist after move.
5. Logs: gzip + truncate; mcp-stderr can refill multi-GB during the same session.
6. Large trees: pathlib/shutil when robocopy becomes `C:\c\...`.
7. Docker: container/image/builder prune only.
8. Always report E: archives and C: free delta separately (vhdx lag).

## Pass 2

1. Port attribution: `:5432` = host PostgreSQL 16; TightVNC on 5800/5900; Gigabyte service ≠ port owner.
2. VNC: stop + Manual start type is reversible.
3. Park Temporal orphans + yt-anim + standalone chatterbox; keep agency TTS/Ollama and revenue stacks.
4. RAM improved ~9GB free → ~12.5GB free after parking idle stacks.
5. MCP crash loops: install `python-docx`/`sqlalchemy` into bizdev-agent project venv; job-agent may lack expected `.venv`.
6. `rotate-hermes-logs.py` + 6h cron; daemon.json log-opts need Desktop restart.
7. Stale C: bookends: zip first; rmtree pack lock → rename `_STALE_*_DELETE_OK_*` then delete; E: clone remains canonical.
8. Tiny non-git `BookEnds_bak` can move to Archives/repos immediately.

## Do not overclaim

Docker prune inside sparse `docker_data.vhdx` may not free much OS-visible C: space until WSL shutdown + compact.

## Protected skills

`windows-cron-msys-path-fix` and external `project-inventory` may be user/external-owned. Recommend adopt/user edit rather than autonomous patch when those files need content updates.