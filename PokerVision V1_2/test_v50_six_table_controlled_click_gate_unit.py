from __future__ import annotations

r"""
test_v50_six_table_controlled_click_gate_unit.py

PokerVision V5.0 — synthetic six-table controlled live-click gate tests.

Purpose:
- Exercise the controlled real-click gate without opening poker tables.
- Use fake mouse execution only.
- Verify table_01..table_06 can be selected as a controlled target via
  POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_ID.
- Verify wrong table, missing env confirmation, outside-slot button, raise/size
  actions, and one-click-per-process limit remain blocked.

Usage:
  cd "C:\PokerVision_Clear_Programing\PokerVision V1_2"
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe test_v50_six_table_controlled_click_gate_unit.py
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import runtime.action_click_stub as click_stub


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


_TABLE_BBOXES: Dict[str, _BBox] = {
    "table_01": _BBox(63, 93, 875, 681),
    "table_02": _BBox(875, 93, 1686, 681),
    "table_03": _BBox(1686, 93, 2498, 681),
    "table_04": _BBox(63, 681, 875, 1269),
    "table_05": _BBox(875, 681, 1686, 1269),
    "table_06": _BBox(1686, 681, 2498, 1269),
}


def _slot(table_id: str) -> _Slot:
    return _Slot(table_id=table_id, bbox=_TABLE_BBOXES[table_id])


def _solver(
    *,
    table_id: str,
    action: str = "fold",
    decision_id: Optional[str] = None,
    hand_id: str = "hand_v50",
    frame_name: str = "hand_v50_preflop",
) -> Dict[str, Any]:
    return {
        "decision_id": decision_id or f"decision_v50_{table_id}_{action}",
        "table_id": table_id,
        "hand_id": hand_id,
        "frame_name": frame_name,
        "action": action,
        "size_pct": None,
    }


def _buttons(class_name: str = "FOLD", *, local_bbox: Optional[List[int]] = None) -> Dict[str, Any]:
    return {
        "best_by_class": {
            class_name: {
                "bbox_xyxy": local_bbox or [300, 350, 380, 400],
                "confidence": 0.91,
            }
        }
    }


def _reset_runtime_state() -> None:
    click_stub._EXECUTED_DECISION_AT.clear()
    click_stub._CONTROLLED_LIVE_CLICK_EXECUTED_DECISION_IDS.clear()
    click_stub._CONTROLLED_LIVE_CLICK_EXECUTED_COUNT = 0
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR), None)
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR), None)


def _set_real_click_mode() -> None:
    click_stub.V11_CLICK_DRY_RUN = False
    click_stub.V11_REAL_MOUSE_CLICK_ENABLED = True
    click_stub.V11_CLICK_STUB_ENABLED = True
    click_stub.V11_CLICK_REQUIRE_ACTIVE = True
    click_stub.V11_CLICK_REQUIRE_BUTTON_DETECTION = True
    click_stub.V11_CLICK_SLOT_GUARD_ENABLED = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_GATE_ENABLED = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN = 1
    click_stub.V31_CONTROLLED_LIVE_CLICK_REQUIRE_ENV_CONFIRM = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_REQUIRE_ROI_GUARD_OK = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_REQUIRE_FULL_SCREEN_BLOCKED = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_REQUIRE_INSIDE_SLOT = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_RAISE_BRANCH_ENABLED = False


def _arm_env_for_table(table_id: str) -> None:
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR)] = table_id
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)


class _FakeMouse:
    def __init__(self) -> None:
        self.calls: List[List[Dict[str, Any]]] = []

    def __call__(self, click_points: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        points = list(click_points)
        self.calls.append(points)
        return {
            "click_count": len(points),
            "movements": [{"clicked": True, "fake": True}],
            "mouse_static": {"status": "fake"},
        }


def _run_with_fake_mouse(*, table_id: str, action: str = "fold", button: str = "FOLD", decision_id: Optional[str] = None) -> Dict[str, Any]:
    fake_mouse = _FakeMouse()
    original = click_stub.execute_click_points_human_like
    click_stub.execute_click_points_human_like = fake_mouse
    try:
        result = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id=table_id, action=action, decision_id=decision_id),
            action_button_result=_buttons(button),
            slot=_slot(table_id),
            active_confirmed=True,
        )
    finally:
        click_stub.execute_click_points_human_like = original
    result["_fake_mouse_calls_count"] = len(fake_mouse.calls)
    return result


def _assert_clicked_for_target(result: Dict[str, Any], table_id: str) -> None:
    assert result["status"] == "clicked", result
    gate = result["controlled_live_click_gate"]
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_PASSED", gate
    assert gate["scope_passed"] is True, gate
    assert gate["table_id"] == table_id, gate
    assert gate["configured_table_id"] == table_id, gate
    assert gate["table_id_env_value"] == table_id, gate
    assert result.get("controlled_live_click_success", {}).get("status") == "CONTROLLED_LIVE_CLICK_SUCCESS_RECORDED", result
    assert result["_fake_mouse_calls_count"] == 1, result


def test_all_six_tables_can_be_targeted_by_env_override_with_fake_mouse() -> None:
    for table_id in ("table_01", "table_02", "table_03", "table_04", "table_05", "table_06"):
        _reset_runtime_state()
        _set_real_click_mode()
        _arm_env_for_table(table_id)
        result = _run_with_fake_mouse(table_id=table_id, decision_id=f"decision_v50_{table_id}")
        _assert_clicked_for_target(result, table_id)


def test_wrong_table_is_blocked_when_env_targets_table03() -> None:
    _reset_runtime_state()
    _set_real_click_mode()
    _arm_env_for_table("table_03")

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_04", decision_id="decision_v50_wrong_table"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_04"),
        active_confirmed=True,
    )

    assert result["status"] == "blocked", result
    gate = result["controlled_live_click_gate"]
    assert gate["configured_table_id"] == "table_03", gate
    assert gate["table_id"] == "table_04", gate
    assert "controlled_live_click_wrong_table_id" in gate["blockers"], gate


def test_missing_env_confirmation_blocks_real_click() -> None:
    _reset_runtime_state()
    _set_real_click_mode()
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR)] = "table_03"

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v50_missing_confirm"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert result["status"] == "blocked", result
    assert "controlled_live_click_env_confirmation_missing" in result["controlled_live_click_gate"]["blockers"]


def test_click_point_outside_slot_or_roi_is_blocked() -> None:
    _reset_runtime_state()
    _set_real_click_mode()
    _arm_env_for_table("table_03")

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v50_outside_slot"),
        action_button_result=_buttons("FOLD", local_bbox=[5000, 5000, 5100, 5100]),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert result["status"] == "blocked", result
    gate = result["controlled_live_click_gate"]
    blockers = set(gate["blockers"])
    assert (
        "controlled_live_click_roi_guard_not_ok" in blockers
        or "controlled_live_click_point_outside_slot" in blockers
    ), gate


def test_raise_and_size_branch_is_blocked() -> None:
    _reset_runtime_state()
    _set_real_click_mode()
    _arm_env_for_table("table_03")

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", action="raise", decision_id="decision_v50_raise"),
        action_button_result=_buttons("Raise"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert result["status"] == "blocked", result
    gate = result["controlled_live_click_gate"]
    blockers = set(gate["blockers"])
    assert (
        "controlled_live_click_action_not_allowed" in blockers
        or "controlled_live_click_button_not_allowed" in blockers
        or "controlled_live_click_raise_or_size_blocked" in blockers
    ), gate


def test_allowed_simple_actions_click_with_expected_buttons() -> None:
    cases = [
        ("fold", "FOLD"),
        ("check", "Check"),
        ("call", "Call"),
        ("check_fold", "Check/fold"),
    ]

    for action, button in cases:
        _reset_runtime_state()
        _set_real_click_mode()
        _arm_env_for_table("table_03")
        result = _run_with_fake_mouse(
            table_id="table_03",
            action=action,
            button=button,
            decision_id=f"decision_v50_{action}",
        )
        _assert_clicked_for_target(result, "table_03")
        assert result["controlled_live_click_gate"]["target_button_class"] == button


def test_second_real_click_in_same_process_is_blocked_by_v50_limit() -> None:
    _reset_runtime_state()
    _set_real_click_mode()
    _arm_env_for_table("table_03")

    first = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v50_first")
    assert first["status"] == "clicked", first

    second = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v50_second"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert second["status"] == "blocked", second
    assert "controlled_live_click_max_clicks_reached" in second["controlled_live_click_gate"]["blockers"], second


def main() -> int:
    tests = [
        test_all_six_tables_can_be_targeted_by_env_override_with_fake_mouse,
        test_wrong_table_is_blocked_when_env_targets_table03,
        test_missing_env_confirmation_blocks_real_click,
        test_click_point_outside_slot_or_roi_is_blocked,
        test_raise_and_size_branch_is_blocked,
        test_allowed_simple_actions_click_with_expected_buttons,
        test_second_real_click_in_same_process_is_blocked_by_v50_limit,
    ]
    try:
        for test in tests:
            test()
            print(f"[OK] {test.__name__}")
    finally:
        _reset_runtime_state()

    print("[RESULT] OK: PokerVision V5.0 six-table controlled click gate synthetic tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


