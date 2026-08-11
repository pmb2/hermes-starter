# Pulse Brain Health Remediation

When running a pulse cycle that interacts with gbrain, check brain health and
remediate low-scoring areas proactively rather than just reporting them.

## Workflow

### 1. Check Health

```python
get_health()  # brain_score, orphan_pages, stale_pages, link_coverage
```

Thresholds that warrant action:
- **brain_score < 60** — needs cross-linking
- **orphan_pages > 50% of page_count** — disconnected graph
- **link_coverage == 0** — zero internal linkage

### 2. Find Orphans

```python
find_orphans(include_pseudo=False)
```

List all orphaned pages (no inbound wikilinks). These are candidates for
strategic linking.

### 3. Categorize Link Candidates

Group orphans by domain/prefix (e.g., `advisors/`, `notes/`, `pulse/`):

| Domain | Likely links to add | Relationship |
|--------|---------------------|--------------|
| `readme` | → `notes/*`, `companies/*`, `people/*` | Directory → content |
| `notes/*` | → `readme`, → `tests/*` | Content → root + verification |
| `advisors/*` | → `pulse/*` | Event → report |
| `companies/*` | → `readme` | Data → directory |
| `people/*` | → `readme` | Data → directory |
| `pulse/*` | → linked entities | Report → referenced pages |

### 4. Add Links (Batch)

Add strategic cross-links one at a time. Prioritize:

1. **Root docs** (`readme`) linking to setup/install/config notes — these are
   the entry points someone hitting the brain reads first
2. **Content docs** linking back to root — establishes bi-directional connectivity
3. **Verification pages** linking from the setup they validate — connects
   evidence to process
4. **Related entities** across domains — advisor entries linking to pulse reports,
   companies linking to people

### 5. Verify Improvement

```python
get_health()  # re-check brain_score, orphan_pages
```

Report the delta:
```
brain_score Δ: 45 → 76 (+31) | orphans: 10 → 3
```

### 6. Report the Delta in Pulse Output

In the pulse report, include a one-line status with before/after:
```
- gbrain health improved 45→76 (+31), 8 links added, orphans 10→3
```

## Link Types to Use

| Link Type | When | Example |
|-----------|------|---------|
| `references` | General knowledge reference | `readme → notes/gbrain-install` |
| `part-of` | Hierarchical membership | `people/readme → readme` |
| `related-to` | Peer relationships | `advisors/advisor-A → pulse/report-X` |

## When NOT to Link

- Don't link purely for score improvement. The connection should be semantically
  meaningful — a human should agree the two pages are related.
- Don't link auto-generated pages to each other unless they share an entity
  reference. Pulse pages and advisor pages from the same date are valid links.
- Don't link pages from different knowledge domains without a clear rationale.
  A companies page and a pulse page are not related unless the pulse mentions
  the company.

## Verification

After linking, confirm:
- [ ] brain_score improved measurably (check before/after)
- [ ] orphan_pages count dropped
- [ ] all remaining orphans are intentional (auto-generated entries awaiting
      backlinks from future content, or genuinely unrelated)
- [ ] no dead links were created (links point to valid slugs)
