r"""
test_action_button_roi_audit_exposure_unit.py

PokerVision V2.7 — verify Action_Button ROI guard is always exposed in runtime/Dark_JSON compact audit.

The bug fixed by V2.7:
- V2.6 built action_button_slot_roi_guard only after click_points existed.
- In live no-click / no-button-detected frames, Dark_JSON did not show the ROI guard.
- V2.7 must expose the ROI guard even when click is blocked/skipped before click_points.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class _BBox:
    x1: int = 100
    y1: int = 200
    x2: int = 500
    y2: int = 600


@dataclass(frozen=True)
class _Slot:
    table_id: str = "table_01"
    bbox: _BBox = field(default_factory=_BBox)


class _ActionButtonResult:
    status = "warning"
    detected_classes = []
    best_by_class: Dict[str, Dict[str, Any]] = {}
    raw_detection_count = 0
    processing_time_ms = 0
    warnings = ["synthetic no detections"]
    errors = []


def test_roi_guard_exposed_when_click_blocked_before_click_points() -> None:
    from runtime.action_click_stub import build_and_maybe_execute_click_plan

    report = build_and_maybe_execute_click_plan(
        solver_decision={
            "decision_id": "v27_roi_exposure_table_01_hand_01_fold",
            "table_id": "table_01",
            "hand_id": "hand_01",
            "frame_name": "hand_01_preflop",
            "action": "fold",
            "size_pct": None,
        },
        action_button_result=_ActionButtonResult(),
        slot=_Slot(),
        active_confirmed=True,
    )

    assert report["status"] in {"blocked", "dry_run", "skipped"}
    assert "action_button_slot_roi_guard" in report
    audit = report["action_button_slot_roi_guard"]
    assert isinstance(audit, dict)
    assert audit["schema_version"] == "action_button_slot_roi_runtime_audit_v2_6"
    assert audit.get("audit_exposure_version") == "v2_7_dark_json_exposure"
    assert audit["detector_input_scope"] == "table_roi"
    assert audit["full_screen_search_blocked"] is True
    assert audit["table_id"] == "table_01"
    assert audit["slot_bbox"] == {"x1": 100.0, "y1": 200.0, "x2": 500.0, "y2": 600.0}
    assert audit["click_points_count"] == 0


def test_dark_json_compact_action_runtime_preserves_roi_guard() -> None:
    from display_analysis_cycle import _compact_action_runtime_report

    audit = {
        "schema_version": "action_button_slot_roi_runtime_audit_v2_6",
        "audit_exposure_version": "v2_7_dark_json_exposure",
        "ok": True,
        "status": "ACTION_BUTTON_SLOT_ROI_RUNTIME_AUDIT_OK",
        "table_id": "table_01",
        "detector_input_scope": "table_roi",
        "full_screen_search_blocked": True,
        "click_points_count": 0,
    }

    compact = _compact_action_runtime_report(
        {
            "payload": {"status": "compile", "path": "solver_payload.json"},
            "solver": {"status": "stub", "decision_id": "d1", "action": "fold"},
            "action_buttons": {"status": "warning", "detected_classes": []},
            "click": {
                "status": "blocked",
                "decision_id": "d1",
                "action": "fold",
                "dry_run": True,
                "real_click_enabled": False,
                "target_sequence": [],
                "click_points": [],
                "action_button_slot_roi_guard": audit,
            },
        }
    )

    assert compact["action_button_slot_roi_guard"] == audit
    assert compact["real_click_enabled"] is False


def run_all() -> None:
    tests = [
        test_roi_guard_exposed_when_click_blocked_before_click_points,
        test_dark_json_compact_action_runtime_preserves_roi_guard,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V2.7 Action_Button ROI audit exposure tests passed.")


if __name__ == "__main__":
    run_all()
