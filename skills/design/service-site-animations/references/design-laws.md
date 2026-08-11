# Service Site Design Laws (the operator, July 2026)

Non-negotiable rules for every template, every generator output. Zero tolerance.

## Law 1: No Badges, Pills, or Chips

Never render any of these in visible content:
- "Niche — City, Region" pills or tags
- "★ rated · N clients" rating badges
- "Auto Repair Shop — Kingston, NY" location tags
- Category/tier badges of any kind
- Decorative pill/chip/category elements

These are dead AI-slop giveaways. Real service sites don't have them.

## Law 2: No Star Ratings

Never render `★` (star) characters anywhere:
- No star ratings in hero sections
- No star ratings in review cards
- No star ratings in trust badges
- No star display functions (remove `stars()` helper)
- No rating: N/5 displays

## Law 3: No Em Dashes in Rendered Content

Replace all `—` (em dash, U+2014) in:
- Template copy text
- Meta descriptions
- Section headers
- Hero taglines
- Any text visible to users

Use commas, periods, spaces, or restructure the sentence. Em dashes in
JSDoc comments and code comments are fine (they don't render).

## Law 4: No Middle Dot Badge Separators

The `·` (middle dot) character used as a badge separator between niche
and city is itself a badge pattern. Remove it.

Bad: `{niche} · {city}`, `{rating} · {reviews}`
Good: Natural prose: "Serving {city}, {region}"

## Law 5: Per-Site Uniqueness

Every generated site must look different from every other:
- Use different template variants (not the same template for all businesses in a niche)
- Use different color palettes per business
- Vary stats: yearsInBusiness, reviewCount, jobsCompleted, rating
- Never produce two sites that share the same hero→CTA→footer rhythm

The variant engine in variants.py handles this via per-business-name hash seed.

## Source

These laws originate from the operator's corrections during website-landlord development (July 2026).
All templates and generator code should already be compliant.

## Verification Checklist

After any template change, verify ALL deployed dist files, not just source:

```bash
# Check dist files for remaining violations
grep -c '—' dist/index.html          # em dashes → 0
grep -c '★' dist/index.html          # stars → 0
grep -c '·' dist/index.html          # middle dots → 0 (in rendered context)
grep -c '&lt;svg' dist/index.html    # escaped SVGs (text, not elements) → 0
```

Source files can have em dashes in comments; dist files must be zero.
Don't trust GH Pages cache — check local dist/ after each build.
