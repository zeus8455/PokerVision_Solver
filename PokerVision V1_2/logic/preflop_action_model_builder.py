from __future__ import annotations

"""
logic/preflop_action_model_builder.py

PokerVision Solver V2.0.3 — build preflop_action_model from Clear_JSON.players chips.

This module does not call the solver and does not click.
It converts a Clear_JSON-like table state into the explicit preflop_action_model
already accepted by logic.poker_preflop_context_builder.build_preflop_engine_context(...).

V2.0.3 initial scope:
- unopened
- facing_limp
- facing_open
- facing_open_callers
- opener_vs_3bet

Later scope:
- threebettor_vs_4bet
- cold_4bet
- 5bet / jam candidates
"""

from typing import Any, Dict, List, Optional, Tuple


POSITIONS = ["UTG", "MP", "CO", "BTN", "SB", "BB"]
BLIND_AMOUNTS = {"SB": 0.5, "BB": 1.0}


def _amount(value: Any) -> float:
    if value is False or value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _is_active_player(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return False
    if payload.get("fold") is True:
        return False
    return True


def _ordered_positions(players: Dict[str, Any]) -> List[str]:
    return [pos for pos in POSITIONS if pos in players]


def _find_hero_pos(players: Dict[str, Any]) -> Optional[str]:
    heroes = []
    for pos, payload in players.items():
        if isinstance(payload, dict) and payload.get("hero") is True:
            heroes.append(str(pos))
    return heroes[0] if len(heroes) == 1 else None


def _positions_before_hero(hero_pos: str, positions: List[str]) -> List[str]:
    if hero_pos not in positions:
        return []
    return positions[:positions.index(hero_pos)]


def _meaningful_preflop_contributions(
    *,
    players: Dict[str, Any],
    positions: List[str],
    hero_pos: str,
) -> List[Tuple[str, float]]:
    """Return active visible preflop contributions, excluding forced blinds.

    Important:
    - This is a single-frame reconstruction helper.
    - It does not claim hand-level reconciliation.
    - HERO contribution is included because HERO can be opener facing a later 3bet.
    - Contributions after HERO are included because they may represent 3bet/4bet pressure.
    - SB=0.5 and BB=1.0 are treated as forced blinds, not limp/open.
    """

    out: List[Tuple[str, float]] = []

    for pos in positions:
        payload = players.get(pos) or {}
        if not _is_active_player(payload):
            continue

        chips = _amount(payload.get("chips"))

        if chips <= 0:
            continue

        if pos in BLIND_AMOUNTS and chips <= BLIND_AMOUNTS[pos]:
            continue

        out.append((pos, chips))

    return out


def build_preflop_action_model_from_clear_json(clear_json: Dict[str, Any]) -> Dict[str, Any]:
    """Build an explicit preflop_action_model from Clear_JSON-like state.

    The output is intentionally compatible with _build_from_action_model(...)
    in logic.poker_preflop_context_builder.
    """

    board = clear_json.get("board") if isinstance(clear_json.get("board"), dict) else {}
    street = board.get("street")
    cards = board.get("cards") or []

    if street != "preflop" or cards:
        return {
            "status": "skipped",
            "reason": "not_preflop",
            "node_type": None,
            "opener_pos": None,
            "three_bettor_pos": None,
            "four_bettor_pos": None,
            "limpers": 0,
            "callers": 0,
            "actions": [],
            "meta": {"builder": "preflop_action_model_builder_v1"},
        }

    players = clear_json.get("players") if isinstance(clear_json.get("players"), dict) else {}
    positions = _ordered_positions(players)
    hero_pos = _find_hero_pos(players)

    if not hero_pos:
        return {
            "status": "error",
            "reason": "hero_missing_or_ambiguous",
            "node_type": None,
            "opener_pos": None,
            "three_bettor_pos": None,
            "four_bettor_pos": None,
            "limpers": 0,
            "callers": 0,
            "actions": [],
            "meta": {"builder": "preflop_action_model_builder_v1"},
        }

    contributions = _meaningful_preflop_contributions(
        players=players,
        positions=positions,
        hero_pos=hero_pos,
    )

    if not contributions:
        return {
            "status": "ok",
            "node_type": "unopened",
            "opener_pos": None,
            "three_bettor_pos": None,
            "four_bettor_pos": None,
            "limpers": 0,
            "callers": 0,
            "actions": [],
            "meta": {
                "builder": "preflop_action_model_builder_v1",
                "inference_source": "players_chips_single_frame",
                "hero_pos": hero_pos,
            },
        }

    limpers = [(pos, amount) for pos, amount in contributions if amount == 1.0]
    raises = [(pos, amount) for pos, amount in contributions if amount > 1.0]

    if raises:
        opener_pos, open_amount = raises[0]
        three_bettor_pos = None
        threebet_amount = None

        callers = 0
        actions: List[Dict[str, Any]] = [
            {"pos": opener_pos, "action": "open_raise", "amount_bb": open_amount}
        ]

        four_bettor_pos = None
        fourbet_amount = None

        for pos, amount in contributions:
            if pos == opener_pos:
                continue
            if amount == open_amount:
                callers += 1
                actions.append({"pos": pos, "action": "call", "amount_bb": amount})
            elif amount > open_amount and three_bettor_pos is None:
                three_bettor_pos = pos
                threebet_amount = amount
            elif three_bettor_pos is not None and amount > float(threebet_amount or 0.0) and four_bettor_pos is None:
                four_bettor_pos = pos
                fourbet_amount = amount

        if three_bettor_pos and four_bettor_pos:
            action_name = "cold_4bet" if four_bettor_pos not in {opener_pos, three_bettor_pos} else "4bet"
            actions.append({"pos": three_bettor_pos, "action": "3bet", "amount_bb": threebet_amount})
            actions.append({"pos": four_bettor_pos, "action": action_name, "amount_bb": fourbet_amount})

            if hero_pos == three_bettor_pos:
                node_type = "threebettor_vs_4bet"
            elif hero_pos == four_bettor_pos and four_bettor_pos not in {opener_pos, three_bettor_pos}:
                node_type = "cold_4bet"
            elif hero_pos == opener_pos:
                node_type = "opener_vs_3bet"
            else:
                node_type = "facing_open"

            return {
                "status": "ok",
                "node_type": node_type,
                "opener_pos": opener_pos,
                "three_bettor_pos": three_bettor_pos,
                "four_bettor_pos": four_bettor_pos,
                "limpers": 0,
                "callers": callers,
                "actions": actions,
                "meta": {
                    "builder": "preflop_action_model_builder_v1",
                    "inference_source": "players_chips_single_frame",
                    "hero_pos": hero_pos,
                    "scope": "v2_0_5_4bet_single_frame",
                },
            }

        if three_bettor_pos:
            actions.append({"pos": three_bettor_pos, "action": "3bet", "amount_bb": threebet_amount})
            return {
                "status": "ok",
                "node_type": "opener_vs_3bet" if hero_pos == opener_pos else "facing_open",
                "opener_pos": opener_pos,
                "three_bettor_pos": three_bettor_pos,
                "four_bettor_pos": None,
                "limpers": 0,
                "callers": callers,
                "actions": actions,
                "meta": {
                    "builder": "preflop_action_model_builder_v1",
                    "inference_source": "players_chips_single_frame",
                    "hero_pos": hero_pos,
                    "limited_scope": "v2_0_3_no_4bet_reconciliation",
                },
            }

        return {
            "status": "ok",
            "node_type": "facing_open_callers" if callers > 0 else "facing_open",
            "opener_pos": opener_pos,
            "three_bettor_pos": None,
            "four_bettor_pos": None,
            "limpers": 0,
            "callers": callers,
            "actions": actions,
            "meta": {
                "builder": "preflop_action_model_builder_v1",
                "inference_source": "players_chips_single_frame",
                "hero_pos": hero_pos,
            },
        }

    return {
        "status": "ok",
        "node_type": "facing_limp",
        "opener_pos": None,
        "three_bettor_pos": None,
        "four_bettor_pos": None,
        "limpers": len(limpers),
        "callers": 0,
        "actions": [
            {"pos": pos, "action": "limp", "amount_bb": amount}
            for pos, amount in limpers
        ],
        "meta": {
            "builder": "preflop_action_model_builder_v1",
            "inference_source": "players_chips_single_frame",
            "hero_pos": hero_pos,
        },
    }
