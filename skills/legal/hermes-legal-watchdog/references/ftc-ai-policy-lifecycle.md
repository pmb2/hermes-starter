# FTC AI Policy Statement Lifecycle Tracking

Track FTC AI-related policy statements through their full lifecycle from press
release announcement to final rule. This is the primary regulatory pipeline
affecting the operator's AI/ML consulting operations.

## Lifecycle Stages

1. Press release announcement — FTC announces proposed policy statement on
   FTC.gov newsroom, opens public comment
2. Federal Register notice — Formal publication in Federal Register with docket
   number and comment deadline
3. Public comment period — Typically 30-60 days. Submit via regulations.gov
4. Final rule publication — FTC publishes final policy statement incorporating
   (or dismissing) public comments
5. Enforcement — FTC begins enforcing the policy statement

## Tracking Sources

| Stage | Source | URL Pattern |
|-------|--------|-------------|
| Press release | FTC.gov newsroom | `ftc.gov/news-events/news/press-releases?field_press_release_date_value=2026` |
| **FR notice (primary detection)** | **Federal Register API** | `federalregister.gov/api/v1/articles.json?conditions%5bagency_ids%5d%5b%5d=192&conditions%5bterm%5d=artificial+intelligence` |
| Comment deadline | Regulations.gov | `regulations.gov/docket/FTC-2026-XXXX` |
| Final rule | Federal Register (API or HTML) | Same query — check `action` field for "final rule" tag |
| Enforcement | FTC enforcement page | `ftc.gov/enforcement` |

## Detection Note

**The Federal Register API via curl is the PRIMARY detection method for new FTC AI policy statements**, not the FTC press releases page. Reason: `ftc.gov/news-events/news/press-releases` is curl-blocked ("abusive automated request" PWH-Alert), and the CDP browser required to reach it is not always available in cron sessions. The FR API (agency_id=192 + term=artificial intelligence) reliably catches FTC AI-related notices within 1-7 days of publication, with full structured metadata (docket number, comment deadline, abstract). See `references/regulatory-source-access.md` for the working curl example.

## Active Policy Statements to Track (as of Jul 2026)

### FTC AI Accuracy Policy Statement
- **Press release:** Jul 1, 2026 — "FTC Seeks Public Comment on Policy
  Statement Addressing AI Accuracy"
- **URL:** `ftc.gov/news-events/news/press-releases/2026/07/ftc-seeks-public-comment-policy-statement-addressing-ai-accuracy`
- **Federal Register:** Published Jul 7, 2026 (FR Doc 2026-13628, 91 FR 41638)
- **Comment deadline:** Jul 31, 2026 (21-day window)
- **Regulations.gov docket:** `FTC-2026-0859-0013` (`regulations.gov/commenton/FTC-2026-0859-0013`)
- **What it does:** Proposes policy statement declaring that marketing AI systems
  that suppress accuracy constitutes a deceptive act or practice under FTC Act
  §5. Targets companies that manipulate AI system behavior contrary to reasonable
  consumer expectations about accuracy and reliability.
- **Relevance to the operator:** Directly affects AI/ML consulting deliverables,
  particularly regarding accuracy claims in AI product marketing, system behavior
  representations, and consumer-facing AI applications. Any client work involving
  AI accuracy claims should be reviewed against this policy.
- **Status:** ✅ COMMENT PERIOD CLOSED Jul 31, 2026 — final rule not yet published as of Aug 10, 2026 (verified via FR API agency_id=192 + term=artificial+intelligence on Aug 10 sweep; only the Jul 7 notice returned)
- **Next check:** Daily — check for final rule publication (FR API agency_id=192 + term=artificial intelligence). Monitor FTC enforcement actions citing this policy statement.
- **Action items:**
  - Comment deadline **Jul 31, 2026** passed — no comment was submitted
  - Monitor for final rule publication after comment period close (checking daily)

## Checking Procedure (sweep step)

When running the Daily Legal Sweep or Regulatory Update Check:

1. **FR API first (primary detection):** Query the Federal Register API
   (`agency_id=192` + `term=artificial+intelligence` via curl) for new
   AI-related notices. This bypasses FTC.gov CAPTCHA blocks and works in
   cron sessions without a browser backend.
2. If a new notice is found, fetch its full text via `full_text_xml_url`
   to extract the comment deadline, docket number, and key provisions
3. Cross-reference with FTC press releases only if CDP browser is available
   (allow 1-7 days lag between press release and FR publication)
4. Record: docket number, comment deadline, key provisions
5. Check `references/ftc-ai-policy-lifecycle.md` for the tracked item's
   current status — update it with any new findings
6. Track in the next sweep until final rule is published or the statement is
   withdrawn

## Known Pitfalls

| Issue | Recognition | Response |
|-------|-------------|----------|
| FR lag | Press release published but no FR notice yet | Allow 1-7 days. Record the press release and check next sweep. |
| Comment deadline passes | Sweep finds final rule without having tracked comment period | Accept the gap — the final rule is what matters for operations |
| Multiple AI-related actions simultaneously | FTC issues AI policy statements, enforcement actions, and business guidance concurrently | Track each separately in its own pipeline entry |
