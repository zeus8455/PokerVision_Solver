from __future__ import annotations

"""
PokerVision V1.5 controlled live-click smoke runner.

This file never performs mouse clicks.
It only evaluates whether the current or simulated config is safe for the first
controlled real-click test.

Usage:
  python controlled_live_click_smoke_runner.py
  python controlled_live_click_smoke_runner.py --manual-controlled-snapshot

Exit codes:
  0 = ready
  2 = blocked/not ready
"""

import argparse
import json
import sys
from typing import Any, Dict, Iterable, List, Tuple

import config
from logic.real_click_readiness import validate_real_click_readiness


SCHEMA_VERSION = "controlled_live_click_smoke_runner_v1"
REQUIRED_TABLE_ID = "table_01"
REQUIRED_MAX_CLICKS_PER_RUN = 1
ALLOWED_ACTIONS = ["fold", "check", "call", "check_fold"]
ALLOWED_BUTTONS = ["FOLD", "Check", "Call", "Check/fold"]

CONFIG_KEYS = [
    "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE",
    "V09_REAL_CLICK_MASTER_ARMED",
    "V11_REAL_MOUSE_CLICK_ENABLED",
    "V11_CLICK_DRY_RUN",
    "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED",
    "V11_TRIGGER_UI_SERVICE_DRY_RUN",
    "V09_CLICK_EXECUTION_GUARD_ENABLED",
    "V09_REQUIRE_SLOT_BOUNDARY_GUARD",
    "V09_REQUIRE_NO_REPEAT_DECISION_GUARD",
    "V09_REQUIRE_BUTTON_AVAILABILITY_GUARD",
    "V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK",
    "V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED",
    "V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG",
    "V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY",
    "V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED",
    "V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED",
    "V10_REAL_CLICK_REQUIRE_MASTER_ARMED",
    "V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED",
    "V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED",
    "V14_CONTROLLED_REAL_CLICK_PRESET_AVAILABLE",
    "V14_CONTROLLED_REAL_CLICK_TEST_MODE",
    "V14_CONTROLLED_REAL_CLICK_TABLE_ID",
    "V14_CONTROLLED_REAL_CLICK_MAX_CLICKS_PER_RUN",
    "V14_CONTROLLED_REAL_CLICK_ACTION_BUTTON_ONLY",
    "V14_CONTROLLED_REAL_CLICK_SERVICE_BRANCH_DISABLED",
    "V14_CONTROLLED_REAL_CLICK_RAISE_BRANCH_ENABLED",
    "V14_CONTROLLED_REAL_CLICK_REQUIRE_SCOPE_AUDIT",
    "V14_CONTROLLED_REAL_CLICK_STARTUP_ABORT_ON_UNSAFE_PRESET",
    "V14_CONTROLLED_REAL_CLICK_ALLOWED_ACTIONS",
    "V14_CONTROLLED_REAL_CLICK_ALLOWED_BUTTONS",
]


def _json_safe(value: Any) -> Any:
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _result_to_dict(result: Any) -> Dict[str, Any]:
    return {
        "ok": bool(getattr(result, "ok", False)),
        "status": str(getattr(result, "status", "unknown")),
        "real_click_ready": bool(getattr(result, "real_click_ready", False)),
        "abort_startup": bool(getattr(result, "abort_startup", False)),
        "errors": list(getattr(result, "errors", []) or []),
        "warnings": list(getattr(result, "warnings", []) or []),
    }


def build_current_config_snapshot() -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {}
    for key in CONFIG_KEYS:
        if hasattr(config, key):
            snapshot[key] = _json_safe(getattr(config, key))
    return snapshot


def build_manual_controlled_snapshot(table_id: str = REQUIRED_TABLE_ID) -> Dict[str, Any]:
    """Build a review-only snapshot for the first intended controlled real-click test.

    This does not mutate config.py and does not click anything.
    """
    snapshot = build_current_config_snapshot()
    snapshot.update(
        {
            "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": False,
            "V09_REAL_CLICK_MASTER_ARMED": True,
            "V11_REAL_MOUSE_CLICK_ENABLED": True,
            "V11_CLICK_DRY_RUN": False,
            "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
            "V11_TRIGGER_UI_SERVICE_DRY_RUN": True,
            "V09_CLICK_EXECUTION_GUARD_ENABLED": True,
            "V09_REQUIRE_SLOT_BOUNDARY_GUARD": True,
            "V09_REQUIRE_NO_REPEAT_DECISION_GUARD": True,
            "V09_REQUIRE_BUTTON_AVAILABILITY_GUARD": True,
            "V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK": True,
            "V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED": True,
            "V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG": True,
            "V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY": True,
            "V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED": True,
            "V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED": True,
            "V10_REAL_CLICK_REQUIRE_MASTER_ARMED": True,
            "V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED": True,
            "V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED": True,
            "V14_CONTROLLED_REAL_CLICK_PRESET_AVAILABLE": True,
            "V14_CONTROLLED_REAL_CLICK_TEST_MODE": True,
            "V14_CONTROLLED_REAL_CLICK_TABLE_ID": table_id,
            "V14_CONTROLLED_REAL_CLICK_MAX_CLICKS_PER_RUN": REQUIRED_MAX_CLICKS_PER_RUN,
            "V14_CONTROLLED_REAL_CLICK_ACTION_BUTTON_ONLY": True,
            "V14_CONTROLLED_REAL_CLICK_SERVICE_BRANCH_DISABLED": True,
            "V14_CONTROLLED_REAL_CLICK_RAISE_BRANCH_ENABLED": False,
            "V14_CONTROLLED_REAL_CLICK_REQUIRE_SCOPE_AUDIT": True,
            "V14_CONTROLLED_REAL_CLICK_ALLOWED_ACTIONS": list(ALLOWED_ACTIONS),
            "V14_CONTROLLED_REAL_CLICK_ALLOWED_BUTTONS": list(ALLOWED_BUTTONS),
        }
    )
    return snapshot


