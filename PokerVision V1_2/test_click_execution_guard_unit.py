r"""
test_click_execution_guard_unit.py

Unit tests for PokerVision V0.9 click execution guard.
"""

from __future__ import annotations

from logic.click_execution_guard import (
    ClickExecutionRequest,
    ClickGuardConfig,
    point_inside_bbox,
    validate_click_execution_request,
)


def _plan() -> dict:
    return {
        "schema_version": "action_runtime_plan_v1",
        "source": "Action_Runtime_Plan_JSON",
        "planned_action": "fold",
        "target_sequence": ["FOLD"],
        "target_sequences": [["FOLD"], ["Check/fold"]],
        "runtime_branch": "action_button",
        "dry_run": True,
        "real_click_enabled": False,
    }


def _request(**overrides) -> ClickExecutionRequest:
    data = dict(
        table_id="table_01",
        hand_id="hand_01",
        street="preflop",
        decision_id="decision_001",
        action="fold",
        target_button_class="FOLD",
        click_point=(100.0, 100.0),
        slot_bbox=(0.0, 0.0, 200.0, 200.0),
        action_runtime_plan=_plan(),
        already_executed_decision_ids=(),
        dry_run=True,
        real_click_enabled=False,
    )
    data.update(overrides)
    return ClickExecutionRequest(**data)


def test_point_inside_bbox_rules() -> None:
    assert point_inside_bbox((10, 10), (0, 0, 20, 20)) is True
    assert point_inside_bbox((0, 0), (0, 0, 20, 20)) is True
    assert point_inside_bbox((21, 10), (0, 0, 20, 20)) is False
    assert point_inside_bbox((10,), (0, 0, 20, 20)) is False
    assert point_inside_bbox((10, 10), (0, 0, 0, 20)) is False


def test_dry_run_allowed_when_all_guards_pass() -> None:
    result = validate_click_execution_request(_request())
    assert result["status"] == "dry_run"
    assert result["guard_passed"] is True
    assert result["guards"]["slot_boundary_guard"] is True
    assert result["guards"]["no_repeat_decision_guard"] is True
    assert result["guards"]["button_availability_guard"] is True


def test_slot_boundary_guard_blocks_outside_click() -> None:
    result = validate_click_execution_request(_request(click_point=(999, 999)))
    assert result["status"] == "blocked"
    assert result["reason"] == "click_point_outside_slot_bbox"
    assert result["guard_passed"] is False


def test_no_repeat_guard_blocks_reused_decision_id() -> None:
    result = validate_click_execution_request(
        _request(already_executed_decision_ids=("decision_001", "other"))
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "decision_id_already_executed"


def test_button_availability_guard_blocks_unplanned_button() -> None:
    result = validate_click_execution_request(_request(target_button_class="CALL"))
    assert result["status"] == "blocked"
    assert result["reason"] == "target_button_not_in_runtime_plan"


def test_real_click_blocked_when_master_not_armed() -> None:
    result = validate_click_execution_request(
        _request(dry_run=False, real_click_enabled=True),
        ClickGuardConfig(
            real_click_master_armed=False,
            live_data_capture_no_click_mode=False,
            action_real_click_enabled=True,
            action_dry_run=False,
        ),
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "real_click_master_not_armed"


def test_real_click_blocked_by_live_no_click_mode_even_if_master_armed() -> None:
    result = validate_click_execution_request(
        _request(dry_run=False, real_click_enabled=True),
        ClickGuardConfig(
            real_click_master_armed=True,
            live_data_capture_no_click_mode=True,
            action_real_click_enabled=True,
            action_dry_run=False,
        ),
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "live_data_capture_no_click_mode"


def test_real_click_readiness_when_all_real_click_guards_pass() -> None:
    result = validate_click_execution_request(
        _request(dry_run=False, real_click_enabled=True),
        ClickGuardConfig(
            real_click_master_armed=True,
            live_data_capture_no_click_mode=False,
            action_real_click_enabled=True,
            action_dry_run=False,
        ),
    )
    assert result["status"] == "ready_for_real_click"
    assert result["guard_passed"] is True


def main() -> int:
    tests = [
        test_point_inside_bbox_rules,
        test_dry_run_allowed_when_all_guards_pass,
        test_slot_boundary_guard_blocks_outside_click,
        test_no_repeat_guard_blocks_reused_decision_id,
        test_button_availability_guard_blocks_unplanned_button,
        test_real_click_blocked_when_master_not_armed,
        test_real_click_blocked_by_live_no_click_mode_even_if_master_armed,
        test_real_click_readiness_when_all_real_click_guards_pass,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Click execution guard unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
