# Gstack File-System Duplication Audit

**Detected:** 2026-07-20 Skillmate pulse  
**Scope:** 4 skills exist as full file copies in BOTH `gstack/` (subdir) AND `gstack-XXX/` (top-level) directories  
**Disk waste:** ~250KB  
**Status:** Resolved (browse/qa/review) · Not applicable (make-pdf — binary-only dir, not a skill dup)

## Description

The gstack skill suite has 54 SKILL.md-bearing directories (as of Jul 20, 2026). Within them, 4 skills are duplicated — their SKILL.md content exists as a full (non-symlink) copy in two locations with near-identical content:

| Skill | `gstack/` subdir | `gstack-XXX/` top-level | Sizes | Notes |
|-------|-----------------|------------------------|-------|-------|
| `browse` | `gstack/browse/` | `gstack-browse/` | 52KB / 53KB | +670B drift (subdir smaller) |
| `qa` | `gstack/qa/` | `gstack-qa/` | 78KB / 79KB | +1.1KB drift (subdir smaller) |
| `review` | `gstack/review/` | `gstack-review/` | 92KB / 80KB | -12KB drift (subdir larger — significant divergence) |
| `make-pdf` | `gstack/make-pdf/` | `gstack-make-pdf/` | binary-only / 31KB | Subdir has NO SKILL.md — contains `pdf.exe` (98MB binary). Invalid as a skill entry; the top-level `gstack-make-pdf/` is the real skill. |

## Detection Script

```bash
cd ~/AppData/Local/hermes/skills
# Get gstack/ subdir skill names
ls -d gstack/*/ 2>/dev/null | sed 's|gstack/||;s|/||' | sort > /tmp/gstack_subs.txt
# Get gstack-XXX top-level skill names
ls -d gstack-*/ 2>/dev/null | sed 's|gstack-||;s|/||' | sort > /tmp/gstack_tops.txt
# Find skills in both = duplicates
echo "=== Duplicated (BOTH locations) ==="
comm -12 /tmp/gstack_subs.txt /tmp/gstack_tops.txt
# Compare sizes
for name in $(comm -12 /tmp/gstack_subs.txt /tmp/gstack_tops.txt); do
  sub_size=$(wc -c < "gstack/$name/SKILL.md" 2>/dev/null || echo "0")
  top_size=$(wc -c < "gstack-$name/SKILL.md" 2>/dev/null || echo "0")
  echo "$name — subdir: ${sub_size}B, top-level: ${top_size}B"
done
```

## Why This Happened

The gstack skill suite is generated/maintained externally and installed as a flat set of top-level `gstack-XXX/` directories plus a `gstack/` umbrella directory that contains its own sub-directory trees. The `gstack/browse/` subdir is the original location; the `gstack-browse/` top-level was added later for bare-name resolution. Neither was cleaned up when the other location was added, creating full file copies instead of deduplicating.

## Remediation Options

### Option A — Remove `gstack/` subdir versions (preferred)
If the top-level `gstack-XXX/` skills are the canonical source:
```bash
# For each dup, verify content is equivalent first
diff gstack/browse/SKILL.md gstack-browse/SKILL.md | head -30
# Remove subdir version if content is superseded
rm -rf gstack/browse
rm -rf gstack/qa
rm -rf gstack/review
rm -rf gstack/make-pdf    # binary-only dir (98MB pdf.exe, no SKILL.md)
```
**Risk:** Breaks `gstack/` as an umbrella — any process that walks `gstack/*/SKILL.md` loses these 4 entries.

### Option B — Convert subdir versions to symlinks
Replace subdir copies with directory symlinks pointing to the top-level canonical location. This preserves the gstack umbrella structure without duplicating bytes:
```bash
# Delete subdir copy
rm -rf gstack/browse
# Create NTFS directory symlink (NOT ln -s on MSYS — that copies)
cmd /c mklink /D "$(pwd -W)/gstack/browse" "$(pwd -W)/gstack-browse"
```
**Risk:** Depends on NTFS reparse-point support; won't survive a cross-filesystem copy. Also, the `rmdir` check in some tools resolves symlinks transparently, but `find -type d` may count them differently.

