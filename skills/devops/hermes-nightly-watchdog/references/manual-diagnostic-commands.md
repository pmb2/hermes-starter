# Manual Diagnostic Commands

When the watchdog script times out via cron, run these phases manually with higher timeouts.

## Preflight

```bash
hermes --version
pip list --format=freeze | wc -l        # quick package count
```

## Hermes Update

```bash
hermes update --check                    # check without applying
hermes update -y                         # apply update if available
```

## Pip Packages (faster alternatives when --outdated hangs)

```bash
python -m pip list --outdated --format=freeze --timeout=5 2>&1 | head -30
# Or just count total packages:
pip list --format=freeze | wc -l
```

## Git Repos (batch check)

```bash
for r in \
  "$HOME/.hermes/hermes-agent" \
  "${MY_REPOS}/Documents/github/hermes-config" \
  "${MY_REPOS}/Documents/github/agent-fleet" \
  "${MY_REPOS}/Documents/github/tor-browser-mcp"; do
  echo "===== $r ====="
  if [ -d "$r/.git" ]; then
    cd "$r"
    echo "BRANCH: $(git branch --show-current 2>&1)"
    echo "BEHIND: $(git rev-list --count HEAD..@{u} 2>&1)"
    echo "AHEAD: $(git rev-list --count @{u}..HEAD 2>&1)"
    echo "UNCOMMITTED: $(git status --short | wc -l)"
    echo "FETCH: $(git fetch --all 2>&1 | tail -3)"
    echo "---"
  else
    echo "NOT A GIT DIR or MISSING"
  fi
done
```

## Camoufox Detection

```bash
# Level 1: binary installed?
which camofox || which camoufox || echo "NOT INSTALLED"
# Level 2: process running?
ps aux | grep -iE "camo|firefox" | grep -v grep
# Level 3: API responding?
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9377/health 2>&1
```

## Gateway

```bash
hermes gateway status                    # check current state
hermes gateway stop                      # stop if running
hermes gateway start                     # start fresh
```

## System Health (Windows/MSYS2)

```bash
df -h /c/ /e/                            # disk (works on MSYS2)
cat /proc/loadavg                        # load (works on MSYS2)
wmic OS get LastBootUpTime /value        # boot time (native Windows)
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory /value  # memory (native Windows)
```
