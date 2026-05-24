r"""
test_table_lifecycle_duplicate_block_unit.py

PokerVision V2.2 — duplicate lifecycle block tests.

Purpose:
- Prove that the early per-table lifecycle gate blocks repeated heavy analysis
  while the same table is still inside an unfinished analysis/action/click cycle.
- Prove that the lock is per-table, not global.
- Prove that click/dry-run completion releases the table for the next valid cycle.

Run directly:
  python test_table_lifecycle_duplicate_block_unit.py
"""

from __future__ import annotations

from logic.table_action_transaction_gate import TableActionTransactionGate


def _ok(name: str) -> None:
    print(f"[OK] {name}")


def _dry_run_runtime_action(decision_id: str = "decision_01") -> dict:
    return {
        "action_button": {
            "status": "dry_run",
            "dry_run": True,
            "real_click_enabled": False,
            "guard_passed": True,
            "solver_action": "fold",
            "decision_id": decision_id,
            "message": "v22_duplicate_lifecycle_test_dry_run",
        }
    }


def test_duplicate_active_blocks_heavy_analysis_while_analyzing() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)

    first = gate.begin_analysis_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_first",
        action_signature="sig_table_01_first",
    )
    assert first.should_process is True
    assert first.status == "started"
    assert first.phase == "analyzing"

    duplicate = gate.begin_analysis_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_duplicate",
        action_signature="sig_table_01_duplicate",
    )
    assert duplicate.should_process is False
    assert duplicate.status == "blocked"
    assert duplicate.reason == "table_lifecycle_already_open_before_analysis"
    assert duplicate.phase == "analyzing"
    assert duplicate.locked_by_transaction_id == first.transaction_id

    _ok("test_duplicate_active_blocks_heavy_analysis_while_analyzing")


def test_duplicate_active_blocks_heavy_analysis_while_waiting_click() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)

    first = gate.begin_analysis_cycle(table_id="table_01")
    action = gate.begin_action_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_action",
        action_signature="sig_table_01_action",
    )
    assert first.should_process is True
    assert action.should_process is True
    assert action.phase == "waiting_click"

    duplicate = gate.begin_analysis_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_duplicate_after_action",
        action_signature="sig_table_01_duplicate_after_action",
    )
    assert duplicate.should_process is False
    assert duplicate.status == "blocked"
    assert duplicate.reason == "table_lifecycle_already_open_before_analysis"
    assert duplicate.phase == "waiting_click"
    assert duplicate.locked_by_transaction_id == first.transaction_id

    _ok("test_duplicate_active_blocks_heavy_analysis_while_waiting_click")


def test_per_table_duplicate_block_does_not_block_other_tables() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)

    table_01 = gate.begin_analysis_cycle(table_id="table_01")
    duplicate_table_01 = gate.begin_analysis_cycle(table_id="table_01")
    table_02 = gate.begin_analysis_cycle(table_id="table_02")

    assert table_01.should_process is True
    assert duplicate_table_01.should_process is False
    assert table_02.should_process is True
    assert table_02.transaction_id != table_01.transaction_id

    _ok("test_per_table_duplicate_block_does_not_block_other_tables")


def test_click_completion_releases_table_for_next_lifecycle() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True)

    first = gate.begin_analysis_cycle(table_id="table_01")
    action = gate.begin_action_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_action",
        action_signature="sig_table_01_action",
    )
    assert first.should_process is True
    assert action.should_process is True

    completed = gate.finalize_from_runtime(
        table_id="table_01",
        runtime_action=_dry_run_runtime_action("decision_01"),
    )
    assert completed["status"] == "completed"
    assert completed["click_completed"] is True
    assert gate.snapshot("table_01") is None

    next_cycle = gate.begin_analysis_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_next",
        action_signature="sig_table_01_next",
    )
    assert next_cycle.should_process is True
    assert next_cycle.status == "started"
    assert next_cycle.phase == "analyzing"
    assert next_cycle.transaction_id != first.transaction_id

    _ok("test_click_completion_releases_table_for_next_lifecycle")


def test_failed_click_keeps_table_locked_until_inactive_release() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)

    gate.begin_analysis_cycle(table_id="table_01")
    gate.begin_action_cycle(
        table_id="table_01",
        action_event_id="evt_table_01_action",
        action_signature="sig_table_01_action",
    )
    failed = gate.finalize_from_runtime(
        table_id="table_01",
        runtime_action={
            "action_button": {
                "status": "blocked",
                "dry_run": False,
                "real_click_enabled": False,
                "decision_id": "decision_blocked",
            }
        },
    )
    assert failed["status"] == "failed"
    assert failed["click_completed"] is False

    duplicate = gate.begin_analysis_cycle(table_id="table_01")
    assert duplicate.should_process is False
    assert duplicate.phase == "click_failed"

    release = gate.observe_inactive("table_01")
    assert release is not None
    assert release["status"] == "aborted"

    next_cycle = gate.begin_analysis_cycle(table_id="table_01")
    assert next_cycle.should_process is True

    _ok("test_failed_click_keeps_table_locked_until_inactive_release")


def run_all() -> None:
    tests = [
        test_duplicate_active_blocks_heavy_analysis_while_analyzing,
        test_duplicate_active_blocks_heavy_analysis_while_waiting_click,
        test_per_table_duplicate_block_does_not_block_other_tables,
        test_click_completion_releases_table_for_next_lifecycle,
        test_failed_click_keeps_table_locked_until_inactive_release,
    ]
    for test in tests:
        test()
    print("[RESULT] OK: PokerVision V2.2 duplicate lifecycle block tests passed.")


if __name__ == "__main__":
    run_all()
