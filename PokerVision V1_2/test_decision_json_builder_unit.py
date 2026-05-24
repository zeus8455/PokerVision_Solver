"""
test_decision_json_builder_unit.py

PokerVision V0.5 — unit tests for Clear_JSON -> Decision_JSON builder.
"""

from __future__ import annotations

from logic.decision_json_builder import (
    build_decision_json_from_clear_state,
    validate_decision_json_contract,
)


def _sample_clear_json():
    return {
        "frame_id": "table_01_hand_01_preflop_01",
        "board": {"cards": [], "street": "preflop"},
        "Total_pot": 4.0,
        "players": {
            "BB": {
                "hero": True,
                "cards": ["Q_spades", "3_diamonds"],
                "stack": 59.0,
                "fold": False,
                "chips": 1.0,
            },
            "SB": {"stack": 155.0, "fold": True, "chips": 0.5},
            "CO": {"stack": 119.0, "fold": False, "chips": 2.5},
        },
    }


def test_decision_json_built_from_clear_json_only() -> None:
    clear_json = _sample_clear_json()
    decision = build_decision_json_from_clear_state(clear_json)
    validation = validate_decision_json_contract(decision)
    assert validation["ok"], validation
    assert decision["source"] == "Clear_JSON"
    assert decision["source_frame_id"] == clear_json["frame_id"]
    assert decision["street"] == "preflop"
    assert decision["hero"]["position"] == "BB"
    assert decision["hero"]["cards"] == ["Q_spades", "3_diamonds"]
    assert "SB" in decision["players"]
    assert "CO" in decision["players"]
    assert "click_result" not in decision
    assert "runtime_action" not in decision


def test_click_result_is_ignored_as_solver_input() -> None:
    clear_json = _sample_clear_json()
    clear_json["click_result"] = {
        "status": "dry_run",
        "branch": "action_button",
        "action": "fold",
        "size_pct": None,
        "dry_run": True,
        "real_click_enabled": False,
        "guard_passed": True,
        "decision_id": "unit_test_decision",
        "message": "unit test",
    }
    decision = build_decision_json_from_clear_state(clear_json)
    validation = validate_decision_json_contract(decision)
    assert validation["ok"], validation
    assert "click_result" not in decision


def test_invalid_clear_json_is_rejected() -> None:
    clear_json = _sample_clear_json()
    clear_json["players"]["BB"].pop("cards")
    try:
        build_decision_json_from_clear_state(clear_json)
    except ValueError as exc:
        assert "Clear_JSON is not valid" in str(exc)
    else:
        raise AssertionError("invalid Clear_JSON must not produce Decision_JSON")


def run() -> None:
    tests = [
        test_decision_json_built_from_clear_json_only,
        test_click_result_is_ignored_as_solver_input,
        test_invalid_clear_json_is_rejected,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Decision_JSON builder unit tests passed.")


if __name__ == "__main__":
    run()
