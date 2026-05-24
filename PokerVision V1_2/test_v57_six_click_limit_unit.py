from __future__ import annotations

r"""
test_v57_six_click_limit_unit.py

PokerVision V5.7 — synthetic controlled real-click limit=6 tests.

Purpose:
- Exercise the six-table controlled live-click gate without live poker tables.
- Use fake mouse execution only.
- Verify table_01..table_06 can each receive one controlled Action_Button click
  in the same process when max_clicks_per_run=6.
- Verify the 7th click is blocked by controlled_live_click_max_clicks_reached.
- Verify duplicate decision_id still blocks even before the limit is reached.

Usage:
  cd "C:\PokerVision_Clear_Programing\PokerVision V1_2"
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe test_v57_six_click_limit_unit.py
"""

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

_ALL_TABLES: List[str] = [
    "table_01",
    "table_02",
    "table_03",
    "table_04",
    "table_05",
    "table_06",
]


def _reset_v57_runtime_state() -> None:
    _reset_runtime_state()
    os.environ.pop(str(getattr(click_stub, "V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR", "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS")), None)


def _set_real_click_mode_limit_six() -> None:
    _set_real_click_mode()
    click_stub.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN = 6


def _arm_all_six_tables() -> None:
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)
    table_ids_env_var = str(getattr(click_stub, "V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR", "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS"))
    os.environ[table_ids_env_var] = ",".join(_ALL_TABLES)


def _assert_clicked(result: Dict[str, Any], table_id: str, expected_count: int) -> None:
    assert result["status"] == "clicked", result
    gate = result["controlled_live_click_gate"]
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_PASSED", gate
    assert gate["scope_passed"] is True, gate
    assert gate["table_id"] == table_id, gate
    assert gate["configured_table_ids"] == _ALL_TABLES, gate
    assert table_id in gate["configured_table_ids"], gate
    assert gate["max_clicks_per_run"] == 6, gate
    assert result.get("controlled_live_click_success", {}).get("status") == "CONTROLLED_LIVE_CLICK_SUCCESS_RECORDED", result
    assert result["controlled_live_click_success"]["executed_clicks_count"] == expected_count, result
    assert result.get("_fake_mouse_calls_count") == 1, result


def test_all_six_tables_can_click_once_then_seventh_is_blocked() -> None:
    _reset_v57_runtime_state()
    _set_real_click_mode_limit_six()
    _arm_all_six_tables()

    for idx, table_id in enumerate(_ALL_TABLES, start=1):
        result = _run_with_fake_mouse(table_id=table_id, decision_id=f"decision_v57_{table_id}")
        _assert_clicked(result, table_id, idx)

    seventh = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_01", decision_id="decision_v57_seventh"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_01"),
        active_confirmed=True,
    )

    assert seventh["status"] == "blocked", seventh
    gate = seventh["controlled_live_click_gate"]
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_BLOCKED", gate
    assert "controlled_live_click_max_clicks_reached" in gate["blockers"], gate
    assert gate["executed_clicks_count"] == 6, gate
    assert gate["max_clicks_per_run"] == 6, gate
    assert gate["configured_table_ids"] == _ALL_TABLES, gate


def test_duplicate_decision_id_blocks_before_six_click_limit() -> None:
    _reset_v57_runtime_state()
    _set_real_click_mode_limit_six()
    _arm_all_six_tables()

    first = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v57_duplicate")
    _assert_clicked(first, "table_03", 1)

    duplicate = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v57_duplicate"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert duplicate["status"] == "blocked", duplicate
    gate = duplicate["controlled_live_click_gate"]
    assert "controlled_live_click_decision_already_executed" in gate["blockers"], gate
    assert "controlled_live_click_max_clicks_reached" not in gate["blockers"], gate
    assert gate["executed_clicks_count"] == 1, gate


def test_unlisted_table_still_blocks_with_limit_six() -> None:
    _reset_v57_runtime_state()
    _set_real_click_mode_limit_six()
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)
    os.environ[str(getattr(click_stub, "V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR", "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS"))] = "table_01,table_02"

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v57_wrong_table"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert result["status"] == "blocked", result
    gate = result["controlled_live_click_gate"]
    assert "controlled_live_click_wrong_table_id" in gate["blockers"], gate
    assert gate["configured_table_ids"] == ["table_01", "table_02"], gate


def main() -> int:
    tests = [
        test_all_six_tables_can_click_once_then_seventh_is_blocked,
        test_duplicate_decision_id_blocks_before_six_click_limit,
        test_unlisted_table_still_blocks_with_limit_six,
    ]
    try:
        for test in tests:
            test()
            print(f"[OK] {test.__name__}")
    finally:
        _reset_v57_runtime_state()

    print("[RESULT] OK: PokerVision V5.7 six-click controlled gate synthetic tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
