#!/usr/bin/env python3
"""
workflow_runner.py — Execute AI Developer Workflows (ADW) for Hermes Agent.

A workflow is a reusable, operator-curated agent loop:
    trigger → prompt template + examples → LLM execution → verification gate → artifact

Usage:
    python workflow_runner.py run <workflow-name> [--input key=value ...]
    python workflow_runner.py list
    python workflow_runner.py learn <task-name> [--from-pim-count 5]
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

# ── Centralized model config ──
sys.path.insert(0, str(Path(__file__).parent))
from hermes_model import get_config, get_api_key

_MODEL_CFG = get_config()
API_URL = _MODEL_CFG["base_url"] + "/chat/completions"
API_MODEL = _MODEL_CFG["model"]

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
WORKFLOWS_DIR = HERMES_HOME / "workflows"
WORKFLOWS_DIR.mkdir(parents=True, exist_ok=True)

PIM_DB = Path("${MY_REPOS}/Documents/github/git-mcp/services/personal-intelligence-mcp/pim.db")
ARTIFACTS_DIR = HERMES_HOME / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def load_workflow(name: str) -> dict:
    path = WORKFLOWS_DIR / f"{name}.yaml"
    if not path.exists():
        path = WORKFLOWS_DIR / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Workflow '{name}' not found in {WORKFLOWS_DIR}")
    if path.suffix == ".yaml":
        import yaml
        with open(path) as f:
            return yaml.safe_load(f)
    with open(path) as f:
        return json.load(f)


def llm_render(prompt: str) -> str:
    key = get_api_key()
    if not key:
        raise RuntimeError(f"No API key found for {_MODEL_CFG['api_key_env']}")
    body = json.dumps({
        "model": API_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 2048,
    }).encode()
    req = Request(
        API_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    resp = urlopen(req, timeout=120)
    result = json.loads(resp.read().decode())
    return result["choices"][0]["message"]["content"]


def verify_artifact(artifact_text: str, verification: dict) -> tuple[bool, str]:
    """Run verification gate. Returns (passed, detail)."""
    if not verification:
        return True, "no verification configured"

    method = verification.get("method", "regex")
    if method == "regex":
        pattern = verification.get("pattern", ".")
        passed = bool(re.search(pattern, artifact_text, re.DOTALL))
        return passed, f"regex check {'passed' if passed else 'failed'}: {pattern}"

    if method == "command":
        cmd = verification.get("command", "")
        # Write artifact to temp file if command expects a path
        if "{{artifact}}" in cmd:
            tmp = ARTIFACTS_DIR / f"verify_tmp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.txt"
            tmp.write_text(artifact_text, encoding="utf-8")
            cmd = cmd.replace("{{artifact}}", str(tmp))
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            passed = result.returncode == 0
            return passed, f"command {'passed' if passed else 'failed'}: {cmd}\n{result.stdout[:200]}\n{result.stderr[:200]}"
        except Exception as e:
            return False, f"command error: {e}"

    if method == "contains":
        required = verification.get("required", [])
        missing = [r for r in required if r not in artifact_text]
        passed = not missing
        return passed, f"contains check {'passed' if passed else 'failed'}, missing: {missing}"

    return True, f"unknown verification method: {method}"


def run_workflow(name: str, inputs: dict) -> dict:
    wf = load_workflow(name)
    prompt_template = wf["prompt_template"]
    examples = wf.get("examples", [])
    verification = wf.get("verification", {})
    output_path_template = wf.get("output_artifact", "")

    # Build prompt
    context = []
    if examples:
        context.append("Examples of good output:")
        for ex in examples:
            context.append(f"Input: {ex.get('input', '')}")
            context.append(f"Output: {ex.get('output', '')}")
            context.append("")

    prompt = prompt_template.replace("{{inputs}}", json.dumps(inputs, indent=2))
    prompt = prompt.replace("{{examples}}", "\n".join(context))

    print(f"[workflow] Running '{name}'...")
    artifact = llm_render(prompt)

    passed, detail = verify_artifact(artifact, verification)
    print(f"[workflow] Verification: {detail}")

    output_path = None
    if output_path_template:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = ARTIFACTS_DIR / output_path_template.replace("{{timestamp}}", ts).replace("{{name}}", name)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(artifact, encoding="utf-8")
        print(f"[workflow] Artifact written to {output_path}")

    return {
        "workflow": name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inputs": inputs,
        "artifact": artifact,
        "verification_passed": passed,
        "verification_detail": detail,
        "artifact_path": str(output_path) if output_path else None,
    }


def list_workflows():
    files = sorted(WORKFLOWS_DIR.glob("*.yaml")) + sorted(WORKFLOWS_DIR.glob("*.json"))
    for f in files:
        print(f.stem)


def learn_from_history(task_name: str, count: int = 5) -> dict:
    """Pull recent similar PIM items and generate a workflow draft."""
    if not PIM_DB.exists():
        raise FileNotFoundError(f"PIM DB not found: {PIM_DB}")

    conn = sqlite3.connect(str(PIM_DB))
    c = conn.cursor()
    c.execute(
        "SELECT source_type, title, full_text FROM saved_items ORDER BY created_at DESC LIMIT ?",
        (count,),
    )
    rows = c.fetchall()
    conn.close()

    examples = []
    for source, title, text in rows:
        examples.append({"input": f"[{source}] {title}", "output": (text or "")[:500]})

    wf = {
        "name": task_name,
        "trigger": f"operator requests {task_name}",
        "prompt_template": f"""You are executing the '{task_name}' workflow for Hermes Agent.

Inputs: {{{{inputs}}}}

{{{examples}}}

Produce the requested output following the style of the examples above.""",
        "examples": examples,
        "verification": {"method": "contains", "required": ["Hermes"]},
        "output_artifact": f"{task_name.replace(' ', '_')}_{{{{timestamp}}}}.md",
    }

    out_path = WORKFLOWS_DIR / f"{task_name.replace(' ', '_')}.yaml"
    import yaml
    with open(out_path, "w") as f:
        yaml.dump(wf, f, sort_keys=False)
    print(f"[workflow] Draft workflow saved to {out_path}")
    return wf


def main():
    parser = argparse.ArgumentParser(description="Hermes AI Developer Workflow runner")
    sub = parser.add_subparsers(dest="cmd")

    run_p = sub.add_parser("run", help="Run a workflow")
    run_p.add_argument("name")
    run_p.add_argument("--input", action="append", default=[], help="key=value")

    sub.add_parser("list", help="List workflows")

    learn_p = sub.add_parser("learn", help="Draft workflow from PIM history")
    learn_p.add_argument("task_name")
    learn_p.add_argument("--from-pim-count", type=int, default=5)

    args = parser.parse_args()

    if args.cmd == "list":
        list_workflows()
    elif args.cmd == "run":
        inputs = {}
        for kv in args.input:
            k, v = kv.split("=", 1)
            inputs[k] = v
        result = run_workflow(args.name, inputs)
        print(json.dumps(result, indent=2, default=str))
        sys.exit(0 if result["verification_passed"] else 1)
    elif args.cmd == "learn":
        learn_from_history(args.task_name, args.from_pim_count)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
