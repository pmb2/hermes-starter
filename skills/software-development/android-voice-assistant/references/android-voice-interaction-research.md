# Android Voice Interaction — Deep Research Notes

> Research performed June 2026 for the "Hey Jippity" → Hermes project.
> Sources: AOSP source code, Android developer docs, Picovoice docs, Home Assistant Android voice integration discussions, XDA forums.

## SoundTrigger HAL Architecture

Android's always-on hotword detection uses a layered stack:

```
┌──────────────────────────────────┐
│  VoiceInteractionService         │ ← App layer (replaceable, no root)
│  (Default Digital Assistant)     │
├──────────────────────────────────┤
│  SoundTrigger HAL (STHAL)        │ ← Vendor HAL (not replaceable without root)
│  Manages DSP sound models        │
├──────────────────────────────────┤
│  DSP Firmware                    │ ← Vendor firmware (locked)
│  Pre-loaded keyphrases only      │
└──────────────────────────────────┘
```

The SoundTrigger HAL provides vendor-implemented engines that run detection algorithms on a dedicated low-power DSP. Each engine has pre-loaded keyphrases (typically "Ok Google" and "Hey Google"). The HAL is at `/vendor/lib64/sound_trigger.primary.*.so` and cannot be modified without root + re-flashing vendor partitions.

## VoiceInteractionService API Details

### Key Classes

| Class | Purpose | Added |
|-------|---------|-------|
| `android.service.voice.VoiceInteractionService` | Base service for custom assistant | API 21 |
| `AlwaysOnHotwordDetector` | DSP-based hotword detection | API 21 |
| `HotwordDetectionService` | Software-based detection (isolated process) | API 30 |
| `VisualQueryDetector` | Camera-based context detection | API 34 |

### AlwaysOnHotwordDetector States

| State | Meaning | Action |
|-------|---------|--------|
| `STATE_HARDWARE_UNAVAILABLE` | DSP not available or permission missing | Grant CAPTURE_AUDIO_HOTWORD |
| `STATE_KEYPHRASE_UNENROLLED` | Keyphrase not in DSP model | Launch enroll intent |
| `STATE_KEYPHRASE_ENROLLED` | Ready to detect | Call `startRecognition()` |

### Software Detection (HotwordDetectionService)

When the DSP doesn't support your keyphrase (it won't for custom phrases), use `HotwordDetectionService`:

- Runs in an isolated process (`android:isolatedProcess="true"`)
- Gets `onDetect(EventPayload, Callback)` when the DSP triggers AND for software-only mode
- Can use any custom wake word engine (Porcupine, etc.)
- Receives raw PCM audio via `EventPayload.getCaptureAudioFormat()`

### Audio Capture After Detection

```java
// From the AOSP sample — creates AudioRecord from detection event
AudioRecord createAudioRecord(EventPayload eventPayload, int bytesPerSecond) {
    return new AudioRecord.Builder()
            .setAudioAttributes(
                    new AudioAttributes.Builder()
                            .setInternalCapturePreset(MediaRecorder.AudioSource.HOTWORD)
                            .build())
            .setAudioFormat(eventPayload.getCaptureAudioFormat())
            .setBufferSizeInBytes(getBufferSizeInBytes(bytesPerSecond, 5))
            .setSharedAudioEvent(eventPayload.getHotwordDetectedResult().getMediaSyncEvent())
            .build();
}
```

## AOSP Sample Code Location

The canonical reference implementation is in the AOSP `development` repo:

- **Clone:** `git clone https://android.googlesource.com/platform/development.git`
- **Path:** `samples/VoiceInteractionService/`
- **Key files:**
  - `AndroidManifest.xml` — service declaration, permissions
  - `res/xml/voice_interaction.xml` — metadata binding hotword/visual services
  - `src/.../SampleVoiceInteractionService.java` — main service with `createAlwaysOnHotwordDetector`
  - `src/.../SampleHotwordDetectionService.java` — software detection in isolated process
  - `src/.../MainActivity.java` — launcher for permission grant UI
  - `com.example.android.voiceinteractor.xml` — priv-app permissions XML for pre-granting CAPTURE_AUDIO_HOTWORD

