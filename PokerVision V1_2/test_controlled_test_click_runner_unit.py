from __future__ import annotations

from controlled_test_click_runner import (
    CONFIRMATION_TOKEN,
    build_arg_parser,
    execute_test_click_candidate,
)


def _parse(args):
    return build_arg_parser().parse_args(args)


def test_blocks_without_test_environment_flag():
    args = _parse([
        "--manual-controlled-snapshot",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--x", "10",
        "--y", "20",
    ])
    result = execute_test_click_candidate(args, environ={})
    assert result["ready"] is False
    assert "test_environment_flag_required" in result["blockers"]


def test_dry_run_candidate_ready_for_table_01():
    args = _parse([
        "--manual-controlled-snapshot",
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--table", "table_01",
        "--action", "fold",
        "--button", "FOLD",
        "--x", "10",
        "--y", "20",
    ])
    result = execute_test_click_candidate(args, environ={})
    assert result["ready"] is True
    assert result["click_execution"] == "dry_run_candidate_recorded"
    assert result["candidate"]["table_id"] == "table_01"


def test_table_02_is_blocked():
    args = _parse([
        "--manual-controlled-snapshot",
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--table", "table_02",
        "--action", "fold",
        "--button", "FOLD",
        "--x", "10",
        "--y", "20",
    ])
    result = execute_test_click_candidate(args, environ={})
    assert result["ready"] is False
    assert "controlled_table_must_be_table_01" in result["blockers"]


def test_raise_branch_is_blocked():
    args = _parse([
        "--manual-controlled-snapshot",
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--table", "table_01",
        "--action", "raise",
        "--button", "Raise",
        "--x", "10",
        "--y", "20",
    ])
    result = execute_test_click_candidate(args, environ={})
    assert result["ready"] is False

    blockers = set(result.get("blockers") or [])
    accepted_action_blockers = {
        # V1.6 names
        "action_not_allowed_for_v1_6_test_click",
        "button_not_allowed_for_v1_6_test_click",
        # V2.9 unified controlled-runner names
        "action_not_allowed_for_controlled_test_click",
        "button_not_allowed_for_controlled_test_click",
        # V2.9 detected-button/scope-style names
        "raise_or_size_branch_blocked",
        "non_simple_action_blocked",
    }
    assert blockers.intersection(accepted_action_blockers), blockers


def test_real_test_click_requires_environment_variable():
    args = _parse([
        "--manual-controlled-snapshot",
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--real-test-click",
        "--table", "table_01",
        "--action", "check",
        "--button", "Check",
        "--x", "10",
        "--y", "20",
    ])
    result = execute_test_click_candidate(args, environ={})
    assert result["ready"] is False
    assert "env_POKERVISION_TEST_ENVIRONMENT_must_equal_1_for_real_test_click" in result["blockers"]


def test_real_test_click_uses_injected_executor_when_all_gates_pass():
    calls = []

    def fake_click(x, y):
        calls.append((x, y))
        return {"backend": "fake", "clicked": True, "x": x, "y": y}

    args = _parse([
        "--manual-controlled-snapshot",
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--real-test-click",
        "--table", "table_01",
        "--action", "call",
        "--button", "Call",
        "--x", "33",
        "--y", "44",
    ])
    result = execute_test_click_candidate(
        args,
        click_executor=fake_click,
        environ={"POKERVISION_TEST_ENVIRONMENT": "1"},
    )
    assert result["ready"] is True
    assert result["clicked"] is True
    assert result["click_execution"] == "clicked_in_test_environment"
    assert calls == [(33, 44)]


def test_bbox_center_can_build_candidate():
    args = _parse([
        "--manual-controlled-snapshot",
        "--test-environment",
        "--confirm-test-click", CONFIRMATION_TOKEN,
        "--table", "table_01",
        "--action", "check_fold",
        "--button", "Check/fold",
        "--bbox", "10,20,30,60",
    ])
    result = execute_test_click_candidate(args, environ={})
    assert result["ready"] is True
    assert result["candidate"]["x"] == 20
    assert result["candidate"]["y"] == 40


def main() -> int:
    tests = [
        test_blocks_without_test_environment_flag,
        test_dry_run_candidate_ready_for_table_01,
        test_table_02_is_blocked,
        test_raise_branch_is_blocked,
        test_real_test_click_requires_environment_variable,
        test_real_test_click_uses_injected_executor_when_all_gates_pass,
        test_bbox_center_can_build_candidate,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: V1.6 controlled test-environment click runner unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
