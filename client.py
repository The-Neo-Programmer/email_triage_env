from __future__ import annotations
from typing import Any, Dict

try:
    from openenv.core.env_client import EnvClient
    from openenv.core.client_types import StepResult
except ImportError:
    class EnvClient:
        def __class_getitem__(cls, _): return cls
    class StepResult:
        def __init__(self, observation, reward, done):
            self.observation = observation
            self.reward = reward
            self.done = done

from models import EmailTriageAction, EmailTriageObservation, EmailTriageState


class EmailTriageEnv(EnvClient[EmailTriageAction, EmailTriageObservation, EmailTriageState]):
    """
    Client for the Email Triage Environment.
    Wraps an HTTP/WebSocket connection to the remote environment.
    """

    def _step_payload(self, action: EmailTriageAction) -> dict:
        return {"content": action.content}

    def _parse_result(self, payload: dict) -> StepResult[EmailTriageObservation]:
        obs_payload = payload.get("observation", {})
        obs = EmailTriageObservation(**obs_payload)
        return StepResult(
            observation=obs,
            reward=payload.get("reward", 0.0),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: dict) -> EmailTriageState:
        return EmailTriageState(**payload)
