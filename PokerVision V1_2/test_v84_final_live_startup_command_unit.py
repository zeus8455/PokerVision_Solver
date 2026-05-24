"""
V8.4 final controlled live startup command contract.

Goal:
- Final live command must run controlled_live_preflight.py first.
- Then it must run main.py --startup-audit-only.
- Only after both checks pass may it run main.py.
"""

from test_v77_final_live_mode_launch_contract_unit import LIVE_TEST_COMMAND


def test_v84_live_command_runs_preflight_then_startup_audit_then_main():
    assert "controlled_live_preflight.py" in LIVE_TEST_COMMAND
    assert "main.py --startup-audit-only" in LIVE_TEST_COMMAND
    assert "main.py" in LIVE_TEST_COMMAND

    preflight_pos = LIVE_TEST_COMMAND.index("controlled_live_preflight.py")
    audit_pos = LIVE_TEST_COMMAND.index("main.py --startup-audit-only")
    main_pos = LIVE_TEST_COMMAND.rindex("main.py")

    assert preflight_pos < audit_pos < main_pos


def test_v84_live_command_guards_each_stage_with_last_exit_code():
    assert "if ($LASTEXITCODE -eq 0)" in LIVE_TEST_COMMAND
    assert LIVE_TEST_COMMAND.count("if ($LASTEXITCODE -eq 0)") >= 2


def test_v84_live_command_keeps_all_required_env_vars():
    assert '$env:POKERVISION_CONTROLLED_LIVE_READY_PROFILE="V8_1_CONTROLLED_ACTION_BUTTON"' in LIVE_TEST_COMMAND
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK="V3_1_ONE_CLICK"' in LIVE_TEST_COMMAND
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS="table_01,table_02,table_03,table_04,table_05,table_06"' in LIVE_TEST_COMMAND
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN="6"' in LIVE_TEST_COMMAND
