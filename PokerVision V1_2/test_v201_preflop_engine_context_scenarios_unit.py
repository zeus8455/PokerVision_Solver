from __future__ import annotations

from logic.poker_preflop_context_builder import build_preflop_engine_context
from logic.poker_preflop_solver_preview_builder import build_preflop_context_from_engine_context
from preflop_advisor import describe_all_supported_spots


def _player(cards=None, chips=False, fold=False, hero=False):
    payload = {
        "hero": bool(hero),
        "cards": cards or [],
        "chips": chips,
        "fold": fold,
        "stack": 100.0,
    }
    return payload


def _clear_json(*, frame_id, hero_pos="BB", hero_cards=None, preflop_action_model=None):
    hero_cards = hero_cards or ["A_spades", "K_spades"]

    players = {
        "UTG": _player(chips=False),
        "MP": _player(chips=False),
        "CO": _player(chips=False),
        "BTN": _player(chips=False),
        "SB": _player(chips=0.5),
        "BB": _player(cards=hero_cards if hero_pos == "BB" else [], chips=1.0, hero=(hero_pos == "BB")),
    }

    if hero_pos != "BB":
        players["BB"]["cards"] = []
        players[hero_pos]["cards"] = hero_cards
        players[hero_pos]["hero"] = True

    state = {
        "frame_id": frame_id,
        "board": {"street": "preflop", "cards": []},
        "Total_pot": 1.5,
        "players": players,
    }

    if preflop_action_model is not None:
        state["preflop_action_model"] = preflop_action_model

    return state


def _assert_context(ctx, *, node_type, hero_pos, opener_pos=None, three_bettor_pos=None, four_bettor_pos=None, limpers=0, callers=0):
    assert ctx["status"] == "ok", ctx
    assert ctx["context_type"] == "PreflopContext"
    assert ctx["street"] == "preflop"
    assert ctx["node_type"] == node_type
    assert ctx["hero_pos"] == hero_pos
    assert ctx["opener_pos"] == opener_pos
    assert ctx["three_bettor_pos"] == three_bettor_pos
    assert ctx["four_bettor_pos"] == four_bettor_pos
    assert ctx["limpers"] == limpers
    assert ctx["callers"] == callers
    assert ctx["meta"]["inference_source"] == "preflop_action_model"

    preflop_context = build_preflop_context_from_engine_context(ctx)
    assert preflop_context.node_type == node_type
    assert preflop_context.hero_pos == hero_pos
    assert preflop_context.opener_pos == opener_pos
    assert preflop_context.three_bettor_pos == three_bettor_pos
    assert preflop_context.four_bettor_pos == four_bettor_pos
    assert preflop_context.limpers == limpers
    assert preflop_context.callers == callers


def test_engine_supported_spots_include_required_advanced_preflop_nodes():
    text = "\n".join(describe_all_supported_spots())

    required = [
        "unopened",
        "facing_limp",
        "bb_vs_sb_limp",
        "facing_open",
        "facing_open_callers",
        "opener_vs_3bet",
        "threebettor_vs_4bet",
        "cold_4bet",
    ]

    for node_type in required:
        assert node_type in text


def test_preflop_action_model_builds_unopened_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_unopened",
            hero_pos="CO",
            preflop_action_model={
                "node_type": "unopened",
                "opener_pos": None,
                "three_bettor_pos": None,
                "four_bettor_pos": None,
                "limpers": 0,
                "callers": 0,
                "actions": [],
            },
        )
    )

    _assert_context(ctx, node_type="unopened", hero_pos="CO")


def test_preflop_action_model_builds_facing_limp_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_facing_limp",
            hero_pos="BTN",
            preflop_action_model={
                "node_type": "facing_limp",
                "limpers": 1,
                "callers": 0,
                "actions": [{"pos": "UTG", "action": "limp", "amount_bb": 1.0}],
            },
        )
    )

    _assert_context(ctx, node_type="facing_limp", hero_pos="BTN", limpers=1)


def test_preflop_action_model_builds_facing_open_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_facing_open",
            hero_pos="BTN",
            preflop_action_model={
                "node_type": "facing_open",
                "opener_pos": "UTG",
                "limpers": 0,
                "callers": 0,
                "actions": [{"pos": "UTG", "action": "open_raise", "amount_bb": 2.5}],
            },
        )
    )

    _assert_context(ctx, node_type="facing_open", hero_pos="BTN", opener_pos="UTG")


