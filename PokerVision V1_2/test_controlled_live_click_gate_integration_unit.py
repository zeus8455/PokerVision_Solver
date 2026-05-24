from __future__ import annotations

import os
from dataclasses import dataclass

import runtime.action_click_stub as click_stub


@dataclass(frozen=True)
class _BBox:
    x1: int = 100
    y1: int = 200
    x2: int = 500
    y2: int = 600


@dataclass(frozen=True)
class _Slot:
    table_id: str = "table_01"
    bbox: _BBox = _BBox()


def _solver(action: str = "fold", table_id: str = "table_01", decision_id: str = "decision_v31_1"):
    return {
        "decision_id": decision_id,
        "table_id": table_id,
        "hand_id": "hand_01",
        "frame_name": "hand_01_preflop",
        "action": action,
        "size_pct": None,
    }


def _buttons(class_name: str = "FOLD"):
    return {
        "best_by_class": {
            class_name: {
                "bbox_xyxy": [300, 350, 380, 400],
                "confidence": 0.91,
            }
        }
    }


def _reset_runtime_state():
    click_stub._EXECUTED_DECISION_AT.clear()
    click_stub._CONTROLLED_LIVE_CLICK_EXECUTED_DECISION_IDS.clear()
    click_stub._CONTROLLED_LIVE_CLICK_EXECUTED_COUNT = 0
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR), None)
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR), None)


def _set_click_mode(*, real: bool, table_id: str = "table_01"):
    click_stub.V11_CLICK_DRY_RUN = not real
    click_stub.V11_REAL_MOUSE_CLICK_ENABLED = real
    click_stub.V11_CLICK_STUB_ENABLED = True
    click_stub.V11_CLICK_REQUIRE_ACTIVE = True
    click_stub.V11_CLICK_REQUIRE_BUTTON_DETECTION = True
    click_stub.V11_CLICK_SLOT_GUARD_ENABLED = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_GATE_ENABLED = True
    click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID = table_id
    click_stub.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN = 1
    click_stub.V31_CONTROLLED_LIVE_CLICK_REQUIRE_ENV_CONFIRM = True


def test_dry_run_path_exposes_v31_gate_without_clicking():
    _reset_runtime_state()
    _set_click_mode(real=False)
    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(),
        action_button_result=_buttons("FOLD"),
        slot=_Slot(),
        active_confirmed=True,
    )
    assert result["status"] == "dry_run"
    assert result["real_click_enabled"] is False
    gate = result["controlled_live_click_gate"]
    assert gate["schema_version"] == "controlled_live_click_gate_v3_1"
    assert gate["scope_passed"] is True
    assert gate["status"] == "CONTROLLED_LIVE_CLICK_GATE_DRY_RUN_ALLOWED"
    assert gate["wants_real_click"] is False


def test_real_click_is_blocked_without_v31_environment_confirmation():
    _reset_runtime_state()
    _set_click_mode(real=True)
    result = click_stub.build_and_maybe_execute_click_plan(
        solver_decision=_solver(),
        action_button_result=_buttons("FOLD"),
        slot=_Slot(),
        active_confirmed=True,
    )
    assert result["status"] == "blocked"
    gate = result["controlled_live_click_gate"]
    assert gate["scope_passed"] is False
    assert "controlled_live_click_env_confirmation_missing" in gate["blockers"]


def test_real_click_passes_once_with_v31_environment_confirmation_and_fake_mouse():
    _reset_runtime_state()
    _set_click_mode(real=True)
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)
    calls = []

    def fake_mouse(click_points):
        points = list(click_points)
        calls.append(points)
        return {"click_count": len(points), "movements": [{"clicked": True}], "mouse_static": {"status": "fake"}}

    original = click_stub.execute_click_points_human_like
    click_stub.execute_click_points_human_like = fake_mouse
    try:
        result = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(decision_id="decision_v31_once"),
            action_button_result=_buttons("FOLD"),
            slot=_Slot(),
            active_confirmed=True,
        )
    finally:
        click_stub.execute_click_points_human_like = original
        os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR), None)
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR), None)

    assert result["status"] == "clicked"
    assert len(calls) == 1
    assert result["controlled_live_click_gate"]["scope_passed"] is True
    assert result["controlled_live_click_success"]["executed_clicks_count"] == 1


