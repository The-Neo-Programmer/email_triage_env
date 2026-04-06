"""
Lightweight runtime smoke checks for local/CI validation.

Validates:
- GET /health returns 200
- GET / returns HTML shell content
- POST /reset returns observation payload
- POST /step accepts canonical {"action": {"content": "..."}} shape
"""

from __future__ import annotations

import json
import sys
from typing import Any, Dict

import requests


def fail(message: str) -> None:
    print(f"[SMOKE][FAIL] {message}", flush=True)
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"[SMOKE][OK] {message}", flush=True)


def assert_has_keys(payload: Dict[str, Any], keys: list[str], label: str) -> None:
    missing = [k for k in keys if k not in payload]
    if missing:
        fail(f"{label} missing keys: {missing}")


def main() -> None:
    base_url = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:7860").rstrip("/")
    timeout = 20

    health = requests.get(f"{base_url}/health", timeout=timeout)
    if health.status_code != 200:
        fail(f"/health returned {health.status_code}")
    ok("/health is reachable")

    root = requests.get(f"{base_url}/", timeout=timeout)
    if root.status_code != 200:
        fail(f"/ returned {root.status_code}")
    content_type = root.headers.get("content-type", "")
    if "text/html" not in content_type:
        fail(f"/ content-type unexpected: {content_type}")
    if "Email Triage OpenEnv" not in root.text:
        fail("/ html shell marker not found")
    ok("/ renders UI shell")

    reset = requests.post(f"{base_url}/reset", json={}, timeout=timeout)
    if reset.status_code != 200:
        fail(f"/reset returned {reset.status_code}")
    reset_payload = reset.json()
    assert_has_keys(reset_payload, ["observation", "reward", "done"], "/reset")
    obs = reset_payload["observation"]
    if not isinstance(obs, dict):
        fail("/reset observation is not an object")
    assert_has_keys(obs, ["task", "instructions", "email_subject"], "/reset observation")
    ok("/reset returns observation payload")

    task_name = obs.get("task", "classify")
    if task_name == "extract":
        action_content = json.dumps({"action_items": ["Check and reply by EOD"]})
    elif task_name == "respond":
        action_content = "Hello Team, I will review this and share an update shortly. Regards, Agent."
    else:
        action_content = json.dumps({"urgency": "high", "category": "incident"})

    step = requests.post(
        f"{base_url}/step",
        json={"action": {"content": action_content}},
        timeout=timeout,
    )
    if step.status_code != 200:
        fail(f"/step returned {step.status_code}: {step.text[:240]}")
    step_payload = step.json()
    assert_has_keys(step_payload, ["observation", "reward", "done"], "/step")
    ok("/step accepts canonical payload")

    print("[SMOKE] all checks passed", flush=True)


if __name__ == "__main__":
    main()
