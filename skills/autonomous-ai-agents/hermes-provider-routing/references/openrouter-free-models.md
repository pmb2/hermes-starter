# OpenRouter Free Model Catalog

As of June 2026, OpenRouter offers **23 free models** (suffix `:free`). All are usable via Hermes fallback or sub-agent delegation at zero token cost.

## Model Table

| Model ID | Context | Best For |
|----------|---------|----------|
| `cognitivecomputations/dolphin-mistral-24b-venice-edition:free` | 32K | General |
| `cohere/north-mini-code:free` | **256K** | Code review, refactoring |
| `google/gemma-4-26b-a4b-it:free` | **262K** | General, vision-capable |
| `google/gemma-4-31b-it:free` | **262K** | General, vision-capable (recommended fallback) |
| `liquid/lfm-2.5-1.2b-instruct:free` | 32K | Tiny/lightweight tasks |
| `liquid/lfm-2.5-1.2b-thinking:free` | 32K | Tiny reasoning |
| `meta-llama/llama-3.2-3b-instruct:free` | **131K** | Lightweight, fast |
| `meta-llama/llama-3.3-70b-instruct:free` | **131K** | Heavy reasoning, critique |
| `nex-agi/nex-n2-pro:free` | **262K** | General purpose |
| `nousresearch/hermes-3-llama-3.1-405b:free` | **131K** | Our namesake — large model |
| `nvidia/nemotron-3-nano-30b-a3b:free` | **256K** | Lightweight Nemotron |
| `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | **256K** | Reasoning-focused |
| `nvidia/nemotron-3-super-120b-a12b:free` | **1M** | Large document processing |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | **1M** | Largest — ultra-context |
| `nvidia/nemotron-3.5-content-safety:free` | **128K** | Content safety filtering |
| `nvidia/nemotron-nano-12b-v2-vl:free` | **128K** | Vision-language |
| `nvidia/nemotron-nano-9b-v2:free` | **128K** | Lightweight general |
| `openai/gpt-oss-120b:free` | **131K** | Open-source GPT-class |
| `openai/gpt-oss-20b:free` | **131K** | Lightweight GPT-class |
| `poolside/laguna-m.1:free` | **262K** | Code-focused |
| `poolside/laguna-xs.2:free` | **262K** | Lightweight code |
| `qwen/qwen3-coder:free` | **1M** | Coding, research (recommended for sub-agents) |
| `qwen/qwen3-next-80b-a3b-instruct:free` | **262K** | Strong general reasoning |

## Top Picks

| Use Case | Best Free Model |
|----------|----------------|
| **Sub-agent default** | `qwen/qwen3-coder:free` — 1M context, strong tool calling, free |
| **Fallback model** | `google/gemma-4-31b-it:free` — 262K context, vision-capable |
| **Heavy reasoning** | `meta-llama/llama-3.3-70b-instruct:free` — strong 70B |
| **Ultra-long context** | `nvidia/nemotron-3-super-120b-a12b:free` — 1M window |
| **Code review** | `cohere/north-mini-code:free` — code-specialized, 256K |
| **Lightning fast** | `liquid/lfm-2.5-1.2b-instruct:free` — tiny, near-instant |

## Rate Limits

Free tier models on OpenRouter are rate-limited (typically 20-60 req/min depending on model). For high-volume sub-agent work, distribute across multiple free models or implement retry with backoff.

All models are subject to OpenRouter's free tier TOS — no commercial/redistribution use without attribution. These are fine for personal automation, research, and development.
