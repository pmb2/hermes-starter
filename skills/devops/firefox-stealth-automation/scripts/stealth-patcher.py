#!/usr/bin/env python3
"""Firefox Stealth Profile Patcher — v2 with remote.active-protocols detection.

Patches Firefox profile prefs to prevent automation detection
and preserve password manager features. Now also detects and fixes
remote.active-protocols=1 and devtools.debugger.remote-enabled=true
in normal-browsing profiles.

Usage:
    python stealth-patcher.py                        # Patch all profiles
    python stealth-patcher.py --profile <path>       # Patch specific profile
    python stealth-patcher.py --check                # Check status only
"""

import argparse
import os
import re
import sys

# Profiles to patch — add or remove as needed
PROFILES = {
    "hermes-mcp (automation)": r"${USER_HOME}\AppData\Local\hermes\firefox-profile",
    "<profile-id> (main - normal)": r"${USER_HOME}\AppData\Roaming\Mozilla\Firefox\Profiles\<profile-id>.default-release-1",
    "bljvedlk (old default)": r"${USER_HOME}\AppData\Roaming\Mozilla\Firefox\Profiles\bljvedlk.default",
}

# Stealth prefs we ALWAYS want in every profile
STEALTH_PREFS = {
    "marionette.enabled": False,
    "dom.webdriver.enabled": False,
    "focusmanager.testmode": False,
    "signon.autofillForms": True,
    "signon.rememberSignons": True,
    "signon.management.page.breach-alerts.enabled": True,
    "signon.management.page.vulnerable-passwords.enabled": True,
}

# Automation prefs — these are OK in the hermes-mcp profile but BAD in normal profiles
# (they cause robot detection + password manager failure)
AUTOMATION_PREFS = {
    "remote.active-protocols": 1,          # Enables BiDi automation protocol
    "devtools.debugger.remote-enabled": True,  # Opens remote debug port
    "devtools.debugger.remote-port": 9222,     # Debug port set to default
    "devtools.debugger.prompt-connection": False,  # Auto-accepts connections
}


def parse_prefs_line(line: str) -> tuple[str, str] | None:
    m = re.match(r'^user_pref\("([^"]+)",\s*(.+)\);', line.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def is_automation_profile(profile_path: str) -> bool:
    """Check if a profile is meant for automation vs normal browsing."""
    name = os.path.basename(profile_path)
    return "hermes-mcp" in name or "cdp-automation" in name or "automation" in name


def patch_profile(profile_path: str, name: str = "") -> int:
    changes = 0
    prefs_path = os.path.join(profile_path, "prefs.js")
    userjs_path = os.path.join(profile_path, "user.js")
    is_automation = is_automation_profile(profile_path)

    if not os.path.exists(prefs_path):
        print(f"  [!] No prefs.js found in {profile_path}")
        return 0

    with open(prefs_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    seen_prefs = set()
    for line in lines:
        parsed = parse_prefs_line(line)
        if parsed:
            name_str, val_str = parsed
            seen_prefs.add(name_str)

            # Always enforce stealth prefs
            if name_str in STEALTH_PREFS:
                desired = STEALTH_PREFS[name_str]
                desired_str = "true" if desired else "false"
                current_val = val_str.strip().rstrip(";")
                if current_val != desired_str:
                    new_lines.append(f'user_pref("{name_str}", {desired_str});\n')
                    print(f"  🔧 {name_str}: {current_val} → {desired_str}")
                    changes += 1
                    continue

            # In NORMAL browsing profiles, flag automation prefs as bad
            if not is_automation and name_str in AUTOMATION_PREFS:
                desired = AUTOMATION_PREFS[name_str]
                desired_str = "true" if desired else "false"
                current_val = val_str.strip().rstrip(";")
                if current_val == desired_str:
                    opposite = not desired
                    opposite_str = "true" if opposite else "false"
                    new_lines.append(f'user_pref("{name_str}", {opposite_str});\n')
                    print(f"  🔧 [AUTOMATION PREF] {name_str}: {current_val} → {opposite_str}")
                    changes += 1
                    continue

        new_lines.append(line)

    # Ensure stealth prefs exist
    for pref_name, pref_val in STEALTH_PREFS.items():
        if pref_name not in seen_prefs:
            val_str = "true" if pref_val else "false"
            new_lines.append(f'user_pref("{pref_name}", {val_str});\n')
            print(f"  ➕ Added {pref_name} = {val_str}")
            changes += 1

    if changes > 0:
        bak_path = prefs_path + ".bak"
        if not os.path.exists(bak_path):
            os.rename(prefs_path, bak_path)
            print(f"  💾 Backup saved: {bak_path}")
        with open(prefs_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"  ✅ {name or profile_path}: {changes} changes applied")
    else:
        print(f"  ✅ {name or profile_path}: Already clean, no changes needed")

    return changes


def check_profile(profile_path: str, name: str = "") -> list[str]:
    issues = []
    prefs_path = os.path.join(profile_path, "prefs.js")
    is_automation = is_automation_profile(profile_path)

    if not os.path.exists(prefs_path):
        return ["No prefs.js found"]

    with open(prefs_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Check stealth prefs
    for pref_name, bad_val in {"marionette.enabled": True, "signon.autofillForms": False,
                                "signon.rememberSignons": False}.items():
        bad_str = "true" if bad_val else "false"
        if re.search(rf'user_pref\("{re.escape(pref_name)}",\s*{re.escape(bad_str)}\);', content):
            issues.append(f"{pref_name} = {bad_str} (should be {not bad_val})")

    # In normal-browsing profiles, check for automation prefs
    if not is_automation:
        for pref_name, bad_val in AUTOMATION_PREFS.items():
            bad_str = "true" if bad_val else "false"
            if re.search(rf'user_pref\("{re.escape(pref_name)}",\s*{re.escape(bad_str)}\);', content):
                issues.append(f"{pref_name} = {bad_str} (AUTOMATION PREF in normal-browsing profile!)")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Firefox Stealth Profile Patcher v2")
    parser.add_argument("--profile", "-p", help="Path to specific profile")
    parser.add_argument("--check", "-c", action="store_true", help="Check status only")
    parser.add_argument("--all", action="store_true", help="Patch all known profiles")
    args = parser.parse_args()

    if args.profile:
        profiles = {"custom": args.profile}
    else:
        profiles = PROFILES if args.all or not args.check else PROFILES

    total = 0
    for name, path in profiles.items():
        label = f"\n📁 {name} ({path})"
        print(label)
        print("─" * len(label))
        if args.check:
            issues = check_profile(path, name)
            for issue in issues:
                print(f"  ❌ {issue}")
            if not issues:
                print(f"  ✅ Clean — no stealth issues detected")
        else:
            total += patch_profile(path, name)

    status = f"\n🎯 {total} change(s) applied — restart Firefox to activate" if total else ""
    print(status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
