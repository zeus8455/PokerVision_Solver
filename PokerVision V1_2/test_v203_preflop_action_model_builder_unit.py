from __future__ import annotations

from logic.preflop_action_model_builder import build_preflop_action_model_from_clear_json
from logic.poker_preflop_context_builder import build_preflop_engine_context
from logic.poker_preflop_solver_preview_builder import build_preflop_context_from_engine_context


def _player(*, hero=False, cards=None, chips=False, fold=False):
    return {
        "hero": bool(hero),
        "cards": cards or [],
        "chips": chips,
        "fold": fold,
        "stack": 100.0,
    }


def _clear(hero_pos="BB", chips=None):
    chips = chips or {}
    players = {
        "UTG": _player(chips=chips.get("UTG", False)),
        "MP": _player(chips=chips.get("MP", False)),
        "CO": _player(chips=chips.get("CO", False)),
        "BTN": _player(chips=chips.get("BTN", False)),
        "SB": _player(chips=chips.get("SB", 0.5)),
        "BB": _player(chips=chips.get("BB", 1.0)),
    }
    players[hero_pos]["hero"] = True
    players[hero_pos]["cards"] = ["A_spades", "K_spades"]

    return {
        "frame_id": "scenario",
        "board": {"street": "preflop", "cards": []},
        "Total_pot": 1.5,
        "players": players,
    }


def test_builds_unopened_from_blinds_only():
    model = build_preflop_action_model_from_clear_json(
        _clear(hero_pos="CO", chips={"SB": 0.5, "BB": 1.0})
    )

    assert model["status"] == "ok"
    assert model["node_type"] == "unopened"
    assert model["opener_pos"] is None
    assert model["three_bettor_pos"] is None
    assert model["four_bettor_pos"] is None
    assert model["actions"] == []


def test_builds_facing_limp_from_one_limper():
    model = build_preflop_action_model_from_clear_json(
        _clear(hero_pos="BTN", chips={"UTG": 1.0, "SB": 0.5, "BB": 1.0})
    )

    assert model["status"] == "ok"
    assert model["node_type"] == "facing_limp"
    assert model["limpers"] == 1
    assert model["actions"] == [{"pos": "UTG", "action": "limp", "amount_bb": 1.0}]


def test_builds_facing_open_from_open_raise():
    model = build_preflop_action_model_from_clear_json(
        _clear(hero_pos="BTN", chips={"UTG": 2.5, "SB": 0.5, "BB": 1.0})
    )

    assert model["status"] == "ok"
    assert model["node_type"] == "facing_open"
    assert model["opener_pos"] == "UTG"
    assert model["three_bettor_pos"] is None
    assert model["actions"] == [{"pos": "UTG", "action": "open_raise", "amount_bb": 2.5}]


def test_builds_facing_open_callers_from_open_and_caller():
    model = build_preflop_action_model_from_clear_json(
        _clear(hero_pos="BTN", chips={"UTG": 2.5, "CO": 2.5, "SB": 0.5, "BB": 1.0})
    )

    assert model["status"] == "ok"
    assert model["node_type"] == "facing_open_callers"
    assert model["opener_pos"] == "UTG"
    assert model["callers"] == 1
    assert {"pos": "CO", "action": "call", "amount_bb": 2.5} in model["actions"]


def test_builds_opener_vs_3bet_when_hero_is_opener():
    model = build_preflop_action_model_from_clear_json(
        _clear(hero_pos="UTG", chips={"UTG": 2.5, "BTN": 8.0, "SB": 0.5, "BB": 1.0})
    )

    assert model["status"] == "ok"
    assert model["node_type"] == "opener_vs_3bet"
    assert model["opener_pos"] == "UTG"
    assert model["three_bettor_pos"] == "BTN"
    assert model["four_bettor_pos"] is None
    assert {"pos": "UTG", "action": "open_raise", "amount_bb": 2.5} in model["actions"]
    assert {"pos": "BTN", "action": "3bet", "amount_bb": 8.0} in model["actions"]

def test_builder_output_integrates_with_engine_context_builder_for_opener_vs_3bet():
    state = _clear(hero_pos="UTG", chips={"UTG": 2.5, "BTN": 8.0, "SB": 0.5, "BB": 1.0})

    model = build_preflop_action_model_from_clear_json(state)
    state["preflop_action_model"] = model

    ctx = build_preflop_engine_context(state)
    preflop_context = build_preflop_context_from_engine_context(ctx)

    assert model["status"] == "ok"
    assert model["node_type"] == "opener_vs_3bet"
    assert model["opener_pos"] == "UTG"
    assert model["three_bettor_pos"] == "BTN"

    assert ctx["status"] == "ok"
    assert ctx["node_type"] == "opener_vs_3bet"
    assert ctx["opener_pos"] == "UTG"
    assert ctx["three_bettor_pos"] == "BTN"
    assert ctx["meta"]["inference_source"] == "preflop_action_model"

    assert preflop_context.node_type == "opener_vs_3bet"
    assert preflop_context.opener_pos == "UTG"
    assert preflop_context.three_bettor_pos == "BTN"

def test_non_preflop_is_skipped():
    state = _clear(hero_pos="BB")
    state["board"] = {"street": "flop", "cards": ["A_spades", "K_hearts", "2_clubs"]}

    model = build_preflop_action_model_from_clear_json(state)

    assert model["status"] == "skipped"
    assert model["reason"] == "not_preflop"


def test_missing_hero_is_error():
    state = _clear(hero_pos="BB")
    state["players"]["BB"]["hero"] = False

    model = build_preflop_action_model_from_clear_json(state)

    assert model["status"] == "error"
    assert model["reason"] == "hero_missing_or_ambiguous"


if __name__ == "__main__":
    tests = [
        test_builds_unopened_from_blinds_only,
        test_builds_facing_limp_from_one_limper,
        test_builds_facing_open_from_open_raise,
        test_builds_facing_open_callers_from_open_and_caller,
        test_builds_opener_vs_3bet_when_hero_is_opener,
        test_builder_output_integrates_with_engine_context_builder_for_opener_vs_3bet,
        test_non_preflop_is_skipped,
        test_missing_hero_is_error,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.0.3 preflop action model builder unit tests passed.")

