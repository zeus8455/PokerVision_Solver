#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PokerVision V1.7 controlled test-click result audit verifier.

Purpose:
  Validate outputs/controlled_test_click/controlled_test_click_result.json
  produced by controlled_test_click_runner.py.

This verifier DOES NOT click. It only reads JSON and validates that a previous
test click was executed under strict test-environment constraints.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


ALLOWED_ACTIONS = {"fold", "check", "call", "check_fold"}
ALLOWED_BUTTONS = {"FOLD", "Check", "Call", "Check/fold"}
DEFAULT_RESULT_PATH = Path("outputs") / "controlled_test_click" / "controlled_test_click_result.json"


def _load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("result_json_root_must_be_object")
    return data


def audit_controlled_test_click_result(data: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    if data.get("schema_version") != "controlled_test_click_runner_v1":
        errors.append("schema_version_must_be_controlled_test_click_runner_v1")

    if data.get("ready") is not True:
        errors.append("ready_must_be_true")

    if data.get("status") != "CONTROLLED_TEST_CLICK_READY":
        errors.append("status_must_be_CONTROLLED_TEST_CLICK_READY")

    if data.get("test_environment") is not True:
        errors.append("test_environment_must_be_true")

    if data.get("manual_controlled_snapshot") is not True:
        errors.append("manual_controlled_snapshot_must_be_true")

    if data.get("real_test_click_requested") is not True:
        errors.append("real_test_click_requested_must_be_true")

    if data.get("click_execution") != "clicked_in_test_environment":
        errors.append("click_execution_must_be_clicked_in_test_environment")

    if data.get("clicked") is not True:
        errors.append("clicked_must_be_true")

    blockers = data.get("blockers")
    if blockers not in ([], None):
        errors.append("blockers_must_be_empty")

    candidate = data.get("candidate")
    if not isinstance(candidate, dict):
        errors.append("candidate_must_be_object")
        candidate = {}

    if candidate.get("table_id") != "table_01":
        errors.append("candidate_table_id_must_be_table_01")

    action = candidate.get("action")
    if action not in ALLOWED_ACTIONS:
        errors.append("candidate_action_must_be_allowed_simple_action")

    button = candidate.get("button")
    if button not in ALLOWED_BUTTONS:
        errors.append("candidate_button_must_be_allowed_simple_button")

    if candidate.get("max_clicks_per_run") != 1:
        errors.append("candidate_max_clicks_per_run_must_be_1")

    x = candidate.get("x")
    y = candidate.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        errors.append("candidate_x_y_must_be_int")
    elif x < 0 or y < 0:
        errors.append("candidate_x_y_must_be_non_negative")

    click_result = data.get("click_result")
    if not isinstance(click_result, dict):
        errors.append("click_result_must_be_object")
        click_result = {}

    if click_result.get("clicked") is not True:
        errors.append("click_result_clicked_must_be_true")

    backend = click_result.get("backend")
    if backend not in {"pyautogui", "ctypes", "win32api"}:
        errors.append("click_result_backend_must_be_known_mouse_backend")

    rx = click_result.get("x")
    ry = click_result.get("y")
    if not isinstance(rx, int) or not isinstance(ry, int):
        errors.append("click_result_x_y_must_be_int")
    elif isinstance(x, int) and isinstance(y, int) and (rx != x or ry != y):
        errors.append("click_result_coordinates_must_match_candidate")

    if backend == "pyautogui":
        warnings.append("backend_pyautogui_confirmed")

    return {
        "schema_version": "controlled_test_click_result_audit_v1",
        "ok": not errors,
        "status": "CONTROLLED_TEST_CLICK_AUDIT_OK" if not errors else "CONTROLLED_TEST_CLICK_AUDIT_FAILED",
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "table_id": candidate.get("table_id"),
            "action": candidate.get("action"),
            "button": candidate.get("button"),
            "x": x,
            "y": y,
            "clicked": data.get("clicked"),
            "click_execution": data.get("click_execution"),
            "backend": click_result.get("backend"),
            "test_environment": data.get("test_environment"),
            "manual_controlled_snapshot": data.get("manual_controlled_snapshot"),
            "real_test_click_requested": data.get("real_test_click_requested"),
        },
    }


def run_audit(result_path: Path) -> Dict[str, Any]:
    data = _load_json(result_path)
    audit = audit_controlled_test_click_result(data)
    audit["result_path"] = str(result_path)
    return audit


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Audit V1.6 controlled test click result JSON.")
    parser.add_argument(
        "--result-json",
        default=str(DEFAULT_RESULT_PATH),
        help="Path to outputs/controlled_test_click/controlled_test_click_result.json",
    )
    parser.add_argument("--json", action="store_true", help="Print full audit JSON only.")
    args = parser.parse_args(argv)

    result_path = Path(args.result_json)

    try:
        audit = run_audit(result_path)
    except Exception as exc:
        audit = {
            "schema_version": "controlled_test_click_result_audit_v1",
            "ok": False,
            "status": "CONTROLLED_TEST_CLICK_AUDIT_FAILED",
            "errors": [f"audit_exception:{type(exc).__name__}:{exc}"],
            "warnings": [],
            "result_path": str(result_path),
        }

    if args.json:
        print(json.dumps(audit, ensure_ascii=False, indent=2))
    else:
        print(f"CONTROLLED_TEST_CLICK_AUDIT_OK = {str(audit.get('ok')).lower()}")
        print(f"CONTROLLED_TEST_CLICK_AUDIT_STATUS = {audit.get('status')}")
        errors = audit.get("errors") or []
        print("CONTROLLED_TEST_CLICK_AUDIT_ERRORS = " + ("none" if not errors else ",".join(errors)))
        print(json.dumps(audit, ensure_ascii=False, indent=2))

    return 0 if audit.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
