# Research Pipeline — Pre-Script Intelligence

TubeFlow-style research to feed competitive/SEO/community intelligence into script generation.

## Tool
`scripts/research_topic.py` — 4 searches via DuckDuckGo (`pip install ddgs`):

1. **Topic gatherer** — Wikipedia/docs overview (`ddgs.text(f"{topic} explained overview")`)
2. **Competitor gatherer** — Existing YouTube videos (`site:youtube.com` search)
3. **SEO gatherer** — Related searches, keywords
4. **Community gatherer** — Reddit/forum discussions (`site:reddit.com` search)

## Usage

```bash
python scripts/research_topic.py "Docker security" --topic-context "Tutorial series"
python create_video_v2.py --topic "Docker security" --research-context research/docker-security-research-context.md
```

## Output Format
A markdown file with sections: Topic Research, Competitor Analysis, SEO & Keyword Research, Community Questions & Discussions, and Research-Driven Scripting Instructions.

## Limitations
- DuckDuckGo results are broad — niche topics may not return relevant content
- No YouTube API integration (uses web search, not YouTube Data API)
- No true parallel execution (DDG searches run sequentially)
