# Google One Storage Manager Cleanup

## Overview

The Google One Storage Manager at `https://one.google.com/storage/management`
provides a structured UI for cleaning up per-service storage. It is the
most reliable interface for bulk deletion of photos, large attachments,
and spam.

## Page Layout

### Main Storage Page (`/storage/management`)

```
Storage used: 15.07 GB of 15 GB
Suggested items:
├── Large photos and videos (1 GB+)    → /storage/management/photos/large
├── Emails with large attachments       → /storage/management/gmail/large
├── Large Drive files                   → /storage/management/drive/large
└── Spam emails                         → /storage/management/gmail/spam

Clean up by service:
├── Google Photos
├── Gmail
└── Google Drive
```

### Large Photos Page (`/storage/management/photos/large`)

Shows items as a table with:
- Checkbox per row (for individual selection)
- "Select all items" checkbox (table header)
- "Download" button (enabled when items are selected)
- "Move to trash" button (enabled when items are selected)
- Category chips: "Large photos and videos", "Unsupported videos"

**IMPORTANT:** Only the first 32 items are shown by default. Scrolling
or pagination may reveal more.

### Gmail Large Attachments Page (`/storage/management/gmail/large`)

Shows emails with their largest attachment, sender, size, and date.
Same table format with "Select all" and "Delete" buttons.

### Spam Page (`/storage/management/gmail/spam`)

Has a **"Delete all"** button that deletes ALL spam in one click.
Also has "Select all items" for more granular selection.

## Deletion Confirmation Dialogs

All deletion actions in the storage manager trigger a confirmation dialog
with a **disabled confirm button** that requires clicking a checkbox first.

### Photos Dialog

```
┌─────────────────────────────────────────────────────────┐
│  Move 32 items to Trash?                                │
│                                                         │
│  This will remove items from your Google Account,       │
│  synced devices, and places shared within Google Photos.│
│                                                         │
│  ☐ I understand that items in Google Photos Trash will  │
│    be permanently deleted after 60 days.                │
│                                                         │
│                    [Cancel]  [Move to trash]             │
└─────────────────────────────────────────────────────────┘
```

### Gmail Dialog

```
┌─────────────────────────────────────────────────────────┐
│  Delete 19 items?                                       │
│                                                         │
│  This will permanently delete emails and attachments.   │
│                                                         │
│  ☐ I understand that deleted items can't be recovered.  │
│                                                         │
│                    [Cancel]  [Permanently delete]        │
└─────────────────────────────────────────────────────────┘
```

### Spam Dialog

Same pattern as Gmail but with "Delete 57 items?" heading.

## Automation Sequence (Camofox API)

```python
# Step 1: Navigate to the category page
POST /tabs/{tabId}/navigate
{"userId": "the operator", "url": "https://one.google.com/storage/management/photos/large"}

# Step 2: Select all items
POST /tabs/{tabId}/click
{"userId": "the operator", "ref": "e7"}  # Select all checkbox

# Step 3: Click action button
POST /tabs/{tabId}/click
{"userId": "the operator", "ref": "e4"}  # Move to trash

# Step 4: Check the confirmation checkbox
POST /tabs/{tabId}/click
{"userId": "the operator", "ref": "e1"}  # Confirmation checkbox

# Step 5: Click confirm (now enabled)
POST /tabs/{tabId}/click
{"userId": "the operator", "ref": "e3"}  # Move to trash / Permanently delete
```

**PITFALL:** The confirm button (step 5) starts `[disabled]` in the a11y
tree even though the checkbox says `[checked]` after clicking. The DOM just
needs a moment to update between steps 4 and 5 — add a 1-second delay.

## Before / After Storage Comparison

After cleanup, navigate to `https://one.google.com/storage` to verify:

| Metric | Full | After cleanup |
|--------|------|--------------|
| Label | "You're out of storage" | "You've used 95% of storage" |
| Percentage | 100% | 95% or lower |
| Email status | Bouncing | Receiving |

## Post-Cleanup Success Page

After deleting items from a cleanup category (photos or Gmail), the storage
manager shows a **success confirmation dialog** instead of immediately
returning to the management page:

```
┌──────────────────────────────────────────────────────────┐
│  ✓ Keep going to make even more room                     │
│                                                          │
│  You've made enough room to resume services, but you     │
│  may run out of storage again soon.                      │
│                                                          │
│              [Clean up Gmail]  [See offer]               │
└──────────────────────────────────────────────────────────┘
```

**Key details:**
- The "Clean up Gmail" button at `[e2]` navigates directly to
  `/storage/management/gmail/large` for the next cleanup step
- The "Close dialog" button at `[e1]` dismisses the success message
- Once this dialog appears, email service has been restored
- The dialog title varies: for Photos trash it says "Keep going to make
  even more room"; the exact phrasing may differ by category

## Item Count Behavior

The storage manager shows one "page" of items at a time. Observations:

| Category | Max items shown per page |
|----------|-------------------------|
| Large photos & videos | 32 items (fixed, no pagination) |
| Gmail large attachments | 19 items (variable) |
| Spam | 32 items (variable, "Delete all" button available) |
| Unsupported videos | 0 items (commonly empty) |

The 32-item cap for photos is a UI limit of the storage management tool.
If the account had more than 32 large photos/videos, they may not appear
in this view — rely on Google Takeout for complete coverage.
