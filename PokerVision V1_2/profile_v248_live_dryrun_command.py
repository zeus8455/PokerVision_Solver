from __future__ import annotations

"""
profile_v248_live_dryrun_command.py

PokerVision Solver V2.4.8 — live dry-run command profile.

Purpose:
- Print a controlled live-preflight dry-run command profile.
- Keep real-click disabled.
- Keep scope preflop-only.
- Prepare operator checklist before real-click live stage.
"""


import json
from pathlib import Path


ROOT = Path(r"C:\PokerVision_Solver")
PROJECT_DIR = ROOT / "PokerVision V1_2"
PYTHON_EXE = Path(r"C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe")


def build_profile() -> dict:
    command = [
        str(PYTHON_EXE),
        str(PROJECT_DIR / "display_analysis_cycle.py"),
        "--live",
        "--duration-sec",
        "900",
        "--preflop-only",
        "--dry-run",
        "--no-real-click",
        "--solver-candidate-runtime-source",
        "--controlled-arming-diagnostics",
    ]

    return {
        "schema_version": "v248_live_dryrun_command_profile_v1",
        "ok": True,
        "mode": "preflop_live_dryrun",
        "duration_seconds": 900,
        "duration_minutes": 15,
        "preflop_only": True,
        "postflop_blocked": True,
        "dry_run": True,
        "real_click_enabled": False,
        "mouse_click_allowed": False,
        "solver_candidate_runtime_source": True,
        "controlled_arming_diagnostics": True,
        "operator_command": command,
        "operator_command_powershell": " ".join(f'"{x}"' if " " in x else x for x in command),
        "required_safety_expectations": {
            "runtime_real_click_enabled_total": 0,
            "runtime_click_points_total": 0,
            "errors_total": 0,
            "postflop_runtime_clicks": 0,
        },
        "notes": [
            "This profile is for live observation/dry-run only.",
            "It must not perform mouse clicks.",
            "It must not enable postflop real-click handling.",
            "Use this before any real-click live test.",
        ],
    }


def main() -> int:
    profile = build_profile()

    print("V2.4.8 LIVE DRY-RUN COMMAND PROFILE")
    print("=" * 100)
    print(json.dumps(profile, indent=2, ensure_ascii=False))

    print()
    print("POWERSHELL COMMAND:")
    print(profile["operator_command_powershell"])

    print()
    print("[RESULT] OK V2.4.8 live dry-run command profile")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
