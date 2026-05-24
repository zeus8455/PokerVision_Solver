from __future__ import annotations

from logic.real_click_readiness import validate_real_click_readiness


def _safe_default_config() -> dict:
    return {
        "V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED": True,
        "V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG": True,
        "V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY": True,
        "V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED": True,
        "V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED": True,
        "V10_REAL_CLICK_REQUIRE_MASTER_ARMED": True,
        "V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED": True,
        "V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED": True,
        "V09_CLICK_EXECUTION_GUARD_ENABLED": True,
        "V09_REAL_CLICK_MASTER_ARMED": False,
        "V09_REQUIRE_SLOT_BOUNDARY_GUARD": True,
        "V09_REQUIRE_NO_REPEAT_DECISION_GUARD": True,
        "V09_REQUIRE_BUTTON_AVAILABILITY_GUARD": True,
        "V09_REQUIRE_ACTION_RUNTIME_PLAN_SOURCE": "Action_Runtime_Plan_JSON",
        "V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK": True,
        "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": True,
        "V11_REAL_MOUSE_CLICK_ENABLED": False,
        "V11_CLICK_DRY_RUN": True,
        "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
        "V11_TRIGGER_UI_SERVICE_DRY_RUN": True,
    }


def _controlled_real_click_config() -> dict:
    cfg = _safe_default_config()
    cfg.update(
        {
            "V09_REAL_CLICK_MASTER_ARMED": True,
            "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": False,
            "V11_REAL_MOUSE_CLICK_ENABLED": True,
            "V11_CLICK_DRY_RUN": False,
            "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
            "V11_TRIGGER_UI_SERVICE_DRY_RUN": True,
        }
    )
    return cfg


def test_default_config_is_safe_but_not_real_click_ready() -> None:
    result = validate_real_click_readiness(_safe_default_config())
    assert result.ok is True
    assert result.status == "safe_no_click"
    assert result.real_click_ready is False
    assert result.abort_startup is False


def test_controlled_action_button_real_click_readiness_passes() -> None:
    result = validate_real_click_readiness(_controlled_real_click_config())
    assert result.ok is True
    assert result.status == "ready_for_controlled_real_click"
    assert result.real_click_ready is True
    assert result.abort_startup is False

    assert result.checks["master_armed"] is True
    assert result.checks["action_mouse_real_enabled"] is True
    assert result.checks["action_mouse_dry_run_disabled"] is True
    assert result.checks["live_no_click_mode_disabled"] is True
    assert result.checks["service_clicks_disabled_for_v10"] is True
    assert result.checks["slot_boundary_guard_required"] is True
    assert result.checks["no_repeat_decision_guard_required"] is True
    assert result.checks["button_availability_guard_required"] is True


def test_service_real_click_blocks_controlled_readiness() -> None:
    cfg = _controlled_real_click_config()
    cfg["V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"] = True

    result = validate_real_click_readiness(cfg)
    assert result.ok is False
    assert result.status == "unsafe_real_click_config"
    assert result.real_click_ready is False
    assert result.abort_startup is True
    assert "service_real_click_disabled" in result.errors
    assert "service_clicks_disabled_for_v10" in result.errors


def test_live_no_click_mode_blocks_controlled_readiness() -> None:
    cfg = _controlled_real_click_config()
    cfg["V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE"] = True

    result = validate_real_click_readiness(cfg)
    assert result.ok is False
    assert result.status == "unsafe_real_click_config"
    assert result.real_click_ready is False
    assert "live_no_click_mode_disabled" in result.errors


def test_controlled_four_to_six_table_scope_contract() -> None:
    allowed_tables = [f"table_{idx:02d}" for idx in range(1, 7)]
    max_clicks_per_run = 6

    result = validate_real_click_readiness(_controlled_real_click_config())
    assert result.real_click_ready is True

    assert allowed_tables == [
        "table_01",
        "table_02",
        "table_03",
        "table_04",
        "table_05",
        "table_06",
    ]
    assert 4 <= max_clicks_per_run <= 6

    for table_id in allowed_tables:
        assert table_id.startswith("table_")
        assert table_id[-2:].isdigit()


def main() -> int:
    tests = [
        test_default_config_is_safe_but_not_real_click_ready,
        test_controlled_action_button_real_click_readiness_passes,
        test_service_real_click_blocks_controlled_readiness,
        test_live_no_click_mode_blocks_controlled_readiness,
        test_controlled_four_to_six_table_scope_contract,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V7.4 controlled real-click readiness 4-6 table tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
