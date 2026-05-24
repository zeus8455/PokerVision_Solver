"""
test_action_decision_stub_unit.py

Unit tests for PokerVision V0.6 Action_Decision_JSON stub contract.
"""

from __future__ import annotations

from logic.action_decision_stub import (
    build_action_decision_from_decision_json,
    validate_action_decision_contract,
)


def _sample_decision_json() -> dict:
    return {
        "schema_version": "decision_json_v1",
        "source": "Clear_JSON",
        "source_frame_id": "table_01_hand_01_preflop_01",
        "street": "preflop",
        "board": [],
        "total_pot": 4.0,
        "hero": {
            "position": "BB",
            "cards": ["A_spades", "K_hearts"],
            "stack": 99.0,
            "chips": 1.0,
        },
        "players": {
            "SB": {"stack": 100.0, "fold": False, "chips": 0.5},
            "BTN": {"stack": 88.0, "fold": True, "chips": False},
        },
        "active_positions": ["BB", "SB"],
        "folded_positions": ["BTN"],
        "decision_context": {
            "is_preflop": True,
            "is_postflop": False,
            "players_total": 3,
            "active_players_total": 2,
            "folded_players_total": 1,
        },
    }


def test_action_decision_built_from_decision_json_only() -> None:
    action = build_action_decision_from_decision_json(_sample_decision_json())
    validation = validate_action_decision_contract(action)
    assert validation["ok"], validation
    assert action["source"] == "Decision_JSON"
    assert action["source_decision_frame_id"] == "table_01_hand_01_preflop_01"
    assert action["action"] == "check_fold"
    assert action["target_button_classes"] == ["Check", "Check/fold", "FOLD"]
    forbidden = {"runtime_action", "click_result", "trigger_ui", "table_structure", "bbox", "confidence"}
    assert not (forbidden & set(action.keys()))


def test_invalid_decision_json_is_rejected() -> None:
    bad = _sample_decision_json()
    bad["hero"]["cards"] = ["A_spades"]
    try:
        build_action_decision_from_decision_json(bad)
    except ValueError as exc:
        assert "Decision_JSON is not valid" in str(exc)
    else:
        raise AssertionError("invalid Decision_JSON was accepted")


def test_action_decision_rejects_runtime_pollution() -> None:
    action = build_action_decision_from_decision_json(_sample_decision_json())
    action["runtime_action"] = {"status": "clicked"}
    validation = validate_action_decision_contract(action)
    assert not validation["ok"]
    assert any("forbidden" in msg for msg in validation["errors"])


def main() -> None:
    tests = [
        test_action_decision_built_from_decision_json_only,
        test_invalid_decision_json_is_rejected,
        test_action_decision_rejects_runtime_pollution,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Action_Decision_JSON stub unit tests passed.")


if __name__ == "__main__":
    main()
