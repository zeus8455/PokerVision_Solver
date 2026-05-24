"""
V7.9 PowerShell live launch command contract.

Goal:
- The documented controlled live-click launch command must be PowerShell-compatible.
- It must use $env:... assignments, not cmd.exe `set VAR=value`.
- It must include V7.8 max-click override for 4-6 table live tests.
"""

from test_v77_final_live_mode_launch_contract_unit import LIVE_TEST_COMMAND


def test_v79_live_command_uses_powershell_env_assignments():
    assert "set POKERVISION_" not in LIVE_TEST_COMMAND
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK="V3_1_ONE_CLICK"' in LIVE_TEST_COMMAND
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK_TABLE_IDS="table_01,table_02,table_03,table_04,table_05,table_06"' in LIVE_TEST_COMMAND


def test_v79_live_command_includes_max_clicks_override():
    assert '$env:POKERVISION_CONTROLLED_LIVE_CLICK_MAX_CLICKS_PER_RUN="6"' in LIVE_TEST_COMMAND


def test_v79_live_command_runs_main_py_after_env_setup():
    assert 'C:\\Users\\user\\AppData\\Local\\Programs\\Python\\Python312\\python.exe main.py' in LIVE_TEST_COMMAND
    assert LIVE_TEST_COMMAND.strip().endswith("main.py")
