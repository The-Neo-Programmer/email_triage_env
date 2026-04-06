"""
server/app.py
=============
FastAPI application entry point for the Email Triage OpenEnv environment.
Exposes the full OpenEnv REST API (reset, step, state, health) and serves
a custom premium HTML dashboard.
"""

import os
import sys
import logging

# Ensure the project root (/app) is in sys.path so all top-level modules
# are importable regardless of how uvicorn imports this file.
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for _path in [_ROOT, _HERE]:
    if _path not in sys.path:
        sys.path.insert(0, _path)

from openenv.core.env_server.http_server import create_fastapi_app
from fastapi.responses import HTMLResponse
from models import EmailTriageAction, EmailTriageObservation
from email_triage_environment import EmailTriageEnvironment

# Load Custom UI
custom_ui_path = os.path.join(_HERE, "custom_ui.html")
with open(custom_ui_path, "r", encoding="utf-8") as f:
    CUSTOM_UI_HTML = f.read()

# Keep custom UI ownership deterministic at "/" for Hugging Face Spaces.
# The OpenEnv web interface can conflict with custom root routes across versions.
os.environ.setdefault("ENABLE_WEB_INTERFACE", "false")

# Create OpenEnv API app
app = create_fastapi_app(
    EmailTriageEnvironment,
    EmailTriageAction,
    EmailTriageObservation,
    max_concurrent_envs=1,
)

logger = logging.getLogger("email_triage_env.app")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_custom_ui():
    return CUSTOM_UI_HTML

@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def serve_custom_ui_alias():
    return CUSTOM_UI_HTML

def main(host: str = "0.0.0.0", port: int = 7860):
    import uvicorn
    port = int(os.getenv("PORT", port))
    logger.info(
        "Starting Email Triage server (port=%s, ENABLE_WEB_INTERFACE=%s)",
        port,
        os.getenv("ENABLE_WEB_INTERFACE"),
    )
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()
