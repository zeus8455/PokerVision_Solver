r"""
test_real_click_readiness_unit.py

Unit tests for V1.0 controlled real-click readiness validator.
"""

from __future__ import annotations

from types import SimpleNamespace

from logic.real_click_readiness import validate_real_click_readiness


def _base_config(**overrides):
    values = dict(
        V10_REAL_CLICK_READINESS_SCHEMA_VERSION="real_click_readiness_v1",
        V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED=True,
        V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG=True,
        V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY=True,
        V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED=True,
        V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED=True,
        V10_REAL_CLICK_REQUIRE_MASTER_ARMED=True,
        V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED=True,
        V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED=True,
        V09_CLICK_EXECUTION_GUARD_ENABLED=True,
        V09_REAL_CLICK_MASTER_ARMED=False,
        V09_REQUIRE_SLOT_BOUNDARY_GUARD=True,
        V09_REQUIRE_NO_REPEAT_DECISION_GUARD=True,
        V09_REQUIRE_BUTTON_AVAILABILITY_GUARD=True,
        V09_REQUIRE_ACTION_RUNTIME_PLAN_SOURCE="Action_Runtime_Plan_JSON",
        V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK=True,
        V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE=True,
        V11_REAL_MOUSE_CLICK_ENABLED=False,
        V11_CLICK_DRY_RUN=True,
        V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED=False,
        V11_TRIGGER_UI_SERVICE_DRY_RUN=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def _assert_ok(name, condition):
    if not condition:
        raise AssertionError(name)
    print(f"[OK] {name}")


def test_default_no_click_config_is_safe_but_not_real_ready():
    result = validate_real_click_readiness(_base_config())
    _assert_ok("default no-click config ok", result.ok is True)
    _assert_ok("default no-click status", result.status == "safe_no_click")
    _assert_ok("default no-click not real-ready", result.real_click_ready is False)
    _assert_ok("default no-click does not abort", result.abort_startup is False)


def test_controlled_real_click_ready_when_all_flags_are_aligned():
    result = validate_real_click_readiness(
        _base_config(
            V09_REAL_CLICK_MASTER_ARMED=True,
            V11_REAL_MOUSE_CLICK_ENABLED=True,
            V11_CLICK_DRY_RUN=False,
            V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE=False,
            V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED=False,
            V11_TRIGGER_UI_SERVICE_DRY_RUN=True,
        )
    )
    _assert_ok("controlled real-click config ok", result.ok is True)
    _assert_ok("controlled real-click ready", result.real_click_ready is True)
    _assert_ok("controlled real-click status", result.status == "ready_for_controlled_real_click")
    _assert_ok("controlled real-click no abort", result.abort_startup is False)


def test_master_armed_but_live_no_click_enabled_is_blocked():
    result = validate_real_click_readiness(
        _base_config(
            V09_REAL_CLICK_MASTER_ARMED=True,
            V11_REAL_MOUSE_CLICK_ENABLED=True,
            V11_CLICK_DRY_RUN=False,
            V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE=True,
        )
    )
    _assert_ok("live no-click blocks real-click", result.ok is False)
    _assert_ok("live no-click error listed", "live_no_click_mode_disabled" in result.errors)
    _assert_ok("unsafe config aborts", result.abort_startup is True)


def test_real_mouse_without_master_arm_is_blocked():
    result = validate_real_click_readiness(
        _base_config(
            V09_REAL_CLICK_MASTER_ARMED=False,
            V11_REAL_MOUSE_CLICK_ENABLED=True,
            V11_CLICK_DRY_RUN=False,
            V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE=False,
        )
    )
    _assert_ok("missing master arm blocks", result.ok is False)
    _assert_ok("master error listed", "master_armed" in result.errors)


def test_service_real_click_is_blocked_in_action_button_only_mode():
    result = validate_real_click_readiness(
        _base_config(
            V09_REAL_CLICK_MASTER_ARMED=True,
            V11_REAL_MOUSE_CLICK_ENABLED=True,
            V11_CLICK_DRY_RUN=False,
            V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE=False,
            V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED=True,
            V11_TRIGGER_UI_SERVICE_DRY_RUN=False,
        )
    )
    _assert_ok("service real-click blocked", result.ok is False)
    _assert_ok("service disabled error listed", "service_real_click_disabled" in result.errors)
    _assert_ok("service action-only error listed", "service_clicks_disabled_for_v10" in result.errors)


def test_missing_slot_guard_is_blocked_even_in_no_click_mode():
    result = validate_real_click_readiness(_base_config(V09_REQUIRE_SLOT_BOUNDARY_GUARD=False))
    _assert_ok("missing slot guard blocks", result.ok is False)
    _assert_ok("slot guard error listed", "slot_boundary_guard_required" in result.errors)


def main() -> int:
    test_default_no_click_config_is_safe_but_not_real_ready()
    test_controlled_real_click_ready_when_all_flags_are_aligned()
    test_master_armed_but_live_no_click_enabled_is_blocked()
    test_real_mouse_without_master_arm_is_blocked()
    test_service_real_click_is_blocked_in_action_button_only_mode()
    test_missing_slot_guard_is_blocked_even_in_no_click_mode()
    print("[RESULT] OK: Real-click readiness unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
