# Legacy Tree Bulk Retirement — Case Study (2026-08-01 Skillmate Pulse)

Retired the inert `~/.hermes/skills/` legacy tree (NOT in the loader path — loader =
HERMES_HOME + `external_dirs` only). This is the reusable procedure + pitfalls.

## Procedure (reusable)

1. **Enumerate with pathlib, not `find`** — `pathlib.Path(root).rglob("SKILL.md")` is ground
   truth. On this MSYS host, `find` silently skipped `find-skills/` and `skybridge/` (88 vs 90
   count), so every prior `find`-based pulse count was off by 2.
2. **Compute legacy-only set** — name-set difference vs load path (HERMES_HOME + external_dirs):
   ```python
   load_names = {p.parent.name for root in load_roots for p in root.rglob("SKILL.md") if ".archive" not in p.parts}
   legacy_only = [p.parent.name for p in legacy_root.rglob("SKILL.md") if ".archive" not in p.parts and p.parent.name not in load_names]
   ```
3. **Promote legacy-only skills FIRST** (before archiving) — copy to the load path with the
   right category, validate frontmatter (`yaml.safe_load` on the head block, check triggers).
   2026-08-01: `find-skills` (5.8KB, skill-discovery, 9 triggers) → `curation/find-skills`;
   `skybridge` (3.4KB, ChatGPT/MCP apps, 7 triggers) → `software-development/skybridge`.
4. **Diff FULL skill dirs, not just SKILL.md byte sizes** — compare references/templates/scripts
   trees too:
   ```python
   legacy_files = {str(p.relative_to(skill_dir)) for p in skill_dir.rglob("*") if p.is_file()}
   ```
   A "missing support file" in the load path is usually an **intentional anti-collision rename**
   (Pitfall 17 convention): `airtable.md`→`airtable-design.md`, `notion.md`→`notion-design.md`,
   `spotify.md`→`spotify-design.md`, `styles/notion.md`→`styles/notion-style.md`. Before flagging
   a loss, grep the load-path SKILL.md for the filename — if unreferenced, it's not a loss.
5. **Archive wholesale, dated batch** — `shutil.move` every stale category dir into
   `.archive/legacy-stale-YYYY-MM-DD/` preserving category structure. Reversible, consistent
   with existing `.archive/` practice. 2026-08-01: 27 items moved (22 category dirs + loose
   `vibe-code-detox.md`), 91 SKILL.md archived.
6. **Verify zero content loss** — every archived SKILL.md's name must exist in the load-path
   name set (91/91 on 2026-08-01). Also verify no source-code dirs (src/dist/test per gstack
   lesson) were swept — legacy `comfyui/tests/` + `google-workspace/scripts/setup.py` flagged but
   confirmed benign (dups with load-path copies).
7. **Post-state check** — legacy tree should contain only `.archive/`; note the tree is retired
   so future pulses stop re-scanning it.

## Key numbers (2026-08-01)

- Legacy tree: 90 SKILL.md (pathlib) — 88 stale dups + 2 legacy-only
- Load path at retirement: 477 skill names (421 AppData + 46 external C: hermes-config + 10 flat)
- Archived: 91 SKILL.md under `.archive/legacy-stale-2026-08-01/`
- Zero content loss: 91/91 archived skills have load-path counterparts
- Promoted: `curation/find-skills` (5.8KB), `software-development/skybridge` (3.4KB)

## Pitfalls

- **`find`/`comm` counts are wrong on MSYS** — always cross-verify with pathlib before acting
  on a "0 legacy-only" or "N dups" conclusion.
- **Byte-size SKILL.md comparison is insufficient** — support-file drift hides in
  references/templates/scripts; compare full trees.
- **Don't archive before promoting legacy-only skills** — they'd be silently lost (the exact
  risk this pulse averted).
- **Dated batch names** — `.archive/legacy-stale-2026-08-01/` makes the retirement auditable and
  reversible; avoid bare `.archive/` mixes.
