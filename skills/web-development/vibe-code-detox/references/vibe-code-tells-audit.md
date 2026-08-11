# Vibe-Code Tells — Source Notes & Fix Guide

Source: JordanKodes, YouTube Short `xz_lJKdODjw` (Jul 2026). Condensed from the video review session where the five tells were mapped into the agent fleet's website-building workflow.

## The Five Tells (with deeper fix notes)

### 1. Blue-purple gradients everywhere
The single most-recognized AI tell. Default Tailwind-ish `linear-gradient(to right, blue, purple)` heroes, cards, buttons.
**Fix:** Industry/brand palette. For local service sites, the per-niche theme system (e.g. navy for plumbers, forest for landscapers) already solves this — the failure mode is falling back to the generic default. Audit gradient hex families: `#3b82f6`, `#2563eb`, `#1d4ed8` paired with `#8b5cf6`, `#7c3aed`, `#a855f7` are the fingerprint.

### 2. Em-dashes in copy
LLMs lean on `—` constantly; human marketing copy almost never uses it. One em-dash on a page is fine; three+ is a tell.
**Fix:** Rewrite with commas, periods, or colons. If the dash is load-bearing, split the sentence. Run a find-and-replace pass over all content before ship — cheap and catches everything.

### 3. Mobile layout cutoff
Desktop-only testing. Overflow-x, truncated CTAs, hero text clipped, cards bleeding off-screen.
**Fix:** 375px viewport check on every page before ship. No static analyzer can catch this — it needs a real render. Browser DevTools device emulation is the minimum; a phone is better.

### 4. Badge pill above the hero H1
`<span class="badge">New</span>`, "Introducing...", "🚀 Now live" chips floating over the headline. Every AI landing-page generator emits this layout.
**Fix:** Delete unless it carries real, current information ("Now serving Saratoga County", actual pricing). If the page works without it, it was decorative — remove.

### 5. Footer missing legal pages
No Terms / Privacy links. Real businesses have legal pages; one-shot generators skip them.
**Fix:** Ship `/privacy` and `/terms` on every site, even template boilerplate, linked in the footer. Also matters for ad-network approval and basic trust signals — not just aesthetics.

## Session Application Notes (Jul 2026)

- Mapped into SOUL.md for both Hermes and Chief of Staff profiles: consult this audit on any website build task.
- `AGENTS.md` added to `website-landlord/astro-sites/service-template/` so any agent working in the template inherits the rules.
- The standalone script at `~/AppData/Local/hermes/scripts/vibe_code_detox.py` and the packaged `scripts/vibe_code_detox.py` in this skill are the same audit — prefer the packaged copy as canonical.

## Related (broader) Anti-Slop Work

The `website-landlord-astro-builder` skill carries the deep design-system references (`ai-slop-avoidance-2026.md`, `anti-ai-slop-design-system-2026.md`) — 3-pass polish, semantic tokens, per-niche themes, layout variants. This detox audit is the 10-second surface check that runs on every build; use the deep references when a site needs a real redesign, not just a lint pass.
