r"""
test_table_action_transaction_gate_unit.py

Unit tests for PokerVision V2.1 early per-table transaction lifecycle gate instrumentation.
Run directly:
  python test_table_action_transaction_gate_unit.py
"""

from __future__ import annotations

from logic.table_action_transaction_gate import TableActionTransactionGate


def _ok(name: str) -> None:
    print(f"[OK] {name}")


def test_gate_blocks_second_active_until_click_completion() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    first = gate.begin_action_cycle(table_id="table_01", action_event_id="evt_1", action_signature="sig_1")
    assert first.should_process is True
    second = gate.begin_action_cycle(table_id="table_01", action_event_id="evt_2", action_signature="sig_2")
    assert second.should_process is False
    assert second.reason == "table_action_transaction_already_open"
    _ok("test_gate_blocks_second_active_until_click_completion")


def test_gate_releases_after_dry_run_when_enabled() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    gate.begin_action_cycle(table_id="table_01", action_event_id="evt_1", action_signature="sig_1")
    report = gate.finalize_from_runtime(
        table_id="table_01",
        runtime_action={"action_button": {"status": "dry_run", "dry_run": True, "decision_id": "d1"}},
    )
    assert report["status"] == "completed"
    assert report["click_completed"] is True
    next_decision = gate.begin_action_cycle(table_id="table_01", action_event_id="evt_2", action_signature="sig_2")
    assert next_decision.should_process is True
    _ok("test_gate_releases_after_dry_run_when_enabled")


def test_gate_keeps_locked_after_blocked_click() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    gate.begin_action_cycle(table_id="table_01", action_event_id="evt_1", action_signature="sig_1")
    report = gate.finalize_from_runtime(
        table_id="table_01",
        runtime_action={"action_button": {"status": "blocked", "dry_run": False, "decision_id": "d1"}},
    )
    assert report["status"] == "failed"
    assert report["click_completed"] is False
    blocked = gate.begin_action_cycle(table_id="table_01", action_event_id="evt_2", action_signature="sig_2")
    assert blocked.should_process is False
    assert blocked.phase == "click_failed"
    _ok("test_gate_keeps_locked_after_blocked_click")


def test_gate_releases_on_inactive_after_unfinished_transaction() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)
    gate.begin_action_cycle(table_id="table_01", action_event_id="evt_1", action_signature="sig_1")
    report = gate.observe_inactive("table_01")
    assert report is not None
    assert report["status"] == "aborted"
    next_decision = gate.begin_action_cycle(table_id="table_01", action_event_id="evt_2", action_signature="sig_2")
    assert next_decision.should_process is True
    _ok("test_gate_releases_on_inactive_after_unfinished_transaction")


def test_v20_begin_analysis_cycle_blocks_second_heavy_analysis() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    first = gate.begin_analysis_cycle(table_id="table_01")
    assert first.should_process is True
    assert first.phase == "analyzing"
    first_json = first.to_json()
    assert first_json["schema_version"] == "table_lifecycle_gate_v2_1"
    assert first_json["heavy_analysis_allowed"] is True
    assert first_json["heavy_analysis_blocked"] is False

    second = gate.begin_analysis_cycle(table_id="table_01")
    assert second.should_process is False
    assert second.reason == "table_lifecycle_already_open_before_analysis"
    assert second.locked_by_transaction_id == first.transaction_id
    second_json = second.to_json()
    assert second_json["schema_version"] == "table_lifecycle_gate_v2_1"
    assert second_json["heavy_analysis_allowed"] is False
    assert second_json["heavy_analysis_blocked"] is True
    assert second_json["blocked_reason"] == "table_lifecycle_already_open_before_analysis"
    _ok("test_v20_begin_analysis_cycle_blocks_second_heavy_analysis")


def test_v20_analysis_cycle_can_enter_action_runtime() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    analysis = gate.begin_analysis_cycle(table_id="table_01")
    action = gate.begin_action_cycle(table_id="table_01", action_event_id="evt_1", action_signature="sig_1")
    assert action.should_process is True
    assert action.status == "continued"
    assert action.transaction_id == analysis.transaction_id
    snap = gate.snapshot("table_01")
    assert snap is not None
    assert snap["phase"] == "waiting_click"
    assert snap["action_event_id"] == "evt_1"
    assert snap["action_signature"] == "sig_1"
    _ok("test_v20_analysis_cycle_can_enter_action_runtime")


def test_v20_abort_analysis_cycle_releases_table() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    gate.begin_analysis_cycle(table_id="table_01")
    report = gate.abort_analysis_cycle(
        table_id="table_01",
        reason="duplicate_action_event_after_analysis",
        message="release test",
    )
    assert report["status"] == "aborted"
    assert report["click_completed"] is False
    assert gate.snapshot("table_01") is None
    next_decision = gate.begin_analysis_cycle(table_id="table_01")
    assert next_decision.should_process is True
    _ok("test_v20_abort_analysis_cycle_releases_table")


def test_v20_table_lifecycle_is_per_table() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)
    t1 = gate.begin_analysis_cycle(table_id="table_01")
    t2 = gate.begin_analysis_cycle(table_id="table_02")
    assert t1.should_process is True
    assert t2.should_process is True
    assert t1.transaction_id != t2.transaction_id
    blocked_t1 = gate.begin_analysis_cycle(table_id="table_01")
    assert blocked_t1.should_process is False
    _ok("test_v20_table_lifecycle_is_per_table")


def run_all() -> None:
    tests = [
        test_gate_blocks_second_active_until_click_completion,
        test_gate_releases_after_dry_run_when_enabled,
        test_gate_keeps_locked_after_blocked_click,
        test_gate_releases_on_inactive_after_unfinished_transaction,
        test_v20_begin_analysis_cycle_blocks_second_heavy_analysis,
        test_v20_analysis_cycle_can_enter_action_runtime,
        test_v20_abort_analysis_cycle_releases_table,
        test_v20_table_lifecycle_is_per_table,
    ]
    for test in tests:
        test()
    print("[RESULT] OK: TableActionTransactionGate V2.1 unit tests passed.")


if __name__ == "__main__":
    run_all()
