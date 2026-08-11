# gbrain Orphan Cross-Linking (Weaver Pulse)

Resolves `orphan_pages` in gbrain by linking consecutive pulse pages. Verified live Aug 7 2026:
2 orphans → 0, brain score 83 → 85 (`no_orphans_score` 13 → 15). PULSE.md had flagged these
orphans as Next Action for multiple cycles before the working sequence was found.

## Tool sequence (all via `mcp__gbrain__*`)

1. **Health snapshot** — `mcp__gbrain__get_health` → read `orphan_pages`, `brain_score`, `page_count`.
2. **Identify orphans** — `mcp__gbrain__find_orphans` → returns `orphans: [{slug, title, domain}]`.
   Pulse pages in the `pulse/` domain are the recurring ones (infra pulses).
3. **Find chain neighbors** — `mcp__gbrain__list_pages` → all pages sorted with `updated_at`.
   The pulse chain is temporal: each page has a predecessor (earlier same-day or prior-day page).
   An orphan is a page nobody links TO — link it to its chronological predecessor so the chain
   is traversable. Do NOT link to arbitrary pages; keep `precedes` edges meaningful.
4. **Add links** — `mcp__gbrain__add_link`:
   - `from`: the orphan slug (e.g. `pulse/infrastructure-2026-08-03-1045`)
   - `to`: its chronological predecessor (`pulse/infrastructure-2026-08-03` = 06:42 ET page)
   - `link_type`: `precedes` (the temporal semantics gbrain reconciliation expects)
   - `link_source`: `integration-lead-pulse` (provenance tag; `manual` is the default if omitted)
   - `context`: short human note ("Temporal pulse chain — 18:59 ET pulse follows 10:45 ET pulse same day")
   Link the 18:59 page → 10:45 page AND the 10:45 page → 06:42 page (each orphan gets its own edge).
5. **Verify** — `mcp__gbrain__get_health` again → expect `orphan_pages: 0` and score bump.

## Naming/temporal notes

- Pulse slugs encode ET time: `pulse/infrastructure-2026-08-03-1045` = Aug 3 10:45 ET,
  `pulse/infrastructure-2026-08-03` = Aug 3 06:42 ET (no time suffix = earliest of the day).
- `list_pages` output is sorted newest-first — read `updated_at` to reconstruct the chain.
- gbrain health fields: `embed_coverage` (1 = 100%), `stale_pages`, `orphan_pages`,
  `missing_embeddings`, `brain_score` (composition of embed_coverage_score, link_density_score,
  no_orphans_score, no_dead_links_score). Score 85 = max no_orphans_score (15) + 10 dead-links.

## Why it's the ideal "one meaningful action" for a quiet pulse

Cheap (4 tool calls), deterministic (verify = score delta), and clears a chronic PULSE.md
Next Action that otherwise accumulates cycle after cycle. Run it when the fleet is healthy
and no integration fix is pending.