def _expect_bool(snapshot: Dict[str, Any], key: str, expected: bool, errors: List[str]) -> None:
    if bool(snapshot.get(key)) is not expected:
        errors.append(f"{key}_must_be_{expected}")


def evaluate_controlled_live_click_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    readiness = _result_to_dict(validate_real_click_readiness(snapshot))
    scope_errors: List[str] = []

    _expect_bool(snapshot, "V14_CONTROLLED_REAL_CLICK_PRESET_AVAILABLE", True, scope_errors)
    _expect_bool(snapshot, "V14_CONTROLLED_REAL_CLICK_TEST_MODE", True, scope_errors)
    _expect_bool(snapshot, "V14_CONTROLLED_REAL_CLICK_ACTION_BUTTON_ONLY", True, scope_errors)
    _expect_bool(snapshot, "V14_CONTROLLED_REAL_CLICK_SERVICE_BRANCH_DISABLED", True, scope_errors)
    _expect_bool(snapshot, "V14_CONTROLLED_REAL_CLICK_RAISE_BRANCH_ENABLED", False, scope_errors)
    _expect_bool(snapshot, "V14_CONTROLLED_REAL_CLICK_REQUIRE_SCOPE_AUDIT", True, scope_errors)

    if str(snapshot.get("V14_CONTROLLED_REAL_CLICK_TABLE_ID")) != REQUIRED_TABLE_ID:
        scope_errors.append("controlled_table_must_be_table_01")

    try:
        max_clicks = int(snapshot.get("V14_CONTROLLED_REAL_CLICK_MAX_CLICKS_PER_RUN"))
    except Exception:
        max_clicks = -1
    if max_clicks != REQUIRED_MAX_CLICKS_PER_RUN:
        scope_errors.append("max_clicks_per_run_must_be_1")

    actions = list(snapshot.get("V14_CONTROLLED_REAL_CLICK_ALLOWED_ACTIONS") or [])
    buttons = list(snapshot.get("V14_CONTROLLED_REAL_CLICK_ALLOWED_BUTTONS") or [])
    if actions != ALLOWED_ACTIONS:
        scope_errors.append("allowed_actions_must_be_fold_check_call_check_fold")
    if buttons != ALLOWED_BUTTONS:
        scope_errors.append("allowed_buttons_must_be_fold_check_call_check_fold")

    _expect_bool(snapshot, "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE", False, scope_errors)
    _expect_bool(snapshot, "V09_REAL_CLICK_MASTER_ARMED", True, scope_errors)
    _expect_bool(snapshot, "V11_REAL_MOUSE_CLICK_ENABLED", True, scope_errors)
    _expect_bool(snapshot, "V11_CLICK_DRY_RUN", False, scope_errors)
    _expect_bool(snapshot, "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED", False, scope_errors)
    _expect_bool(snapshot, "V11_TRIGGER_UI_SERVICE_DRY_RUN", True, scope_errors)

    ready = bool(readiness["real_click_ready"] and not readiness["errors"] and not scope_errors)
    status = "CONTROLLED_REAL_CLICK_READY" if ready else "CONTROLLED_REAL_CLICK_BLOCKED"

    return {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "ready": ready,
        "readiness": readiness,
        "scope_errors": scope_errors,
        "table_id": snapshot.get("V14_CONTROLLED_REAL_CLICK_TABLE_ID"),
        "max_clicks_per_run": snapshot.get("V14_CONTROLLED_REAL_CLICK_MAX_CLICKS_PER_RUN"),
        "allowed_actions": actions,
        "allowed_buttons": buttons,
        "click_execution": "not_performed_by_smoke_runner",
    }


def print_smoke_report(report: Dict[str, Any]) -> None:
    print(f"CONTROLLED_REAL_CLICK_READY = {str(bool(report['ready'])).lower()}")
    print(f"CONTROLLED_REAL_CLICK_STATUS = {report['status']}")
    blockers = list(report.get("scope_errors") or []) + list(report.get("readiness", {}).get("errors") or [])
    if blockers:
        print("CONTROLLED_REAL_CLICK_BLOCKERS = " + ", ".join(blockers))
    else:
        print("CONTROLLED_REAL_CLICK_BLOCKERS = none")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="PokerVision V1.5 controlled live-click smoke runner.")
    parser.add_argument(
        "--manual-controlled-snapshot",
        action="store_true",
        help="Evaluate the intended first real-click config snapshot without mutating config.py.",
    )
    parser.add_argument(
        "--table-id",
        default=REQUIRED_TABLE_ID,
        help="Table id for the manual snapshot. First live-click stage requires table_01.",
    )
    args = parser.parse_args(argv)

    if args.manual_controlled_snapshot:
        snapshot = build_manual_controlled_snapshot(table_id=args.table_id)
    else:
        snapshot = build_current_config_snapshot()

    report = evaluate_controlled_live_click_snapshot(snapshot)
    print_smoke_report(report)
    return 0 if report["ready"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
