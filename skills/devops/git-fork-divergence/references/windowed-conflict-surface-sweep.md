# Windowed Conflict-Surface Sweep (pulse cadence)

For fork-divergence monitoring on a **pulse cadence** (checks every few hours), the merge-base audit is heavy for a cycle check. The cheaper per-cycle question: **which of MY patched files did upstream touch since MY LAST CHECK?** This drives triage — which files need a deep-dive now, which can wait.

## The sweep

```bash
git fetch origin   # always step 1 — a stale ref silently corrupts the sweep
# For each file in your local patch set, count upstream commits in the window:
for f in tools/approval.py hermes_cli/model_switch.py cron/scheduler.py; do
  n=$(git log --oneline --since="2026-08-07 09:30:00 -0400" origin/main -- "$f" | wc -l)
  [ "$n" -gt 0 ] && echo "=== $f ($n) ===" && \
    git log --oneline --since="2026-08-07 09:30:00 -0400" origin/main -- "$f"
done
```

⚠️ **Timezone trap: `--since`/`--until` parse in LOCAL time.** Pass the previous pulse's time converted to local, or better, diff against the previous fetch's ref — `git log --oneline origin/main@{1}..origin/main -- "$f"` — which is timezone-immune (the reflog delta).

**Per-file hit counts, not just presence.** `git log --since ... origin/main -- <file> | wc -l` per patched file, sorted descending, tells you which zone is hottest THIS window (`gateway/run.py: 13` vs `model_switch.py: 5`). The flat `--name-only` union only says "touched or not."

**Include YOUR OWN files in the sweep — especially test files.** Upstream commits landing on test files you created/modified locally is an early, sharp signal of parallel work on the same feature. When you cherry-picked an upstream feature commit but wrote your own test suite for it, upstream often evolves the same feature independently and their test additions land under the SAME path (see add/add below).

**Free-gains triage — hits on files NOT in your stack are wins, not risks.** When the sweep grep (filtered to your patched files) shows hits, also run the unfiltered `--name-only` list and look for upstream commits on files you have NO local patch on (e.g. `hermes_state.py`, `config_defaults.py`) and brand-new modules upstream created (detect via `git diff --diff-filter=A --name-only <base>..origin/main`, e.g. `hermes_cli/resource_limits.py` + its test file). Classify these as **free gains**: adopt-on-rebase additions, zero conflict surface — add them to the rebase plan's "gain" column so they don't get dropped in the merge. Observed Aug 11 2026: of 4 upstream hits in a 4h window, 2 (hermes_state.py, config_defaults.py) were outside the local stack entirely and 1 (`acb7547dac` nofile-limit) created a new module 1000+ lines away from any local hunk — the only real touchpoint was `6a7cf19302` on run.py, and even that was ~200 lines below our nearest hunk (:22296/:22310) → context-shift grade.

**Quantify hunk distance before classifying — line numbers, not vibes.** For each hit, compare `git show <sha> -- <file> | grep -E "^@@"` (upstream hunk lines) against `git diff origin/main...HEAD -- <file> | grep -E "^@@"` (your hunk lines). Same file is NOT the same zone: upstream hunk at :27267 vs your hunks at :260-22310 is effectively zero-risk; ~200 lines of separation is context-shift; any overlap is structural. Record the nearest-pair distance so the next cycle can spot drift toward your zone.

## Digest-script `[SILENT]` is the script's own gate, not an order

Pulse jobs that append findings to a shared daily digest (e.g. `append-digest.py` in a the planning repo repo) may print `[Digest] Quiet hours … saved to digest only` + `[SILENT]` **even when the job's own TZ gate says it is NOT quiet hours** (observed Aug 11 2026 03:29 UTC: job gate returned 23:29 ET → report delivered, digest script simultaneously self-suppressed its own channel). The script evaluates quiet hours independently (its window can disagree with the job's `TZ=EST5EDT` gate — check whether it's UTC-based vs ET-based if it keeps firing at the wrong hour). Consequences for the job:
- Do NOT read the script's `[SILENT]` as an instruction to suppress YOUR report — your delivery decision comes from the job's own quiet-hours check.
- Do NOT treat the script's "saved to digest only" as a failed append — the content DID land; only the script's own notification was suppressed.

