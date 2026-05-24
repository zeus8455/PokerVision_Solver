"""
test_action_button_slot_roi_guard_unit.py

PokerVision V2.5 — Action_Button_Detector slot ROI guard/audit tests.
"""

from __future__ import annotations

from logic.action_button_slot_roi_guard import (
    ActionButtonSlotRoiGuardRequest,
    validate_action_button_slot_roi_guard,
)


def _assert_ok(report: dict) -> None:
    assert report["ok"] is True, report
    assert report["status"] == "ACTION_BUTTON_SLOT_ROI_GUARD_OK", report
    assert report["errors"] == [], report


def _assert_blocked(report: dict, reason: str) -> None:
    assert report["ok"] is False, report
    assert report["status"] == "ACTION_BUTTON_SLOT_ROI_GUARD_BLOCKED", report
    assert reason in report["errors"], report


def test_table_roi_scope_with_click_point_inside_slot_is_allowed() -> None:
    report = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_01",
            detector_input_scope="table_roi",
            slot_bbox=(100, 200, 900, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(50, 40, 170, 95),
            click_point_global=(210, 260),
        )
    )
    _assert_ok(report)
    assert report["guards"]["detector_input_scope_guard"] is True
    assert report["guards"]["click_point_inside_slot_guard"] is True
    assert report["mapped_global_bbox_xyxy"] == [150.0, 240.0, 270.0, 295.0]


def test_full_screen_action_button_search_is_forbidden() -> None:
    report = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_01",
            detector_input_scope="full_screen",
            slot_bbox=(100, 200, 900, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(50, 40, 170, 95),
            click_point_global=(210, 260),
        )
    )
    _assert_blocked(report, "full_screen_action_button_search_forbidden")
    assert report["guards"]["detector_input_scope_guard"] is False


def test_click_point_outside_slot_bbox_is_blocked() -> None:
    report = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_01",
            detector_input_scope="table_roi",
            slot_bbox=(100, 200, 900, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(50, 40, 170, 95),
            click_point_global=(950, 260),
        )
    )
    _assert_blocked(report, "click_point_outside_slot_bbox")
    assert report["guards"]["click_point_inside_slot_guard"] is False


def test_local_button_bbox_outside_table_roi_is_blocked() -> None:
    report = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_01",
            detector_input_scope="table_roi",
            slot_bbox=(100, 200, 900, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(50, 40, 850, 95),
            click_point_global=(210, 260),
        )
    )
    _assert_blocked(report, "local_button_bbox_outside_table_roi")
    assert report["guards"]["local_bbox_inside_roi_guard"] is False


def test_detector_roi_audit_can_run_without_click_point() -> None:
    report = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_02",
            detector_input_scope="table_roi",
            slot_bbox=(900, 200, 1700, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(10, 10, 120, 60),
            click_point_global=None,
        )
    )
    _assert_ok(report)
    assert "click_point_not_provided_detector_roi_audit_only" in report["warnings"]
    assert report["guards"]["click_point_inside_slot_guard"] is None


def test_table_01_click_candidate_cannot_land_in_table_02_slot() -> None:
    # table_01 slot ends at x=900; candidate x=950 belongs to the next slot area.
    report = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_01",
            detector_input_scope="table_roi",
            slot_bbox=(100, 200, 900, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(40, 40, 160, 90),
            click_point_global=(950, 260),
        )
    )
    _assert_blocked(report, "click_point_outside_slot_bbox")


def test_each_table_slot_is_independent() -> None:
    table_01 = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_01",
            detector_input_scope="table_roi",
            slot_bbox=(100, 200, 900, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(20, 20, 100, 70),
            click_point_global=(150, 250),
        )
    )
    table_02 = validate_action_button_slot_roi_guard(
        ActionButtonSlotRoiGuardRequest(
            table_id="table_02",
            detector_input_scope="table_roi",
            slot_bbox=(900, 200, 1700, 800),
            roi_size=(800, 600),
            local_bbox_xyxy=(20, 20, 100, 70),
            click_point_global=(950, 250),
        )
    )
    _assert_ok(table_01)
    _assert_ok(table_02)
    assert table_01["slot_bbox"]["x1"] != table_02["slot_bbox"]["x1"]


def run_all() -> None:
    tests = [
        test_table_roi_scope_with_click_point_inside_slot_is_allowed,
        test_full_screen_action_button_search_is_forbidden,
        test_click_point_outside_slot_bbox_is_blocked,
        test_local_button_bbox_outside_table_roi_is_blocked,
        test_detector_roi_audit_can_run_without_click_point,
        test_table_01_click_candidate_cannot_land_in_table_02_slot,
        test_each_table_slot_is_independent,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V2.5 Action_Button_Detector slot ROI guard/audit tests passed.")


if __name__ == "__main__":
    run_all()
