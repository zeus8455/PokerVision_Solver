r"""
test_action_button_runtime_roi_integration_unit.py

PokerVision V2.6 — runtime integration tests for Action_Button_Detector slot ROI audit.

These tests do not run YOLO and do not click. They validate that the runtime
click-report now carries action_button_slot_roi_guard audit and blocks plans
whose detector-local bbox leaves the current table_N ROI. V2.7 also requires the ROI audit to be present when button detections are missing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from runtime.action_click_stub import build_and_maybe_execute_click_plan


@dataclass(frozen=True)
class _BBox:
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass(frozen=True)
class _Slot:
    table_id: str
    bbox: _BBox


def _solver(decision_id: str = "decision_v26_001", action: str = "fold") -> Dict[str, Any]:
    return {
        "status": "ok",
        "decision_id": decision_id,
        "table_id": "table_01",
        "hand_id": "hand_01",
        "frame_name": "hand_01_preflop",
        "action": action,
        "size_pct": None,
    }


def _button_result(local_bbox):
    return {
        "status": "ok",
        "detected_classes": ["FOLD"],
        "best_by_class": {
            "FOLD": {
                "class_name": "FOLD",
                "confidence": 0.94,
                "bbox_xyxy": list(local_bbox),
            }
        },
    }


def test_runtime_click_report_contains_slot_roi_audit() -> None:
    slot = _Slot(table_id="table_01", bbox=_BBox(100, 200, 900, 700))
    report = build_and_maybe_execute_click_plan(
        solver_decision=_solver("decision_v26_runtime_ok"),
        action_button_result=_button_result([10, 20, 60, 70]),
        slot=slot,
        active_confirmed=True,
    )

    assert report["status"] in {"dry_run", "clicked"}
    audit = report.get("action_button_slot_roi_guard")
    assert isinstance(audit, dict)
    assert audit["schema_version"] == "action_button_slot_roi_runtime_audit_v2_6"
    assert audit["ok"] is True
    assert audit["detector_input_scope"] == "table_roi"
    assert audit["full_screen_search_blocked"] is True
    assert audit["table_id"] == "table_01"
    assert audit["click_points_count"] == 1
    assert audit["per_button"][0]["button_class"] == "FOLD"
    assert audit["per_button"][0]["guards"]["detector_input_scope_guard"] is True
    assert audit["per_button"][0]["guards"]["local_bbox_inside_roi_guard"] is True
    assert audit["per_button"][0]["guards"]["click_point_inside_slot_guard"] is True


def test_runtime_roi_audit_blocks_local_bbox_outside_slot_roi() -> None:
    slot = _Slot(table_id="table_01", bbox=_BBox(100, 200, 900, 700))
    report = build_and_maybe_execute_click_plan(
        solver_decision=_solver("decision_v26_runtime_blocked"),
        action_button_result=_button_result([790, 20, 840, 70]),
        slot=slot,
        active_confirmed=True,
    )

    assert report["status"] == "blocked"
    assert report["guard_passed"] is False
    assert "slot ROI guard blocked" in str(report["message"])

    audit = report.get("action_button_slot_roi_guard")
    assert isinstance(audit, dict)
    assert audit["ok"] is False
    assert "local_button_bbox_outside_table_roi" in audit["errors"]
    assert audit["per_button"][0]["guards"]["local_bbox_inside_roi_guard"] is False


def test_runtime_roi_audit_is_built_when_button_detection_missing() -> None:
    slot = _Slot(table_id="table_01", bbox=_BBox(100, 200, 900, 700))
    report = build_and_maybe_execute_click_plan(
        solver_decision=_solver("decision_v26_no_buttons"),
        action_button_result={"status": "warning", "detected_classes": [], "best_by_class": {}},
        slot=slot,
        active_confirmed=True,
    )

    assert report["status"] == "blocked"
    audit = report.get("action_button_slot_roi_guard")
    assert isinstance(audit, dict)
    assert audit["schema_version"] == "action_button_slot_roi_runtime_audit_v2_6"
    assert audit.get("audit_exposure_version") == "v2_7_dark_json_exposure"
    assert audit["ok"] is True
    assert audit["detector_input_scope"] == "table_roi"
    assert audit["full_screen_search_blocked"] is True
    assert audit["table_id"] == "table_01"
    assert audit["click_points_count"] == 0
    assert audit["per_button"][0]["guards"]["detector_input_scope_guard"] is True
    assert "click_point_not_provided_detector_roi_audit_only" in audit["warnings"]


def run_all() -> None:
    tests = [
        test_runtime_click_report_contains_slot_roi_audit,
        test_runtime_roi_audit_blocks_local_bbox_outside_slot_roi,
        test_runtime_roi_audit_is_built_when_button_detection_missing,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V2.6 runtime action-button slot ROI audit integration tests passed.")


if __name__ == "__main__":
    run_all()
