"""
inference.py
============
Baseline inference script for the Email Triage OpenEnv environment.
Meta x PyTorch x HuggingFace x SST Hackathon 2026 — Round 1 Submission

MANDATORY CONFIGURATION:
    HF_TOKEN        Your Hugging Face token (used as API key for the HF Router)
    API_BASE_URL    LLM API endpoint (default: https://router.huggingface.co/v1)
    MODEL_NAME      Model identifier (default: Qwen/Qwen2.5-72B-Instruct)
    ENV_BASE_URL    Environment server base URL (default: http://localhost:7860)

STDOUT FORMAT (strictly enforced by hackathon evaluator):
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...>
"""

import os
import sys
import json
import textwrap
import requests
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration — read from environment variables with sensible defaults
# ---------------------------------------------------------------------------

HF_TOKEN: Optional[str] = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME: str = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_BASE_URL: str = os.getenv("ENV_BASE_URL", "http://localhost:7860").rstrip("/")
LOCAL_IMAGE_NAME: Optional[str] = os.getenv("LOCAL_IMAGE_NAME")

BENCHMARK: str = "email_triage"
MAX_STEPS: int = 5
TEMPERATURE: float = 0.2
MAX_TOKENS: int = 400
SUCCESS_SCORE_THRESHOLD: float = 0.8

# ---------------------------------------------------------------------------
# Stderr-only diagnostics (stdout is reserved for [START]/[STEP]/[END])
# ---------------------------------------------------------------------------

def _eprint(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _single_line(val: Any, max_len: Optional[int] = None) -> str:
    s = "null" if val is None else str(val)
    s = s.replace("\r", " ").replace("\n", " ").strip()
    s = " ".join(s.split())
    if max_len is not None and len(s) > max_len:
        s = s[: max_len - 3] + "..."
    return s


# ---------------------------------------------------------------------------
# Mandatory structured logging functions
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(
    step: int,
    action: str,
    reward: float,
    done: bool,
    error: Optional[str],
) -> None:
    done_val = str(done).lower()
    safe_action = _single_line(action, max_len=300)
    safe_error = _single_line(error)
    print(
        f"[STEP] step={step} action={safe_action} "
        f"reward={reward:.2f} done={done_val} error={safe_error}",
        flush=True,
    )


def log_end(
    success: bool,
    steps: int,
    score: float,
    rewards: List[float],
) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} "
        f"score={score:.3f} rewards={rewards_str}",
        flush=True,
    )

def _emit_failure_episode(task_name: str, reason: str) -> None:
    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    _eprint(f"[ERROR] task={task_name} {reason}")
    log_end(success=False, steps=0, score=0.0, rewards=[])


# ---------------------------------------------------------------------------
# Environment HTTP client helpers (synchronous, no async dependency)
# ---------------------------------------------------------------------------

def reset_env(task_name: str) -> dict:
    """
    Call POST /reset on the environment server.
    Returns the observation dict from the environment.
    """
    resp = requests.post(
        f"{ENV_BASE_URL}/reset",
        json={"task_name": task_name},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    # Handle both flat observation response and wrapped StepResult response
    return data.get("observation", data)


def step_env(content: str) -> dict:
    """
    Call POST /step on the environment server.
    Returns the updated observation dict (which includes done and reward fields).
    """
    resp = requests.post(
        f"{ENV_BASE_URL}/step",
        json={"action": {"content": content}},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("observation", data)

def _obs_to_dict(obs: Any) -> Dict[str, Any]:
    if obs is None:
        return {}
    if isinstance(obs, dict):
        return obs
    # Pydantic v2 / v1
    if hasattr(obs, "model_dump"):
        return obs.model_dump()
    if hasattr(obs, "dict"):
        return obs.dict()
    # Fallback to attribute introspection
    try:
        return dict(vars(obs))
    except Exception:
        return {"value": str(obs)}


# ---------------------------------------------------------------------------
# LLM prompt construction and action generation
# ---------------------------------------------------------------------------

def build_prompt(obs_data: dict) -> str:
    return textwrap.dedent(
        f"""
        You are a precise, professional email triage assistant.

        Email Subject : {obs_data.get('email_subject', 'N/A')}
        From          : {obs_data.get('sender', 'N/A')}
        Date          : {obs_data.get('timestamp', 'N/A')}

        Email Body:
        {obs_data.get('email_body', '')}

        Task Instructions:
        {obs_data.get('instructions', '')}

        Previous Feedback: {obs_data.get('feedback', 'None') or 'None'}
        """
    ).strip()


def _strip_markdown_blocks(text: str) -> str:
    """Remove markdown code fences that LLMs sometimes wrap JSON in."""
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    elif "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1].strip()
    return text.strip()


def get_model_action(client: OpenAI, obs_data: dict) -> str:
    """Query the LLM and return a cleaned action string."""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a precise and professional email triage assistant. "
                        "Follow task instructions exactly. For JSON tasks, output only "
                        "valid JSON with no extra text or markdown."
                    ),
                },
                {"role": "user", "content": build_prompt(obs_data)},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
        )
        raw = (completion.choices[0].message.content or "").strip()
        return _strip_markdown_blocks(raw)
    except Exception as exc:
        _eprint(f"[ERROR] LLM request failed: {_single_line(exc)}")
        return ""


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_task_http(task_name: str, client: OpenAI) -> None:
    """
    Run one complete episode for the given task.
    Emits mandatory [START], [STEP]*, [END] log lines to stdout.
    """
    rewards: List[float] = []
    steps_taken: int = 0
    cumulative_score: float = 0.0
    success: bool = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs_data = reset_env(task_name)

        for step in range(1, MAX_STEPS + 1):
            if obs_data.get("done", False):
                break

            action_content = get_model_action(client, obs_data)
            obs_data = step_env(action_content)

            reward = float(obs_data.get("reward", 0.0))
            done = bool(obs_data.get("done", False))

            # Extract error from metadata if present
            metadata = obs_data.get("metadata") or {}
            error = metadata.get("error") if isinstance(metadata, dict) else None

            rewards.append(reward)
            steps_taken = step
            cumulative_score += reward

            log_step(step=step, action=action_content, reward=reward, done=done, error=error)

            if done:
                break

        # Clamp cumulative score to [0.0, 1.0]
        cumulative_score = min(max(cumulative_score, 0.0), 1.0)
        success = cumulative_score >= SUCCESS_SCORE_THRESHOLD

    except requests.exceptions.ConnectionError:
        _eprint(
            f"[ERROR] Cannot connect to environment server at {ENV_BASE_URL}. "
            "Ensure the server is running before executing inference.py."
        )
    except requests.exceptions.HTTPError as exc:
        _eprint(f"[ERROR] HTTP error communicating with environment: {_single_line(exc)}")
    except Exception as exc:
        _eprint(f"[ERROR] Unexpected exception during task '{task_name}': {_single_line(exc)}")
    finally:
        log_end(success=success, steps=steps_taken, score=cumulative_score, rewards=rewards)

