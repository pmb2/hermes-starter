# Gmail IMAP Deletion: The \Deleted Flag Quirk

## The Problem

Gmail's IMAP implementation is non-standard for deletion. The standard IMAP
workflow:

```python
mail.select('INBOX')
mail.uid('STORE', '1:*', '+FLAGS', '\\Deleted')
mail.expunge()
```

...does NOT permanently delete messages in Gmail. It appears to succeed
(returns `OK` from both STORE and EXPUNGE), but:

- Messages remain in `[Gmail]/All Mail`
- Storage quota does not decrease
- Messages are still visible in the web UI

**Root cause:** Gmail treats `\Deleted` as a "hide from current folder view"
flag rather than a "delete permanently" marker. The `EXPUNGE` operation only
removes messages that have `\Deleted` from the current folder's label — it
does not free the storage because the message still has other labels
(Inbox, All Mail, etc.).

## Confirmed Working Approaches

### 1. Gmail X-GM-LABELS Extension (Slow but Scriptable)

Gmail adds proprietary IMAP extensions via `X-GM-LABELS`. To move a message
to the Trash (which counts as deletion for Gmail):

```python
# Move to Trash by adding \Trash label and \Deleted flag
mail.select('"[Gmail]/All Mail"', readonly=False)

for uid in all_uids:
    mail.uid('STORE', uid, '+X-GM-LABELS', '(\\Trash \\Deleted)')

# Then empty Trash
mail.select('"[Gmail]/Trash"', readonly=False)
mail.uid('STORE', '1:*', '+FLAGS', '\\Deleted')
mail.expunge()
```

**Performance:** ~100 UIDs per minute. For 50k+ messages, this will exceed
the default 300-second `execute_code` timeout. Run as a background terminal
process instead.

The `(\\Trash \\Deleted)` argument is a space-separated parenthesized list
of label names in a single string. The double-backslash is Python escaping
for a literal backslash.

### 2. Google One Storage Manager (Recommended for speed)

Navigate to `https://one.google.com/storage/management` and use the Clean up
suggested items section. This handles deletion correctly through Gmail's own
API.

### 3. Gmail Web UI

Log in and use Select All → Delete. Gmail's own UI handles the label
operations correctly.

## What Does NOT Work

| Approach | Result |
|----------|--------|
| `STORE +FLAGS \\Deleted` + `expunge()` | ❌ Messages stay in All Mail |
| `STORE +FLAGS \\Deleted` + `CLOSE()` | ❌ Same issue |
| `COPY` to Trash then `STORE \\Deleted` + `expunge` on source | ❌ `COPY` doesn't move, it copies |
| Bulk `UID STORE` with comma-separated UIDs + `X-GM-LABELS` | ⚠️ Works but very slow |

## Verification

After cleanup, verify via IMAP:

```python
for folder in ['"[Gmail]/All Mail"', '"INBOX"', '"[Gmail]/Trash"', '"[Gmail]/Spam"']:
    status, msgs = mail.select(folder, readonly=True)
    count = int(msgs[0])
    print(f"{folder}: {count}")
```

If All Mail still shows the original count, the deletion did NOT work.
The storage quota page at `https://one.google.com/storage` may also lag
by several minutes after successful deletion.
