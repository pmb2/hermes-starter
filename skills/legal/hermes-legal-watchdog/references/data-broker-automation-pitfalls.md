# Data Broker Opt-Out Automation — Pitfalls & Techniques

## Overview

Most data broker opt-out forms CAN be automated via browser tools (Playwright MCP or CDP browser), but they have specific quirks this file documents. Every site requires some form of email or phone verification that the agent cannot complete without the user.

## Generalized Workflow (All Sites)

1. Fill form with canonical identity (name, email, address, DOB)
2. Handle checkbox/interaction traps (React intercepts, label overlaps)
3. Submit form
4. **User action required:** Click verification link from email, or answer phone/SMS
5. Done — log to removal-tracker.yaml

---

## Automation Technique Cheatsheet

### React/Angular/Vue Form Frameworks (common on broker opt-out pages)

**Problem:** Modern SPA frameworks track form field "touched" state. Programmatic `.value = 'x'` does NOT trigger validation. The Submit button stays disabled.

**Solutions (in priority order):**

| Method | How | Best For |
|--------|-----|----------|
| `fill_form()` | Playwright's native fill — triggers input + change events | Most React forms |
| `evaluate()` dispatchEvent | `field.dispatchEvent(new Event('input', {bubbles: true}))` after setting value | Stubborn frameworks |
| Click label instead of checkbox | Checkbox is behind a `<label>` overlay | Intercepting label elements |
| Playwright `click()` by role | `page.getByRole('checkbox', { name: '...' }).click()` | Accessible React forms |
| Force submit via JS | `document.querySelector('button[type="submit"]').removeAttribute('disabled')` | Last resort |

### Common Interception Patterns

**Checkbox intercepted by `<label>` element:**
- Symptom: Accessibility tree shows checkbox but `fill_form` times out with "label intercepts pointer events"
- Fix: Click the label text instead (`page.getByText('I agree to the terms').click()`)
- The label toggles the underlying checkbox via the `for` attribute

**Submit button disabled by framework validation:**
- Symptom: All fields filled, DSA/belief checkbox checked, but button has `cursor-not-allowed` and `opacity-50`
- Fix: Check whether a hidden required field (country, state) hasn't been properly set. The Country dropdown on Cloudflare abuse form is a custom combobox that needs explicit interaction, not programmatic value setting.

**Email field with inline verification (MyLife pattern):**
- MyLife has a separate iframe-based email verification inside the form
- Requires clicking "Verify Email" button before the main form is valid
- Can't automate — needs user action

---

## Site-by-Site Opt-Out Automation Status

### Can Automate (submit forms autonomously):

| Site | Form Type | Verification | Notes |
|------|-----------|-------------|-------|
| PeopleConnect Suppression | Simple email + checkbox | **Email link** | Form is easy to fill via JS. Email link needed to complete. One submission covers 10+ PeopleConnect sites. |
| Cloudflare Abuse Report | Multi-field with country selector | **None** | Submit button stays disabled due to React validation. Try clicking each field, tabbing out, then retry. If still blocked, user must click Submit on pre-filled form. |

### Cloudflare/recaptcha Blocked (cannot access form):

| Site | Block Type | Alternate Path |
|------|-----------|---------------|
| BeenVerified optout | Cloudflare | Try at different time of day |
| Radaris optout | Cloudflare | Try via email instead: privacy@radaris.com |
| MyLife optout | reCAPTCHA | Manual: mylife.com/privacyrequest |
| Spokeo optout | Accessible but needs profile URL | Search for specific profile URL first, then submit |

### Forms That Need Profile URL First:

| Site | How to find URL |
|------|---------------|
| Spokeo | Search "site:spokeo.com \"the operator\" your city" — locate specific profile link |
| MyLife | Search "site:mylife.com \"the operator\" \"Schenectady\"" — e30015000306 profile |

---

## The Email Verification Bottleneck

**Every major broker site sends a confirmation email.** This is the universal bottleneck for full automation.

**Pattern:** Submit form → "Check your email for a verification link" → user clicks → "Your opt-out request is being processed."

**What the agent can do autonomously:**
- Navigate to form
- Fill all fields
- Accept terms
- Click Submit

**What needs user action:**
- Open email (Gmail IMAP could be automated but the operator hasn't set that up for rep-team address)
- Click verification link
- Sometimes: reply to confirmation email with additional info

**Recommendation:** When batch-submitting opt-outs, submit them all in one session, then direct the operator to check email once and click all links at once. Much more efficient than one-at-a-time.

---

## Syndicated Content Network

**Known auto-generated false-positive network (site family):**
- allrecentarrests.org (may show 404 after removal)
- alljailsearch.org
- inmateaid.com

**Pattern:** All share the same internal ID number (e.g. 1649468 for the operator). Removing from one does NOT remove from the others. Each site must be targeted separately.

**How to identify syndicated content:**
1. Same ID number in URL or page content
2. Same placeholder photo (no actual booking photo)
3. All fields are "Unknown" (no inmate ID, no charges, no booking date)
4. Generic template text repeated across all three sites

**Recommended takedown order:**
1. allrecentarrests.org (via Cloudflare abuse report or contact form)
2. alljailsearch.org (same process)
3. inmateaid.com (same process)
4. Google removal tool (deindex all three URLs from search results — this stops traffic even if sites don't remove content)

---

## Verification Timeline (from submission to confirmed removal)

| Phase | What Happens | Timeframe |
|-------|-------------|-----------|
| Submit | Form sent, email verification sent | Day 1 |
| Verify | User clicks email link | Day 1-2 |
| Processing | Broker processes request | Day 2-7 |
| Check | Visit the site and search for name | Day 7 |
| Confirm | Update removal-tracker.yaml status to "removed" | Day 7-14 |
| Re-check | Some brokers "forget" after 30-90 days | Monthly |

**Sites requiring annual re-opt-out:** Radaris (30 days — shortest cycle), Intelius family (annual), Spokeo (annual via phone verification).

---

## CRM Fields for Removal Tracker

When adding sites to `removal-tracker.yaml`, include these fields:

```yaml
- site: "SiteName"
  priority: 1-4     # 1=critical defamation, 2=major broker, 3=secondary, 4=low
  status: pending|submitted|email_verification_pending|removed|verified|escalated|reappeared
  date_discovered: "YYYY-MM-DD"
  date_submitted: "YYYY-MM-DD"
  date_verified: "YYYY-MM-DD"
  url: "https://..."
  opt_out_url: "https://..."
  removal_method: "web_form|email|phone|dmca_or_defamation"
  requires_email: true
  requires_phone: true
  takes_effect: "24-48 hours"
  notes: "Any quirks from this session"
  actions_taken: []
```
