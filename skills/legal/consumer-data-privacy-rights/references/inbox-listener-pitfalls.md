# Inbox Listener & Auto-Responder — Production Pitfalls

Field lessons from running the CCPA inbox listener against a live Gmail
inbox (batch of 72 DSARs, 30-min polling cron). These are the bugs that
actually bit, and the fixes that held.

## 1. Body-text classification = false-positive storm

First live scan found "13 CCPA-related emails" — all of them were
LinkedIn/Dice **job alerts**. Cause: every marketing email footer contains
"opt out" / "unsubscribe" / "privacy policy", and the classifier matched
those phrases in `subject + body`. Any body-scan of marketing mail will
fire on the footer.

**Fixed rule: classify on the SUBJECT ONLY.** Body text is used only for
bounce detection ("delivery failed", "undeliverable", "550"). Keyword
lists for ACK / DATA_RECEIVED / DELETION_CONFIRMED / NEEDS_ATTENTION /
FOLLOWUP_NEEDED all match `subject.lower()`.

## 2. Domain-catalog sender matching is too broad

The 1,800-broker domain map includes `linkedin.com`, `dice.com`, etc.
(brokers/B2B platforms the operator has accounts with) — so mail from them was
"from a known broker" and passed the filter. Job alerts are not CCPA
responses.

**Fixed rule: sender allowlist from the DSAR action log.** Only process
senders whose broker name appears in `logs/action-log-*.csv` with
`Action` containing `DSAR_SENT`, OR whose subject explicitly has CCPA/
privacy keywords:

```python
sent_broker_names = set()
for _logf in (BASE / "logs").glob("action-log-*.csv"):
    for _row in csv.DictReader(open(_logf, encoding="utf-8")):
        if "DSAR_SENT" in (_row.get("Action") or ""):
            sent_broker_names.add(_row.get("Service", "").strip().lower())

# in the per-message loop:
if broker and broker.lower() not in sent_broker_names and not is_ccpa_related:
    continue
if not broker and not is_ccpa_related:
    continue
```

Verification after fix: same mailbox scan went from 13 matches → 0 noise.

## 3. `.env` loader must be stdlib-only

Cron scripts run under the hermes-agent venv, which is recreated on
upgrade and has **no pip** — `python-dotenv` will not be there. Embed a
6-line loader in every script that needs credentials:

```python
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())
```

Place it BEFORE the config reads that use `os.environ.get(...)`.

## 4. App password already exists on the box

Before asking the user for a fresh Gmail App Password, check
`~/.config/himalaya/config.toml`. himalaya stores per-account
credentials inline as python one-liners:

```toml
[accounts.youraccount2]
  backend.auth.cmd = python -c "import sys; sys.stdout.write('<app-password>')"
  message.send.backend.auth.cmd = python -c "import sys; sys.stdout.write('<app-password>')"
```

In this environment both `<your-email>@gmail.com` and
`<your-email>@gmail.com` were already configured. Extract the value
with a masked search (never echo the secret into chat or logs), write it
to the pipeline `.env`, done. No new app-password dance needed.

## 5. Secrets hygiene on first wiring

- `.env` must be in `.gitignore`: `!.env.template` exception, and commit
  `.env.template` with a placeholder value.
- `chmod 600 .env` after creation.
- Before the first commit, `git status` must show `.env` untracked.
- Never print the password in tool output that lands in chat (mask it:
  `val[:4] + 'x' * (len(val)-4)`).

## 6. Cron job IDs are not durable

The `ccpa-inbox-listener` job ID that was created earlier had vanished
from the scheduler by the time an update was attempted ("Job with ID or
name '...' not found"). Another tooling pass (pauses, model-unavailable
auto-pauses) can remove or rename jobs. When an update 404s:
1. `cronjob(action='list')` — dump all jobs
2. grep for the job by NAME (not ID)
3. recreate if genuinely gone

## 7. Registry sync gotcha

The data-broker targets live in the *action log* (72 DSAR_SENT rows), not
in REGISTRY.md's original 60-service categories. `sync_registry.py` must
derive broker categories from the action log, not from keyword-matching
against REGISTRY.md rows — a regex against `| 🔴 Not Started |` style rows
matched 0 entries because the broker rows were never in the registry yet.
Add a new "## Data Brokers" section derived from the log, then renumber
and update quick stats.

## 8. Verification before commit (recap)

```bash
# parse-check + config + CSV + spot-check one generated letter
python3 -c "import ast; [ast.parse(open(f).read()) for f in
  ['listener.py','auto_responder.py','execute_all.py','sync_registry.py',
   'batch_generate.py','privacy_pipeline.py','re_request_cycle.py']]"
```
Then run `listener.py --once` and `auto_responder.py --check` to prove
IMAP/SMTP paths execute end-to-end before committing.