from __future__ import annotations

r"""
test_v54_multi_target_table_set_unit.py

PokerVision V5.4 — synthetic controlled live-click multi-target table set tests.

Purpose:
- Exercise the new comma-separated controlled target table set without live poker tables.
- Use fake mouse execution only.
- Verify POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS=table_01,table_02 allows both tables
  in one process while still blocking unlisted tables.
- Keep backward compatibility with the old single-table env override:
  POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_ID=table_03.
"""

import os
from typing import Any, Dict

import runtime.action_click_stub as click_stub

from test_v50_six_table_controlled_click_gate_unit import (
    _arm_env_for_table,
    _assert_clicked_for_target,
    _buttons,
    _reset_runtime_state as _reset_v50_runtime_state,
    _run_with_fake_mouse,
    _set_real_click_mode,
    _slot,
    _solver,
)


def _reset_runtime_state() -> None:
    _reset_v50_runtime_state()
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR), None)


def _set_real_click_mode_limit_two() -> None:
    _set_real_click_mode()
    click_stub.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN = 2


def _arm_env_for_table_set(*table_ids: str) -> None:
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_IDS_ENV_VAR)] = ",".join(table_ids)
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)


def _assert_blocked_wrong_table(result: Dict[str, Any], *, blocked_table_id: str, configured_table_ids: list[str]) -> None:
    assert result["status"] == "blocked", result
    gate = result["controlled_live_click_gate"]
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_BLOCKED", gate
    assert gate["table_id"] == blocked_table_id, gate
    assert gate["configured_table_ids"] == configured_table_ids, gate
    assert "controlled_live_click_wrong_table_id" in gate["blockers"], gate


def _assert_clicked_for_multi_target(result: Dict[str, Any], table_id: str, configured_table_ids: list[str]) -> None:
    assert result["status"] == "clicked", result
    gate = result["controlled_live_click_gate"]
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_PASSED", gate
    assert gate["scope_passed"] is True, gate
    assert gate["table_id"] == table_id, gate
    assert gate["configured_table_ids"] == configured_table_ids, gate
    assert table_id in gate["configured_table_ids"], gate
    assert result.get("controlled_live_click_success", {}).get("status") == "CONTROLLED_LIVE_CLICK_SUCCESS_RECORDED", result
    assert result["_fake_mouse_calls_count"] == 1, result


def test_table_01_and_table_02_are_allowed_by_multi_target_env_set() -> None:
    _reset_runtime_state()
    _set_real_click_mode_limit_two()
    _arm_env_for_table_set("table_01", "table_02")

    first = _run_with_fake_mouse(table_id="table_01", decision_id="decision_v54_table01")
    _assert_clicked_for_multi_target(first, "table_01", ["table_01", "table_02"])
    assert first["controlled_live_click_gate"]["configured_table_ids"] == ["table_01", "table_02"], first

    second = _run_with_fake_mouse(table_id="table_02", decision_id="decision_v54_table02")
    _assert_clicked_for_multi_target(second, "table_02", ["table_01", "table_02"])
    assert second["controlled_live_click_gate"]["configured_table_ids"] == ["table_01", "table_02"], second
    assert second["controlled_live_click_success"]["executed_clicks_count"] == 2, second


def test_unlisted_table_is_blocked_by_multi_target_env_set() -> None:
    _reset_runtime_state()
    _set_real_click_mode_limit_two()
    _arm_env_for_table_set("table_01", "table_02")

    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v54_table03_blocked"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    _assert_blocked_wrong_table(result, blocked_table_id="table_03", configured_table_ids=["table_01", "table_02"])


def test_multi_target_env_ignores_invalid_values_without_broadening_scope() -> None:
    _reset_runtime_state()
    _set_real_click_mode_limit_two()
    _arm_env_for_table_set("bad", "table_02", "table_02", "table_04", "unknown")

    allowed = _run_with_fake_mouse(table_id="table_02", decision_id="decision_v54_table02_allowed")
    _assert_clicked_for_multi_target(allowed, "table_02", ["table_02", "table_04"])
    assert allowed["controlled_live_click_gate"]["configured_table_ids"] == ["table_02", "table_04"], allowed

    blocked = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v54_table03_still_blocked"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )
    _assert_blocked_wrong_table(blocked, blocked_table_id="table_03", configured_table_ids=["table_02", "table_04"])


def test_legacy_single_table_env_override_still_works() -> None:
    _reset_runtime_state()
    _set_real_click_mode_limit_two()
    _arm_env_for_table("table_03")

    allowed = _run_with_fake_mouse(table_id="table_03", decision_id="decision_v54_legacy_table03")
    _assert_clicked_for_multi_target(allowed, "table_03", ["table_03"])
    assert allowed["controlled_live_click_gate"]["configured_table_id"] == "table_03", allowed
    assert allowed["controlled_live_click_gate"]["configured_table_ids"] == ["table_03"], allowed

    blocked = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_04", decision_id="decision_v54_legacy_wrong_table"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_04"),
        active_confirmed=True,
    )
    _assert_blocked_wrong_table(blocked, blocked_table_id="table_04", configured_table_ids=["table_03"])


def test_multi_target_set_still_respects_max_click_limit_two() -> None:
    _reset_runtime_state()
    _set_real_click_mode_limit_two()
    _arm_env_for_table_set("table_01", "table_02", "table_03")

    first = _run_with_fake_mouse(table_id="table_01", decision_id="decision_v54_limit_first")
    assert first["status"] == "clicked", first

    second = _run_with_fake_mouse(table_id="table_02", decision_id="decision_v54_limit_second")
    assert second["status"] == "clicked", second

    third = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(table_id="table_03", decision_id="decision_v54_limit_third"),
        action_button_result=_buttons("FOLD"),
        slot=_slot("table_03"),
        active_confirmed=True,
    )

    assert third["status"] == "blocked", third
    gate = third["controlled_live_click_gate"]
    assert gate["configured_table_ids"] == ["table_01", "table_02", "table_03"], gate
    assert "controlled_live_click_max_clicks_reached" in gate["blockers"], gate


def main() -> int:
    tests = [
        test_table_01_and_table_02_are_allowed_by_multi_target_env_set,
        test_unlisted_table_is_blocked_by_multi_target_env_set,
        test_multi_target_env_ignores_invalid_values_without_broadening_scope,
        test_legacy_single_table_env_override_still_works,
        test_multi_target_set_still_respects_max_click_limit_two,
    ]
    try:
        for test in tests:
            test()
            print(f"[OK] {test.__name__}")
    finally:
        _reset_runtime_state()

    print("[RESULT] OK: PokerVision V5.4 multi-target controlled click gate synthetic tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
