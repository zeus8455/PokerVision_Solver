"""
test_v71_multi_table_ordered_service_first_contract_unit.py

PokerVision V7.1 — multi-table ordered service-first contract.

Contract:
- service branch is evaluated before Active/poker branch per table/frame.
- actionable service result stops poker branch only for its own table.
- passive service result such as detected_only/Remove_Table does not stop poker branch.
- tables remain isolated: table_01 service action must not block table_02 Active.
"""

from __future__ import annotations

import display_analysis_cycle as dac


def _service_report(status: str, *, target_class: str | None = None, frame_finished: bool = False, skip_action: bool = False) -> dict:
    return {
        "service_click": {
            "status": status,
            "target_class": target_class,
            "target_sequence": [target_class] if target_class else [],
            "frame_finished": frame_finished,
            "skip_action_button_runtime": skip_action,
            "click_points": [{"class_name": target_class}] if status in {"dry_run", "clicked"} and target_class else [],
            "dry_run": status == "dry_run",
            "real_click_enabled": False,
        }
    }


def _ordered_branch_decision(*, table_id: str, service_report: dict, active_detected: bool) -> dict:
    service_stops = dac._should_service_stop_poker_branch(service_report)

    if service_stops:
        return {
            "table_id": table_id,
            "branch": "service",
            "poker_analysis_allowed": False,
            "action_button_allowed": False,
            "service_stops": True,
        }

    if active_detected:
        return {
            "table_id": table_id,
            "branch": "active",
            "poker_analysis_allowed": True,
            "action_button_allowed": True,
            "service_stops": False,
        }

    return {
        "table_id": table_id,
        "branch": "skip",
        "poker_analysis_allowed": False,
        "action_button_allowed": False,
        "service_stops": False,
    }


def test_service_action_stops_only_its_own_table() -> None:
    table_01 = _ordered_branch_decision(
        table_id="table_01",
        service_report=_service_report("dry_run", target_class="Exit_cashOut"),
        active_detected=True,
    )
    table_02 = _ordered_branch_decision(
        table_id="table_02",
        service_report=_service_report("skipped"),
        active_detected=True,
    )

    assert table_01["branch"] == "service"
    assert table_01["poker_analysis_allowed"] is False
    assert table_01["action_button_allowed"] is False

    assert table_02["branch"] == "active"
    assert table_02["poker_analysis_allowed"] is True
    assert table_02["action_button_allowed"] is True


def test_detected_only_remove_table_does_not_stop_active_branch() -> None:
    table_03 = _ordered_branch_decision(
        table_id="table_03",
        service_report=_service_report("detected_only", target_class="Remove_Table"),
        active_detected=True,
    )

    assert table_03["branch"] == "active"
    assert table_03["service_stops"] is False
    assert table_03["poker_analysis_allowed"] is True


def test_confirmed_service_stops_without_click_points() -> None:
    table_04 = _ordered_branch_decision(
        table_id="table_04",
        service_report=_service_report("confirmed", target_class=None, frame_finished=True, skip_action=True),
        active_detected=True,
    )

    assert table_04["branch"] == "service"
    assert table_04["service_stops"] is True
    assert table_04["poker_analysis_allowed"] is False
    assert table_04["action_button_allowed"] is False


def test_mixed_six_table_ordered_cycle_contract() -> None:
    decisions = {
        "table_01": _ordered_branch_decision(
            table_id="table_01",
            service_report=_service_report("dry_run", target_class="Exit_cashOut"),
            active_detected=True,
        ),
        "table_02": _ordered_branch_decision(
            table_id="table_02",
            service_report=_service_report("skipped"),
            active_detected=True,
        ),
        "table_03": _ordered_branch_decision(
            table_id="table_03",
            service_report=_service_report("detected_only", target_class="Remove_Table"),
            active_detected=True,
        ),
        "table_04": _ordered_branch_decision(
            table_id="table_04",
            service_report=_service_report("confirmed", frame_finished=True, skip_action=True),
            active_detected=True,
        ),
        "table_05": _ordered_branch_decision(
            table_id="table_05",
            service_report=_service_report("blocked", target_class="Non_active_fold"),
            active_detected=False,
        ),
        "table_06": _ordered_branch_decision(
            table_id="table_06",
            service_report=_service_report("skipped"),
            active_detected=False,
        ),
    }

    assert decisions["table_01"]["branch"] == "service"
    assert decisions["table_02"]["branch"] == "active"
    assert decisions["table_03"]["branch"] == "active"
    assert decisions["table_04"]["branch"] == "service"
    assert decisions["table_05"]["branch"] == "skip"
    assert decisions["table_06"]["branch"] == "skip"

    assert decisions["table_01"]["table_id"] == "table_01"
    assert decisions["table_02"]["table_id"] == "table_02"
    assert decisions["table_03"]["table_id"] == "table_03"
    assert decisions["table_04"]["table_id"] == "table_04"
    assert decisions["table_05"]["table_id"] == "table_05"
    assert decisions["table_06"]["table_id"] == "table_06"


def run_all() -> None:
    tests = [
        test_service_action_stops_only_its_own_table,
        test_detected_only_remove_table_does_not_stop_active_branch,
        test_confirmed_service_stops_without_click_points,
        test_mixed_six_table_ordered_cycle_contract,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: PokerVision V7.1 multi-table ordered service-first contract tests passed.")


if __name__ == "__main__":
    run_all()
