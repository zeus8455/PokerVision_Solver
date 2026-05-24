from __future__ import annotations

import config as c


def test_default_service_real_click_is_blocked_by_safe_config() -> None:
    assert c.V11_TRIGGER_UI_SERVICE_CLICK_ENABLED is True

    assert c.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED is False
    assert c.V11_TRIGGER_UI_SERVICE_DRY_RUN is True

    assert c.V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE is True
    assert c.V09_REAL_CLICK_MASTER_ARMED is False
    assert c.V11_REAL_MOUSE_CLICK_ENABLED is False
    assert c.V11_CLICK_DRY_RUN is True


def test_real_click_readiness_requires_service_clicks_disabled_for_action_button_path() -> None:
    assert c.V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED is True
    assert c.V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED is True
    assert c.V10_REAL_CLICK_REQUIRE_MASTER_ARMED is True
    assert c.V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED is True
    assert c.V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED is True


def main() -> int:
    test_default_service_real_click_is_blocked_by_safe_config()
    test_real_click_readiness_requires_service_clicks_disabled_for_action_button_path()
    print("[RESULT] OK: PokerVision V6.9 service real-click guard config tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
