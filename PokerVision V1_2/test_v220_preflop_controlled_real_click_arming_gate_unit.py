from __future__ import annotations

"""
test_v220_preflop_controlled_real_click_arming_gate_unit.py

PokerVision Solver V2.2.0 — unit tests for controlled preflop real-click arming gate.
"""

from logic.v22_preflop_controlled_real_click_arming_gate import (
    build_v22_preflop_controlled_real_click_arming_gate,
    validate_v22_preflop_controlled_real_click_arming_gate_report,
)


def _candidate(*, action="fold", allowed_kind="simple_preflop_action", seq=None, table_id="table_01"):
    seq = seq if seq is not None else ["FOLD"]
    return {
        "schema_version": "v214_preflop_real_click_candidate_v1",
        "planned_action": action,
        "allowed_kind": allowed_kind,
        "target_sequence": seq,
        "target_sequences": [seq],
        "runtime_branch": "action_button",
        "dry_run": True,
        "real_click_enabled": False,
        "decision_context": {"street": "preflop", "table_id": table_id},
        "v21_preflight": {
            "ok": True,
            "allowed": True,
            "allowed_kind": allowed_kind,
            "street": "preflop",
            "planned_action": action,
            "target_sequence": seq,
            "real_click_enabled": False,
            "errors": [],
        },
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
    }


def _assert_valid(report):
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)
    assert validation["ok"] is True, validation


def test_blocks_without_explicit_controlled_token():
    report = build_v22_preflop_controlled_real_click_arming_gate(_candidate())
    assert report["ok"] is False
    assert report["armed"] is False
    assert "explicit_controlled_real_click_token_missing" in report["errors"]
    _assert_valid(report)


def test_allows_simple_preflop_candidate_when_all_guards_pass():
    report = build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(),
        required_table_id="table_01",
        slot_bbox_guard_ok=True,
        no_repeat_guard_ok=True,
        button_availability_guard_ok=True,
        export_validator_ok=True,
        explicit_controlled_real_click_token=True,
    )
    assert report["ok"] is True
    assert report["armed"] is True
    assert report["candidate_action"] == "fold"
    assert report["candidate_allowed_kind"] == "simple_preflop_action"
    assert report["candidate_real_click_enabled"] is False
    _assert_valid(report)


def test_allows_preflop_raise_98_candidate_when_all_guards_pass():
    report = build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(action="bet_raise", allowed_kind="preflop_raise_98_sequence", seq=["98%", "Bet/Raise"]),
        required_table_id="table_01",
        explicit_controlled_real_click_token=True,
    )
    assert report["ok"] is True
    assert report["armed"] is True
    assert report["candidate_allowed_kind"] == "preflop_raise_98_sequence"
    assert report["candidate_target_sequence"] == ["98%", "Bet/Raise"]
    _assert_valid(report)


def test_blocks_wrong_raise_sequence():
    report = build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(action="bet_raise", allowed_kind="preflop_raise_98_sequence", seq=["50%", "Bet/Raise"]),
        required_table_id="table_01",
        explicit_controlled_real_click_token=True,
    )
    assert report["ok"] is False
    assert report["armed"] is False
    assert any("raise_sequence_must_be_98_bet_raise" in item for item in report["errors"])
    _assert_valid(report)


def test_blocks_wrong_table():
    report = build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(table_id="table_02"),
        required_table_id="table_01",
        explicit_controlled_real_click_token=True,
    )
    assert report["ok"] is False
    assert report["armed"] is False
    assert "table_id_not_allowed:table_02" in report["errors"]
    _assert_valid(report)


def test_blocks_guard_failures():
    report = build_v22_preflop_controlled_real_click_arming_gate(
        _candidate(),
        required_table_id="table_01",
        slot_bbox_guard_ok=False,
        no_repeat_guard_ok=False,
        button_availability_guard_ok=False,
        explicit_controlled_real_click_token=True,
    )
    assert report["ok"] is False
    assert report["armed"] is False
    assert "slot_bbox_guard_not_ok" in report["errors"]
    assert "no_repeat_guard_not_ok" in report["errors"]
    assert "button_availability_guard_not_ok" in report["errors"]
    _assert_valid(report)


def test_blocks_candidate_with_real_click_already_enabled():
    candidate = _candidate()
    candidate["real_click_enabled"] = True
    report = build_v22_preflop_controlled_real_click_arming_gate(
        candidate,
        required_table_id="table_01",
        explicit_controlled_real_click_token=True,
    )
    assert report["ok"] is False
    assert report["armed"] is False
    assert "candidate_real_click_enabled_must_be_false_before_arming" in report["errors"]
    validation = validate_v22_preflop_controlled_real_click_arming_gate_report(report)
    assert validation["ok"] is False
    assert "candidate_real_click_enabled_true_forbidden" in validation["errors"]


def main() -> None:
    tests = [
        test_blocks_without_explicit_controlled_token,
        test_allows_simple_preflop_candidate_when_all_guards_pass,
        test_allows_preflop_raise_98_candidate_when_all_guards_pass,
        test_blocks_wrong_raise_sequence,
        test_blocks_wrong_table,
        test_blocks_guard_failures,
        test_blocks_candidate_with_real_click_already_enabled,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.2.0 controlled preflop real-click arming gate unit tests passed.")


if __name__ == "__main__":
    main()
