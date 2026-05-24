r"""
test_live_hand_continuity_unit.py

Unit tests for PokerVision V0.8 live hand continuity logic.
"""

from __future__ import annotations

from display_analysis_cycle import HandIdentityTracker
from logic.live_hand_continuity import (
    board_is_same_or_forward_extension,
    decide_live_hand_continuity,
    normalize_hero_cards_key,
)


def assert_true(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)


def assert_equal(actual: object, expected: object, message: str) -> None:
    if actual != expected:
        raise AssertionError(f"{message}: expected={expected!r}, actual={actual!r}")


def test_board_extension_rules() -> None:
    assert_true(board_is_same_or_forward_extension([], ["5_spades", "K_hearts", "8_hearts"]), "empty board may advance to flop")
    assert_true(board_is_same_or_forward_extension(["5_spades", "K_hearts", "8_hearts"], ["5_spades", "K_hearts", "8_hearts", "4_hearts"]), "flop may advance to turn")
    assert_true(not board_is_same_or_forward_extension(["5_spades", "K_hearts", "8_hearts", "4_hearts"], ["5_spades", "K_hearts", "8_hearts"]), "turn must not go back to flop")


def test_decide_live_hand_continuity_for_uploaded_example() -> None:
    hero = normalize_hero_cards_key(["K_diamonds", "4_diamonds"])
    decision = decide_live_hand_continuity(
        previous_hero_cards_key=hero,
        current_hero_cards_key=hero,
        previous_board_cards=["5_spades", "K_hearts", "8_hearts"],
        current_board_cards=["5_spades", "K_hearts", "8_hearts", "4_hearts", "8_spades"],
        previous_street="flop",
        current_street="river",
    )
    assert_true(decision.should_continue, "flop-to-river same hero/board extension must continue the same hand")


def test_hand_identity_tracker_preserves_hand_across_inactive_gap() -> None:
    tracker = HandIdentityTracker()

    flop = tracker.resolve(
        table_id="table_02",
        active_confirmed=True,
        hero_cards=["K_diamonds", "4_diamonds"],
        street="flop",
        board_cards=["5_spades", "K_hearts", "8_hearts"],
    )

    inactive = tracker.resolve(
        table_id="table_02",
        active_confirmed=False,
        hero_cards=[],
        street=None,
        board_cards=[],
    )
    assert_true(not inactive.active_confirmed, "inactive frame must stay inactive")

    turn = tracker.resolve(
        table_id="table_02",
        active_confirmed=True,
        hero_cards=["K_diamonds", "4_diamonds"],
        street="turn",
        board_cards=["5_spades", "K_hearts", "8_hearts", "4_hearts"],
    )

    river = tracker.resolve(
        table_id="table_02",
        active_confirmed=True,
        hero_cards=["K_diamonds", "4_diamonds"],
        street="river",
        board_cards=["5_spades", "K_hearts", "8_hearts", "4_hearts", "8_spades"],
    )

    assert_equal(turn.hand_id, flop.hand_id, "turn must keep flop hand_id")
    assert_equal(river.hand_id, flop.hand_id, "river must keep flop hand_id")
    assert_true(turn.frame_name.endswith("_turn"), "turn frame_name must use same hand and turn street")
    assert_true(river.frame_name.endswith("_river"), "river frame_name must use same hand and river street")


def test_hand_identity_tracker_starts_new_hand_on_board_mismatch() -> None:
    tracker = HandIdentityTracker()
    first = tracker.resolve(
        table_id="table_02",
        active_confirmed=True,
        hero_cards=["K_diamonds", "4_diamonds"],
        street="flop",
        board_cards=["5_spades", "K_hearts", "8_hearts"],
    )
    second = tracker.resolve(
        table_id="table_02",
        active_confirmed=True,
        hero_cards=["K_diamonds", "4_diamonds"],
        street="flop",
        board_cards=["A_spades", "2_hearts", "3_hearts"],
    )
    assert_true(second.hand_id != first.hand_id, "same hero with incompatible board must start a new hand")


def main() -> None:
    tests = [
        test_board_extension_rules,
        test_decide_live_hand_continuity_for_uploaded_example,
        test_hand_identity_tracker_preserves_hand_across_inactive_gap,
        test_hand_identity_tracker_starts_new_hand_on_board_mismatch,
    ]
    for test in tests:
        test()
        print(f"[OK] {test.__name__}")
    print("[RESULT] OK: Live hand continuity unit tests passed.")


if __name__ == "__main__":
    main()
