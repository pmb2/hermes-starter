#!/usr/bin/env python3
"""
vibe_code_detox.py — Pre-ship audit for AI-generated website tells.

Statically checks a built site directory for the JordanKodes vibe-coding tells:
1. Generic blue-purple gradients (html/css)
2. Em-dashes in copy (html)
3. Badge pill above the hero H1 (html)
4. Footer missing privacy/terms links (html)

Mobile cutoff (tell 3) needs a real viewport check — do it in a browser at 375px.

Usage:
    python vibe_code_detox.py <site-directory>

Exit 0 = clean, exit 1 = tells found.
"""
import re
import sys
from pathlib import Path

GRADIENT_PATTERNS = [
    re.compile(r"linear-gradient\([^)]*blue[^)]*purple", re.IGNORECASE),
    re.compile(r"linear-gradient\([^)]*purple[^)]*blue", re.IGNORECASE),
    re.compile(r"linear-gradient\([^)]*indigo[^)]*violet", re.IGNORECASE),
    re.compile(r"linear-gradient\([^)]*violet[^)]*indigo", re.IGNORECASE),
    re.compile(r"linear-gradient\([^)]*#(?:3b82f6|2563eb|1d4ed8)[^)]*#(?:8b5cf6|7c3aed|a855f7)", re.IGNORECASE),
    re.compile(r"linear-gradient\([^)]*#(?:8b5cf6|7c3aed|a855f7)[^)]*#(?:3b82f6|2563eb|1d4ed8)", re.IGNORECASE),
]

EM_DASH = "—"  # —

BADGE_PATTERNS = [
    re.compile(r'<span[^>]*class="[^"]*badge[^"]*"[^>]*>[^<]{1,40}</span>', re.IGNORECASE),
    re.compile(r'<span[^>]*class="[^"]*chip[^"]*"[^>]*>[^<]{1,40}</span>', re.IGNORECASE),
    re.compile(r'<span[^>]*class="[^"]*pill[^"]*"[^>]*>[^<]{1,40}</span>', re.IGNORECASE),
]

H1_PATTERN = re.compile(r"<h1[^>]*>", re.IGNORECASE)
FOOTER_PATTERN = re.compile(r"<footer[\s\S]*?</footer>", re.IGNORECASE)
PRIVACY_PATTERN = re.compile(r'href="[^"]*privacy', re.IGNORECASE)
TERMS_PATTERN = re.compile(r'href="[^"]*terms', re.IGNORECASE)

HTML_EXT = {".html", ".htm"}
CSS_EXT = {".css"}


def scan_file(path: Path, issues: list) -> None:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return
    rel = path.name
    ext = path.suffix.lower()

    if ext in HTML_EXT or ext in CSS_EXT:
        for i, line in enumerate(text.splitlines(), 1):
            for pat in GRADIENT_PATTERNS:
                if pat.search(line):
                    issues.append(("generic_gradient", rel, i, line.strip()[:120]))

    if ext in HTML_EXT:
        for i, line in enumerate(text.splitlines(), 1):
            if EM_DASH in line:
                issues.append(("em_dash", rel, i, line.strip()[:120]))

        h1 = H1_PATTERN.search(text)
        if h1:
            before = text[: h1.start()]
            window = before[-500:]
            for pat in BADGE_PATTERNS:
                if pat.search(window):
                    issues.append(("badge_above_h1", rel, 0, "badge/chip/pill within 500 chars before first <h1>"))

        footer = FOOTER_PATTERN.search(text)
        if footer:
            body = footer.group(0)
            if not PRIVACY_PATTERN.search(body) or not TERMS_PATTERN.search(body):
                issues.append(("missing_legal_links", rel, 0, "footer missing privacy and/or terms link"))


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    root = Path(sys.argv[1])
    if not root.is_dir():
        print(f"Not a directory: {root}")
        return 2

    issues: list = []
    for path in sorted(root.rglob("*")):
        if path.is_file() and path.suffix.lower() in (HTML_EXT | CSS_EXT):
            scan_file(path, issues)

    if not issues:
        print(f"CLEAN: no vibe-code tells found in {root}")
        return 0

    print(f"DIRTY: {len(issues)} vibe-code tell(s) found in {root}\n")
    for kind, rel, line, snippet in issues:
        loc = f"{rel}:{line}" if line else rel
        print(f"  [{kind}] {loc}  {snippet}")
    print("\nFix guide: references/vibe-code-tells-audit.md")
    return 1


if __name__ == "__main__":
    sys.exit(main())
