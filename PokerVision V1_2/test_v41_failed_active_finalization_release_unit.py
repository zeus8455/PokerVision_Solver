r"""
test_v41_failed_active_finalization_release_unit.py

PokerVision V4.1/V4.2 — release/abort transaction on invalid Active finalization.

Contract:
- if a strong Active frame enters action runtime but cannot build a valid
  Clear_JSON/Decision/RuntimePlan completion path, the table transaction must be
  released;
- later streets/new Active signatures must not be blocked by the old
  click_pending/waiting_click lifecycle;
- the Dark_JSON audit must preserve the release reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from display_analysis_cycle import _release_failed_active_finalization_if_needed
from logic.table_action_transaction_gate import TableActionTransactionGate


@dataclass(frozen=True)
class _Decision:
    should_process: bool = True


def _failed_state() -> dict:
    return {
        "frame_id": "table_02_hand_33_flop",
        "runtime_action": {
            "status": "skipped",
            "action_button": {
                "status": "skipped",
                "payload_status": "error",
                "click_points": [],
            },
            "action_runtime_plan_contract": {
                "status": "not_built",
            },
        },
        "clear_json_contract": {
            "status": "validation_failed",
            "reason": "pending_clear_json_contract_validation_failed",
            "publication_stage": "pending",
            "path": None,
        },
        "action_transaction_runtime": {
            "status": "pending",
            "reason": "click_cycle_not_completed",
            "phase": "click_pending",
            "click_completed": False,
            "click_result": {
                "status": "skipped",
                "branch": "action_button",
                "dry_run": False,
                "real_click_enabled": False,
            },
        },
    }


def test_failed_active_finalization_releases_click_pending_transaction() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)
    first = gate.begin_analysis_cycle(table_id="table_02", action_event_id="evt_table_02_a")
    assert first.should_process is True
    action = gate.begin_action_cycle(
        table_id="table_02",
        action_event_id="evt_table_02_a",
        action_signature="sig_a",
    )
    assert action.should_process is True

    runtime_report = gate.finalize_from_runtime(
        table_id="table_02",
        runtime_action={
            "action_button": {
                "status": "skipped",
                "dry_run": False,
                "real_click_enabled": False,
            }
        },
    )
    assert runtime_report["status"] == "pending"
    assert runtime_report["reason"] == "click_cycle_not_completed"
    assert gate.begin_analysis_cycle(table_id="table_02", action_event_id="evt_table_02_blocked").should_process is False

    state = _failed_state()
    release = _release_failed_active_finalization_if_needed(
        state=state,
        table_action_transaction_gate=gate,
        table_id="table_02",
        action_transaction_decision=_Decision(True),
        transaction_runtime_report=runtime_report,
        clear_json_path=None,
    )

    assert isinstance(release, dict)
    assert release["status"] == "FAILED_ACTIVE_FINALIZATION_RELEASED"
    assert release["reason"] == "pending_clear_json_contract_validation_failed"
    assert state["failed_active_finalization_release"]["status"] == "FAILED_ACTIVE_FINALIZATION_RELEASED"
    assert state["action_transaction_runtime"]["status"] == "aborted"
    assert state["action_transaction_runtime"]["reason"] == "failed_active_finalization_released"
    assert state["action_transaction_runtime"]["v4_1_failed_active_finalization_release"]["release_report"]["status"] == "aborted"
    assert state["clear_json_contract"]["v4_1_failed_active_finalization_release"]["status"] == "FAILED_ACTIVE_FINALIZATION_RELEASED"

    second = gate.begin_analysis_cycle(table_id="table_02", action_event_id="evt_table_02_next")
    assert second.should_process is True
    assert second.reason == "new_active_table_analysis_lifecycle_started"


def test_failed_active_finalization_allows_immediate_next_table02_lifecycle() -> None:
    """
    V4.2 synthetic regression for the live hand_33_flop -> next street failure mode.

    Reproduces the lock class without needing the exact poker table scenario:
    - table_02 starts a strong Active action lifecycle;
    - runtime cannot complete because the frame is invalid / runtime plan is not built;
    - V4.1 release hook aborts the impossible transaction;
    - the next table_02 Active lifecycle is accepted immediately and can complete.
    """
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)

    first = gate.begin_analysis_cycle(table_id="table_02", action_event_id="evt_table_02_hand_33_flop")
    assert first.should_process is True
    assert first.reason == "new_active_table_analysis_lifecycle_started"

    first_action = gate.begin_action_cycle(
        table_id="table_02",
        action_event_id="evt_table_02_hand_33_flop",
        action_signature="sig_hand_33_flop",
    )
    assert first_action.should_process is True
    assert first_action.phase == "waiting_click"

    pending_report = gate.finalize_from_runtime(
        table_id="table_02",
        runtime_action={
            "action_button": {
                "status": "skipped",
                "dry_run": False,
                "real_click_enabled": False,
            }
        },
    )
    assert pending_report["status"] == "pending"
    assert pending_report["reason"] == "click_cycle_not_completed"
    assert pending_report["phase"] == "click_pending"

    blocked = gate.begin_analysis_cycle(table_id="table_02", action_event_id="evt_table_02_should_block_before_release")
    assert blocked.should_process is False
    assert blocked.reason == "table_lifecycle_already_open_before_analysis"

    state = _failed_state()
    release = _release_failed_active_finalization_if_needed(
        state=state,
        table_action_transaction_gate=gate,
        table_id="table_02",
        action_transaction_decision=_Decision(True),
        transaction_runtime_report=pending_report,
        clear_json_path=None,
    )
    assert isinstance(release, dict)
    assert release["status"] == "FAILED_ACTIVE_FINALIZATION_RELEASED"

    next_analysis = gate.begin_analysis_cycle(table_id="table_02", action_event_id="evt_table_02_hand_33_turn")
    assert next_analysis.should_process is True
    assert next_analysis.reason == "new_active_table_analysis_lifecycle_started"
    assert next_analysis.locked_by_transaction_id is None

    next_action = gate.begin_action_cycle(
        table_id="table_02",
        action_event_id="evt_table_02_hand_33_turn",
        action_signature="sig_hand_33_turn",
    )
    assert next_action.should_process is True

    completed = gate.finalize_from_runtime(
        table_id="table_02",
        runtime_action={
            "action_button": {
                "status": "dry_run",
                "dry_run": True,
                "real_click_enabled": False,
            }
        },
    )
    assert completed["status"] == "completed"
    assert completed["reason"] == "click_cycle_completed"
    assert completed["click_completed"] is True


def test_completed_runtime_is_not_released() -> None:
    gate = TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)
    gate.begin_analysis_cycle(table_id="table_01", action_event_id="evt_table_01_a")
    gate.begin_action_cycle(table_id="table_01", action_event_id="evt_table_01_a", action_signature="sig_a")
    runtime_report = gate.finalize_from_runtime(
        table_id="table_01",
        runtime_action={
            "action_button": {
                "status": "dry_run",
                "dry_run": True,
                "real_click_enabled": False,
            }
        },
    )
    assert runtime_report["status"] == "completed"

    state = _failed_state()
    release = _release_failed_active_finalization_if_needed(
        state=state,
        table_action_transaction_gate=gate,
        table_id="table_01",
        action_transaction_decision=_Decision(True),
        transaction_runtime_report=runtime_report,
        clear_json_path=None,
    )
    assert release is None


def main() -> int:
    test_failed_active_finalization_releases_click_pending_transaction()
    print("[OK] test_failed_active_finalization_releases_click_pending_transaction")
    test_completed_runtime_is_not_released()
    print("[OK] test_completed_runtime_is_not_released")
    test_failed_active_finalization_allows_immediate_next_table02_lifecycle()
    print("[OK] test_failed_active_finalization_allows_immediate_next_table02_lifecycle")
    print("[RESULT] OK: PokerVision V4.2 failed Active finalization synthetic lifecycle tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
