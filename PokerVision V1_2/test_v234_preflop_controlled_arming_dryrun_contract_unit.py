from __future__ import annotations

"""
test_v234_preflop_controlled_arming_dryrun_contract_unit.py

PokerVision Solver V2.3.4 — controlled preflop arming dry-run activation contract.

Purpose:
- Prove the V22 arming gate can mark a preflop candidate as structurally armed.
- Prove this is still diagnostic/dry-run only.
- Prove the arming gate itself does not enable real-click.
"""

from logic.v22_preflop_controlled_real_click_arming_gate import (
    build_v22_preflop_controlled_real_click_arming_gate,
    validate_v22_preflop_controlled_real_click_arming_gate_report,
)


def _preflop_fold_candidate() -> dict:
    return {
        "source": "Solver_Action_Decision_Candidate_JSON",
        "runtime_branch": "action_button",
        "planned_action": "fold",
        "target_sequence": ["FOLD"],
        "real_click_enabled": False,
        "dry_run": True,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "allowed_kind": "simple_preflop_action",
        "table_id": "table_01",
        "decision_context": {
            "street": "preflop",
            "table_id": "table_01",
        },
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": "simple_preflop_action",
            "street": "preflop",
            "real_click_enabled": False,
        },
    }


def _preflop_raise_98_candidate() -> dict:
    return {
        "source": "Solver_Action_Decision_Candidate_JSON",
        "runtime_branch": "action_button",
        "planned_action": "bet_raise",
        "target_sequence": ["98%", "Bet/Raise"],
        "real_click_enabled": False,
        "dry_run": True,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "allowed_kind": "preflop_raise_98_sequence",
        "table_id": "table_01",
        "decision_context": {
            "street": "preflop",
            "table_id": "table_01",
        },
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": "preflop_raise_98_sequence",
            "street": "preflop",
            "real_click_enabled": False,
        },
    }


def _armed_report(candidate: dict) -> dict:
    return build_v22_preflop_controlled_real_click_arming_gate(
        candidate,
        allowed_table_ids=["table_01"],
        slot_bbox_guard_ok=True,
        no_repeat_guard_ok=True,
        button_availability_guard_ok=True,
        export_validator_ok=True,
        explicit_controlled_real_click_token=True,
    )


def test_preflop_fold_can_be_armed_but_not_real_clicked() -> None:
    report = _armed_report(_preflop_fold_candidate())
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["ok"] is True
    assert report["armed"] is True
    assert report["diagnostic_only"] is True
    assert report["does_not_enable_real_click"] is True
    assert report["candidate_real_click_enabled"] is False
    assert report["candidate_allowed_kind"] == "simple_preflop_action"


def test_preflop_raise_98_can_be_armed_but_not_real_clicked() -> None:
    report = _armed_report(_preflop_raise_98_candidate())
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["ok"] is True
    assert report["armed"] is True
    assert report["diagnostic_only"] is True
    assert report["does_not_enable_real_click"] is True
    assert report["candidate_real_click_enabled"] is False
    assert report["candidate_allowed_kind"] == "preflop_raise_98_sequence"
    assert report["candidate_target_sequence"] == ["98%", "Bet/Raise"]


def test_missing_explicit_token_blocks_arming() -> None:
    report = build_v22_preflop_controlled_real_click_arming_gate(
        _preflop_fold_candidate(),
        allowed_table_ids=["table_01"],
        slot_bbox_guard_ok=True,
        no_repeat_guard_ok=True,
        button_availability_guard_ok=True,
        export_validator_ok=True,
        explicit_controlled_real_click_token=False,
    )
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["ok"] is False
    assert report["armed"] is False
    assert "explicit_controlled_real_click_token_missing" in report["errors"]


def run_all() -> None:
    tests = [
        test_preflop_fold_can_be_armed_but_not_real_clicked,
        test_preflop_raise_98_can_be_armed_but_not_real_clicked,
        test_missing_explicit_token_blocks_arming,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.3.4 controlled preflop arming dry-run contract tests passed.")


if __name__ == "__main__":
    run_all()