### Option C — Leave as-is (acceptable)
The duplication is cosmetic — 250KB on a modern SSD is negligible. No skills loading is affected because each path resolves independently. The only cost is inflated `find`/`ls` counts and confusion during audits.

## Pitfalls

- **`ln -s` on MSYS copies directories instead of symlinking** — Always use `cmd /c mklink /D <link> <target>` for directory symlinks on Windows/MSYS.
- **Content may have minor drift** — The `review` subdir (92KB) is 12KB larger than its top-level counterpart (80KB). Check `diff` before removing either copy.
- **Some gstack skills exist ONLY in `gstack/` subdir** — `bin` and `design` have no top-level counterpart. Don't blanket-remove `gstack/*/`.
- **The gstack install process may re-create subdir copies** — if gstack is re-installed after remediation, the duplication may return. Document the expected state so the timing of re-detection can be distinguished from failure.

## Drift Resolution Procedure

When gstack top-level wrappers (`gstack-XXX/`) and subdir canonical copies (`gstack/XXX/`) have drifted — same skill, different content — use this procedure to re-sync without removing either location.

### Step 1: Confirm drift direction

Compare sizes and actual content:

```bash
cd ~/AppData/Local/hermes/skills
for name in browse qa review; do
  sub=$(wc -c < "gstack/$name/SKILL.md" 2>/dev/null || echo 0)
  top=$(wc -c < "gstack-$name/SKILL.md" 2>/dev/null || echo 0)
  diff_size=$((top - sub))
  sign="+" && [ "$diff_size" -lt 0 ] && sign=""
  echo "$name — subdir: ${sub}B, top-level: ${top}B (${sign}${diff_size}B drift)"
  diff "gstack/$name/SKILL.md" "gstack-$name/SKILL.md" | head -10
done
```

### Step 2: Determine which copy is canonical

The `gstack/` subdir versions are the canonical gstack source. Key indicators:

| Signal | Canonical (subdir) | Wrapper (top-level) |
|--------|-------------------|-------------------|
| Has `preamble-tier` | ✅ Yes | ❌ No |
| Has `allowed-tools` | ✅ Yes | ❌ No |
| Has `name:` matched to skill | ✅ Yes | ❌ No |
| Has gstack tags | `[gstack, browse, ...]` | No `gstack` prefix |
| Rich descriptions | Compact inline | Richer, more specific |

The subdir version carries gstack-runtime metadata (`preamble-tier`, `allowed-tools`) that the top-level wrapper lacks. This makes the subdir the **authoritative** copy — the top-level wrapper exists only for bare-name resolution and should mirror the subdir.

### Step 3: Sync wrapper from canonical

```bash
cd ~/AppData/Local/hermes/skills
cp gstack/browse/SKILL.md gstack-browse/SKILL.md
cp gstack/qa/SKILL.md gstack-qa/SKILL.md
cp gstack/review/SKILL.md gstack-review/SKILL.md
```

### Step 4: Verify match

```bash
cd ~/AppData/Local/hermes/skills
for name in browse qa review; do
  diff "gstack/$name/SKILL.md" "gstack-$name/SKILL.md" > /dev/null 2>&1 \
    && echo "✅ $name: MATCH" \
    || echo "❌ $name: DRIFT PERSISTS"
done
```

### Step 5: Note `make-pdf` exception

`gstack/make-pdf/` is a binary-only directory (contains `pdf.exe` at 98MB but NO `SKILL.md`). It is NOT a skill duplicate — the top-level `gstack-make-pdf/` is the real skill entry. Do not attempt to sync or remove this pair.

### When to use this (vs. Options A/B/C)

Use this **sync-wrapper** approach when both locations are intentionally kept for different resolution purposes and you only need to correct content drift. Use Options A/B/C (above) when the duplication itself is the problem (disk waste, count inflation) and you want to eliminate the dual location entirely.

## Resolution Worklog

| Date | Action | Verified By |
|------|--------|------------|
| 2026-07-20 23:22 ET | browse/qa/review synced from `gstack/` subdir → `gstack-XXX/` top-level wrappers. `cp` + `diff` verification. `make-pdf` confirmed binary-only (no action). | Skillmate pulse ✅ |

