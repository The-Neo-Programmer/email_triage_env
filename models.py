from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from uuid import uuid4

try:
    from openenv.core.env_server.types import Action, Observation, State
except ImportError:
    try:
        from openenv.core.env_server import Action, Observation, State
    except ImportError:
        # Minimal stubs for standalone / pre-install development
        class Action(BaseModel):
            pass

        class Observation(BaseModel):
            done: bool = False
            reward: float = 0.0
            metadata: Dict = Field(default_factory=dict)

        class State(BaseModel):
            episode_id: str = Field(default_factory=lambda: str(uuid4()))
            step_count: int = 0


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class EmailTriageAction(Action):
    """
    Action sent by the agent to the Email Triage environment.
    """
    content: str = ""


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class EmailTriageObservation(Observation):
    """
    Observation returned by the environment after reset() or step().
    """
    # --- Email payload ---
    email_id: str = ""
    email_subject: str = ""
    email_body: str = ""
    sender: str = ""
    timestamp: str = ""

    # --- Task info ---
    task: str = "classify"
    instructions: str = ""

    # --- Step feedback (populated after step()) ---
    feedback: str = ""
    last_score: float = 0.0


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class EmailTriageState(State):
    """
    Full episode state for the Email Triage environment.
    """
    email_id: str = ""
    task: str = "classify"
    cumulative_reward: float = 0.0
    best_score: float = 0.0
    attempts: int = 0
    max_steps: int = 3
    is_done: bool = False


# ---------------------------------------------------------------------------
# Task instructions (shown to agent in every observation)
# ---------------------------------------------------------------------------

TASK_INSTRUCTIONS = {
    "classify": (
        "Classify this email. Reply with valid JSON:\n"
        '{"urgency": "<low|medium|high|critical>", "category": "<incident|request|collaboration|info|spam>"}\n'
        "No extra keys, no markdown."
    ),
    "extract": (
        "List every concrete action item the recipient must perform. Reply with valid JSON:\n"
        '{"action_items": ["item 1", "item 2", ...]}\n'
        "Include only specific tasks, not general observations."
    ),
    "respond": (
        "Draft a professional email response that:\n"
        "  1. Addresses ALL required action items\n"
        "  2. Uses an appropriate tone for the sender's role\n"
        "  3. Is 30–180 words\n"
        "  4. Starts with a greeting and ends with a sign-off\n"
        "Reply with the plain-text response only — no JSON, no metadata."
    ),
}
