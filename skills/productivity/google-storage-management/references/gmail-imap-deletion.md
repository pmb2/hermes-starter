# Gmail IMAP Deletion — X-GM-LABELS Technique

Gmail's IMAP implementation does NOT handle `\Deleted` + `EXPUNGE` the way standard IMAP does. This reference documents the correct approach verified against a live Gmail account with 51,965 messages.

## The Problem

Standard IMAP deletion pattern:
```python
mail.uid('STORE', uid, '+FLAGS', '\\Deleted')
mail.expunge()
```

**On Gmail this does NOT permanently delete.** It only removes the message from the current folder view. The message remains in All Mail and still counts against storage quota. Expunge in Gmail is essentially a no-op for permanent deletion.

## The Fix: X-GM-LABELS

Gmail has a proprietary IMAP extension called `X-GM-LABELS` that directly manipulates Gmail's label system. To delete, add the `\Trash` and `\Deleted` labels:

```python
# Move to Trash (this is the key step)
mail.uid('STORE', uid, '+X-GM-LABELS', '(\\Trash \\Deleted)')
```

### Verified Syntax

The labels `\Trash` and `\Deleted` must be passed as a space-separated parenthesized list:

```python
# ✅ Correct
mail.uid('STORE', uid, '+X-GM-LABELS', '(\\Trash \\Deleted)')

# ❌ Wrong — backslash-quoting fails
mail.uid('STORE', uid, '+X-GM-LABELS', '\\\\Trash')
```

After the X-GM-LABELS command, the message appears in `[Gmail]/Trash`.

### Batch Operation

```python
# Batch with comma-separated UIDs
uids = ['10641', '10642', '10643']
uid_str = ','.join(uids)
mail.uid('STORE', uid_str, '+X-GM-LABELS', '(\\Trash \\Deleted)')
```

Batch size: ~100-200 works reliably. Larger batches may timeout.

### Step 2: Empty Trash

After moving messages to Trash, select the Trash folder and permanently delete:

```python
mail.select('"[Gmail]/Trash"', readonly=False)

# Mark all as deleted
mail.uid('STORE', '1:*', '+FLAGS', '\\Deleted')

# Permanently remove
mail.expunge()
```

### For Other Folders (Inbox, Spam, etc.)

Non-All-Mail folders can use `1:*` wildcard:

```python
mail.select('"[Gmail]/Spam"', readonly=False)
mail.uid('STORE', '1:*', '+FLAGS', '\\Deleted')
mail.expunge()

mail.select('INBOX', readonly=False)
# For Inbox, also use X-GM-LABELS to move to Trash first
mail.uid('STORE', '1:*', '+X-GM-LABELS', '(\\Trash \\Deleted)')
mail.uid('STORE', '1:*', '+FLAGS', '\\Deleted')
mail.expunge()
```

## Verification

After deletion, check remaining messages:

```python
for folder in ['"[Gmail]/All Mail"', '"INBOX"', '"[Gmail]/Trash"', '"[Gmail]/Spam"']:
    mail.select(folder, readonly=True)
    status, msgs = mail.select(folder, readonly=True)
    print(f"{folder}: {msgs[0].decode()} messages" if status == 'OK' else f"{folder}: ERROR")
```

## Web UI Alternative

The IMAP approach is slow for 50k+ messages (takes many minutes). The Google One Storage Manager web UI is much faster for bulk deletion:

1. `https://one.google.com/storage/management`
2. Go to specific service sections
3. Select all → Delete
4. Empty Trash

## Why This Works

Gmail's IMAP stores messages in `[Gmail]/All Mail` regardless of labels. The `X-GM-LABELS` extension tells Gmail's server-side label engine to add the `\Trash` system label, which Gmail's web UI and storage manager recognize as "in trash." Without this label, the message remains in All Mail with user labels and is not counted as trash — even if marked `\Deleted`.

The `\Deleted` flag is still needed alongside `\Trash` for the IMAP EXPUNGE command to process the message, even though EXPUNGE alone wouldn't have deleted it.
