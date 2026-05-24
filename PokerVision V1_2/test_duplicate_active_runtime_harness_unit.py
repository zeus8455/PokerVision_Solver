r"""
test_duplicate_active_runtime_harness_unit.py

PokerVision V2.3 — duplicate Active runtime lifecycle harness.

Purpose:
- Prove at runtime-harness level that the early per-table lifecycle gate blocks
  repeated heavy analysis before detector/pipeline calls.
- Prove that the duplicate block is per-table and does not block other slots.
- Prove that click/dry-run completion releases the slot for the next lifecycle.

This file intentionally does not import YOLO detectors and does not run the real
pipeline. It models the exact gate boundary that display_analysis_cycle.py must
respect before expensive detector stages.

Run directly:
  python test_duplicate_active_runtime_harness_unit.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from logic.table_action_transaction_gate import TableActionTransactionGate


@dataclass
class _RuntimeHarness:
    gate: TableActionTransactionGate = field(
        default_factory=lambda: TableActionTransactionGate(dry_run_counts_as_completed=True, release_on_inactive=True)
    )
    heavy_analysis_calls_by_table: Dict[str, int] = field(default_factory=dict)
    reports: List[dict] = field(default_factory=list)

    def observe_active_before_heavy_analysis(
        self,
        *,
        table_id: str,
        action_event_id: Optional[str] = None,
        action_signature: Optional[str] = None,
    ) -> dict:
        decision = self.gate.begin_analysis_cycle(
            table_id=table_id,
            action_event_id=action_event_id,
            action_signature=action_signature,
        )
        audit = decision.to_json()
        report = {
            "schema_version": "duplicate_active_runtime_harness_v2_3",
            "table_id": table_id,
            "stage": "before_heavy_analysis",
            "table_lifecycle_gate": audit,
            "heavy_analysis_called": False,
            "heavy_analysis_call_count_after": self.heavy_analysis_calls_by_table.get(table_id, 0),
        }

        if decision.should_process:
            self.heavy_analysis_calls_by_table[table_id] = self.heavy_analysis_calls_by_table.get(table_id, 0) + 1
            report["heavy_analysis_called"] = True
            report["heavy_analysis_call_count_after"] = self.heavy_analysis_calls_by_table[table_id]

        self.reports.append(report)
        return report

    def enter_action_runtime(self, *, table_id: str, action_event_id: str, action_signature: str) -> dict:
        decision = self.gate.begin_action_cycle(
            table_id=table_id,
            action_event_id=action_event_id,
            action_signature=action_signature,
        )
        audit = decision.to_json()
        report = {
            "schema_version": "duplicate_active_runtime_harness_v2_3",
            "table_id": table_id,
            "stage": "before_action_runtime",
            "table_lifecycle_gate": audit,
        }
        self.reports.append(report)
        return report

    def finalize_dry_run(self, *, table_id: str, decision_id: str = "decision_01") -> dict:
        report = self.gate.finalize_from_runtime(
            table_id=table_id,
            runtime_action={
                "action_button": {
                    "status": "dry_run",
                    "dry_run": True,
                    "real_click_enabled": False,
                    "guard_passed": True,
                    "solver_action": "fold",
                    "decision_id": decision_id,
                    "message": "v23_duplicate_active_runtime_harness_dry_run",
                }
            },
        )
        self.reports.append({
            "schema_version": "duplicate_active_runtime_harness_v2_3",
            "table_id": table_id,
            "stage": "finalize_runtime",
            "transaction_report": report,
        })
        return report

    def finalize_blocked(self, *, table_id: str, decision_id: str = "decision_blocked") -> dict:
        report = self.gate.finalize_from_runtime(
            table_id=table_id,
            runtime_action={
                "action_button": {
                    "status": "blocked",
                    "dry_run": False,
                    "real_click_enabled": False,
                    "guard_passed": False,
                    "solver_action": "fold",
                    "decision_id": decision_id,
                    "message": "v23_duplicate_active_runtime_harness_blocked",
                }
            },
        )
        self.reports.append({
            "schema_version": "duplicate_active_runtime_harness_v2_3",
            "table_id": table_id,
            "stage": "finalize_runtime",
            "transaction_report": report,
        })
        return report


def _ok(name: str) -> None:
    print(f"[OK] {name}")


def _gate(report: dict) -> dict:
    value = report.get("table_lifecycle_gate")
    assert isinstance(value, dict), "report must contain table_lifecycle_gate"
    return value


def test_runtime_harness_blocks_duplicate_active_before_heavy_analysis() -> None:
    harness = _RuntimeHarness()

    first = harness.observe_active_before_heavy_analysis(
        table_id="table_01",
        action_event_id="evt_table_01_first",
        action_signature="sig_table_01_first",
    )
    assert first["heavy_analysis_called"] is True
    assert first["heavy_analysis_call_count_after"] == 1
    assert _gate(first)["heavy_analysis_allowed"] is True
    assert _gate(first)["heavy_analysis_blocked"] is False
    assert _gate(first)["phase"] == "analyzing"

    duplicate = harness.observe_active_before_heavy_analysis(
        table_id="table_01",
        action_event_id="evt_table_01_duplicate",
        action_signature="sig_table_01_duplicate",
    )
    assert duplicate["heavy_analysis_called"] is False
    assert duplicate["heavy_analysis_call_count_after"] == 1
    assert _gate(duplicate)["heavy_analysis_allowed"] is False
    assert _gate(duplicate)["heavy_analysis_blocked"] is True
    assert _gate(duplicate)["blocked_reason"] == "table_lifecycle_already_open_before_analysis"
    assert _gate(duplicate)["locked_by_transaction_id"] == _gate(first)["transaction_id"]

    _ok("test_runtime_harness_blocks_duplicate_active_before_heavy_analysis")


def test_runtime_harness_blocks_duplicate_active_while_waiting_click() -> None:
    harness = _RuntimeHarness()

    first = harness.observe_active_before_heavy_analysis(table_id="table_01")
    action = harness.enter_action_runtime(
        table_id="table_01",
        action_event_id="evt_table_01_action",
        action_signature="sig_table_01_action",
    )
    assert _gate(action)["phase"] == "waiting_click"

    duplicate = harness.observe_active_before_heavy_analysis(table_id="table_01")
    assert duplicate["heavy_analysis_called"] is False
    assert duplicate["heavy_analysis_call_count_after"] == 1
    assert _gate(duplicate)["heavy_analysis_blocked"] is True
    assert _gate(duplicate)["phase"] == "waiting_click"
    assert _gate(duplicate)["locked_by_transaction_id"] == _gate(first)["transaction_id"]

    _ok("test_runtime_harness_blocks_duplicate_active_while_waiting_click")


def test_runtime_harness_duplicate_block_is_per_table() -> None:
    harness = _RuntimeHarness()

    table_01_first = harness.observe_active_before_heavy_analysis(table_id="table_01")
    table_01_duplicate = harness.observe_active_before_heavy_analysis(table_id="table_01")
    table_02_first = harness.observe_active_before_heavy_analysis(table_id="table_02")

    assert table_01_first["heavy_analysis_called"] is True
    assert table_01_duplicate["heavy_analysis_called"] is False
    assert table_02_first["heavy_analysis_called"] is True
    assert table_02_first["heavy_analysis_call_count_after"] == 1
    assert _gate(table_02_first)["heavy_analysis_allowed"] is True
    assert _gate(table_02_first)["transaction_id"] != _gate(table_01_first)["transaction_id"]

    _ok("test_runtime_harness_duplicate_block_is_per_table")


def test_runtime_harness_completion_releases_for_next_active() -> None:
    harness = _RuntimeHarness()

    first = harness.observe_active_before_heavy_analysis(table_id="table_01")
    harness.enter_action_runtime(
        table_id="table_01",
        action_event_id="evt_table_01_action",
        action_signature="sig_table_01_action",
    )
    completed = harness.finalize_dry_run(table_id="table_01", decision_id="decision_01")
    assert completed["status"] == "completed"
    assert completed["click_completed"] is True

    next_cycle = harness.observe_active_before_heavy_analysis(
        table_id="table_01",
        action_event_id="evt_table_01_next",
        action_signature="sig_table_01_next",
    )
    assert next_cycle["heavy_analysis_called"] is True
    assert next_cycle["heavy_analysis_call_count_after"] == 2
    assert _gate(next_cycle)["heavy_analysis_allowed"] is True
    assert _gate(next_cycle)["transaction_id"] != _gate(first)["transaction_id"]

    _ok("test_runtime_harness_completion_releases_for_next_active")


def test_runtime_harness_blocked_click_keeps_duplicate_active_blocked() -> None:
    harness = _RuntimeHarness()

    first = harness.observe_active_before_heavy_analysis(table_id="table_01")
    harness.enter_action_runtime(
        table_id="table_01",
        action_event_id="evt_table_01_action",
        action_signature="sig_table_01_action",
    )
    failed = harness.finalize_blocked(table_id="table_01")
    assert failed["status"] == "failed"
    assert failed["click_completed"] is False

    duplicate = harness.observe_active_before_heavy_analysis(table_id="table_01")
    assert duplicate["heavy_analysis_called"] is False
    assert duplicate["heavy_analysis_call_count_after"] == 1
    assert _gate(duplicate)["heavy_analysis_blocked"] is True
    assert _gate(duplicate)["phase"] == "click_failed"
    assert _gate(duplicate)["locked_by_transaction_id"] == _gate(first)["transaction_id"]

    release = harness.gate.observe_inactive("table_01")
    assert release is not None
    assert release["status"] == "aborted"

    next_cycle = harness.observe_active_before_heavy_analysis(table_id="table_01")
    assert next_cycle["heavy_analysis_called"] is True
    assert _gate(next_cycle)["heavy_analysis_allowed"] is True

    _ok("test_runtime_harness_blocked_click_keeps_duplicate_active_blocked")


def run_all() -> None:
    tests = [
        test_runtime_harness_blocks_duplicate_active_before_heavy_analysis,
        test_runtime_harness_blocks_duplicate_active_while_waiting_click,
        test_runtime_harness_duplicate_block_is_per_table,
        test_runtime_harness_completion_releases_for_next_active,
        test_runtime_harness_blocked_click_keeps_duplicate_active_blocked,
    ]
    for test in tests:
        test()
    print("[RESULT] OK: PokerVision V2.3 duplicate Active runtime lifecycle harness tests passed.")


if __name__ == "__main__":
    run_all()
