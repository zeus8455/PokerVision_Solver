from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, List

from controlled_test_click_runner import (
    CONFIRMATION_TOKEN,
    DETECTED_BUTTON_CONFIRMATION_TOKEN,
    build_arg_parser,
    execute_test_click_candidate,
)


def _args(argv: List[str]) -> argparse.Namespace:
    return build_arg_parser().parse_args(argv)


def _write_dark_json(payload: Dict[str, Any]) -> Path:
    tmp = tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".dark.json", delete=False)
    with tmp:
        json.dump(payload, tmp)
    return Path(tmp.name)


def _valid_dark_json(button: str = "FOLD", x: int = 333, y: int = 444) -> Dict[str, Any]:
    return {
        "table": {"table_id": "table_01"},
        "runtime_action": {
            "action_button": {
                "status": "dry_run",
                "solver_action": "fold",
                "decision_id": "decision_v29_detected_001",
                "click_points": [
                    {
                        "class_name": button,
                        "confidence": 0.91,
                        "global_click_point": {"x": x, "y": y},
                        "inside_slot_bbox": True,
                    }
                ],
                "action_button_slot_roi_guard": {
                    "schema_version": "action_button_slot_roi_runtime_audit_v2_6",
                    "audit_exposure_version": "v2_7_dark_json_exposure",
                    "ok": True,
                    "status": "ACTION_BUTTON_SLOT_ROI_RUNTIME_AUDIT_OK",
                    "table_id": "table_01",
                    "detector_input_scope": "table_roi",
                    "full_screen_search_blocked": True,
                    "click_points_count": 1,
                },
            }
        },
    }


def test_detected_button_candidate_dry_run_is_ready_without_clicking() -> None:
    path = _write_dark_json(_valid_dark_json())
    args = _args([
        "--from-dark-json", str(path),
        "--detected-button-candidate",
        "--confirm-detected-button", DETECTED_BUTTON_CONFIRMATION_TOKEN,
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
    ])

    result = execute_test_click_candidate(args, environ={})

    assert result["ready"] is True
    assert result["click_execution"] == "dry_run_candidate_recorded"
    assert result["clicked"] is False
    assert result["candidate"]["source"] == "detected_action_button_dark_json"
    assert result["candidate"]["button"] == "FOLD"
    assert result["candidate"]["x"] == 333
    assert result["candidate"]["y"] == 444
    assert result["candidate"]["roi_guard_ok"] is True
    assert result["controlled_detected_button_click_audit"]["schema_version"] == "controlled_detected_button_click_v2_9"


def test_detected_button_real_click_requires_environment_token() -> None:
    path = _write_dark_json(_valid_dark_json())
    args = _args([
        "--from-dark-json", str(path),
        "--detected-button-candidate",
        "--confirm-detected-button", DETECTED_BUTTON_CONFIRMATION_TOKEN,
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--real-test-click",
    ])

    result = execute_test_click_candidate(args, environ={})

    assert result["ready"] is False
    assert result["click_execution"] == "blocked"
    assert "env_POKERVISION_TEST_ENVIRONMENT_must_equal_1_for_real_test_click" in result["blockers"]


def test_detected_button_real_click_uses_injected_executor_once() -> None:
    path = _write_dark_json(_valid_dark_json("Call", 555, 666))
    calls: List[tuple[int, int]] = []

    def fake_executor(x: int, y: int) -> Dict[str, Any]:
        calls.append((x, y))
        return {"backend": "fake", "clicked": True, "x": x, "y": y}

    args = _args([
        "--from-dark-json", str(path),
        "--detected-button-candidate",
        "--confirm-detected-button", DETECTED_BUTTON_CONFIRMATION_TOKEN,
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--real-test-click",
    ])

    result = execute_test_click_candidate(args, click_executor=fake_executor, environ={"POKERVISION_TEST_ENVIRONMENT": "1"})

    assert result["ready"] is True
    assert result["click_execution"] == "clicked_in_test_environment"
    assert result["clicked"] is True
    assert calls == [(555, 666)]
    assert result["candidate"]["button"] == "Call"


def test_raise_or_size_button_is_blocked() -> None:
    path = _write_dark_json(_valid_dark_json("Raise", 100, 200))
    args = _args([
        "--from-dark-json", str(path),
        "--detected-button-candidate",
        "--confirm-detected-button", DETECTED_BUTTON_CONFIRMATION_TOKEN,
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
    ])

    result = execute_test_click_candidate(args, environ={})

    assert result["ready"] is False
    assert "no_allowed_simple_button_click_point_found" in result["blockers"]


def test_roi_guard_must_be_ok_and_full_screen_blocked() -> None:
    payload = _valid_dark_json()
    payload["runtime_action"]["action_button"]["action_button_slot_roi_guard"]["ok"] = False
    payload["runtime_action"]["action_button"]["action_button_slot_roi_guard"]["full_screen_search_blocked"] = False
    path = _write_dark_json(payload)

    args = _args([
        "--from-dark-json", str(path),
        "--detected-button-candidate",
        "--confirm-detected-button", DETECTED_BUTTON_CONFIRMATION_TOKEN,
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
    ])

    result = execute_test_click_candidate(args, environ={})

    assert result["ready"] is False
    assert "action_button_slot_roi_guard_not_ok" in result["blockers"]
    assert "full_screen_search_not_confirmed_blocked" in result["blockers"]


def run_all() -> None:
    tests = [
        test_detected_button_candidate_dry_run_is_ready_without_clicking,
        test_detected_button_real_click_requires_environment_token,
        test_detected_button_real_click_uses_injected_executor_once,
        test_raise_or_size_button_is_blocked,
        test_roi_guard_must_be_ok_and_full_screen_blocked,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V2.9 controlled detected-button test-click runner tests passed.")


if __name__ == "__main__":
    run_all()
