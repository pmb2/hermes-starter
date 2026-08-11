# Free OpenRouter Models (as of 2026-05-29)

Live-quoted from `GET https://openrouter.ai/api/v1/models`. All models below have `pricing.prompt=0` and `pricing.completion=0` — completely free.

## Totally Free Models ($0/$0)

| Model | Context | Notes |
|-------|---------|-------|
| `openrouter/owl-alpha` | 1,048,756 | Strong agentic foundation model, code + general |
| `qwen/qwen3-coder:free` | 1,048,576 | Code-specialized MoE 480B-A35B |
| `deepseek/deepseek-v4-flash:free` | 1,048,576 | Fast MoE, the model this Hermes runs on |
| `nousresearch/hermes-3-llama-3.1-405b:free` | 131,072 | 405B param, strongest general model |
| `nvidia/nemotron-3-super-120b-a12b:free` | 1,000,000 | NVIDIA's strongest open hybrid MoE |
| `google/gemma-4-31b-it:free` | 262,144 | Dense 30.7B multimodal |
| `google/gemma-4-26b-a4b-it:free` | 262,144 | MoE variant |
| `meta-llama/llama-3.3-70b-instruct:free` | 131,072 | Reliable multilingual |
| `openai/gpt-oss-120b:free` | 131,072 | OpenAI open weights 117B MoE |
| `openai/gpt-oss-20b:free` | 131,072 | OpenAI open weights 21B dense |
| `minimax/minimax-m2.5:free` | 204,800 | Strong productivity model |
| `moonshotai/kimi-k2.6:free` | 262,144 | Strong multimodal |
| `qwen/qwen3-next-80b-a3b-instruct:free` | 262,144 | Next-gen Qwen |
| `poolside/laguna-m.1:free` | 262,144 | Code-focused |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | 256,000 | Multimodal reasoning |
| `nvidia/nemotron-3-nano-30b-a3b:free` | 262,144 | Lightweight reasoning |
| `z-ai/glm-4.5-air:free` | 131,072 | Lightweight GLM |

## Recommended Per-Task

| Task | Pick | Why |
|------|------|-----|
| Idea generation | `owl-alpha` | 1M ctx, free, strong creative reasoning |
| Code / experiments | `qwen/qwen3-coder:free` | 1M ctx, MoE design for coding |
| Paper writing | `owl-alpha` | 1M ctx for long structured output |
| Peer review | `nousresearch/hermes-3-llama-3.1-405b:free` | 405B, strongest critical reasoning |
| General fallback | `qwen/qwen3-coder:free` | Best balance of speed + quality + price |

## Model Name Format

Always use the full OpenRouter model ID. The AI Scientist's `llm.py` patches auto-detect OpenRouter models by:
1. `openrouter/` prefix (explicit) — strips prefix, passes rest as model name
2. Bare `provider/model:free` format — detected via `_is_openrouter_model()` which checks for `/` in the name

The `:free` suffix is passed through as part of the model name — OpenRouter handles rate limiting on free tier endpoints.

## Pricing Note

Free models may have rate limits. The `openrouter/free` meta-model routes to random free models but is less predictable than picking a specific one. `owl-alpha` is the only model with truly 0 pricing across all parameters (no `:free` suffix needed).
