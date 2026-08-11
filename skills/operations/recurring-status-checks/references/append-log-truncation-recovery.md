# Append-Log Truncation: Recovery Patterns

When a daily digest, PULSE.md, or other append-only cron log is accidentally truncated by `write_file`.

## Root Cause

The agent read the file incompletely (via `head -40` in terminal, a paginated `read_file`, or a grep snippet from a prior session), then called `write_file` with only the subset it had in context. The file on disk was silently overwritten with just those lines.

## Detection

After a `write_file` on an append-only log, verify the file integrity:

```bash
wc -l path/to/daily-digest/YYYY-MM-DD.md
# If line count looks too low (e.g., digest that had 15+ entries now has 3), you truncated it.
```

## Recovery Steps

### 1. Determine what was lost

Check the file's current mtime vs the session timestamp. If the write happened in the last few minutes, the conversation transcript has your earlier reads — but it may have also had readings from OTHER agents' earlier pulses that you never saw.

### 2. Reconstruct from session history

Every `read_file` call returns `N|CONTENT` with line numbers. Mine the transcript for ALL pulse entries from the current day:

```python
# Pseudocode: combine all {n}| lines found in transcript, strip prefix, sort by line number
lines = []
for match in re.finditer(r'^(\d+)\|(.+)', transcript, re.M):
    lines.append((int(match[1]), match[2]))
lines.sort()
reconstructed = '\n'.join(line for _, line in lines)
```

This works for `read_file` data. For `head`/`tail`/`cat` output from terminal — the transcript has the raw lines without line numbers. You can still reconstruct from them but cannot auto-detect gaps.

### 3. Use archive fallback

If the truncated file is the daily digest:
- Yesterday's digest (`<date-1>.md`) may exist at the same path
- The daily brief archive at `06-reports/daily-briefs/` may have a parallel version
- Older weekly council reports at `06-reports/weekly-council/` may contain summaries of the same pulses
- git reflog (`git reflog --diff-filter=M -- daily-digest/`) on the the planning repo repo may show the file's previous content if it was ever committed or stashed

### 4. Worst case: regenerate

If none of the above recovers the missing content, admit the loss clearly and regenerate from remaining archives. A pulse entry that reads:

> **[23:50 ET] Skillmate Pulse**
> - [Pulse content — original truncated; regenerated from remaining archives]

...is better than a silently corrupt file.

## Prevention Checklist

Before every `write_file` call that targets an append-only log, ask:

- [ ] Did I read the COMPLETE file (all lines, no pagination, no `head`/`tail`)?
- [ ] Is this the dedicated append script path I should be using instead?
- [ ] If I'm reconstructing from terminal output (head/tail), do I have ANY evidence the output was truncated?

**Rule of thumb:** If you called `read_file(path)` earlier in the session and the result had `truncated: true` or you used `limit=` to constrain lines, you do NOT have the full file. Re-read without limit.
