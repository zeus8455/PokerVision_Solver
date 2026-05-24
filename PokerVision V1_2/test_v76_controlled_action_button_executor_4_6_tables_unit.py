from __future__ import annotations

import os
from typing import Any, Dict, List

import runtime.action_click_stub as click_stub

from test_v50_six_table_controlled_click_gate_unit import (
    _buttons,
    _reset_runtime_state,
    _run_with_fake_mouse,
    _set_real_click_mode,
    _slot,
    _solver,
)


ALL_TABLES: List[str] = [
    "table_01",
    "table_02",
    "table_03",
    "table_04",
    "table_05",
    "table_06",
]


def _reset_v76_runtime_state() -> None:
    _reset_runtime_state()
    os.environ.pop(str(getattr(click_stub, "V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR", "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS")), None)


def _arm_tables(*, tables: List[str], max_clicks: int) -> None:
    _set_real_click_mode()
    click_stub.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN = int(max_clicks)

    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)
    table_ids_env_var = str(getattr(click_stub, "V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR", "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS"))
    os.environ[table_ids_env_var] = ",".join(tables)


def _assert_clicked(result: Dict[str, Any], table_id: str, expected_count: int) -> None:
    assert result["status"] == "clicked", result
    assert result.get("_fake_mouse_calls_count") == 1, result

    gate = result["controlled_live_click_gate"]
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_PASSED", gate
    assert gate["table_id"] == table_id, gate
    assert gate["scope_passed"] is True, gate
    assert gate["executed_clicks_count"] == expected_count - 1, gate

    success = result.get("controlled_live_click_success") or {}
    assert success.get("status") == "CONTROLLED_LIVE_CLICK_SUCCESS_RECORDED", result
    assert success.get("executed_clicks_count") == expected_count, result


def test_v76_four_table_fake_executor_clicks_are_allowed() -> None:
    _reset_v76_runtime_state()
    target_tables = ALL_TABLES[:4]
    _arm_tables(tables=target_tables, max_clicks=4)

    try:
        for idx, table_id in enumerate(target_tables, start=1):
            result = _run_with_fake_mouse(table_id=table_id, decision_id=f"decision_v76_{table_id}")
            _assert_clicked(result, table_id, idx)

        fifth = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_01", decision_id="decision_v76_fifth"),
            action_button_result=_buttons("FOLD"),
            slot=_slot("table_01"),
            active_confirmed=True,
        )

        assert fifth["status"] == "blocked", fifth
        assert "controlled_live_click_max_clicks_reached" in fifth["controlled_live_click_gate"]["blockers"], fifth
    finally:
        _reset_v76_runtime_state()


def test_v76_six_table_fake_executor_clicks_are_allowed() -> None:
    _reset_v76_runtime_state()
    _arm_tables(tables=ALL_TABLES, max_clicks=6)

    try:
        for idx, table_id in enumerate(ALL_TABLES, start=1):
            result = _run_with_fake_mouse(table_id=table_id, decision_id=f"decision_v76_six_{table_id}")
            _assert_clicked(result, table_id, idx)

        seventh = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_01", decision_id="decision_v76_seventh"),
            action_button_result=_buttons("FOLD"),
            slot=_slot("table_01"),
            active_confirmed=True,
        )

        assert seventh["status"] == "blocked", seventh
        assert "controlled_live_click_max_clicks_reached" in seventh["controlled_live_click_gate"]["blockers"], seventh
    finally:
        _reset_v76_runtime_state()


def test_v76_wrong_table_is_blocked() -> None:
    _reset_v76_runtime_state()
    _arm_tables(tables=["table_01", "table_02", "table_03", "table_04"], max_clicks=4)

    try:
        result = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_05", decision_id="decision_v76_wrong_table"),
            action_button_result=_buttons("FOLD"),
            slot=_slot("table_05"),
            active_confirmed=True,
        )

        assert result["status"] == "blocked", result
        assert "controlled_live_click_wrong_table_id" in result["controlled_live_click_gate"]["blockers"], result
    finally:
        _reset_v76_runtime_state()


def test_v76_duplicate_decision_id_is_blocked_before_limit() -> None:
    _reset_v76_runtime_state()
    _arm_tables(tables=ALL_TABLES, max_clicks=6)

    try:
        first = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v76_duplicate")
        _assert_clicked(first, "table_03", 1)

        duplicate = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_03", decision_id="decision_v76_duplicate"),
            action_button_result=_buttons("FOLD"),
            slot=_slot("table_03"),
            active_confirmed=True,
        )

        assert duplicate["status"] == "blocked", duplicate
        blockers = duplicate["controlled_live_click_gate"]["blockers"]
        assert "controlled_live_click_decision_already_executed" in blockers, duplicate
        assert "controlled_live_click_max_clicks_reached" not in blockers, duplicate
    finally:
        _reset_v76_runtime_state()


def test_v76_raise_and_size_branch_remain_blocked() -> None:
    _reset_v76_runtime_state()
    _arm_tables(tables=ALL_TABLES, max_clicks=6)

    try:
        result = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_01", decision_id="decision_v76_raise", action="raise"),
            action_button_result=_buttons("Raise"),
            slot=_slot("table_01"),
            active_confirmed=True,
        )

        assert result["status"] == "blocked", result
        assert result.get("_fake_mouse_calls_count", 0) == 0, result
    finally:
        _reset_v76_runtime_state()


def main() -> int:
    tests = [
        test_v76_four_table_fake_executor_clicks_are_allowed,
        test_v76_six_table_fake_executor_clicks_are_allowed,
        test_v76_wrong_table_is_blocked,
        test_v76_duplicate_decision_id_is_blocked_before_limit,
        test_v76_raise_and_size_branch_remain_blocked,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: PokerVision V7.6 controlled action-button executor 4-6 table tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
