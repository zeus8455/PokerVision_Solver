from __future__ import annotations

import config


EXPECTED_TABLES = [
    "table_01",
    "table_02",
    "table_03",
    "table_04",
    "table_05",
    "table_06",
]

LIVE_TEST_ENV = {
    "POKERVISION_CONTROLLED_LIVE_READY_PROFILE": "V8_1_CONTROLLED_ACTION_BUTTON",
    "POKERVISION_CONTROLLED_LIVE_CLICK": "V3_1_ONE_CLICK",
    "POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS": ",".join(EXPECTED_TABLES),
    "POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN": "6",
}

LIVE_TEST_COMMAND = (
    'cd "C:\\PokerVision_Clear_Programing\\PokerVision V1_2"; '
    '$env:POKERVISION_CONTROLLED_LIVE_READY_PROFILE="V8_1_CONTROLLED_ACTION_BUTTON"; '
    '$env:POKERVISION_CONTROLLED_LIVE_CLICK="V3_1_ONE_CLICK"; '
    '$env:POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS="table_01,table_02,table_03,table_04,table_05,table_06"; '
    '$env:POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN="6"; '
    'C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python312\\python.exe controlled_live_preflight.py; '
    'if ($LASTEXITCODE -eq 0) { '
    'C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python312\\python.exe main.py --startup-audit-only; '
    'if ($LASTEXITCODE -eq 0) { '
    'C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python312\\python.exe main.py '
    '} '
    '}'
)


def test_v77_default_config_remains_safe_no_click() -> None:
    assert config.V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE is True
    assert config.V09_REAL_CLICK_MASTER_ARMED is False
    assert config.V11_REAL_MOUSE_CLICK_ENABLED is False
    assert config.V11_CLICK_DRY_RUN is True
    assert config.V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED is False
    assert config.V11_TRIGGER_UI_SERVICE_DRY_RUN is True


def test_v77_controlled_env_targets_all_six_tables() -> None:
    tables = LIVE_TEST_ENV["POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS"].split(",")

    assert tables == EXPECTED_TABLES
    assert len(tables) == 6
    assert all(t.startswith("table_") for t in tables)


def test_v77_launch_command_contains_required_safety_tokens() -> None:
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK="V3_1_ONE_CLICK"' in LIVE_TEST_COMMAND
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS="table_01,table_02,table_03,table_04,table_05,table_06"' in LIVE_TEST_COMMAND
    assert "main.py" in LIVE_TEST_COMMAND
    assert "Python312\\python.exe" in LIVE_TEST_COMMAND


def test_v77_runtime_default_gate_still_one_click_unless_explicitly_overridden() -> None:
    assert config.V31_CONTROLLED_LIVE_CLICK_GATE_ENABLED is True
    assert config.V31_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN == 1
    assert config.V31_CONTROLLED_LIVE_CLICK_SERVICE_BRANCH_DISABLED is True
    assert config.V31_CONTROLLED_LIVE_CLICK_RAISE_BRANCH_ENABLED is False
    assert config.V31_CONTROLLED_LIVE_CLICK_ACTION_BUTTON_ONLY is True


def test_v77_allowed_actions_remain_simple_only() -> None:
    assert list(config.V31_CONTROLLED_LIVE_CLICK_ALLOWED_ACTIONS) == ["fold", "check", "call", "check_fold"]
    assert list(config.V31_CONTROLLED_LIVE_CLICK_ALLOWED_BUTTONS) == ["FOLD", "Check", "Call", "Check/fold"]


def main() -> int:
    tests = [
        test_v77_default_config_remains_safe_no_click,
        test_v77_controlled_env_targets_all_six_tables,
        test_v77_launch_command_contains_required_safety_tokens,
        test_v77_runtime_default_gate_still_one_click_unless_explicitly_overridden,
        test_v77_allowed_actions_remain_simple_only,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V7.7 final live-mode launch contract tests passed.")
    print("[V7.7 LIVE TEST COMMAND]")
    print(LIVE_TEST_COMMAND)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
