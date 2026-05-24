"""
V8.2 live launch command must run controlled_live_preflight.py before main.py.

Goal:
- Final live command must set V8.1 + V31 env vars.
- It must execute controlled_live_preflight.py first.
- main.py may run only after $LASTEXITCODE -eq 0.
"""

from test_v77_final_live_mode_launch_contract_unit import LIVE_TEST_COMMAND


def test_v82_live_command_includes_v81_ready_profile_env():
    assert '$env:POKERVISION_CONTROLLED_LIVE_READY_PROFILE="V8_1_CONTROLLED_ACTION_BUTTON"' in LIVE_TEST_COMMAND


def test_v82_live_command_runs_preflight_before_main():
    assert "controlled_live_preflight.py" in LIVE_TEST_COMMAND
    assert "main.py" in LIVE_TEST_COMMAND
    assert LIVE_TEST_COMMAND.index("controlled_live_preflight.py") < LIVE_TEST_COMMAND.index("main.py")


def test_v82_live_command_guards_main_with_last_exit_code():
    assert "if ($LASTEXITCODE -eq 0)" in LIVE_TEST_COMMAND
    assert "controlled_live_preflight.py" in LIVE_TEST_COMMAND
    assert "main.py" in LIVE_TEST_COMMAND