async def run_task_docker(task_name: str, client: OpenAI, env: Any) -> None:
    """
    Docker-image mode: interact with the environment via OpenEnv client methods.
    Emits mandatory [START], [STEP]*, [END] log lines to stdout.
    """
    from models import EmailTriageAction

    rewards: List[float] = []
    steps_taken: int = 0
    cumulative_score: float = 0.0
    success: bool = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        reset_result = env.reset({"task_name": task_name}) if callable(getattr(env, "reset", None)) else None
        if hasattr(reset_result, "__await__"):
            reset_result = await reset_result

        # Some clients return StepResult-like wrappers; accept dict or object.
        obs_data = _obs_to_dict(getattr(reset_result, "observation", reset_result))

        for step in range(1, MAX_STEPS + 1):
            if obs_data.get("done", False):
                break

            action_content = get_model_action(client, obs_data)
            step_result = env.step(EmailTriageAction(content=action_content))
            if hasattr(step_result, "__await__"):
                step_result = await step_result

            obs_obj = getattr(step_result, "observation", step_result)
            obs_data = _obs_to_dict(obs_obj)

            reward = float(getattr(step_result, "reward", obs_data.get("reward", 0.0)) or 0.0)
            done = bool(getattr(step_result, "done", obs_data.get("done", False)))

            metadata = obs_data.get("metadata") or {}
            error = metadata.get("error") if isinstance(metadata, dict) else None

            rewards.append(reward)
            steps_taken = step
            cumulative_score += reward

            log_step(step=step, action=action_content, reward=reward, done=done, error=error)

            if done:
                break

        cumulative_score = min(max(cumulative_score, 0.0), 1.0)
        success = cumulative_score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        _eprint(f"[ERROR] Docker-mode exception during task '{task_name}': {_single_line(exc)}")
    finally:
        log_end(success=success, steps=steps_taken, score=cumulative_score, rewards=rewards)


# ---------------------------------------------------------------------------
# Entry point — runs all three tasks in order
# ---------------------------------------------------------------------------

def main() -> None:
    if not HF_TOKEN:
        for task in ["classify", "extract", "respond"]:
            _emit_failure_episode(task, "Missing HF_TOKEN environment variable.")
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    # Mode selection:
    # - If LOCAL_IMAGE_NAME is set, run via docker image using OpenEnv client.
    # - Otherwise, run against an already-running server at ENV_BASE_URL.
    if LOCAL_IMAGE_NAME:
        import asyncio
        from client import EmailTriageEnv

        async def _run_all() -> None:
            env = await EmailTriageEnv.from_docker_image(LOCAL_IMAGE_NAME)
            try:
                for task in ["classify", "extract", "respond"]:
                    await run_task_docker(task, client, env)
            finally:
                try:
                    close_result = env.close()
                    if hasattr(close_result, "__await__"):
                        await close_result
                except Exception as exc:
                    _eprint(f"[ERROR] env.close() failed: {_single_line(exc)}")

        asyncio.run(_run_all())
        return

    # HTTP mode: optional health check (stderr only)
    try:
        health_resp = requests.get(f"{ENV_BASE_URL}/health", timeout=10)
        health_resp.raise_for_status()
    except Exception as exc:
        _eprint(f"[ERROR] Health check failed: {_single_line(exc)}. Continuing anyway.")

    for task in ["classify", "extract", "respond"]:
        run_task_http(task, client)


if __name__ == "__main__":
    main()
