r"""
test_clear_json_recovery_unit.py

Small unit tests for PokerVision Clear_JSON recovery rules.
Run from project root:
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe .\test_clear_json_recovery_unit.py
"""

from __future__ import annotations

from logic.clear_json_recovery import recover_clear_json_state


def _base_previous():
    return {
        "frame_id": "table_01_hand_01_flop_01",
        "board": {"cards": ["5_diamonds", "K_spades", "A_clubs"], "street": "flop"},
        "Total_pot": 4.5,
        "players": {
            "SB": {"hero": True, "cards": ["A_spades", "9_clubs"], "stack": 26.0, "fold": False, "chips": 0.5},
            "BB": {"stack": 100.5, "fold": False, "chips": 1.0},
            "CO": {"stack": 108.0, "fold": True, "chips": False},
        },
    }


def test_chips_are_not_recovered() -> None:
    previous = _base_previous()
    current = {
        "frame_id": "table_01_hand_01_flop_02",
        "board": {"cards": ["5_diamonds", "K_spades", "A_clubs"], "street": "flop"},
        "Total_pot": 4.5,
        "players": {"BB": {"stack": 100.5, "fold": False}},
    }
    recovered, report = recover_clear_json_state(current, previous)
    assert recovered["players"]["BB"]["chips"] is False, report


def test_stack_and_fold_are_recovered() -> None:
    previous = _base_previous()
    current = {
        "frame_id": "table_01_hand_01_flop_02",
        "board": {"cards": ["5_diamonds", "K_spades", "A_clubs"], "street": "flop"},
        "Total_pot": 4.5,
        "players": {"CO": {"stack": None, "fold": False, "chips": False}},
    }
    recovered, report = recover_clear_json_state(current, previous)
    assert recovered["players"]["CO"]["stack"] == 108.0, report
    assert recovered["players"]["CO"]["fold"] is True, report


def test_hero_recovered_when_board_continuation_is_confirmed() -> None:
    previous = _base_previous()
    current = {
        "frame_id": "table_01_hand_01_turn_01",
        "board": {"cards": ["5_diamonds", "K_spades", "A_clubs", "2_hearts"], "street": "turn"},
        "Total_pot": 8.5,
        "players": {
            "SB": {"stack": 25.0, "fold": False, "chips": False},
            "BB": {"stack": 100.5, "fold": False, "chips": False},
        },
    }
    recovered, report = recover_clear_json_state(current, previous)
    hero = recovered["players"]["SB"]
    assert hero["hero"] is True, report
    assert hero["cards"] == ["A_spades", "9_clubs"], report


def test_hero_not_recovered_without_same_hand_proof() -> None:
    previous = _base_previous()
    current = {
        "frame_id": "table_01_hand_01_flop_02",
        "board": {"cards": ["2_diamonds", "3_spades", "4_clubs"], "street": "flop"},
        "Total_pot": 4.5,
        "players": {"SB": {"stack": 25.0, "fold": False, "chips": False}},
    }
    recovered, report = recover_clear_json_state(current, previous)
    assert "hero" not in recovered["players"]["SB"], report
    assert "cards" not in recovered["players"]["SB"], report


def main() -> int:
    tests = [
        test_chips_are_not_recovered,
        test_stack_and_fold_are_recovered,
        test_hero_recovered_when_board_continuation_is_confirmed,
        test_hero_not_recovered_without_same_hand_proof,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Clear_JSON recovery unit tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
