# Classifier False Positives — Marketing Footers Break Body-Text Matching

Field lesson from a live IMAP watchdog that scanned an inbox for
"CCPA/privacy response" emails and initially matched **13 junk emails**
(all job alerts/newsletters) as real responses.

## The Bug

Every marketing email footer contains phrases like:
- "opt out"
- "unsubscribe"
- "privacy policy"
- "you are receiving this because..."

A classifier that matches keywords against `subject + body` will fire on
almost ANY marketing/newsletter email. In our case, LinkedIn and Dice
job alerts were classified as `OPT_OUT` / CCPA-related because their
footers contained "opt out".

## The Fixes (both required)

### 1. Classify on SUBJECT ONLY
Match classification keywords against `subject.lower()`, never the body.
Body text is used for exactly one thing: bounce/delivery detection
("delivery failed", "undeliverable", "550", "mailer-daemon").

### 2. Sender allowlist, not domain catalog
A domain map of "known senders" is too broad — it includes domains the
user has *accounts* with, whose mail is routine (job alerts, receipts,
newsletters). The reliable filter: only process senders that are in the
set of senders you are **actively waiting on a reply from**.

For the CCPA pipeline that set came from the DSAR action log:

```python
sent_broker_names = set()
for _logf in (BASE / "logs").glob("action-log-*.csv"):
    for _row in csv.DictReader(open(_logf, encoding="utf-8")):
        if "DSAR_SENT" in (_row.get("Action") or ""):
            sent_broker_names.add(_row.get("Service", "").strip().lower())

# per message:
if broker and broker.lower() not in sent_broker_names and not is_ccpa_related:
    continue
if not broker and not is_ccpa_related:
    continue
```

Generic form: keep a `pending_senders` set (loaded from a state file or
log) of entities you've sent something to and are awaiting a response.
Anything else is noise and skipped.

## Verification

After both fixes, rescanning the same mailbox went from 13 false
positives → 0. A true CCPA response (subject like "Your privacy
request" or sender=broker-with-pending-DSAR) still surfaces.

## General Rule for Watchdog Classifiers

If your watchdog classifies email by content keywords:
1. Subject-only matching for intent classification
2. Sender must be in the "expecting reply from" set OR subject must
   contain explicit task keywords
3. Never match generic footer words (opt out, unsubscribe, privacy)
   even in subjects, unless combined with the pending-sender check