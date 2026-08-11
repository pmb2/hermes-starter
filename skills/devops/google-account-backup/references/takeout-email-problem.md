# Google Takeout Email Notification Problem

## The Problem

When a Google account is **over the 15GB free quota**, Gmail stops accepting
incoming messages. Emails are bounced back to the sender with a
delivery-failure notice.

Google Takeout sends the download link via email when archives are ready.
**If the account is over quota, this notification will never arrive.**

## Symptoms

- Gmail shows: "You haven't gotten any emails in 2 days since you've been
  out of storage. Emails sent to you will be bounced back to the sender."
- Google Takeout page says: "You'll receive an email when your export is done"
  — but the email won't arrive
- The Manage Exports page continues to show "Export in progress" even after
  completion

## Solution: Poll Manage Exports Directly

Instead of waiting for the email, periodically check:

```
https://takeout.google.com/manage
```

When the export is complete, the page transitions from "Export in progress"
to showing a download button next to the completed archive.

### Cron Job Pattern

Set a cron job to poll every 4 hours:

```python
# Pseudocode in the check script:
1. Create Camofox tab for takeout.google.com/manage
2. Take snapshot / evaluate JS
3. Check for "Download" button or download link
4. If found, download the archive(s) to local storage
5. Report back to user
```

### Download URLs

Takeout archives are large (often 2GB+ per file, multiple files). Download
them with `aria2c` or `wget` with resume support:

```bash
aria2c -x 4 -s 4 --continue=true "https://takeout.download.url/..."
```

### Notification Workaround

If email notification is critical (e.g., for automation), free up just
enough Gmail space (~80 MB via the storage manager's "Clean up suggested
items") to allow incoming email delivery. The exact threshold is shown on
the storage management page: "Clean up X MB to resume emails."
