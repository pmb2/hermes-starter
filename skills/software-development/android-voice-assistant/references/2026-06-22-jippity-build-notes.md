# "Hey Jippity" Build — June 22, 2026

## Device Profile
- **Phone:** Samsung Galaxy S23 Ultra (SM-S918U)
- **Android:** 16 (SDK 36)
- **Build type:** Debug (for `run-as` access + component visibility)

## Custom APK Build

### Source
Fork of WakeHermesClaw (openclaw-assistant by yuga-hashimoto)
- **GitHub:** github.com/yuga-hashimoto/openclaw-assistant
- **Branch:** main (v2.4.9.1 tag)
- **Cloned to:** /tmp/openclaw-assistant/

### Defaults Changed
```kotlin
// SettingsRepository.kt
const val DEFAULT_OPENCLAW_WAKE_WORD = "hey jippity"
const val DEFAULT_HERMES_WAKE_WORD = "hey jippity"
```

### Build Config Changes
```kotlin
// build.gradle.kts — removed Google Services plugin
// id("com.google.gms.google-services")
// id("com.google.firebase.crashlytics")
// applicationIdSuffix = ".debug"  // removed to keep com.openclaw.assistant
```

### Build Command
```bash
export FIREBASE_ENABLED=false
export JAVA_HOME="/c/Program Files/OpenJDK/jdk-17.0.2"
./gradlew assembleStandardDebug
# → app/build/outputs/apk/standard/debug/openclaw-05a3bcb-dirty-debug.apk
```

## Infrastructure Setup

### Traefik Route
Added to `${MY_REPOS}\Documents\github\n8n\data\traefik\config\docker-fallback.yml`:
```yaml
routers:
  agency-hermes-api:
    rule: "Host(`api.your-domain.example`) && PathPrefix(`/hermes`)"
    entryPoints: [websecure]
    middlewares: [strip-hermes-prefix, hermes-cors]
    service: agency-hermes-api
    tls: { certresolver: letsencrypt }
services:
  agency-hermes-api:
    loadBalancer:
      servers:
        - url: 'http://host.docker.internal:8642'
      passHostHeader: true
```
Route accessible at: `https://api.your-domain.example/hermes/health`

### ADB Reverse Proxy
```bash
adb reverse tcp:8642 tcp:8642
```
Phone `localhost:8642` → host Hermes API. Re-establishes after ADD reconnect.

## ADB Automation Sequence (Phone Screen Unlocked)

### 1. Dismiss Keyguard
```bash
adb shell input keyevent KEYCODE_WAKEUP
adb shell wm dismiss-keyguard
```
`wm dismiss-keyguard` bypasses lock screen. Works on Android 16 (tested on Samsung One UI).

### 2. Configure Hermes Backend via Deep Link
```bash
adb shell "am start -n com.openclaw.assistant/.ui.setup.HermesImportActivity \
  -d 'agentvoice://setup?hu=https://api.your-domain.example/hermes&hk=&hm=default&hn=Jippity'"
```
Use `-n` with explicit component — implicit deep links (`am start -d`) fail on Android 16 due to package visibility restrictions.

### 3. Confirm Import (Tap "Add and open")
```bash
# The button is a Compose view at [63,1990][1017,2095]
adb shell input tap 540 2042
```
The activity navigates to MainActivity after successful save.

### 4. Enable Hotword Detection
```bash
# Open app to Home screen
adb shell am start -n com.openclaw.assistant/.MainActivity

# Tap the Wake Word toggle switch (Compose switch)
# Switch bounds from uiautomator dump: [873,1393][982,1494]
adb shell input tap 928 1444
```
The status text changes from "open claw / hey jippity (OFF)" to "(ON)".

### 5. Verify HotwordService is Running
```bash
# Check process
adb shell ps | grep openclaw

# Check notification (foreground service)
adb shell dumpsys notification | grep -A5 openclaw

# Check from app UI: should show persistent notification with wake word
```

## MSYS2/PATH Handling (Windows Git-Bash)
The default Git-Bash translates POSIX paths starting with `/` to Windows paths, breaking adb commands. Workaround:
```bash
export MSYS2_ARG_CONV_EXCL="*"
```
This env var disables all MSYS2 path translation for the rest of the shell session. Set it at the top of every ADB automation script.

Alternative: Use double-slash for key paths:
```bash
adb shell screencap -p //sdcard/screen.png  # double-slash prevents translation
```

## Technical Constraints Discovered
- **EncryptedSharedPreferences:** Cannot inject config via `adb shell` commands. Deep-link URI is the only ADB-accessible path.
- **Release APK proguard:** Strips non-launcher activities (HermesImportActivity absent). Debug builds retain all components.
- **Android 16 implicit intents:** `am start -d` with custom schemes fails. Use `-n` explicit component targeting.
- **Compose UI tapping:** Compose clickable views may not respond to `input tap` at exact coordinates as reliably as native Views. Multiple taps at different y offsets within the bounds increase success rate.
- **HotwordService not exported:** Cannot start via `am startservice`. Must be enabled through app UI toggle.

## Verification Points
1. `adb shell settings get secure voice_interaction_service` → `com.openclaw.assistant/.service.OpenClawAssistantService`
2. `adb shell dumpsys voiceinteraction` → `mComponent=com.openclaw.assistant/...`
3. Hermes health from phone: `adb shell curl -s http://127.0.0.1:8642/health`
4. Hermes health from internet: `curl -sk https://api.your-domain.example/hermes/health`
5. App UI shows "Hermes Agent" with connection status (HTTP 401 = connected, needs auth key)
6. Wake Word section shows "hey jippity (ON)"
