# WakeHermesClaw Deployment Notes

> Deployment tested June 2026 on Samsung Galaxy S23 Ultra (SM-S918U), Android 16 (SDK 36).
> Source: `github.com/yuga-hashimoto/openclaw-assistant`

## Device Info

| Property | Value |
|----------|-------|
| Device | Samsung Galaxy S23 Ultra (SM-S918U) |
| Android | 16 (SDK 36) |
| ADB | Platform Tools 36.0.2 |
| Host | Windows 10 — Hermes Agent (OpenCode Go provider) |

## Full Deployment Sequence

### 1. Install APK

```bash
# Download from GitHub releases
curl -sL -o openclaw-assistant.apk \
  https://github.com/yuga-hashimoto/openclaw-assistant/releases/download/v2.4.9.1/OpenClawAssistant-v2.4.9.1.apk

adb install -r openclaw-assistant.apk
```

### 2. Set as Default Assistant

```bash
adb shell settings put secure voice_interaction_service \
  com.openclaw.assistant/.service.OpenClawAssistantService
adb shell settings put secure assistant \
  com.openclaw.assistant/.service.OpenClawAssistantService

# Check it took effect
adb shell dumpsys voiceinteraction | grep mComponent
# Expected: mComponent=com.openclaw.assistant/.service.OpenClawAssistantService
```

### 3. ADB Reverse Proxy

```bash
adb reverse tcp:8642 tcp:8642

# Verify Hermes API is reachable from phone
adb shell curl -s http://127.0.0.1:8642/health
# Expected: {"status": "ok", "platform": "hermes-agent", "version": "0.17.0"}
```

### 4. App Config (UI Required)

Settings are stored in EncryptedSharedPreferences — cannot inject via shell.

Open the app → Settings:
1. Backends → Add Hermes API Server → URL: `http://127.0.0.1:8642`
2. Wake Word → Set OpenClaw word: `hey jippity`
3. Wake Word → Set Hermes word: `hey jippity`
4. Hotword Detection → Enable
5. TTS → Enable (Edge TTS works with no API key)
6. Grant permissions (Mic, Notifications)

### 5. Wake Word Setup (Alternative: ADB)

If the running app accepts broadcast commands, set the wake word directly:

```bash
# Set openclaw wake word via secure settings-adjacent method
# Note: EncryptedSharedPreferences means this may not work
# Check hotword_prefs for unencrypted fallback values
adb shell am broadcast \
  -a com.openclaw.assistant.ACTION_UPDATE_WAKE_WORD \
  -n com.openclaw.assistant/.receiver.WakeWordUpdateReceiver
```

## Verifying Functionality

```bash
# Check voice interaction service is active
adb shell dumpsys voiceinteraction

# Check app has mic permission
adb shell dumpsys package com.openclaw.assistant | grep RECORD_AUDIO

# Monitor hotword detection
adb logcat -s HotwordService VIS OpenClawAssistantSvc

# Test Hermes API tunnel
adb shell curl -s http://127.0.0.1:8642/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"hermes-agent","messages":[{"role":"user","content":"hello"}]}'
```

## Restoring Google Assistant

```bash
adb shell settings put secure voice_interaction_service \
  com.google.android.googlequicksearchbox/com.google.android.voiceinteraction.GsaVoiceInteractionService
adb shell settings put secure assistant \
  com.google.android.googlequicksearchbox/com.google.android.voiceinteraction.GsaVoiceInteractionService
```

## Known Issues

- **CAPTURE_AUDIO_HOTWORD** is role-managed on Android 14+. It is automatically granted when the app holds the ASSISTANT role (set via secure settings). It cannot be granted with `pm grant`.
- **`adb reverse` is not persistent.** The tunnel breaks when USB is disconnected. Re-run after reconnecting.
- **Release APK has R8-optimized activities.** Only `MainActivity` is resolvable by component name. Most settings activities are `exported=false` and cannot be launched from shell.
- **Deep-link `agentvoice://` scheme** may not resolve on first install until the app has been launched once. Always open the app manually before attempting deep-link setup.
