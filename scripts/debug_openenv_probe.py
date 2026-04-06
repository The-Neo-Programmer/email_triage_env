from __future__ import annotations

import importlib
import importlib.util
import json
import pkgutil
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

SESSION_ID = "2530f0"
RUN_ID = f"probe-{int(time.time())}"
LOG_PATH = Path(__file__).resolve().parents[2] / "debug-2530f0.log"


def _log(hypothesis_id: str, location: str, message: str, data: dict) -> None:
    payload = {
        "sessionId": SESSION_ID,
        "runId": RUN_ID,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=True) + "\n")


def _run_cmd(cmd: list[str]) -> tuple[int, str]:
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        merged = (out.stdout or "") + (out.stderr or "")
        return out.returncode, merged.strip()
    except Exception as exc:
        return 999, f"{type(exc).__name__}: {exc}"


def _safe_find_spec(name: str) -> bool:
    try:
        return bool(importlib.util.find_spec(name))
    except Exception:
        return False


def main() -> None:
    # region agent log
    _log(
        "H0",
        "scripts/debug_openenv_probe.py:main",
        "Probe started",
        {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "executable": sys.executable,
            "cwd": str(Path.cwd()),
        },
    )
    # endregion

    specs = {
        "openenv": _safe_find_spec("openenv"),
        "openenv.cli": _safe_find_spec("openenv.cli"),
        "openenv_core": _safe_find_spec("openenv_core"),
        "openenv_core.cli": _safe_find_spec("openenv_core.cli"),
        "openenv_core.core.cli": _safe_find_spec("openenv_core.core.cli"),
    }
    # region agent log
    _log(
        "H1",
        "scripts/debug_openenv_probe.py:main",
        "Module spec availability",
        specs,
    )
    # endregion

    submods: dict[str, list[str] | str] = {}
    for mod_name in ("openenv", "openenv_core"):
        try:
            mod = importlib.import_module(mod_name)
            if hasattr(mod, "__path__"):
                names = sorted(m.name for m in pkgutil.iter_modules(mod.__path__))[:40]
                submods[mod_name] = names
            else:
                submods[mod_name] = ["<no __path__>"]
        except Exception as exc:
            submods[mod_name] = f"{type(exc).__name__}: {exc}"

    # region agent log
    _log(
        "H2",
        "scripts/debug_openenv_probe.py:main",
        "Top-level submodules",
        submods,
    )
    # endregion

    cmd_results = {}
    command_matrix = {
        "python_m_openenv_cli": [sys.executable, "-m", "openenv.cli", "--help"],
        "python_m_openenv_core_cli": [sys.executable, "-m", "openenv_core.cli", "--help"],
        "python_m_openenv_core_core_cli": [sys.executable, "-m", "openenv_core.core.cli", "--help"],
    }
    for label, cmd in command_matrix.items():
        rc, output = _run_cmd(cmd)
        cmd_results[label] = {"rc": rc, "output_head": output[:500]}

    openenv_bin = shutil.which("openenv")
    if openenv_bin:
        rc, output = _run_cmd([openenv_bin, "--help"])
        cmd_results["openenv_binary_help"] = {"rc": rc, "bin": openenv_bin, "output_head": output[:500]}
    else:
        cmd_results["openenv_binary_help"] = {"rc": 127, "bin": None, "output_head": "openenv binary not found"}

    # region agent log
    _log(
        "H3",
        "scripts/debug_openenv_probe.py:main",
        "CLI command matrix results",
        cmd_results,
    )
    # endregion

    # region agent log
    _log(
        "H4",
        "scripts/debug_openenv_probe.py:main",
        "Probe finished",
        {"log_path": str(LOG_PATH)},
    )
    # endregion

    print(f"debug probe complete; logs written to: {LOG_PATH}")


if __name__ == "__main__":
    main()
