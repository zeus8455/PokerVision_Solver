from __future__ import annotations

"""
test_v230_preflop_only_postflop_hard_block_unit.py

PokerVision Solver V2.3.0 — hard block non-preflop arming.

Controlled arming must stay preflop-only:
- preflop can arm only when all explicit/synthetic guards pass
- flop/turn/river/unknown/service must never arm
- real-click must not become enabled by this gate
"""

from logic.v22_preflop_controlled_real_click_arming_gate import (
    build_v22_preflop_controlled_real_click_arming_gate,
    validate_v22_preflop_controlled_real_click_arming_gate_report,
)


def _candidate(street: str) -> dict:
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
            "street": street,
            "table_id": "table_01",
        },
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": "simple_preflop_action",
            "street": street,
            "real_click_enabled": False,
        },
    }


def _build(street: str) -> dict:
    return build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(street),
        allowed_table_ids=["table_01"],
        slot_bbox_guard_ok=True,
        no_repeat_guard_ok=True,
        button_availability_guard_ok=True,
        export_validator_ok=True,
        explicit_controlled_real_click_token=True,
    )


def test_preflop_can_arm_when_all_guards_pass() -> None:
    report = _build("preflop")
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["ok"] is True
    assert report["armed"] is True
    assert report.get("does_not_enable_real_click") is True
    assert report.get("candidate_real_click_enabled") is False


def test_flop_is_hard_blocked() -> None:
    report = _build("flop")
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["armed"] is False
    assert report.get("does_not_enable_real_click") is True
    assert report.get("candidate_real_click_enabled") is False
    assert report.get("reason") in {
        "non_preflop_blocked",
        "v22_arming_gate_blocked",
    }


def test_turn_is_hard_blocked() -> None:
    report = _build("turn")
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["armed"] is False
    assert report.get("does_not_enable_real_click") is True
    assert report.get("candidate_real_click_enabled") is False


def test_river_is_hard_blocked() -> None:
    report = _build("river")
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["armed"] is False
    assert report.get("does_not_enable_real_click") is True
    assert report.get("candidate_real_click_enabled") is False


def test_unknown_is_hard_blocked() -> None:
    report = _build("unknown")
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)

    assert validation["ok"] is True
    assert report["armed"] is False
    assert report.get("does_not_enable_real_click") is True
    assert report.get("candidate_real_click_enabled") is False


def run_all() -> None:
    tests = [
        test_preflop_can_arm_when_all_guards_pass,
        test_flop_is_hard_blocked,
        test_turn_is_hard_blocked,
        test_river_is_hard_blocked,
        test_unknown_is_hard_blocked,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.3.0 preflop-only postflop hard-block tests passed.")


if __name__ == "__main__":
    run_all()
