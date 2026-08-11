"""
Multi-Model Sub-Agent Launcher
================================
Spawn parallel sub-agents with different OpenRouter models for
cost-efficient task distribution.

Usage:
    python multi_agent_launch.py --task "Research X" --model "qwen/qwen3-coder:free"
    python multi_agent_launch.py --parallel --tasks-file tasks.json

This implements Jack's Level 5 orchestration pattern:
- Cheap models (Qwen3 Coder free) for grunt work
- Strong models (Llama 3.3 70B free) for synthesis/critique
- All running in parallel, results merged
"""

import json
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

HERMES_HOME = Path.home() / "AppData/Local/hermes"
SCRIPTS_DIR = HERMES_HOME / "scripts"


def run_agent_task(goal: str, model: str, provider: str = "openrouter",
                   timeout: int = 300, agent_name: str = None) -> dict:
    """
    Run a single Hermes agent task with a specific model.
    
    This shells out to `hermes chat -q` with model override.
    Returns dict with {name, model, output, exit_code, duration_s}
    """
    name = agent_name or f"agent-{model.split('/')[-1].split(':')[0]}"
    start = time.time()
    
    cmd = [
        "hermes", "chat", "-q", goal,
        "--model", f"{provider}/{model}" if provider != "openrouter" else model,
        "-Q",  # quiet mode
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"HERMES_HOME": str(HERMES_HOME), **__import__('os').environ}
        )
        duration = time.time() - start
        return {
            "name": name,
            "model": model,
            "output": result.stdout.strip(),
            "exit_code": result.returncode,
            "duration_s": round(duration, 1),
            "success": result.returncode == 0
        }
    except subprocess.TimeoutExpired:
        return {
            "name": name,
            "model": model,
            "output": f"TIMEOUT after {timeout}s",
            "exit_code": -1,
            "duration_s": timeout,
            "success": False
        }
    except Exception as e:
        return {
            "name": name,
            "model": model,
            "output": f"ERROR: {e}",
            "exit_code": -1,
            "duration_s": round(time.time() - start, 1),
            "success": False
        }


def parallel_launch(tasks: list, max_workers: int = 3) -> list:
    """
    Launch multiple agent tasks in parallel with their specified models.
    
    Each task: {goal, model, provider, agent_name, timeout}
    """
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(run_agent_task, **task): task.get("agent_name", f"task-{i}")
            for i, task in enumerate(tasks)
        }
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "✓" if result["success"] else "✗"
            print(f"  [{status}] {result['name']} ({result['model']}) — "
                  f"{result['duration_s']}s")
    
    return sorted(results, key=lambda r: r.get("duration_s", 0))


def orchestrate_with_critique(research_goal: str, critique_goal: str = None):
    """
    Jack's Level 5 pattern:
    1. Researcher (cheap model) does deep research
    2. Critic (stronger model) reviews and critiques
    3. Synthesizer (another model) produces final output
    
    All steps run in parallel where possible, then chained.
    """
    print(f"\n{'='*60}")
    print(f"ORCHESTRATION: {research_goal[:60]}...")
    print(f"{'='*60}")
    
    # Step 1: Research with cheap model
    print(f"\n[Step 1] Researching with Qwen3 Coder...")
    researcher = run_agent_task(
        goal=research_goal,
        model="qwen/qwen3-coder:free",
        agent_name="researcher"
    )
    
    if not researcher["success"]:
        return researcher
    
    # Step 2: Critique with stronger model (parallel if multiple critiques)
    if critique_goal:
        print(f"\n[Step 2] Critiquing with Llama 3.3 70B...")
        critic_prompt = f"{critique_goal}\n\nResearch findings:\n{researcher['output'][:3000]}"
        critic = run_agent_task(
            goal=critic_prompt,
            model="meta-llama/llama-3.3-70b-instruct:free",
            agent_name="critic"
        )
        
        # Step 3: Synthesis with a third model
        print(f"\n[Step 3] Synthesizing with Qwen3...")
        synthesis_prompt = (
            f"Synthesize the following research and critique into a final report.\n\n"
            f"RESEARCH:\n{researcher['output'][:2000]}\n\n"
            f"CRITIQUE:\n{critic['output'][:2000]}\n\n"
            f"Produce a concise, actionable final report."
        )
        synthesizer = run_agent_task(
            goal=synthesis_prompt,
            model="qwen/qwen3-next-80b-a3b-instruct:free",
            agent_name="synthesizer"
        )
        
        return {
            "researcher": researcher,
            "critic": critic,
            "synthesizer": synthesizer,
            "final": synthesizer["output"]
        }
    
    return {"researcher": researcher, "final": researcher["output"]}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Multi-model agent launcher")
    parser.add_argument("--task", help="Single task goal")
    parser.add_argument("--model", default="qwen/qwen3-coder:free",
                       help="Model to use")
    parser.add_argument("--orchestrate", action="store_true",
                       help="Run orchestration pattern (research + critique + synthesize)")
    parser.add_argument("--critique-goal", help="Goal for critique phase")
    parser.add_argument("--tasks-file", help="JSON file with task array")
    parser.add_argument("--parallel", action="store_true",
                       help="Run tasks in parallel")
    
    args = parser.parse_args()
    
    if args.orchestrate:
        result = orchestrate_with_critique(args.task, args.critique_goal)
        print(f"\n{'='*60}")
        print("FINAL OUTPUT:")
        print(f"{'='*60}")
        print(result.get("final", json.dumps(result, indent=2)))
    
    elif args.tasks_file:
        with open(args.tasks_file) as f:
            tasks = json.load(f)
        if args.parallel:
            results = parallel_launch(tasks)
        else:
            results = [run_agent_task(**t) for t in tasks]
        print(json.dumps(results, indent=2))
    
    elif args.task:
        result = run_agent_task(args.task, args.model)
        print(result["output"])
    
    else:
        parser.print_help()
