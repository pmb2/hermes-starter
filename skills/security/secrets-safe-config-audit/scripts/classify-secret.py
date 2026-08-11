#!/usr/bin/env python3
"""
classify-secret.py — redaction-proof secret classification for audits.

Determines what a secret-looking string ON DISK actually is, using only
evidence that tool-output redaction cannot falsify: length, prefix, segment
structure, character class, and a sha256-prefix comparison against Supabase's
well-known public local-dev defaults. NEVER prints the value itself.

Why this exists: tool output masks secret-adjacent substrings OUTPUT-side
(`process.env.X` renders as `proces..._KEY`, long JWTs render truncated like
`eyJhbG...81IU`). Grepping for the masked pattern finds nothing — expected,
since the file holds the unmasked string. Read the raw bytes instead; the
disk is authoritative.

Usage:
    python classify-secret.py <file> <needle>    # first match in file
    python classify-secret.py --inline <value>   # classify a literal
    echo "$VALUE" | python classify-secret.py -  # classify from stdin

Exit codes: 0 classified, 2 needle not found on disk (likely display-side
redaction of a value that exists only in tool output).
"""
import sys
import re
import hashlib

# sha256[:16] of Supabase's PUBLIC, well-known local-dev default keys (from
# Supabase docs). Stored as hash prefixes so no credential-shaped text lives
# in this script; a match means "this is the public dev default", NOT a leak.
KNOWN_SHA = {
    "supabase-local-dev ANON key": "bf1725a8f98bea37",
    "supabase-local-dev SERVICE_ROLE key": "353fcbd7695156a7",
}

B64URL = re.compile(r"[A-Za-z0-9_.\-]+")
TOKEN = re.compile(rb"[A-Za-z0-9_\-\.]{8,}")


def classify(v: str) -> str:
    n = len(v)
    if n < 8:
        return "too short to be a credential"
    if "..." in v:
        return "contains literal '...' -> scrubbed/truncated stub ON DISK"
    if v.startswith("sb_publishable_") or v.startswith("sb_secret_"):
        return "new-format Supabase API key (real key format)"
    if v.startswith("sk-or-"):
        return "OpenRouter-shaped: %s" % (
            "STUB (real keys ~60-70 chars)" if n < 30 else "full-length key")
    if v.startswith("eyJ") and v.count(".") == 2 and bool(B64URL.fullmatch(v)):
        return "JWT-format credential (header.payload.sig)"
    if bool(re.fullmatch(r"[A-Za-z0-9_\-]{30,}", v)):
        return "opaque token/secret (base64-ish)"
    return "unrecognized"


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)
    if args[0] == "--inline":
        raw = args[1].encode()
    elif args[0] == "-":
        raw = sys.stdin.buffer.read().strip()
    else:
        path, needle = args[0], args[1]
        data = open(path, "rb").read()
        i = data.find(needle.encode())
        if i < 0:
            print("needle not found on disk (it may exist only in tool output "
                  "-- display-side redaction; grep the unmasked pattern, e.g. 'process.env')")
            sys.exit(2)
        m = TOKEN.search(data[i:i + 400])
        raw = m.group(1) if m else data[i:i + 400]
    v = raw.decode("utf-8", "replace").strip().strip("'\"")
    h = hashlib.sha256(v.encode()).hexdigest()[:16]
    match = next((name for name, prefix in KNOWN_SHA.items() if h == prefix), None)
    print("len=%d prefix=%r suffix=%r dots=%d b64url_clean=%s" % (
        len(v), v[:8], v[-4:], v.count("."),
        bool(B64URL.fullmatch(v))))
    print("classify: %s" % classify(v))
    print("sha256[:16]=%s" % h)
    print("known_default_match: %s" % (match or "none -> unique credential, treat as live, flag for rotation"))


if __name__ == "__main__":
    main()
