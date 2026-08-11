# Custom APK Build — "Hey Jippity" → Hermes

> Build performed June 22, 2026. Samsung Galaxy S23 Ultra (SM-S918U), Android 16 (SDK 36).
> Source at `github.com/yuga-hashimoto/openclaw-assistant`

## Changes Made to Source

### 1. Default Wake Words — SettingsRepository.kt

```kotlin
// Lines 427-428 (companion object)
const val DEFAULT_OPENCLAW_WAKE_WORD = "hey jippity"   // was "hey claw"
const val DEFAULT_HERMES_WAKE_WORD = "hey jippity"      // was "hey hermes"
```

This makes both the OpenClaw and Hermes wake word targets default to "hey jippity" on fresh install.

### 2. Package Name — build.gradle.kts

```kotlin
debug {
    // applicationIdSuffix = ".debug"   // commented out
    isMinifyEnabled = false
```

Without the suffix, the debug APK uses `com.openclaw.assistant` (same as release), so the `voice_interaction_service` and `assistant` secure settings persist across installs without adjustment.

### 3. Firebase Plugin Removal — build.gradle.kts

Commented out the Google Services and Crashlytics plugins:

```kotlin
// id("com.google.gms.google-services")
// id("com.google.firebase.crashlytics")
```

Firebase implementation dependencies were kept — they resolve from Maven without the plugin. The `FIREBASE_ENABLED=false` env var prevents Firebase code paths at runtime.

## Build & Install

```bash
cd /tmp/openclaw-assistant
export JAVA_HOME="/c/Program Files/OpenJDK/jdk-17.0.2"
export PATH="$JAVA_HOME/bin:$PATH"
export FIREBASE_ENABLED=false

./gradlew assembleStandardDebug
# First build: ~4 min (downloads deps)
# Subsequent: ~1 min

# Install
adb uninstall com.openclaw.assistant    # remove release version first
adb install app/build/outputs/apk/standard/debug/openclaw-*-debug.apk
```

## Traefik Route for Hermes API External Access

Added to `${MY_REPOS}\Documents\github\n8n\data\traefik\config\docker-fallback.yml`:

```yaml
    agency-hermes-api:
      rule: 'Host(`api.your-domain.example`) && PathPrefix(`/hermes`)'
      entryPoints:
        - 'websecure'
      middlewares:
        - strip-hermes-prefix
        - hermes-cors
      service: 'agency-hermes-api'
      tls:
        certresolver: 'letsencrypt'

  middlewares:
    strip-hermes-prefix:
      stripPrefix:
        prefixes:
          - /hermes
    hermes-cors:
      headers:
        accessControlAllowOriginList:
          - '*'
        accessControlAllowMethods:
          - GET
          - POST
          - PUT
          - PATCH
          - DELETE
          - OPTIONS
        accessControlAllowHeaders:
          - '*'
        accessControlMaxAge: 86400

  services:
    agency-hermes-api:
      loadBalancer:
        servers:
          - url: 'http://host.docker.internal:8642'
        passHostHeader: true
```

Reload Traefik: `docker kill -s HUP traefik`

The Hermes API server is then accessible from anywhere at `https://api.your-domain.example/hermes/health`.

## Deep Link Config Delivery

The HermesImportActivity accepts `agentvoice://setup` URIs:

```
agentvoice://setup?hu=https://api.your-domain.example/hermes&hk=&hm=default&hn=Jippity
```

Where:
- `hu` — Hermes base URL (primary)
- `hk` — API key (optional, blank for no auth)
- `hm` — Model name (defaults to "default")
- `hn` — Display name

Launch via ADB (explicit component):

```bash
adb shell "am start \
  -n com.openclaw.assistant/.ui.setup.HermesImportActivity \
  -d 'agentvoice://setup?hu=https://api.your-domain.example/hermes&hk=&hm=default&hn=Jippity'"
```

The user must tap "Add & Open" to confirm — there is no auto-apply.

## DNS Note

For `hermes.your-domain.example` subdomain: DNS is managed by Namecheap (registrar-servers.com). Adding a new A record for the subdomain requires Namecheap dashboard access or API credentials — not available during this deployment. Used `api.your-domain.example/hermes` path prefix instead, since that domain already had DNS pointing to the Traefik host.
