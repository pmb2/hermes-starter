# Timezone & Backlog Counting Patterns

## Timezone handling

The system clock may show a different date than America/New_York ET.

**Proven pattern:**
```bash
TODAY=$(TZ='America/New_York' date +%Y-%m-%d)
```
But check the digest directory if the file doesn't exist — the last digest may be from the previous ET day.

**Trust the digest directory, not the clock.** The most recent `.md` file in the digest dir is the one to summarize (unless it's >36h old).

## Counting backlog items

The `list` command outputs Unicode bullet characters (`○`) at the start of each line. These don't pipe cleanly through MSYS `wc -l`.

**Do this instead:**
```bash
# Count critical items only
python "$SCRIPTS" list --unseen-only --priority=critical 2>&1 | grep -c "\[CRITICAL\]"

# Count all items
python "$SCRIPTS" list --unseen-only 2>&1 | grep -cE "\[(CRITICAL|HIGH|MEDIUM|LOW|FYI)\]"
```

## Critical thread tracking

Many critical items repeat across days (e.g. GPU VRAM, crash-loops, P0 cold). When delivering the PULSAR, call out how many days an item has been outstanding so the operator can prioritize urgency — items flagged 5+ consecutive days need escalation.
