# Pulse Log File Recovery

Recovering a PULSE.md (or any append-only cron log) after accidental truncation by `write_file`.

## Problem

You read a log file using `read_file(path, offset=N, limit=N)` (pagination mode), then called `write_file(path, content)` using only the partial content you had in context. The tool warned:

```
"was last read with offset/limit pagination (partial view). Re-read the whole file before overwriting it."
```

But you wrote anyway. The file is now truncated — only N lines remain instead of the original length.

## Recovery Pattern

1. **Do not panic.** Every `read_file` result from this session is in the conversation history. Each line is prefixed with `N|CONTENT` where N is the original line number.

2. **Reconstruct from session reads.** Your earlier `read_file` calls returned line-numbered content. Strip the `N|` prefixes to recover the raw markdown:

```
# From tool output:
501|  - 🟡 **37 tests still missing**: mempalace (20) + docker_lifecycle (17) stripped upstream, not re-applied

# Strip line prefix → clean markdown:
  - 🟡 **37 tests still missing**: mempalace (20) + docker_lifecycle (17) stripped upstream, not re-applied
```

3. **Assemble the full file.** Merge all read segments in order (offset=1 + offset=N + offset=M + ...) into a single content string.

4. **Write the full file back** — now with all content, not just the partial window.

## Prevention

Shift the tool-warning from a "warning you'll read later" to an enforced pre-check:
- Before ANY `write_file(path)` call on a file you've previously `read_file` with offset/limit, the check is: **do I have lines 1 through N in my current context where N ≥ total_lines in the original**? If not, re-read without offset/limit first.
- Use the safe pattern: `read_file(path)` → construct existing + new entry → `write_file(path)`.