## Hunk-region classification

For every hit, classify the collision by comparing hunk regions:

```bash
# Upstream's changed line ranges:
git show <sha> -- <file> | grep -E "^@@"
# Your patch's region (marker lines) in the current tree:
grep -n "<your-patch-marker>" <file>
```

| Upstream hunks vs your region | Verdict |
|---|---|
| All hunks above/below your region, different function | Context-shift only — rebase merges clean, trivial conflicts at most |
| Hunks inside the same function as your patch, non-overlapping lines | Same-function — verify orthogonal (audit checklist item 5); may add merge touchpoints |
| Hunks overlap your lines | Structural conflict — plan semantic re-apply |
| No line overlap, but upstream changed the PATTERN your patch uses | **Last-instance drift** (below) |
| Both sides ADDED the same path since merge-base | **Add/add collision** (below) |

## Two-dot diff trap — combined hunks include YOUR OWN additions

The naive "where did upstream touch this file" scan is `git diff HEAD..origin/main -- <file> | grep -E '^@@'`. **That is a full-branch diff, not an upstream diff** — the old-side (`-`) hunk locations are YOUR tree's lines, and every line your local commits added shows up as a deletion because upstream doesn't have it. So a combined-diff hunk at old-:2501 that "matches your call site at :2501" proves nothing about upstream touching your zone — you're looking at your own patch reflected back at you.

The true upstream-only surface anchors at the fork point:

```bash
MB=$(git merge-base HEAD origin/main)
git diff $MB..origin/main -- <file> | grep -E '^@@'     # upstream-only hunks (old side = merge-base file)
git log --oneline $MB..origin/main -- <file>            # upstream commit list for attribution
```

Old-side numbers in the merge-base-anchored diff refer to the merge-base file version; genuine overlap only exists where those hunks fall inside line ranges your local commits added. For per-commit precision (attributing a specific hunk to a specific upstream commit), use `git show <sha> -- <file> | grep -E '^@@'` — the reference's `git show` form is the safe one; the two-dot `git diff HEAD..origin/main` form is the trap.

### Worked example — Aug 11 2026, `tools/file_operations.py` vs commit #29

The 08-10 23:27 pulse flagged "commit #29 (`96c21f39a`, MSYS→native rg/grep path fix) adds a small file_operations.py conflict zone" as a rebase risk. Verifying it this cycle:

1. Combined diff (`git diff HEAD..origin/main -- tools/file_operations.py | grep '^@@'`) showed hunks at old-:2501/:2516/:2600 — **exactly** our #29 call-site lines. Alarming; looked like upstream landed on our patch.
2. Merge-base-anchored diff (`git diff $(git merge-base HEAD origin/main)..origin/main`) showed the REAL upstream surface: all hunks ≤:1957 (read/parse/pipeline region) plus one 1-line hunk at :2684. Nearest distance to our #29 search region (:2501-:2736) is ~52 lines at :2684, and that hunk is in a different function → **context-shift grade, zero overlap**.
3. The first-step "hunks at :2501" were #29's own additions appearing as `-` deletions — pure misattribution. Standing risk retracted; file dropped off the conflict list.

**Lesson:** when a combined-diff hunk lands on your patch's lines, don't panic and don't classify — re-run anchored at the merge-base (or per-commit `git show`) before any verdict. The two-dot diff is only safe for the *file-level* overlap questions (`--name-only`), never for hunk-line-level attribution.

## Last-instance drift — the silent one

Upstream can change the architecture of a function **without touching your lines**: they introduce a cached/refactored variant of a call and migrate all call sites, while your patch (merged earlier, different region) still uses the raw old call. Git merges cleanly — **no conflict** — but your patch is now the LAST instance of the pattern upstream is eliminating. It's not "still needed" as-is; it's "still needed but wrong-shaped": plan a rebase-time adaptation onto the new API.

Detection requires reading what the upstream commit actually does (`git show <sha> --stat` + the changed lines), **not** just counting file hits.

