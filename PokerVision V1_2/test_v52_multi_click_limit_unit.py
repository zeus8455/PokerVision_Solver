from __future__ import annotations

r"""
test_v52_multi_click_limit_unit.py

PokerVision V5.2 — synthetic controlled real-click gate limit=2 tests.

Purpose:
- Exercise multi-click controlled gate logic without live poker tables.
- Use fake mouse execution only.
- Prove max_clicks_per_run=2 allows exactly two physical-click plans in one process.
- Prove the third click is blocked by controlled_live_click_max_clicks_reached.
- Keep service-click logic outside this test; this is Action_Button only.

Usage:
  cd "C:\PokerVision_Clear_Programing\PokerVision V1_2"
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe test_v52_multi_click_limit_unit.py
"""

from typing import Any, Dict

import runtime.action_click_stub as click_stub

from test_v50_six_table_controlled_click_gate_unit import (
    _arm_env_for_table,
    _assert_clicked_for_target,
    _buttons,
    _reset_runtime_state,
    _run_with_fake_mouse,
    _set_real_click_mode,
    _slot,
    _solver,
)


def _set_controlled_limit_two() -> None:
    _set_real_click_mode()
    click_stub.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN = 2


def _gate(result: Dict[str, Any]) -> Dict[str, Any]:
    gate = result.get("controlled_live_click_gate")
    assert isinstance(gate, dict), result
    return gate


def test_two_real_clicks_are_allowed_then_third_is_blocked_same_table() -> None:
    _reset_runtime_state()
    _set_controlled_limit_two()
    _arm_env_for_table("table_03")

    first = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v52_table03_first")
    _assert_clicked_for_target(first, "table_03")
    assert first["controlled_live_click_success"]["executed_clicks_count"] == 1, first

    second = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v52_table03_second")
    _assert_clicked_for_target(second, "table_03")
    assert second["controlled_live_click_success"]["executed_clicks_count"] == 2, second

    third = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v52_table03_third")

    assert third["status"] == "blocked", third
    gate = _gate(third)
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_BLOCKED", gate
    assert gate["configured_table_id"] == "table_03", gate
    assert gate["table_id"] == "table_03", gate
    assert gate["executed_clicks_count"] == 2, gate
    assert gate["max_clicks_per_run"] == 2, gate
    assert "controlled_live_click_max_clicks_reached" in gate["blockers"], gate
    assert third["_fake_mouse_calls_count"] == 0, third


def test_two_real_clicks_are_allowed_then_third_is_blocked_across_different_tables() -> None:
    _reset_runtime_state()
    _set_controlled_limit_two()

    # First click on table_03.
    _arm_env_for_table("table_03")
    first = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v52_cross_table03")
    _assert_clicked_for_target(first, "table_03")

    # Second click on table_04, same process/global controlled counter.
    _arm_env_for_table("table_04")
    second = _run_with_fake_mouse(table_id="table_04", decision_id="decision_v52_cross_table04")
    _assert_clicked_for_target(second, "table_04")
    assert second["controlled_live_click_success"]["executed_clicks_count"] == 2, second

    # Third click attempts table_05 and must be blocked by the global V5.2 limit.
    _arm_env_for_table("table_05")
    third = _run_with_fake_mouse(table_id="table_05", decision_id="decision_v52_cross_table05")

    assert third["status"] == "blocked", third
    gate = _gate(third)
    assert gate["configured_table_id"] == "table_05", gate
    assert gate["table_id"] == "table_05", gate
    assert gate["executed_clicks_count"] == 2, gate
    assert gate["max_clicks_per_run"] == 2, gate
    assert "controlled_live_click_max_clicks_reached" in gate["blockers"], gate
    assert third["_fake_mouse_calls_count"] == 0, third


def test_duplicate_decision_id_still_blocks_before_limit_is_reached() -> None:
    _reset_runtime_state()
    _set_controlled_limit_two()
    _arm_env_for_table("table_03")

    first = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v52_duplicate")
    _assert_clicked_for_target(first, "table_03")

    duplicate = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v52_duplicate")

    assert duplicate["status"] == "blocked", duplicate
    gate = _gate(duplicate)
    assert "controlled_live_click_decision_already_executed" in gate["blockers"], gate
    assert gate["executed_clicks_count"] == 1, gate
    assert gate["max_clicks_per_run"] == 2, gate
    assert duplicate["_fake_mouse_calls_count"] == 0, duplicate


def test_wrong_target_table_still_blocks_with_limit_two() -> None:
    _reset_runtime_state()
    _set_controlled_limit_two()
    _arm_env_for_table("table_03")

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_04", decision_id="decision_v52_wrong_table"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_04"),
        active_confirmed=True,
    )

    assert result["status"] == "blocked", result
    gate = _gate(result)
    assert gate["configured_table_id"] == "table_03", gate
    assert gate["table_id"] == "table_04", gate
    assert gate["max_clicks_per_run"] == 2, gate
    assert "controlled_live_click_wrong_table_id" in gate["blockers"], gate


def main() -> int:
    tests = [
        test_two_real_clicks_are_allowed_then_third_is_blocked_same_table,
        test_two_real_clicks_are_allowed_then_third_is_blocked_across_different_tables,
        test_duplicate_decision_id_still_blocks_before_limit_is_reached,
        test_wrong_target_table_still_blocks_with_limit_two,
    ]
    try:
        for test in tests:
            test()
            print(f"[OK] {test.__name__}")
    finally:
        _reset_runtime_state()

    print("[RESULT] OK: PokerVision V5.2 controlled multi-click limit=2 synthetic tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
