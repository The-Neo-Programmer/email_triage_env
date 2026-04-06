---
title: Email Triage Env
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
tags:
  - openenv
  - rl
  - email
  - nlp
  - real-world
  - agent-benchmark
pinned: false
license: mit
---

# Email Triage OpenEnv Environment

**Meta x PyTorch x HuggingFace x Scaler School of Technology Hackathon 2026 — Round 1 Submission**

Author: Anurag Mukherjee (The-Neo-Programmer)

---

## Overview

The Email Triage environment places an AI agent inside a simulated professional inbox. The agent must perform three progressively difficult real-world business tasks across a diverse set of synthetic enterprise emails — making it a genuine benchmark for evaluating LLM utility in everyday knowledge work.

This environment implements the full OpenEnv specification: typed Pydantic models, step/reset/state API endpoints, a dense reward function, and a containerised Hugging Face Space deployment.

---

## Environment Description

**Domain:** Professional enterprise email management.

**Why this domain:** Email triage is a genuine, high-value task that every professional performs. Training agents to classify, extract action items from, and respond to emails has direct commercial value — and evaluating whether an LLM can do this reliably is a meaningful benchmark. Unlike toy games, this environment measures a skill that matters.

**Dataset:** 10 diverse synthetic emails spanning critical incidents, vendor requests, collaboration proposals, compliance reminders, and spam.

---

## Action and Observation Spaces

### Action Space: EmailTriageAction

The agent sends a single action per step containing a text response.

| Field     | Type | Description                                              |
|-----------|------|----------------------------------------------------------|
| `content` | str  | The agent's response — JSON string or plain text depending on the active task |

### Observation Space: EmailTriageObservation

Returned after every `reset()` and `step()` call.

| Field            | Type  | Description                                      |
|------------------|-------|--------------------------------------------------|
| `email_id`       | str   | Unique identifier for the email                  |
| `email_subject`  | str   | Subject line of the email                        |
| `email_body`     | str   | Full body text of the email                      |
| `sender`         | str   | Sender email address                             |
| `timestamp`      | str   | ISO 8601 timestamp of the email                  |
| `task`           | str   | Active task: classify, extract, or respond       |
| `instructions`   | str   | Natural language instructions for the agent      |
| `feedback`       | str   | Evaluation feedback from the previous step       |
| `last_score`     | float | Absolute score for the last action (0.0 to 1.0)  |
| `done`           | bool  | Whether the episode has ended                    |
| `reward`         | float | Delta reward for this step (0.0 to 1.0)          |

---

## The Three Tasks

### Task 1: Classify (Easy)

The agent reads the email and outputs a JSON object with two fields.

**Expected action format:**
```json
{"urgency": "high", "category": "incident"}
```

**Valid urgency values:** low, medium, high, critical

**Valid category values:** incident, request, collaboration, info, spam

**Grading logic:**
- Exact urgency match: +0.5
- Adjacent-tier urgency (e.g., high vs critical): +0.25
- Exact category match: +0.5
- Maximum score: 1.0

---

### Task 2: Extract (Medium)

The agent reads the email and extracts all concrete action items the recipient must perform.

**Expected action format:**
```json
{"action_items": ["Complete compliance training by Friday", "Log in to HR portal"]}
```

**Grading logic:**
- Jaccard similarity computed between each predicted item and the closest ground-truth item
- Precision penalty applied for hallucinated excess items
- Score normalised to [0.0, 1.0]

---

### Task 3: Respond (Hard)

The agent drafts a professional email reply as a plain-text string.

**Expected action format:** Plain text email response (no JSON, no markdown).

**Grading logic:**
- Word count between 5 and 250 words: +0.2
- Presence of greeting in first 50 characters: +0.1
- Presence of sign-off in last 100 characters: +0.1
- Keyword coverage score (up to +0.6): fraction of required semantic keywords present

---

## Reward Function

The environment uses a **delta reward** design:

- Each step, the agent's raw score is computed deterministically (0.0 to 1.0).
- The reward emitted is the improvement over the episode's running best score: `reward = max(0, score - best_score)`.
- This provides a dense learning signal across the full trajectory and penalises stagnation — an agent that submits the same guess repeatedly earns zero reward on subsequent identical attempts.
- The episode ends when score >= 0.8 (success) or after 5 steps (max steps reached).

---

## Project Structure

```
email_triage_env/
├── Dockerfile                        Root Dockerfile for HF Spaces deployment
├── openenv.yaml                      OpenEnv spec metadata and task registry
├── pyproject.toml                    Package configuration
├── requirements.txt                  Root-level Python dependencies
├── inference.py                      Baseline inference script (mandatory)
├── models.py                         Typed Pydantic models (Action, Observation, State)
├── client.py                         HTTP environment client wrapper
├── data/
│   └── emails.json                   10 synthetic enterprise emails with ground truth
└── server/
    ├── __init__.py
    ├── app.py                        FastAPI application entry point with web UI
    ├── email_triage_environment.py   Core environment lifecycle logic
    ├── graders.py                    Deterministic evaluation logic for all 3 tasks
    ├── requirements.txt              Server-specific dependencies
    └── Dockerfile                    Server-only Dockerfile (for standalone builds)
```

