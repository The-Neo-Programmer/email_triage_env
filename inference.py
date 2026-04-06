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
from typing import List, Optional

from openai import OpenAI

# ---------------------------------------------------------------------------
# Configuration — read from environment variables with sensible defaults
# ---------------------------------------------------------------------------

API_KEY: str = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "dummy-key")
API_BASE_URL: str = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME: str = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_BASE_URL: str = os.getenv("ENV_BASE_URL", "http://localhost:7860").rstrip("/")

BENCHMARK: str = "email_triage"
MAX_STEPS: int = 5
TEMPERATURE: float = 0.2
MAX_TOKENS: int = 400
SUCCESS_SCORE_THRESHOLD: float = 0.8

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
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Sanitise action string: remove newlines, truncate for readability
    safe_action = str(action).replace("\n", " ").replace("\r", "").strip()
    if len(safe_action) > 300:
        safe_action = safe_action[:297] + "..."
    print(
        f"[STEP] step={step} action={safe_action} "
        f"reward={reward:.2f} done={done_val} error={error_val}",
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
        print(f"[DEBUG] LLM request failed: {exc}", flush=True)
        return ""


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_task(task_name: str, client: OpenAI) -> None:
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
        print(
            f"[DEBUG] Cannot connect to environment server at {ENV_BASE_URL}. "
            "Ensure the server is running before executing inference.py.",
            flush=True,
        )
    except requests.exceptions.HTTPError as exc:
        print(f"[DEBUG] HTTP error communicating with environment: {exc}", flush=True)
    except Exception as exc:
        print(f"[DEBUG] Unexpected exception during task '{task_name}': {exc}", flush=True)
    finally:
        log_end(success=success, steps=steps_taken, score=cumulative_score, rewards=rewards)


# ---------------------------------------------------------------------------
# Entry point — runs all three tasks in order
# ---------------------------------------------------------------------------

def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"[DEBUG] Environment URL  : {ENV_BASE_URL}", flush=True)
    print(f"[DEBUG] LLM API endpoint : {API_BASE_URL}", flush=True)
    print(f"[DEBUG] Model            : {MODEL_NAME}", flush=True)

    # Pre-flight health check
    try:
        health_resp = requests.get(f"{ENV_BASE_URL}/health", timeout=10)
        health_resp.raise_for_status()
        print(f"[DEBUG] Server health    : {health_resp.json()}", flush=True)
    except Exception as exc:
        print(f"[DEBUG] Health check failed: {exc}. Continuing anyway.", flush=True)

    print("", flush=True)

    for task in ["classify", "extract", "respond"]:
        run_task(task, client)
        print("", flush=True)


if __name__ == "__main__":
    main()
