# PIM Ingestion: YouTube Watch Later Folder Structure

When the user asks to "transcribe and save" a YouTube video to the PIM (Personal Intelligence Management) library for "watch later" processing, use this folder structure.

## Output Path

```
~/AppData/Local/hermes/PIM/watch-later/{sanitized-video-title}/
```

## File Convention

Numbered files with descriptive prefixes, all `.md`:

| File | Content | Always created? |
|------|---------|-----------------|
| `00-metadata.md` | Raw video metadata + description + transcript failure notes | Yes |
| `01-summary.md` | Overview, key themes, interview topics, key numbers | Yes |
| `02-playbook.md` | Step-by-step actionable framework from the video | When applicable |
| `03-something-specific.md` | Specific extract the user asked for (e.g., VA criteria, exact setup steps) | When user asks for specific extraction |
| `04-tr…` | Additional extracts as needed | As needed |

## Title Sanitization

Replace problematic filename characters in the video title:
- `:` → empty (remove)
- `/` → `-`
- `?` → empty
- `"` → `'`
- Spaces → spaces (keep)
- Max length: keep title-readable, trim if absurdly long

## File Content Guidelines

### 00-metadata.md
- Video title, URL, channel name
- Duration, view count, publish date
- Full raw description (as-is from YouTube)
- Tags/hashtags
- Transcript attempt log (which methods tried, which failed, why)

### 01-summary.md
- Overview paragraph
- Key themes (3-6 bullet sections with detail)
- Structured list of interview topics (from description or transcript)
- Key numbers table
- Note about transcript source (full vs description-only)

### 02-playbook.md
- Phase-based structure (Phase 1: X, Phase 2: Y, etc.)
- Concrete actionable steps with numbered lists
- Framework summary (visual/mnemonic if helpful)
- Common mistakes section

### 03-specific-extract.md (user-dependent naming)
- The exact thing the user asked to extract
- Very detailed — this is what they specifically wanted
- If from a specific timestamp, note it

## When Transcript Is Unavailable (IP Blocked)

If ALL transcript endpoints return HTTP 429 (YouTube IP block):
1. Extract video metadata from `ytInitialPlayerResponse` in the page source
2. Pull the full description — interview/educational videos often have detailed bullet-point outlines
3. Build the summary/playbook from the description bullet points + channel/guest context
4. Note in `00-metadata.md` which transcript methods were tried and what failed
5. The content quality is lower without a transcript, but the structure is still valuable

### Transcript Attempt Log Pattern

When the transcript fetch fails, document the attempts in `00-metadata.md`:

```markdown
## Transcript Note

Full transcript could not be extracted. YouTube's timedtext API returned HTTP 429
(rate limited) on all attempts including:
- youtube-transcript-api (direct + language-specific)
- InnerTube API via browser cookies
- youtubetranscript.com / downsub.com
- video.google.com/timedtext
- yt-dlp with browser cookies (n-challenge failure)
- Invidious API (captions listed but content empty)

The IP address is currently blocked by YouTube for automated caption requests.
A different exit IP (VPN or proxy rotation) would be required to fetch the
full transcript.
```

### Description-Only Content Building

When working from just the description:
- Use the bullet points as a **table of contents** — each bullet is a section/topic in the video
- Enrich each section with common knowledge about the topic and channel/guest context
- Build the playbook around the **sequence** implied by the bullet order
- For VA criteria, scripts, or other specific extracts the user asks about: look for clues in the description topics near the timestamp (if provided in the URL), and build the extract from the topic context. Note clearly that it's synthesized from the outline, not verbatim.
