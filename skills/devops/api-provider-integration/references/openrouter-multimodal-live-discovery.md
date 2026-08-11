# OpenRouter Multimodal Integration Patterns

Validated on a production Next.js application using OpenRouter for text, audio transcription, and image generation.

## Discover capabilities from live metadata

Do not retain stale model IDs from examples or documentation. Query `GET https://openrouter.ai/api/v1/models` using the configured production key and inspect:

- `architecture.input_modalities` for `audio`, `image`, `file`, or `video`
- `architecture.output_modalities` for image-producing models
- pricing and model availability

A configured key and a model name in source code do not prove the model is currently served. Run one real low-cost request before wiring the UI.

## Audio transcription through chat completions

Use a model whose live metadata includes `audio` input. Send audio as a multimodal content part, not as base64 pasted into a text prompt:

```json
{
  "model": "<live-audio-capable-model>",
  "messages": [{
    "role": "user",
    "content": [
      {"type": "text", "text": "Transcribe exactly. Return only spoken words."},
      {"type": "input_audio", "input_audio": {"data": "<base64>", "format": "wav"}}
    ]
  }]
}
```

Browser `MediaRecorder` commonly returns WebM/Opus. If the provider contract accepts WAV, decode it with `AudioContext`, write a PCM WAV header, interleave samples, and upload `recording.wav`. Verify with a generated phrase whose expected text is known.

## Image generation through chat completions

For models whose output modalities include `image`, include `modalities: ["text", "image"]`. OpenRouter may return generated images under:

```text
choices[0].message.images[0].image_url.url
```

The URL may be a `data:image/png;base64,...` value rather than a hosted URL. The client must accept both and must reject placeholders or absent image data.

## Provider fallback decision

When one provider returns an explicit account state such as HTTP 403 `Exhausted balance`, stop retrying endpoints on that same account. Query the already-funded router/provider for equivalent live capabilities and prove one real generation before changing the integration. This is provider substitution based on observed capability, not a generic retry.

## Verification matrix

For each exposed AI control, test through an authenticated browser/session and assert:

1. HTTP 200.
2. Non-placeholder output.
3. Expected output shape (streamed text, known-phrase transcript, decodable image).
4. No browser `pageerror` events.
5. Current production key/model, not a mocked response.
