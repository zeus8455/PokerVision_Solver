"""
test_six_slot_lifecycle_audit_unit.py

PokerVision V2.4 — six-slot lifecycle audit.
"""

from __future__ import annotations

from typing import Dict, Optional

from logic.table_action_transaction_gate import TableActionTransactionGate


def _gate() -> TableActionTransactionGate:
    return TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)


def _begin_analysis(gate: TableActionTransactionGate, table_id: str, signature: str):
    return gate.begin_analysis_cycle(
        table_id=table_id,
        action_event_id=f"evt_{table_id}_{signature}",
        action_signature=signature,
    )


def _begin_action(gate: TableActionTransactionGate, table_id: str, signature: str):
    return gate.begin_action_cycle(
        table_id=table_id,
        action_event_id=f"evt_{table_id}_{signature}",
        action_signature=signature,
    )


def _runtime_action(
    *,
    status: str,
    dry_run: bool = True,
    real_click_enabled: bool = False,
    decision_id: Optional[str] = None,
    action: str = "fold",
) -> Dict[str, object]:
    return {
        "action_button": {
            "status": status,
            "branch": "action_button",
            "solver_action": action,
            "action": action,
            "dry_run": dry_run,
            "real_click_enabled": real_click_enabled,
            "guard_passed": status in {"dry_run", "clicked", "confirmed"},
            "decision_id": decision_id or f"decision_{status}",
            "message": f"unit runtime action {status}",
        }
    }


def _assert_blocked(decision, *, table_id: str) -> None:
    assert decision.table_id == table_id
    assert decision.should_process is False
    assert decision.status == "blocked"
    assert decision.locked_by_transaction_id


def _assert_allowed(decision, *, table_id: str) -> None:
    assert decision.table_id == table_id
    assert decision.should_process is True
    assert decision.transaction_id


def test_six_slots_start_independently_while_table_01_is_analyzing() -> None:
    gate = _gate()
    first = _begin_analysis(gate, "table_01", "sig_t01_a")
    _assert_allowed(first, table_id="table_01")
    assert first.phase == "analyzing"

    duplicate_t01 = _begin_analysis(gate, "table_01", "sig_t01_a")
    _assert_blocked(duplicate_t01, table_id="table_01")
    assert duplicate_t01.phase == "analyzing"

    for idx in range(2, 7):
        table_id = f"table_{idx:02d}"
        decision = _begin_analysis(gate, table_id, f"sig_{table_id}_a")
        _assert_allowed(decision, table_id=table_id)
        assert decision.phase == "analyzing"


def test_waiting_click_on_one_table_does_not_block_other_tables() -> None:
    gate = _gate()
    _assert_allowed(_begin_analysis(gate, "table_01", "sig_t01_a"), table_id="table_01")
    action_t01 = _begin_action(gate, "table_01", "sig_t01_a")
    _assert_allowed(action_t01, table_id="table_01")
    assert action_t01.phase == "waiting_click"

    duplicate_t01 = _begin_analysis(gate, "table_01", "sig_t01_b")
    _assert_blocked(duplicate_t01, table_id="table_01")
    assert duplicate_t01.phase == "waiting_click"

    decision_t02 = _begin_analysis(gate, "table_02", "sig_t02_a")
    _assert_allowed(decision_t02, table_id="table_02")
    assert decision_t02.phase == "analyzing"


def test_mixed_six_slot_lifecycle_states_are_isolated() -> None:
    gate = _gate()
    _assert_allowed(_begin_analysis(gate, "table_01", "sig_t01_a"), table_id="table_01")
    _assert_blocked(_begin_analysis(gate, "table_01", "sig_t01_dup"), table_id="table_01")

    _assert_allowed(_begin_analysis(gate, "table_02", "sig_t02_a"), table_id="table_02")
    action_t02 = _begin_action(gate, "table_02", "sig_t02_a")
    _assert_allowed(action_t02, table_id="table_02")
    assert action_t02.phase == "waiting_click"
    _assert_blocked(_begin_analysis(gate, "table_02", "sig_t02_dup"), table_id="table_02")

    _assert_allowed(_begin_analysis(gate, "table_03", "sig_t03_a"), table_id="table_03")
    _assert_allowed(_begin_action(gate, "table_03", "sig_t03_a"), table_id="table_03")
    failed = gate.finalize_from_runtime(
        table_id="table_03",
        runtime_action=_runtime_action(status="blocked", dry_run=False, real_click_enabled=False),
    )
    assert failed["status"] == "failed"
    assert failed["click_completed"] is False
    _assert_blocked(_begin_analysis(gate, "table_03", "sig_t03_dup"), table_id="table_03")

    _assert_allowed(_begin_analysis(gate, "table_04", "sig_t04_a"), table_id="table_04")
    _assert_allowed(_begin_action(gate, "table_04", "sig_t04_a"), table_id="table_04")
    completed = gate.finalize_from_runtime(
        table_id="table_04",
        runtime_action=_runtime_action(status="dry_run", dry_run=True, real_click_enabled=False),
    )
    assert completed["status"] == "completed"
    assert completed["click_completed"] is True
    _assert_allowed(_begin_analysis(gate, "table_04", "sig_t04_b"), table_id="table_04")

    _assert_allowed(_begin_analysis(gate, "table_05", "sig_t05_a"), table_id="table_05")
    inactive = gate.observe_inactive("table_05")
    assert isinstance(inactive, dict)
    assert inactive["status"] == "aborted"
    _assert_allowed(_begin_analysis(gate, "table_05", "sig_t05_b"), table_id="table_05")

    _assert_allowed(_begin_analysis(gate, "table_06", "sig_t06_a"), table_id="table_06")


def test_dry_run_completion_releases_only_target_table() -> None:
    gate = _gate()
    _assert_allowed(_begin_analysis(gate, "table_01", "sig_t01_a"), table_id="table_01")
    _assert_allowed(_begin_action(gate, "table_01", "sig_t01_a"), table_id="table_01")
    _assert_allowed(_begin_analysis(gate, "table_02", "sig_t02_a"), table_id="table_02")
    _assert_allowed(_begin_action(gate, "table_02", "sig_t02_a"), table_id="table_02")

    completed_t01 = gate.finalize_from_runtime(
        table_id="table_01",
        runtime_action=_runtime_action(status="dry_run", decision_id="decision_t01"),
    )
    assert completed_t01["status"] == "completed"

    _assert_allowed(_begin_analysis(gate, "table_01", "sig_t01_b"), table_id="table_01")
    _assert_blocked(_begin_analysis(gate, "table_02", "sig_t02_dup"), table_id="table_02")


def run_all() -> None:
    tests = [
        test_six_slots_start_independently_while_table_01_is_analyzing,
        test_waiting_click_on_one_table_does_not_block_other_tables,
        test_mixed_six_slot_lifecycle_states_are_isolated,
        test_dry_run_completion_releases_only_target_table,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V2.4 six-slot lifecycle audit tests passed.")


if __name__ == "__main__":
    run_all()