---

## Setup and Local Testing

### Step 0: Install the Package

```powershell
cd "C:\Users\Anura\Python\Hackathons\MPO X SST Hackathon [25-03-26]\email_triage_env"
pip install -e .
```

### Step 1: Validate OpenEnv Spec Compliance

```powershell
python -m openenv.cli validate
```

Expected output: `[OK] email_triage: Ready for multi-mode deployment`

### Step 2: Start the Environment Server

Open a terminal and run:

```powershell
python -m server.app
```

The server starts on port 7860. Verify at `http://localhost:7860/health` (returns `{"status": "ok"}`).

### Step 3: Run Baseline Inference

Open a second terminal:

```powershell
$env:HF_TOKEN = "hf_YourTokenHere"
$env:ENV_BASE_URL = "http://localhost:7860"
python inference.py
```

**Expected output format:**

```
[START] task=classify env=email_triage model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"urgency": "high", "category": "incident"} reward=1.00 done=true error=null
[END] success=true steps=1 score=1.000 rewards=1.00

[START] task=extract env=email_triage model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"action_items": ["..."]} reward=0.80 done=true error=null
[END] success=true steps=1 score=0.800 rewards=0.80

[START] task=respond env=email_triage model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action=Dear Team, ... reward=0.40 done=false error=null
...
[END] success=false steps=5 score=0.450 rewards=0.40,0.05,...
```

---

## Deployment to Hugging Face Spaces

```powershell
cd "C:\Users\Anura\Python\Hackathons\MPO X SST Hackathon [25-03-26]\email_triage_env"

# Login to Hugging Face
hf auth login

# Push to Spaces
python -m openenv.cli push --repo-id The-Neo-Programmer/email-triage-env
```

After deployment, configure the following secrets in the Space settings:

| Secret Name   | Value                             |
|---------------|-----------------------------------|
| `HF_TOKEN`    | Your Hugging Face token           |
| `API_BASE_URL`| `https://router.huggingface.co/v1`|
| `MODEL_NAME`  | `Qwen/Qwen2.5-72B-Instruct`       |

---

## API Endpoints

| Method | Path     | Description                                           |
|--------|----------|-------------------------------------------------------|
| GET    | /        | Live status dashboard (web UI)                        |
| GET    | /health  | Liveness check — returns `{"status": "ok"}`           |
| POST   | /reset   | Start a new episode. Body: `{"task_name": "classify"}`|
| POST   | /step    | Submit an action. Body: `{"action": {"content": "..."}}` (canonical) |
| GET    | /state   | Current episode state                                 |
| GET    | /docs    | Interactive Swagger API documentation                 |

---

## Baseline Scores

| Task     | Difficulty | Expected Score | Notes                                              |
|----------|------------|----------------|----------------------------------------------------|
| classify | Easy       | 0.75 to 1.00   | Strong LLMs map urgency and category reliably       |
| extract  | Medium     | 0.50 to 0.85   | Jaccard scoring rewards partial overlap             |
| respond  | Hard       | 0.30 to 0.60   | Constrained by keyword coverage and length checks  |

---

## Pre-Submission Checklist

- [x] `pip install -e .` completes without errors
- [x] `python -m openenv.cli validate` returns OK
- [x] `python -m server.app` starts on port 7860 and `/health` returns 200
- [x] `python inference.py` completes with valid [START], [STEP], [END] logs
- [x] All 3 tasks produce a score in the 0.0 to 1.0 range
- [x] `Dockerfile` exists at project root and `docker build` succeeds
- [x] HF Space is publicly accessible and responds at `/health`
- [x] `openenv.yaml` is in the repository root with correct metadata
- [x] Public GitHub repository is ready for submission

---

## UI and Deployment Stability Notes

- The custom UI is served at both `/` and `/ui`.
- The deployment sets `ENABLE_WEB_INTERFACE=false` to prevent OpenEnv web route conflicts with the custom UI on Spaces.
- Frontend API calls use origin-based routing to avoid proxy/path rewriting issues on hosted domains.

---

## GitHub Auto-Deploy to Hugging Face Space

A CI workflow is provided at `.github/workflows/deploy-hf-space.yml`.

On every push to `main`/`master`, it will:

1. Install dependencies
2. Run `python -m openenv.cli validate`
3. Launch the server and run `python scripts/smoke_test.py`
4. Upload the repository to your Hugging Face Space

Set these GitHub repository secrets before enabling the workflow:

- `HF_USERNAME` -> your Hugging Face username (example: `The-Neo-Programmer`)
- `HF_SPACE_REPO` -> your Space repo name (example: `email-triage-env`)
- `HF_TOKEN` -> Hugging Face token with write permissions for Spaces
