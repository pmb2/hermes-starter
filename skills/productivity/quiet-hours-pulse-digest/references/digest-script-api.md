# append-digest.py — Script API

**STATUS: EXISTS AND WORKS.** Script at `${MY_REPOS}/_project/scripts/append-digest.py` was created after the initial digest system design. All pulse cron jobs now call it successfully.

## API

Append pulse findings to the daily digest file. Handles quiet-hours detection and suppresses Discord delivery via `[SILENT]` output during the sleep window (00:00-06:59 EST).

## Usage

### From a Cron Job Prompt

```
After your pulse work, run:
python ${MY_REPOS}/_project/scripts/append-digest.py "Pulse Name" "- <finding 1>\n- <finding 2>\n..."
```

The script will:
1. Append your findings to `${MY_REPOS}/_project/daily-digest/YYYY-MM-DD.md`
2. Check current EST hour
3. If 00:00-06:59 → print `[SILENT]` (suppress Discord delivery)
4. If 07:00+ → print nothing special (normal delivery proceeds)

### From Command Line

```bash
# Via argument
python append-digest.py "Pulse Name" "- System healthy\n- No issues"

# Via stdin
echo "- System healthy\n- No issues" | python append-digest.py "Pulse Name"
```

## Output

| Condition | Output | Effect |
|-----------|--------|--------|
| Waking hours, findings saved | `[Digest] Appended to ...` then `[Digest] Waking hours — ...` | Cron continues to produce its normal report |
| Quiet hours, findings saved | `[Digest] Appended to ...` then `[Digest] Quiet hours...` then `[SILENT]` | Cron's `[SILENT]` output suppresses Discord delivery |
| No findings provided | `[Digest] No findings to record, skipping.` | Nothing appended, delivery proceeds normally |

## Digest File Format

```
# Daily Digest — YYYY-MM-DD

## [HH:MM EST] the operator's Pulse
- Intel: 3 new bookmarks
- Git: dev-lead pushed 2 commits

## [HH:MM EST] dev-lead-pulse
- Reviewed gateway wrapper
- All patches confirmed working
```

## Helper Functions (for use by Morning Brief)

```python
# Read today's digest
python -c "
from append_digest import read_todays_digest
print(read_todays_digest())
"

# Check if we're in quiet hours
python -c "
from append_digest import is_quiet_hours
print('QUIET' if is_quiet_hours() else 'AWAKE')
"
```
