# Scan-Flagged Regressions Can Self-Resolve (concurrent writers)

Worked example for the core rule "verify before reporting negatives" — with
the twist that the SCAN can be wrong even when the file is fine.

## Case (2026-08-08 Scribe pulse)

A library-health scan (YAML frontmatter audit over the local skills tree)
flagged `data-engineering/market-signal-scanner` as NO_TRIGGERS. Over the
next few minutes the file was observed in THREE different states:

1. Health scan: frontmatter with no `metadata.hermes.triggers`
2. `read_file` (minutes later): 4-line frontmatter — even OLDER state
3. `cat -A`: version/author/license present (middle state)

Re-inspection showed the full `metadata.hermes` block with 7 triggers already
present. A concurrent skill-sync / hub-import process was mid-write during
the scan and completed its write between scan and inspection. Re-scan:
465/465 clean, zero patching needed.

## Why it matters

- Patching a mid-write file wastes the cycle and can fight the sync writer
  (overwrite its in-flight metadata, or get clobbered by it).
- Reporting a concurrent-write artifact as a "regression" poisons the
  Next-Action chain: the next pulse inherits "market-signal-scanner needs
  frontmatter fix" and re-fixes a file that was never broken.

## Rule

**Re-scan (or re-read the file) immediately before patching any scan-flagged
regression.** If the second pass is clean, the flag was a mid-write snapshot —
report it as a concurrent-write artifact, do not "fix" it.

## Tell-tale signs of a mid-write snapshot

- The same file shows inconsistent states across two read tools within
  minutes (scan vs read_file vs cat -A disagreeing).
- The flagged field is `metadata.hermes` — the LAST block written when a
  skill is created/updated (name → description → metadata.hermes order).
- The file mtime is within the last few minutes of the scan.
- Known sync processes are active (external_dirs sync, hub imports,
  Skillmate canonical syncs).
