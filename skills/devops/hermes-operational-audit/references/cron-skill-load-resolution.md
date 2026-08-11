# Cron Skill-Load Resolution — Reference & Incident (Jul 31 2026)

## The failure

`docs-lead-pulse` cron job (jobs.json `d822778b2b15`, profile `docs-lead`) lists 4 skills:
`discord-report-format`, `project-documentation-standards`, `hermes-agent-skill-authoring`,
`writing-plans`. One run injected the skip notice for the last two:
"The following skill(s) were listed for this job but could not be found and were skipped:
hermes-agent-skill-authoring, writing-plans". The job still ran — those skills' guidance was
simply absent from the prompt.

## Loader mechanics (from source)

- `cron/scheduler.py` (~line 2501): `loaded = json.loads(skill_view(normalize_skill_lookup_name(skill_name)))`.
  On `success != true` the name is appended to `skipped` and the notice is prepended to the
  prompt (lines 2530-2536). A failed load never fails the job — it degrades silently.
- **Resolution universe = local skills dir + `skills.external_dirs` only.**
  - local: default profile `~/AppData/Local/hermes/skills/`
  - external_dirs: `skills.external_dirs` in `config.yaml` (this host:
    `${USER_HOME}/Documents/github/hermes-config/skills` — a git repo, branch `vps-hybrid`)
  - Profile-local trees (`profiles/<p>/skills/`) and the bundled tree are NOT consulted;
    there is NO fallback when the file is missing.
- **Duplicate across local + external_dirs = hard fail.** `skill_view` returns
  "Ambiguous skill name 'X': 2 skills match across your local skills dir and external_dirs."
  No content is loaded. Do NOT copy an external_dirs skill into the local tree as
  "redundancy" — it breaks loading entirely (verified by experiment, reverted).
- **Note for curation:** skills under `skills.external_dirs` are read-only to autonomous
  curation — `skill_manage` refuses patches/writes to them ("externally owned and
  read-only"). The canonical knowledge skill `hermes-agent-skill-authoring` lives there,
  so loader-resolution lessons must be documented in agent-owned skills (like this one).

## Root cause of the incident

Both SKILL.md files were **missing from the hermes-config working tree** at job assembly
(~08:00 ET); their mtimes showed re-creation at 08:54 restored to committed state.
Deletion happened between Jul 29 (last commit 8c75922) and Aug 1; deleter unidentified
(suspect a sync/cleanup process). Files were tracked on `vps-hybrid` (commit 00460b4),
so `git checkout -- <path>` restored them with zero diff vs HEAD.

## Diagnosis recipe — reproduce the exact loader call

`hermes skills list` / `hermes skills inspect` are NOT reliable diagnostics:
`list` shows a merged ~444-entry index identical across profiles; `inspect` searches
registry sources (skills.sh) and can report "No skill named X found" or
"Multiple skills named X found" even when the real loader resolves fine.

```python
# from the hermes-agent package dir (contains tools/, agent/)
import os, json
def try_resolve():
    from tools.skills_tool import skill_view
    from agent.skill_utils import normalize_skill_lookup_name
    for n in ["hermes-agent-skill-authoring", "writing-plans"]:
        try:
            r = json.loads(skill_view(normalize_skill_lookup_name(n)))
            print(n, "OK" if r.get("success") else f"FAIL: {r.get('error','')[:120]}")
        except Exception as e:
            print(n, "EXC", e)
try_resolve()
os.environ["HERMES_PROFILE"] = "docs-lead"   # profile-dependent behavior
try_resolve()
```

Check the external_dirs repo working tree for the file (`git status` / `ls`), then restore
tracked files with `git checkout -- <path>`.

## Environment quirks hit during diagnosis

- `git -C /e/...` (MSYS path) → "fatal: not a git repository" for EVERY repo in cron
  sessions, while `cd /e/... && git log` and `git -C "E:\\..."` work fine. The common
  `xargs git -C "$d"` multi-repo scan pattern silently returns empty under this condition —
  a false "environment quiet" signal. Use `cd`-based loops or native backslash paths.
- Native Windows python (hermes venv) rejects MSYS paths:
  `python ${MY_REPOS}/.../append-digest.py` → "can't open file 'C:\e\yourdata...'".
  Use `python "${MY_REPOS}/..."` (forward-slash native path).
- A shallow `ls -la .git | head` can make a healthy .git look gutted — verify
  objects/, refs/, HEAD, index before concluding corruption. And test a SECOND repo
  before blaming a specific repo: a failure affecting every repo is environmental.

## Prevention (deployed Jul 31 2026)

Scribe profile AGENTS.md gained a "Pulse Pre-flight" section: verify the two
external-dir SKILL.md files exist each pulse; restore via `git checkout --` from the
hermes-config repo; reminder of the ambiguity rule and the git path quirk.
