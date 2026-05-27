from __future__ import annotations

"""
audit_v250_final_prelive_checkpoint.py

PokerVision Solver V2.5.0 — final pre-live checkpoint audit.

Purpose:
- Summarize readiness for 10–15 minute preflop live dry-run.
- Confirm real-click is still blocked.
- Confirm current state is NOT approved for real-click live mode.
"""

from collections import Counter
from typing import Any, Dict

import config as c
from audit_v246_live_preflight_dryrun_command_contract import audit as audit_v246
from profile_v248_live_dryrun_command import build_profile as build_v248_profile


def _bool(name: str, default: bool = False) -> bool:
    return bool(getattr(c, name, default))


def audit() -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    warnings: list[str] = []

    v246 = audit_v246()
    v248 = build_v248_profile()

    counters["v246_checked"] += 1
    counters["v248_profile_checked"] += 1

    if v246.get("ok") is True:
        counters["v246_ok"] += 1
    else:
        errors.append({"reason": "v246_live_preflight_contract_failed", "report": v246})

    if v248.get("ok") is True:
        counters["v248_profile_ok"] += 1
    else:
        errors.append({"reason": "v248_live_dryrun_profile_failed", "profile": v248})

    real_click_flags = {
        "V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK": _bool("V16_SOLVER_CANDIDATE_RUNTIME_ALLOW_REAL_CLICK"),
        "V11_REAL_MOUSE_CLICK_ENABLED": _bool("V11_REAL_MOUSE_CLICK_ENABLED"),
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": _bool("V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"),
        "V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK": _bool("V22_CONTROLLED_PREFLOP_REAL_CLICK_ALLOW_REAL_CLICK"),
    }

    enabled_real_click_flags = {k: v for k, v in real_click_flags.items() if v is True}
    if enabled_real_click_flags:
        errors.append({"reason": "real_click_flags_enabled_forbidden_before_live_click_stage", "flags": enabled_real_click_flags})
    else:
        counters["real_click_flags_all_disabled"] += 1

    if _bool("V11_CLICK_DRY_RUN") is True:
        counters["click_dry_run_true"] += 1
    else:
        errors.append({"reason": "V11_CLICK_DRY_RUN_must_be_true_for_prelive_checkpoint"})

    if _bool("V16_USE_SOLVER_CANDIDATE_AS_RUNTIME_SOURCE") is True:
        counters["solver_candidate_source_switch_enabled"] += 1
    else:
        warnings.append("Solver candidate source switch is not enabled in config; dry-run profile still documents the intended command path.")

    if _bool("V16_SOLVER_CANDIDATE_RUNTIME_DRY_RUN_ONLY") is True:
        counters["solver_candidate_dry_run_only_true"] += 1
    else:
        errors.append({"reason": "solver_candidate_runtime_dry_run_only_must_be_true"})

    readiness = {
        "ready_for_10_15_min_live_dryrun": True,
        "ready_for_real_click_live": False,
        "approved_scope": "preflop_only_dryrun_observation",
        "blocked_scope": "postflop_real_click_and_any_mouse_click",
        "required_operator_command": v248.get("operator_command_powershell"),
        "required_post_run_expectations": {
            "runtime_real_click_enabled_total": 0,
            "runtime_click_points_total": 0,
            "errors_total": 0,
            "postflop_runtime_clicks": 0,
        },
    }

    ok = (
        counters.get("v246_ok", 0) == 1
        and counters.get("v248_profile_ok", 0) == 1
        and counters.get("real_click_flags_all_disabled", 0) == 1
        and counters.get("click_dry_run_true", 0) == 1
        and counters.get("solver_candidate_dry_run_only_true", 0) == 1
        and not errors
    )

    return {
        "schema_version": "v250_final_prelive_checkpoint_audit_v1",
        "ok": ok,
        "readiness": readiness,
        "real_click_flags": real_click_flags,
        "counters": dict(counters),
        "warnings": warnings,
        "errors": errors,
    }


def main() -> int:
    report = audit()

    print("V2.5.0 FINAL PRE-LIVE CHECKPOINT AUDIT")
    print("=" * 100)

    print()
    print("READINESS:")
    for key, value in report["readiness"].items():
        print(f"  {key}: {value}")

    print()
    print("REAL CLICK FLAGS:")
    for key, value in report["real_click_flags"].items():
        print(f"  {key}: {value}")

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    if report["warnings"]:
        print()
        print("WARNINGS:")
        for item in report["warnings"]:
            print(" ", item)

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.5.0 final pre-live checkpoint audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
