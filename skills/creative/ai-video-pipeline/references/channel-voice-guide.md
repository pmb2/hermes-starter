# Channel Voice Guide Reference

## Purpose

The channel voice guide (`prompts/channel-voice.md`) defines the narrative voice for animated YouTube content. It is loaded automatically by `create_video_v2.py` and injected as `{{VOICE_GUIDE}}` in the script generation prompt.

## Sections to Fill

### 1. Core Voice
Define the overall tone. Examples:
- "First-person conversational thriller"
- "Professional documentary narrator"
- "Self-deprecating but confident"

### 2. Sentence Patterns — DO/DON'T Table

| Pattern | Example |
|---------|---------|
| Short declarative | "I open ChatGPT. I type a question." |
| Question → answer | "What happens next? Nothing you'd expect." |
| Present tense | "The cursor blinks. The text streams out." |
| Sentence fragment | "Three dots. Then text. Then everything changes." |
| Then-continuation | "I close the laptop. Then my phone lights up." |

### 3. Narrative Framing
How the story is framed (e.g., hypothetical frame, first-person, observer POV).

### 4. Pacing Rules
- Hook in first 10 seconds
- Build every 30 seconds — new detail, new turn
- End scenes on a punch — reveal, question, or cliffhanger
- Vary sentence length — 3 short minimums then a longer descriptive
- Read aloud before finalizing

### 5. Word Choice Table

| Do Use | Don't Use |
|--------|-----------|
| "Here's the thing" | "It is important to note" |
| "What happens next?" | "Subsequently" |
| Short conversational | Generic AI phrases |
| Specific, vivid | Abstract, vague |

### 6. Visual-Narration Coupling
Rule: narration says what, visual shows where/how. They overlap but don't repeat.

## File Location

`prompts/channel-voice.md` in the yt-animations repo. Auto-loaded by create_video_v2.py.