def test_real_click_can_target_table02_with_v47_env_override_and_fake_mouse():
    _reset_runtime_state()
    _set_click_mode(real=True, table_id="table_01")
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR)] = "table_02"
    calls = []

    def fake_mouse(click_points):
        points = list(click_points)
        calls.append(points)
        return {"click_count": len(points), "movements": [{"clicked": True}], "mouse_static": {"status": "fake"}}

    original = click_stub.execute_click_points_human_like
    click_stub.execute_click_points_human_like = fake_mouse
    try:
        result = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_02", decision_id="decision_v47_table02"),
            action_button_result=_buttons("FOLD"),
            slot=_Slot(table_id="table_02", bbox=_BBox(600, 200, 1200, 700)),
            active_confirmed=True,
        )
    finally:
        click_stub.execute_click_points_human_like = original
        os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR), None)
        os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR), None)

    assert result["status"] == "clicked"
    assert len(calls) == 1
    gate = result["controlled_live_click_gate"]
    assert gate["scope_passed"] is True
    assert gate["configured_table_id"] == "table_02"
    assert gate["table_id_env_value"] == "table_02"


def test_second_real_click_in_same_process_is_blocked_by_v31_limit():
    _reset_runtime_state()
    _set_click_mode(real=True)
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)

    def fake_mouse(click_points):
        return {"click_count": len(list(click_points)), "movements": [{"clicked": True}], "mouse_static": {"status": "fake"}}

    original = click_stub.execute_click_points_human_like
    click_stub.execute_click_points_human_like = fake_mouse
    try:
        first = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(decision_id="decision_v31_first"),
            action_button_result=_buttons("FOLD"),
            slot=_Slot(),
            active_confirmed=True,
        )
        second = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(decision_id="decision_v31_second"),
            action_button_result=_buttons("FOLD"),
            slot=_Slot(),
            active_confirmed=True,
        )
    finally:
        click_stub.execute_click_points_human_like = original
        os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR), None)
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR), None)

    assert first["status"] == "clicked"
    assert second["status"] == "blocked"
    assert "controlled_live_click_max_clicks_reached" in second["controlled_live_click_gate"]["blockers"]


def test_wrong_table_is_blocked_for_real_click():
    _reset_runtime_state()
    _set_click_mode(real=True)
    os.environ[str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR)] = str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VALUE)
    try:
        result = click_stub.build_and_maybe_execute_click_plan(
            solver_decision=_solver(table_id="table_02"),
            action_button_result=_buttons("FOLD"),
            slot=_Slot(table_id="table_02", bbox=_BBox(600, 200, 1200, 700)),
            active_confirmed=True,
        )
    finally:
        os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_ENV_VAR), None)
    os.environ.pop(str(click_stub.V31_CONTROLLED_LIVE_CLICK_TABLE_ID_ENV_VAR), None)
    assert result["status"] == "blocked"
    assert "controlled_live_click_wrong_table_id" in result["controlled_live_click_gate"]["blockers"]


def main() -> int:
    tests = [
        test_dry_run_path_exposes_v31_gate_without_clicking,
        test_real_click_is_blocked_without_v31_environment_confirmation,
        test_real_click_passes_once_with_v31_environment_confirmation_and_fake_mouse,
        test_real_click_can_target_table02_with_v47_env_override_and_fake_mouse,
        test_second_real_click_in_same_process_is_blocked_by_v31_limit,
        test_wrong_table_is_blocked_for_real_click,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V4.7 configurable controlled live-click target tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
