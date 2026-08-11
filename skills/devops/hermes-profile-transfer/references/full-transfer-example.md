# Default → Chief-of-Staff Transfer — Full Example

Transferred from Hermes default profile to `chief-of-staff` (Aegis) on 2026-06-06.

## Profiles

| Property | Source | Target |
|----------|--------|--------|
| Profile dir | `~/AppData/Local/hermes/` | `~/AppData/Local/hermes/profiles/chief-of-staff/` |
| Skills count | 182 SKILL.md (150 active, 32 archived) | 90 SKILL.md before → 171 after |
| Memories | MEMORY.md (2,204 bytes) + USER.md (1,362 bytes) | Empty → same as source |
| Config model | opencode-go/deepseek-v4-flash | openrouter/deepseek-chat → opencode-go/deepseek-v4-flash |
| Gateway | Running | Running (needs restart for new config) |

## Commands Run

### Inventory
```bash
ls ~/AppData/Local/hermes/profiles/chief-of-staff/
find ~/AppData/Local/hermes/skills/ -name 'SKILL.md' | wc -l    # → 182
find ~/AppData/Local/hermes/profiles/chief-of-staff/skills/ -name 'SKILL.md' | wc -l  # → 90
```

### Skills copy
```bash
cd ~/AppData/Local/hermes/skills
find . -type f -not -path './.archive/*' \
  -not -name '.bundled_manifest' \
  -not -name '.curator_*' \
  -not -name '.usage.json*' | \
while IFS= read -r f; do
  dest=~/AppData/Local/hermes/profiles/chief-of-staff/skills/"$f"
  mkdir -p "$(dirname "$dest")"
  cp "$f" "$dest"
done
```

### Memory copy
```bash
cp ~/AppData/Local/hermes/memories/MEMORY.md ~/AppData/Local/hermes/profiles/chief-of-staff/memories/
cp ~/AppData/Local/hermes/memories/USER.md ~/AppData/Local/hermes/profiles/chief-of-staff/memories/
```

### AGENTS.md changes
- Updated model/provider in YAML frontmatter from `deepseek/deepseek-chat` + `openrouter` to `deepseek-v4-flash` + `opencode-go`
- Added ## Skill Inheritance section with domain→skills table (23 categories)
- Added ## Knowledge Sources section (MEMORY.md, USER.md, MemPalace wings, Skills/ dir)

### Config.yaml changes
- Removed `api_mode` and `base_url` (misconfigured for opencode-go)
- Kept same `fallback_model`

## Unique Target Files Preserved
6 chief-of-staff-specific flat `.md` files at skills root:
- `morning-briefing.md` (daily command brief)
- `task-processing.md`
- `weekly-council.md` (weekly council check-in)
- `open-loop-tracker.md`
- `decision-logger.md`
- `conflict-detector.md`

## Verification
```bash
find ~/AppData/Local/hermes/profiles/chief-of-staff/skills/ -name 'SKILL.md' | wc -l  # → 171
```

## Gateway Restart Required
Config changes only take effect after gateway restart:
```bash
kill $(cat ~/AppData/Local/hermes/profiles/chief-of-staff/gateway.pid)
# Then restart gateway via normal profile launch
```