## ADB Commands Reference

### Set Default Assistant

```bash
# Primary method (secure settings)
adb shell settings put secure voice_interaction_service <package>/<service>
adb shell settings put secure assistant <package>/<service>
adb shell settings put secure voice_recognition_service <package>/<service>

# Role method (Android 10+)
adb shell cmd role set-bypassing-role-qualification true
adb shell cmd role add-role-holder android.app.role.ASSISTANT <package>

# Verify
adb shell settings get secure voice_interaction_service
adb shell settings get secure assistant
adb shell dumpsys role | grep ASSISTANT
```

### Check Permissions

```bash
adb shell dumpsys package <package> | grep -E "HOTWORD|RECORD_AUDIO|CAPTURE"
```

### Pre-Grant Privileged Permissions

For apps that need CAPTURE_AUDIO_HOTWORD (a signature|privileged permission), push a permissions XML:

```bash
adb root
adb remount
adb push com.example.permissions.xml /system/etc/permissions/
adb reboot
```

The XML format (from AOSP sample):
```xml
<permissions>
    <privapp-permissions package="com.example.assistant">
        <permission name="android.permission.CAPTURE_AUDIO_HOTWORD"/>
        <permission name="android.permission.INTERACT_ACROSS_USERS"/>
        <permission name="android.permission.MANAGE_HOTWORD_DETECTION"/>
    </privapp-permissions>
</permissions>
```

### Log Filtering

```bash
# Watch voice interaction events
adb logcat -s VIS SHotwordDetectionSrvc AlwaysOnHotword SoundTrigger

# Verbose audio debugging
adb logcat \
  com.example.assistant|AlwaysOnHotword|SoundTrigger|RecordingActivityMonitor|soundtrigger|AudioPolicyManager|AudioFlinger|AudioPolicyIntefaceImpl|AudioPolicyService|VIS|SHotwordDetectionSrvc|Hotword-AudioUtils
```

### Restore Google Assistant

```bash
adb shell settings put secure voice_interaction_service \
  com.google.android.googlequicksearchbox/com.google.android.voiceinteraction.GsaVoiceInteractionService
adb shell settings put secure assistant \
  com.google.android.googlequicksearchbox/.search.SearchApplication
```

## Porcupine Integration Notes

- **SDK:** `ai.picovoice:porcupine-android:${version}` from Maven Central
- **Custom word:** Train at console.picovoice.ai → download .ppn file → place in `assets/`
- **Built-in keywords:** `Porcupine.BuiltInKeyword` enum (computer, grasshopper, etc.)
- **API:** `PorcupineManager` handles audio capture + detection in one class
- **Free tier:** Unlimited custom wake words, commercial use allowed
- **Metrics:** ~200ms inference, 2MB library, 98% accuracy, runs on-device with no network

```kotlin
// Minimal integration
val porcupineManager = PorcupineManager(
    context,
    accessKey,
    listOf("hey_jippity.ppn"),       // custom wake word model paths
    porcupineManagerCallback { keywordIndex ->
        // Wake word detected — start recording
    }
)
porcupineManager.start()
```

## Home Assistant Assist as Precedent

Home Assistant's Android app implements a similar pattern — they use `VoiceInteractionService` to replace Google Assistant and route audio to their own Assist pipeline. Key takeaways from HA's implementation:
- The approach is proven in production
- Settings may need re-application after APK updates
- Works on Android 10+ without root
- HA uses a Wyoming protocol satellite pattern for audio streaming

## References

- AOSP VoiceInteractionService sample: https://android.googlesource.com/platform/development/+/HEAD/samples/VoiceInteractionService/
- Android VoiceInteractionService docs: https://developer.android.com/reference/android/service/voice/VoiceInteractionService
- AOSP Sound Trigger docs: https://source.android.com/docs/core/audio/sound-trigger
- Porcupine Android SDK: https://picovoice.ai/docs/quick-start/porcupine-android/
- Home Assistant Android voice: https://www.home-assistant.io/voice_control/android/
- Home Assistant voice discussions: https://github.com/home-assistant/android/discussions/5974
