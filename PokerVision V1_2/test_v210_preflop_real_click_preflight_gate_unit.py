from __future__ import annotations

"""
test_v210_preflop_real_click_preflight_gate_unit.py

PokerVision Solver V2.1.0 — preflop-only real-click preflight gate unit tests.
"""

from logic.v21_preflop_real_click_preflight_gate import (
    build_v21_preflop_real_click_preflight_gate,
    validate_v21_preflop_real_click_preflight_gate_report,
)


def _plan(action="fold", *, street="preflop", source="Solver_Action_Decision_Candidate_JSON", seq=None, real_click_enabled=False):
    if seq is None:
        if action == "fold":
            seq = ["FOLD"]
        elif action == "call":
            seq = ["Call"]
        elif action == "check":
            seq = ["Check"]
        elif action == "check_fold":
            seq = ["Check"]
        elif action == "bet_raise":
            seq = ["98%", "Bet/Raise"]
        else:
            seq = []

    return {
        "schema_version": "solver_action_runtime_plan_candidate_v1",
        "source": source,
        "status": "ok",
        "planned_action": action,
        "target_sequence": list(seq),
        "target_sequences": [list(seq)] if seq else [],
        "runtime_branch": "action_button",
        "dry_run_required": True,
        "dry_run": True,
        "real_click_enabled": bool(real_click_enabled),
        "solver_stub": False,
        "diagnostic_candidate": True,
        "does_not_replace_runtime_plan": True,
        "does_not_enable_real_click": True,
        "decision_context": {
            "street": street,
            "hero_position": "BB",
            "source_frame_id": "v210_unit",
        },
    }


def _assert_valid_report(report):
    validation = validate_v21_preflop_real_click_preflight_gate_report(report)
    assert validation["ok"], validation


def test_allows_simple_preflop_actions():
    for action in ["fold", "call", "check", "check_fold"]:
        report = build_v21_preflop_real_click_preflight_gate(_plan(action))
        _assert_valid_report(report)

        assert report["ok"] is True
        assert report["allowed"] is True
        assert report["allowed_kind"] == "simple_preflop_action"
        assert report["real_click_enabled"] is False


def test_allows_preflop_raise_98_sequence_dryrun_only():
    report = build_v21_preflop_real_click_preflight_gate(
        _plan("bet_raise", seq=["98%", "Bet/Raise"])
    )
    _assert_valid_report(report)

    assert report["ok"] is True
    assert report["allowed"] is True
    assert report["allowed_kind"] == "preflop_raise_98_sequence"
    assert report["target_sequence"] == ["98%", "Bet/Raise"]
    assert report["real_click_enabled"] is False


def test_blocks_postflop_raise():
    report = build_v21_preflop_real_click_preflight_gate(
        _plan("bet_raise", street="flop", seq=["98%", "Bet/Raise"])
    )
    validation = validate_v21_preflop_real_click_preflight_gate_report(report)

    assert validation["ok"], validation
    assert report["ok"] is False
    assert report["allowed"] is False
    assert any("street must be preflop" in err for err in report["errors"])


def test_blocks_real_click_enabled_even_for_preflop_raise():
    report = build_v21_preflop_real_click_preflight_gate(
        _plan("bet_raise", seq=["98%", "Bet/Raise"], real_click_enabled=True)
    )
    validation = validate_v21_preflop_real_click_preflight_gate_report(report)

    assert validation["ok"] is False
    assert report["ok"] is False
    assert report["allowed"] is False
    assert any("real_click_enabled must remain False" in err for err in report["errors"])


def test_blocks_wrong_raise_sequence():
    report = build_v21_preflop_real_click_preflight_gate(
        _plan("bet_raise", seq=["Bet/Raise"])
    )
    validation = validate_v21_preflop_real_click_preflight_gate_report(report)

    assert validation["ok"], validation
    assert report["ok"] is False
    assert any("preflop raise target_sequence" in err for err in report["errors"])


def test_blocks_raise_from_action_decision_source():
    report = build_v21_preflop_real_click_preflight_gate(
        _plan("bet_raise", source="Action_Decision_JSON", seq=["98%", "Bet/Raise"])
    )
    validation = validate_v21_preflop_real_click_preflight_gate_report(report)

    assert validation["ok"], validation
    assert report["ok"] is False
    assert any("requires Solver_Action_Decision_Candidate_JSON source" in err for err in report["errors"])


def main() -> None:
    tests = [
        test_allows_simple_preflop_actions,
        test_allows_preflop_raise_98_sequence_dryrun_only,
        test_blocks_postflop_raise,
        test_blocks_real_click_enabled_even_for_preflop_raise,
        test_blocks_wrong_raise_sequence,
        test_blocks_raise_from_action_decision_source,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.1.0 preflop real-click preflight gate unit tests passed.")


if __name__ == "__main__":
    main()
