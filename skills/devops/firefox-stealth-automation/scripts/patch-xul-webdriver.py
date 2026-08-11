#!/usr/bin/env python3
"""
| `scripts/patch-xul-webdriver.py` | Binary-patch Firefox xul.dll to hide navigator.webdriver |

Firefox 151+ forces `navigator.webdriver = true` at the C++ level when
`--remote-debugging-port` is active (via RemoteAgent::IsRunning()). This is
NOT fixable with user.js, autoconfig.cfg, or JS preload scripts.

The fix: replace all occurrences of the string "webdriver" in xul.dll with
random 8-byte strings. The C++ property getter fails to return a meaningful
value, making `navigator.webdriver` undefined.

Usage:
    python patch-xul-webdriver.py                        # Patch C:\Program Files\Mozilla Firefox\xul.dll
    python patch-xul-webdriver.py --dir /path/to/firefox # Patch custom Firefox directory
    python patch-xul-webdriver.py --check                # Check if xul.dll is already patched
"""
import argparse
import os
import random
import shutil
import string

OLD_STRING = b"webdriver"  # 8 bytes


def patch_xul(xul_path: str, dry_run: bool = False) -> int:
    """Patch xul.dll by replacing 'webdriver' with random 8-char string.
    Returns number of replacements made.
    """
    with open(xul_path, "rb") as f:
        data = f.read()

    count = data.count(OLD_STRING)
    if count == 0:
        print(f"✅ {xul_path}: Already patched (0 occurrences of 'webdriver')")
        return 0

    random_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))
    new_bytes = random_str.encode()

    print(f"🔧 {xul_path}: Found {count} occurrence(s) of 'webdriver', replacing with '{random_str}'")
    
    if not dry_run:
        # Create backup
        bak_path = xul_path + ".bak"
        if not os.path.exists(bak_path):
            shutil.copy2(xul_path, bak_path)
            print(f"💾 Backup saved: {bak_path}")

        data = data.replace(OLD_STRING, new_bytes)
        with open(xul_path, "wb") as f:
            f.write(data)

        # Verify
        remaining = data.count(OLD_STRING)
        print(f"✅ Patch applied: {count} replaced, {remaining} remaining")
    else:
        print(f"📋 Dry run: would replace {count} occurrence(s)")

    return count


def find_xul(search_dir: str = None) -> str:
    """Find xul.dll in a Firefox installation directory."""
    if search_dir:
        path = os.path.join(search_dir, "xul.dll")
        if os.path.exists(path):
            return path
        raise FileNotFoundError(f"No xul.dll found in {search_dir}")

    # Common locations
    candidates = [
        r"C:\Program Files\Mozilla Firefox\xul.dll",
        r"C:\Program Files (x86)\Firefox\xul.dll",
        os.path.expandvars(r"%LOCALAPPDATA%\hermes\firefox-portable\xul.dll"),
        os.path.expandvars(r"%USERPROFILE%\firefox-portable\xul.dll"),
        os.path.expandvars(r"%USERPROFILE%\camoufox\xul.dll"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "No xul.dll found. Specify --dir /path/to/firefox/installation"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Patch Firefox xul.dll to hide navigator.webdriver"
    )
    parser.add_argument("--dir", help="Firefox installation directory (default: auto-detect)")
    parser.add_argument("--check", action="store_true", help="Check if already patched (no changes)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be patched without writing")
    args = parser.parse_args()

    xul_path = find_xul(args.dir)
    print(f"📁 Found xul.dll: {xul_path} ({os.path.getsize(xul_path):,} bytes)")

    if args.check:
        with open(xul_path, "rb") as f:
            data = f.read()
        count = data.count(OLD_STRING)
        if count == 0:
            print("✅ Already patched — no 'webdriver' strings found")
        else:
            print(f"❌ NOT patched — {count} 'webdriver' string(s) found")
        return

    patch_xul(xul_path, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