def test_preflop_action_model_builds_facing_open_callers_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_facing_open_callers",
            hero_pos="BTN",
            preflop_action_model={
                "node_type": "facing_open_callers",
                "opener_pos": "UTG",
                "limpers": 0,
                "callers": 1,
                "actions": [
                    {"pos": "UTG", "action": "open_raise", "amount_bb": 2.5},
                    {"pos": "CO", "action": "call", "amount_bb": 2.5},
                ],
            },
        )
    )

    _assert_context(ctx, node_type="facing_open_callers", hero_pos="BTN", opener_pos="UTG", callers=1)


def test_preflop_action_model_builds_opener_vs_3bet_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_opener_vs_3bet",
            hero_pos="UTG",
            preflop_action_model={
                "node_type": "opener_vs_3bet",
                "opener_pos": "UTG",
                "three_bettor_pos": "BTN",
                "limpers": 0,
                "callers": 0,
                "actions": [
                    {"pos": "UTG", "action": "open_raise", "amount_bb": 2.5},
                    {"pos": "BTN", "action": "3bet", "amount_bb": 8.0},
                ],
            },
        )
    )

    _assert_context(ctx, node_type="opener_vs_3bet", hero_pos="UTG", opener_pos="UTG", three_bettor_pos="BTN")


def test_preflop_action_model_builds_threebettor_vs_4bet_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_threebettor_vs_4bet",
            hero_pos="BTN",
            preflop_action_model={
                "node_type": "threebettor_vs_4bet",
                "opener_pos": "UTG",
                "three_bettor_pos": "BTN",
                "four_bettor_pos": "UTG",
                "limpers": 0,
                "callers": 0,
                "actions": [
                    {"pos": "UTG", "action": "open_raise", "amount_bb": 2.5},
                    {"pos": "BTN", "action": "3bet", "amount_bb": 8.0},
                    {"pos": "UTG", "action": "4bet", "amount_bb": 22.0},
                ],
            },
        )
    )

    _assert_context(
        ctx,
        node_type="threebettor_vs_4bet",
        hero_pos="BTN",
        opener_pos="UTG",
        three_bettor_pos="BTN",
        four_bettor_pos="UTG",
    )


def test_preflop_action_model_builds_cold_4bet_context():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_cold_4bet",
            hero_pos="SB",
            preflop_action_model={
                "node_type": "cold_4bet",
                "opener_pos": "UTG",
                "three_bettor_pos": "BTN",
                "four_bettor_pos": "SB",
                "limpers": 0,
                "callers": 0,
                "actions": [
                    {"pos": "UTG", "action": "open_raise", "amount_bb": 2.5},
                    {"pos": "BTN", "action": "3bet", "amount_bb": 8.0},
                    {"pos": "SB", "action": "cold_4bet", "amount_bb": 22.0},
                ],
            },
        )
    )

    _assert_context(
        ctx,
        node_type="cold_4bet",
        hero_pos="SB",
        opener_pos="UTG",
        three_bettor_pos="BTN",
        four_bettor_pos="SB",
    )


def test_action_model_builder_default_path_does_not_claim_advanced_3bet_without_raise_data():
    ctx = build_preflop_engine_context(
        _clear_json(
            frame_id="scenario_players_chips_fallback_current_limit",
            hero_pos="UTG",
            preflop_action_model=None,
        )
    )

    assert ctx["status"] == "ok", ctx
    assert ctx["meta"]["inference_source"] == "preflop_action_model_builder"
    assert ctx["node_type"] in {"unopened", "facing_limp", "facing_open", "facing_open_callers"}
    assert ctx["three_bettor_pos"] is None
    assert ctx["four_bettor_pos"] is None


if __name__ == "__main__":
    tests = [
        test_engine_supported_spots_include_required_advanced_preflop_nodes,
        test_preflop_action_model_builds_unopened_context,
        test_preflop_action_model_builds_facing_limp_context,
        test_preflop_action_model_builds_facing_open_context,
        test_preflop_action_model_builds_facing_open_callers_context,
        test_preflop_action_model_builds_opener_vs_3bet_context,
        test_preflop_action_model_builds_threebettor_vs_4bet_context,
        test_preflop_action_model_builds_cold_4bet_context,
        test_action_model_builder_default_path_does_not_claim_advanced_3bet_without_raise_data,
    ]

    for test in tests:
        test()
        print(f"[OK] {test.__name__}")

    print("[RESULT] OK: V2.0.2 preflop engine context scenario tests passed.")
