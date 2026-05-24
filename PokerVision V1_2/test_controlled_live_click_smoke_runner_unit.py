from __future__ import annotations

from controlled_live_click_smoke_runner import (
    ALLOWED_ACTIONS,
    ALLOWED_BUTTONS,
    build_current_config_snapshot,
    build_manual_controlled_snapshot,
    evaluate_controlled_live_click_snapshot,
    main,
)


def test_v15_default_current_config_is_blocked_no_click() -> None:
    snapshot = build_current_config_snapshot()
    report = evaluate_controlled_live_click_snapshot(snapshot)

    assert report["ready"] is False
    assert report["status"] == "CONTROLLED_REAL_CLICK_BLOCKED"
    assert report["click_execution"] == "not_performed_by_smoke_runner"


def test_v15_manual_controlled_snapshot_is_ready_for_table_01() -> None:
    snapshot = build_manual_controlled_snapshot()
    report = evaluate_controlled_live_click_snapshot(snapshot)

    assert report["ready"] is True
    assert report["status"] == "CONTROLLED_REAL_CLICK_READY"
    assert report["scope_errors"] == []
    assert report["readiness"]["real_click_ready"] is True
    assert report["table_id"] == "table_01"
    assert report["max_clicks_per_run"] == 1
    assert report["allowed_actions"] == ALLOWED_ACTIONS
    assert report["allowed_buttons"] == ALLOWED_BUTTONS


def test_v15_manual_snapshot_blocks_wrong_table() -> None:
    snapshot = build_manual_controlled_snapshot(table_id="table_02")
    report = evaluate_controlled_live_click_snapshot(snapshot)

    assert report["ready"] is False
    assert "controlled_table_must_be_table_01" in report["scope_errors"]


def test_v15_manual_snapshot_blocks_service_real_click() -> None:
    snapshot = build_manual_controlled_snapshot()
    snapshot["V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED"] = True
    snapshot["V11_TRIGGER_UI_SERVICE_DRY_RUN"] = False
    report = evaluate_controlled_live_click_snapshot(snapshot)

    assert report["ready"] is False
    assert "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED_must_be_False" in report["scope_errors"]
    assert "V11_TRIGGER_UI_SERVICE_DRY_RUN_must_be_True" in report["scope_errors"]
    assert "service_real_click_disabled" in report["readiness"]["errors"]


def test_v15_manual_snapshot_blocks_raise_branch() -> None:
    snapshot = build_manual_controlled_snapshot()
    snapshot["V14_CONTROLLED_REAL_CLICK_RAISE_BRANCH_ENABLED"] = True
    report = evaluate_controlled_live_click_snapshot(snapshot)

    assert report["ready"] is False
    assert "V14_CONTROLLED_REAL_CLICK_RAISE_BRANCH_ENABLED_must_be_False" in report["scope_errors"]


def test_v15_main_manual_snapshot_returns_zero() -> None:
    assert main(["--manual-controlled-snapshot"]) == 0


def test_v15_main_wrong_table_returns_blocked() -> None:
    assert main(["--manual-controlled-snapshot", "--table-id", "table_02"]) == 2


if __name__ == "__main__":
    test_v15_default_current_config_is_blocked_no_click()
    test_v15_manual_controlled_snapshot_is_ready_for_table_01()
    test_v15_manual_snapshot_blocks_wrong_table()
    test_v15_manual_snapshot_blocks_service_real_click()
    test_v15_manual_snapshot_blocks_raise_branch()
    test_v15_main_manual_snapshot_returns_zero()
    test_v15_main_wrong_table_returns_blocked()
    print("[RESULT] OK: V1.5 controlled live-click smoke runner unit tests passed.")
