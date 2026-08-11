# AI Scientist — Setup & Usage Reference

## Venv Setup

```bash
cd ${MY_REPOS}/AI-Scientist
python -m venv venv
venv/Scripts/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
venv/Scripts/pip install anthropic aider-chat backoff openai google-generativeai matplotlib pypdf
venv/Scripts/pip install transformers datasets tiktoken wandb tqdm pymupdf4llm einops scikit-learn pyalex mcp
```

## Patches Applied

### `ai_scientist/llm.py`
- Added `_is_openrouter_model()` helper — detects any `provider/model:free` format
- Added `openrouter/` prefix handling in `create_client()` — strips prefix, passes bare name to OpenRouter
- Added generic OpenRouter catch-all in `create_client()` — catches any model with `/` that isn't bedrock/vertex_ai/deepseek/gemini
- Added OpenRouter branches in `get_response_from_llm()` and `get_batch_responses_from_llm()` — uses OpenAI-compatible client with OpenRouter base URL
- Added Claude Sonnet 4/4.5 to `AVAILABLE_LLMS`

### `launch_scientist.py`
- Added `_aider_model_name()` helper — maps model names to Aider's `Model()` format
- Added `openrouter/` passthrough for Aider integration (was hardcoded to Llama 3.1 405B)
- Patched review step (line ~270) — was hardcoded `model="gpt-4o-2024-05-13"` + `client=openai.OpenAI()`, now uses OpenRouter with `openrouter/google/gemma-4-31b-it:free`
- Patched improvement review (line ~301) — same fix
- Both review patches use `api_key=os.environ.get("OPENROUTER_API_KEY", os.environ.get("OPENAI_API_KEY", ""))` and `base_url="https://openrouter.ai/api/v1"`

### `hermes_mcp_server.py` (new file)
- FastMCP server with 9 tools
- `_run_ai_scientist()` helper for subprocess calls to the project venv
- `_list_templates()` / `_list_results()` helpers
- Tools: `system_status`, `list_templates`, `list_results`, `generate_ideas`, `run_experiment`, `prepare_baseline`, `review_paper`, `read_template_info`, `run_command`

## MCP Config Entry

```yaml
mcp_servers:
  ai-scientist:
    args:
    - ${MY_REPOS}/Documents/github/AI-Scientist/hermes_mcp_server.py
    - --stdio
    command: ${MY_REPOS}/Documents/github/AI-Scientist/venv/Scripts/python.exe
    env:
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
      AI_SCIENTIST_DIR: ${MY_REPOS}/Documents/github/AI-Scientist
      PATH: ${USER_HOME}/AppData/Local/Programs/MiKTeX/miktex/bin/x64;${PATH}
    timeout: 600
    workdir: ${MY_REPOS}/Documents/github/AI-Scientist
```

## Verification

```bash
# Import test
venv/Scripts/python -c "import sys; sys.path.insert(0,'.'); from ai_scientist.llm import create_client, _is_openrouter_model; assert _is_openrouter_model('google/gemma-4-31b-it:free'); assert not _is_openrouter_model('gpt-4o'); print('OK')"

# GPU check
venv/Scripts/python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0)}')"

# MCP server test
hermes mcp test ai-scientist

# MCP server list
hermes mcp list | grep ai-scientist
```

## GitHub

Our patched repo: https://github.com/pmb2/ai-scientist
Upstream: https://github.com/SakanaAI/AI-Scientist

The patched repo is a **clean fork** — only the patched files, no upstream history or large example datasets. To use it:
1. Clone the upstream (full templates + data)
2. Copy the 4 patched files from this repo over the upstream
3. Create a venv and install deps