**Signature evolution is last-instance drift too.** When upstream adds a parameter to a function you adopted and reworks its call sites (e.g. `cache_only` kwarg + `cache_only=not _probe_live` pattern), your call site — even if it merged cleanly a cycle ago — is now on a changed API. Your `timeout=1.5 if for_picker`-style hack becomes obsolete even though git reports no conflict. Re-check the signature of every adopted function each cycle, not just at rebase.

## Add/add collision — parallel feature work on the same path

**The signature:** `git diff origin/main...HEAD -- <path>` shows the file as `new file` (both sides added it since the merge-base), yet `git ls-tree origin/main -- <path>` shows the path EXISTS upstream. Detection:

```bash
# 1. Files you created that upstream also has:
git diff origin/main...HEAD --name-only --diff-filter=A | while read f; do
  git ls-tree origin/main -- "$f" >/dev/null 2>&1 && echo "ADD/ADD: $f"
done

# 2. How far the two versions diverge:
git diff origin/main HEAD -- "$f" | grep -c "^[+-]"   # 159 lines = real merge work

# 3. Which upstream commits created/evolved it:
git log --oneline origin/main -- "$f"   # created by the feature commit you adopted,
                                        # then evolved by follow-ups
```

**Why it happens:** you cherry-picked the *function* half of an upstream feature commit (e.g. `fb435aae9`'s `models.py +95`) but wrote your OWN test file under the same path the upstream commit itself used. Upstream's follow-up PRs then evolve their test file independently → both branches carry the same path with divergent content.

**Rebase reality:** this is real merge work, not context-shift — combine the two suites (your contract class + their new contract class), keeping both invariants. The upstream test often pins NEW behavior (e.g. `cache_only` no-probe semantics) that reveals what your rebase-time adaptation must satisfy.

## Worked example — Aug 7→10 2026, Hermes Agent `model_switch.py` cached-catalog zone

**Aug 7 (planned):** Upstream `fb435aae9` added `cached_fetch_api_models()` (TTL disk cache for custom-provider `/v1/models` probes) and migrated 3 probe sites in `list_authenticated_providers()`. Our OmniRoute lock's picker row (same function, local lines ~2045-2110 vs upstream hunks at :2725/:2795/:3039) still did a raw `urllib.request` probe with a 5s timeout. Zero line overlap → clean, but last-uncached-instance → plan rebase-time swap.

**Aug 7 (executed, #26 `3bc78f53d`):** Swapped the picker row to `cached_fetch_api_models("", base, timeout=1.5 if for_picker)`. Pulse declared the zone "byte-identical to upstream — context-shift grade only."

**Aug 10 (the trap):** Upstream `e0c3caf3b` (#81973) evolved the SAME feature: added `cache_only` to `cached_fetch_api_models()` (+21 `models.py`) and split all 3 call sites into `cache_only=not _probe_live` (:2726/:2814/:3094). The "byte-identical" zone is now real merge work again — and `tests/hermes_cli/test_cached_fetch_api_models.py` is an **add/add collision** (our 207-line cache-contract suite vs upstream's version evolved +67 lines by `7cf71c32b` + `e0c3caf3b`; 159 diff lines).

**Lessons:**
- A clean/byte-identical classification is **per-pulse, not persistent**. Upstream continuing the same feature area is the #1 way context-shift becomes real conflict between pulses. Re-sweep every cycle; never carry last cycle's "clean" verdict forward.
- The rebase adaptation here is to ADOPT upstream's new semantics (`cache_only=not _probe_live`), which subsumes the `timeout=1.5 if for_picker` hack — and to merge the two test suites (their no-probe-open contract pins the `cache_only` behavior your adaptation must satisfy).
- Positive contrast for the same window: upstream `f1c13377a` (cron encoding cluster) also touched `tests/cron/test_cron_script.py`, which we patched — but their tests land in `TestRunJobScript` (:200) while our `TestWindowsBashScriptPathConversion` appends at :372+. Same file, different classes → complementary, NO collision. Verify region placement before assuming the worst.
