# Profile Contamination: Diagnosis & Restoration

## What Happened

On 2026-05-30, headless PIM extraction runs that used the operator's main profile (`<profile-id>`) with `--remote-debugging-port` wrote automation prefs into `prefs.js`. Combined with 23 orphan Firefox processes that accumulated over ~2 days from headless sessions that weren't properly cleaned up, this prevented Firefox from opening normally.

## Symptoms

- Firefox won't start or opens with wrong profile
- "parent.lock" files found in profile directories with no Firefox running
- Multiple Firefox processes in Task Manager (orphans accumulated from headless runs)
- Password manager disabled, robot icon visible
- Firefox Sync not connecting
- Wrong profile opens when clicking the Firefox icon

## Detection Commands

```bash
# Find orphan Firefox processes
tasklist /FI "IMAGENAME eq firefox.exe" /FO CSV

# Find stale lock files
find ${USER_HOME}/AppData/Roaming/Mozilla/Firefox/Profiles -name "parent.lock"
find ${USER_HOME}/AppData/Roaming/Mozilla/Firefox/Profiles -name ".parentlock"

# Check for contaminated prefs
python << 'PYEOF'
import os
profiles_dir = r'${USER_HOME}\AppData\Roaming\Mozilla\Firefox\Profiles'
for p in os.listdir(profiles_dir):
    prefs_path = os.path.join(profiles_dir, p, 'prefs.js')
    if os.path.exists(prefs_path):
        with open(prefs_path) as f:
            content = f.read()
        issues = []
        if 'remote.active-protocols' in content:
            if any('1' in l for l in content.splitlines() if 'remote.active-protocols' in l):
                issues.append('remote.active-protocols set')
        if 'devtools.debugger.remote-enabled' in content:
            if any('true' in l for l in content.splitlines() if 'devtools.debugger.remote-enabled' in l):
                issues.append('debugger.remote-enabled=true')
        if issues:
            print(f'{p}: {", ".join(issues)}')
PYEOF
```

## Restoration Procedure

### Step 1: Kill ALL orphan Firefox processes
```python
import subprocess, os
os.system('taskkill /F /IM firefox.exe 2>nul')
# Wait for ports to release
import time; time.sleep(3)
```

### Step 2: Remove stale parent.lock files
```bash
find ${USER_HOME}/AppData/Roaming/Mozilla/Firefox/Profiles -name "parent.lock" -delete
find ${USER_HOME}/AppData/Roaming/Mozilla/Firefox/Profiles -name ".parentlock" -delete
find ${USER_HOME}/AppData/Roaming/Mozilla/Firefox/Profiles -name "Telemetry.FailedProfileLocks.txt" -delete
```

### Step 3: Fix profiles.ini
Set the operator's profile as default for the main Firefox installation:
```
[Install308046B0AF4A39CB]
Default=Profiles/<profile-id>.default-release-1
Locked=1
```
Remove `Default=1` from other profile sections. Keep `StartWithLastProfile=1` in `[General]`.

### Step 4: Clean contaminated prefs in the operator's main profile
In `<profile-id>.default-release-1/prefs.js`, ensure these values:
```
user_pref("remote.active-protocols", 0);
user_pref("devtools.debugger.remote-enabled", false);
user_pref("devtools.debugger.prompt-connection", true);
```

### Step 5: Verify
- No `parent.lock` files remain
- `remote.active-protocols=0` and `devtools.debugger.remote-enabled=false` in <profile-id>'s prefs.js
- profiles.ini has <profile-id> as default for the main installation
- Firefox opens correctly with saved passwords and bookmarks

## Prevention

The PIM ingestion script now runs orphan cleanup BEFORE launching Firefox:
1. Kill any Firefox on port 9239 by PID (surgical, not kill-all)
2. Remove parent.lock from automation profile
3. Sync cookies from main profile to auto profile (before headless launch)
4. Only then start the headless Firefox with automation profile

The independent cron job `28d080a625fd` runs every 2h to sync profile data.

## Related Scripts

| Script | Path | Purpose |
|--------|------|---------|
| `profile-sync.py` | `${USER_HOME}\AppData\Local\hermes\scripts\profile-sync.py` | Copies cookies/logins from main → auto profile (cron job, every 2h) |
| `ingest-chatgpt-grok.sh` | `${USER_HOME}\AppData\Local\hermes\scripts\ingest-chatgpt-grok.sh` | PIM ingestion: orphan cleanup → sync → launch → extract → sync MemPalace |
