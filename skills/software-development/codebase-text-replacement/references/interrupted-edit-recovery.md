# Interrupted-Edit Recovery (Windows patch tooling)

Class of failure seen July 2026: a long multi-patch editing session gets interrupted
(mid-turn context compaction / transport error). When the session resumes, the patch
tool has already applied some hunks — the target file now contains DUPLICATE or
OVERLAPPING blocks, and further patches applied on stale assumptions mangle it worse
(wrong indentation, half-deleted functions, orphaned code).

## Recovery procedure (in order)

1. STOP patching. Do not attempt incremental fixes on a suspected-mangled file.
2. Read the ENTIRE file (paginate through all of it) and map the damage regions.
3. If damage is localized (<30% of file): delete the duplicated region with one
   surgical patch whose old_string spans the full duplicate block.
4. If damage is spread out: rewrite the whole file with write_file. Get the clean
   head and tail by reading the file, then compose head + new body + tail in one
   write. Strip `NNN|` line-number prefixes from read_file output before reusing it.
5. Immediately syntax-check the rewrite:
   - Python: `python -c "import ast; ast.parse(open('f.py',encoding='utf-8').read())"`
   - Astro/TS: `npm run build`
6. Only then continue with the original task.

## Pitfalls

- When reconstructing head+body+tail, verify the head's LAST line and the tail's
  FIRST line. Cutting mid-signature (e.g. inside a `def run(...)` parameter list)
  produces `SyntaxError: '(' was never closed` — the most common reconstruction bug.
- A partial rewrite that drops trailing lines of a function signature needs the
  missing lines re-added as a separate small patch BEFORE running the syntax check.
- After ANY interrupted turn, run a syntax check before the next edit even if you
  believe all patches landed — interrupted patch series are often invisible until
  the file is parsed.
