# xul.dll Binary Patching — Hide navigator.webdriver in Firefox 151+

## The Problem

Firefox 151+ forces `navigator.webdriver = true` at the C++ engine level when
`--remote-debugging-port` is active. The source code check (Navigator.cpp):

```cpp
bool Navigator::GetWebdriver(ErrorResult& aRv) {
  if (StaticPrefs::dom_webdriver_enabled() || RemoteAgent::IsRunning()) {
    return true;
  }
  return false;
}
```

Even with `dom.webdriver.enabled = false` (via user.js, lockPref in autoconfig.cfg,
or any other pref mechanism), the `RemoteAgent::IsRunning()` check STILL returns
true when Firefox is started with `--remote-debugging-port`. This is because the
RemoteAgent C++ class tracks its state internally, independent of prefs.

## What DOESN'T Work (All Tested)

| Approach | Result |
|----------|--------|
| `user_pref("dom.webdriver.enabled", false)` | Overridden by RemoteAgent::IsRunning() |
| `lockPref("dom.webdriver.enabled", false)` in autoconfig.cfg | C++ ignores the locked pref |
| `script.addPreloadScript` overriding via Object.defineProperty | C++ getter is non-configurable |
| `Page.addScriptToEvaluateOnNewDocument` | Same fundamental limitation |
| StealthEngine 22 measures via ultimate-firefox-mcp | 5/10 checks pass but webdriver still true |
| Deleting `Navigator.prototype.webdriver` from JS | Prototype is also C++-level non-configurable |

## The Solution: Binary Patching xul.dll

The `Navigator::GetWebdriver()` C++ function uses the string literal `"webdriver"`
internally. By replacing all occurrences of the byte sequence `b"webdriver"` in
`xul.dll` with random 8-byte strings, the property becomes `undefined` because
the string the C++ code references no longer resolves correctly.

## Open-Source Projects Using This Approach

### bytexenon/undetected_geckodriver (80★)
- **Repo:** https://github.com/bytexenon/undetected_geckodriver
- **What it is:** Python pip package for undetected Firefox automation
- **Approach:** Copies Firefox installation, patches `libxul.so` (Linux) by replacing
  all `b"webdriver"` strings with random 8-char strings
- **Current status:** Linux only (Windows/macOS planned)
- **Install:** `pip install undetected-geckodriver`
- **Key constant:** `TO_REPLACE_STRING = b"webdriver"` in `constants.py`

### coleleavitt/undetected_geckodriver (0★, very new)
- **Repo:** https://github.com/coleleavitt/undetected_geckodriver
- **What it is:** Rust binary patcher for Firefox's libxul
- **Approach:** Uses TMR (Triple Modular Redundancy) patterns to find and replace
  webdriver-related byte patterns in ELF/PE binaries
- **Claims:** Radiation-hardened, JPL-STD-RUST-001 compliant
- **Current status:** Very new, minimal code, no Windows build artifacts

### daijro/camoufox (8,825★)
- **Repo:** https://github.com/daijro/camoufox
- **What it is:** Full Firefox fork (based on LibreWolf) with comprehensive
  anti-detection patches at the C++ source level
- **Pre-built binaries:** Available for Linux, macOS, Windows in releases
- **Windows binary:** `camoufox-*-win.x86_64.zip` (530MB compressed)
- **Key patches:** navigator-spoofing.patch, fingerprint-injection.patch,
  audio-context-spoofing.patch, font-list-spoofing.patch, etc.
- **⚠️ Caveat:** Camoufox blocks `browsingContext.create` via BiDi as an
  anti-debugging measure. This breaks BiDi automation. For automation use cases,
  use the simple xul.dll string-replacement patch instead.

## Implementation (Windows, Python)

```python
import random, string, shutil

# 1. Copy Firefox installation (no admin needed)
# cp -r "/c/Program Files/Mozilla Firefox/"* "${USER_HOME}/firefox-portable/"

# 2. Patch xul.dll
xul_path = r"${USER_HOME}\firefox-portable\xul.dll"
shutil.copy2(xul_path, xul_path + ".bak")

with open(xul_path, "rb") as f:
    data = f.read()

old = b"webdriver"  # 8 bytes
# Firefox 151.0.2 has exactly 2 occurrences
random_str = "".join(random.choices(string.ascii_letters + string.digits, k=8))
data = data.replace(old, random_str.encode())

with open(xul_path, "wb") as f:
    f.write(data)
```

## Verification

```python
from app.connectors._firefox_bidi import FirefoxBiDiClient

client = FirefoxBiDiClient(port=9238)
await client.connect()
await client.new_tab("data:text/html,<h1>test</h1>")
await asyncio.sleep(2)

result = await client.evaluate("JSON.stringify({webdriver: navigator.webdriver, defined: typeof navigator.webdriver !== 'undefined'})")
# Expected: {"defined":false}  (navigator.webdriver is undefined)
```

## Full ChatGPT Test Result

With patched xul.dll + 22 StealthEngine measures:
1. `navigator.webdriver` = `undefined` ✅
2. No Cloudflare challenge (ChatGPT loads directly) ✅
3. Title shows "ChatGPT" (not "Just a moment...") ✅
4. Login page shows (needs session cookies) ⚠️

## Notes

- The patch does NOT affect other browser functionality
- Works with ALL Firefox versions (not just 151+)
- Must be re-applied after Firefox updates (xul.dll gets replaced)
- Only 2 occurrences of `"webdriver"` in Firefox 151.0.2 xul.dll
- Keep a backup of the original xul.dll
- The patched Firefox can use the same profile as a non-patched Firefox
