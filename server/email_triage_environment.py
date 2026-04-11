"""
server/email_triage_environment.py
===================================
Core lifecycle engine for the Email Triage OpenEnv environment.
Inherits from openenv.core.env_server.Environment and implements
reset(), step(), and state() per the OpenEnv specification.
"""

import json
import os
import sys
import random
import uuid
from typing import Any, Optional

# Add both the server directory and the project root to sys.path so that
# imports work regardless of whether this file is run as __main__, imported
# as a subpackage (server.email_triage_environment), or loaded by uvicorn.
_HERE = os.path.dirname(os.path.abspath(__file__))   # .../server/
_ROOT = os.path.dirname(_HERE)                         # .../email_triage_env/
for _path in [_HERE, _ROOT]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

try:
    from openenv.core.env_server import Environment
except ImportError:
    # Minimal stub — used only during initial development before openenv-core install
    class Environment:
        """No-op base class stub."""
        def __init__(self):
            pass

from models import (
    EmailTriageAction,
    EmailTriageObservation,
    EmailTriageState,
    TASK_INSTRUCTIONS,
)
from graders import TriageGraders


class EmailTriageEnvironment(Environment):
    """
    Email Triage Environment.

    Simulates a professional email inbox where an AI agent must:
    1. Classify each email by urgency and category (Easy)
    2. Extract all concrete action items (Medium)
    3. Draft a professional email response (Hard)

    Reward is returned as a delta improvement over the episode best score,
    providing a dense signal across the full trajectory.
    """

    TASKS = ["classify", "extract", "respond"]
    _task_index: int = 0   # class-level cycler for sequential task coverage

    def __init__(self, data_path: str = None):
        super().__init__()
        if data_path is None:
            data_path = os.path.join(_ROOT, "data", "emails.json")

        with open(data_path, "r", encoding="utf-8") as f:
            self.emails = json.load(f)

        self._state: EmailTriageState = EmailTriageState()
        self._current_email: dict = None

    # ------------------------------------------------------------------
    # OpenEnv API
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> EmailTriageObservation:
        """
        Reset the environment to a fresh episode.

        Accepts an optional `task_name` kwarg to pin a specific task.
        Without it, tasks cycle sequentially: classify -> extract -> respond.
        """
        if seed is not None:
            random.seed(seed)

        # Resolve the task for this episode
        requested = kwargs.get("task_name", None)
        if requested in self.TASKS:
            task = requested
        else:
            # Cycle through tasks so consecutive resets cover all three
            task = self.TASKS[EmailTriageEnvironment._task_index % len(self.TASKS)]
            EmailTriageEnvironment._task_index += 1

        # Draw a random email from the synthetic dataset
        self._current_email = random.choice(self.emails)

        self._state = EmailTriageState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            email_id=self._current_email["id"],
            task=task,
            cumulative_reward=0.0,
            best_score=0.0,
            attempts=0,
            max_steps=5,
            is_done=False,
        )

        return self._make_observation("Environment reset. Ready for new task.")

    def step(
        self,
        action: EmailTriageAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> EmailTriageObservation:
        """
        Evaluate the agent's action and return an updated observation with reward.

        Reward is the marginal improvement in score over the episode best
        (delta reward), providing dense learning signal over the full episode.
        Score ranges in [0.0, 1.0] per task.
        """
        if self._state.is_done:
            return self._make_observation(
                "Episode is done. Please call reset() to start a new episode.",
                done=True,
                reward=0.0,
            )

        # Defensive: OpenEnv HTTP servers can be configured statelessly (new env instance
        # per request). If that happens, reconstruct episode context from action.metadata
        # so the web UI (and simple HTTP clients) still work without cookies/session IDs.
        if not self._current_email:
            meta = getattr(action, "metadata", None) or {}
            meta_email_id = meta.get("email_id")
            meta_task = meta.get("task")
            meta_episode_id = meta.get("episode_id")

            if meta_task in self.TASKS:
                self._state.task = meta_task

            if meta_episode_id and not getattr(self._state, "episode_id", None):
                self._state.episode_id = meta_episode_id

            if meta_email_id:
                found = next((e for e in self.emails if e.get("id") == meta_email_id), None)
                if found:
                    self._current_email = found
                    self._state.email_id = found.get("id", "")

        if not self._current_email:
            return self._make_observation(
                "No active email loaded for this session. Please call reset() and try again.",
                done=False,
                reward=0.0,
            )

        self._state.step_count += 1
        self._state.attempts += 1

        content = (action.content or "").strip()
        score = 0.0
        feedback = ""
        done = False
        error = None

        try:
            gt = self._current_email["ground_truth"]

            if self._state.task == "classify":
                parsed = json.loads(content)
                score = TriageGraders.grade_classify(parsed, gt)
                feedback = f"Classification score: {score:.2f}."

            elif self._state.task == "extract":
                parsed = json.loads(content)
                score = TriageGraders.grade_extract(parsed, gt)
                feedback = f"Extraction score: {score:.2f}."

            elif self._state.task == "respond":
                score = TriageGraders.grade_respond(content, gt)
                feedback = f"Response score: {score:.2f}."

        except json.JSONDecodeError as exc:
            feedback = f"Invalid JSON format — could not parse action: {exc}"
            score = 0.0
        except KeyError as exc:
            feedback = f"Missing required key in email data: {exc}"
            score = 0.0
        except Exception as exc:
            feedback = f"Unexpected error evaluating action: {exc}"
            score = 0.0
            error = str(exc)

        # Validator requirement: task scores must be strictly within (0, 1).
        # Clamp *all* paths (including error cases) into the open interval.
        score = min(max(float(score or 0.0), 0.0), 1.0)
        if score <= 0.0:
            score = 1e-6
        elif score >= 1.0:
            score = 1.0 - 1e-6

        # Delta reward: reward only improvements beyond the current episode best
        reward = 0.0
        if score > self._state.best_score:
            reward = score - self._state.best_score
            self._state.best_score = score
            self._state.cumulative_reward += reward

        # Episode termination conditions
        if score >= 0.8 or self._state.step_count >= self._state.max_steps:
            done = True
            self._state.is_done = True
            feedback += " | Task succeeded." if score >= 0.8 else " | Maximum steps reached."

        return self._make_observation(
            feedback=feedback,
            done=done,
            reward=reward,
            last_score=score,
            error=error,
        )

    @property
    def state(self) -> EmailTriageState:
        """Return the current episode state (OpenEnv server expects an attribute)."""
        return self._state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _make_observation(
        self,
        feedback: str,
        done: bool = False,
        reward: float = 0.0,
        last_score: float = 0.0,
        error: str = None,
    ) -> EmailTriageObservation:
        email = self._current_email or {}
        obs = EmailTriageObservation(
            email_id=email.get("id", ""),
            email_subject=email.get("subject", ""),
            email_body=email.get("body", ""),
            sender=email.get("sender", ""),
            timestamp=email.get("timestamp", ""),
            task=self._state.task,
            instructions=TASK_INSTRUCTIONS.get(self._state.task, ""),
            feedback=feedback,
            last_score=last_score,
            cumulative_reward=self._state.cumulative_reward,
            best_score=self._state.best_score,
            done=done,
            reward=reward,
        )
        return obs
