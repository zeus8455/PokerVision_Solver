from __future__ import annotations

import config
from logic.real_click_readiness import validate_real_click_readiness


CONTROLLED_REAL_CLICK_READY_SNAPSHOT = {
    "V10_REAL_CLICK_READINESS_SCHEMA_VERSION": "real_click_readiness_v1",
    "V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED": True,
    "V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG": True,
    "V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY": True,
    "V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED": True,
    "V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED": True,
    "V10_REAL_CLICK_REQUIRE_MASTER_ARMED": True,
    "V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED": True,
    "V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED": True,
    "V09_CLICK_EXECUTION_GUARD_ENABLED": True,
    "V09_REAL_CLICK_MASTER_ARMED": True,
    "V09_REQUIRE_SLOT_BOUNDARY_GUARD": True,
    "V09_REQUIRE_NO_REPEAT_DECISION_GUARD": True,
    "V09_REQUIRE_BUTTON_AVAILABILITY_GUARD": True,
    "V09_REQUIRE_ACTION_RUNTIME_PLAN_SOURCE": "Action_Runtime_Plan_JSON",
    "V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK": True,
    "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": False,
    "V11_REAL_MOUSE_CLICK_ENABLED": True,
    "V11_CLICK_DRY_RUN": False,
    "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
    "V11_TRIGGER_UI_SERVICE_DRY_RUN": True,
}


def test_v14_default_config_remains_safe_no_click() -> None:
    result = validate_real_click_readiness(config)

    assert result.ok is True
    assert result.real_click_ready is False
    assert result.abort_startup is False
    assert config.V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE is True
    assert config.V09_REAL_CLICK_MASTER_ARMED is False
    assert config.V11_REAL_MOUSE_CLICK_ENABLED is False
    assert config.V11_CLICK_DRY_RUN is True
    assert config.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED is False
    assert config.V11_TRIGGER_UI_SERVICE_DRY_RUN is True


def test_v14_preset_contract_values() -> None:
    preset = config.get_v14_controlled_real_click_preset()

    assert preset["schema_version"] == "controlled_real_click_preset_v1"
    assert preset["preset_available"] is True
    assert preset["test_mode"] is False
    assert preset["table_id"] == "table_01"
    assert preset["max_clicks_per_run"] == 1
    assert preset["action_button_only"] is True
    assert preset["service_branch_disabled"] is True
    assert preset["raise_branch_enabled"] is False
    assert preset["require_scope_audit"] is True
    assert preset["allowed_actions"] == ["fold", "check", "call", "check_fold"]
    assert preset["allowed_buttons"] == ["FOLD", "Check", "Call", "Check/fold"]


def test_v14_manual_controlled_real_click_snapshot_is_readiness_ready() -> None:
    snapshot = dict(CONTROLLED_REAL_CLICK_READY_SNAPSHOT)
    snapshot.update(
        {
            "V14_CONTROLLED_REAL_CLICK_TEST_MODE": True,
            "V14_CONTROLLED_REAL_CLICK_TABLE_ID": "table_01",
            "V14_CONTROLLED_REAL_CLICK_MAX_CLICKS_PER_RUN": 1,
            "V14_CONTROLLED_REAL_CLICK_ACTION_BUTTON_ONLY": True,
            "V14_CONTROLLED_REAL_CLICK_SERVICE_BRANCH_DISABLED": True,
            "V14_CONTROLLED_REAL_CLICK_RAISE_BRANCH_ENABLED": False,
        }
    )

    result = validate_real_click_readiness(snapshot)

    assert result.ok is True
    assert result.status == "ready_for_controlled_real_click"
    assert result.real_click_ready is True
    assert result.abort_startup is False
    assert result.errors == []


def test_v14_service_real_click_is_rejected_even_when_action_click_is_ready() -> None:
    snapshot = dict(CONTROLLED_REAL_CLICK_READY_SNAPSHOT)
    snapshot["V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"] = True
    snapshot["V11_TRIGGER_UI_SERVICE_DRY_RUN"] = False

    result = validate_real_click_readiness(snapshot)

    assert result.ok is False
    assert result.status == "unsafe_real_click_config"
    assert result.real_click_ready is False
    assert "service_real_click_disabled" in result.errors
    assert "service_dry_run_enabled" in result.errors
    assert "service_clicks_disabled_for_v10" in result.errors


if __name__ == "__main__":
    test_v14_default_config_remains_safe_no_click()
    test_v14_preset_contract_values()
    test_v14_manual_controlled_real_click_snapshot_is_readiness_ready()
    test_v14_service_real_click_is_rejected_even_when_action_click_is_ready()
    print("[RESULT] OK: V1.4 controlled real-click preset unit tests passed.")
