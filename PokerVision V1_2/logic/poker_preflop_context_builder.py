"""
logic/poker_preflop_context_builder.py

PokerVision Solver V0.5 — Clear_JSON -> preflop engine_context builder.

This module does not call the poker engine.
It only translates a clean Clear_JSON-like state into a compact preflop engine_context.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "poker_engine_context_v1"
SUPPORTED_POSITIONS = {"UTG", "MP", "CO", "BTN", "SB", "BB"}

RANK_MAP = {
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "T": "T",
    "10": "T",
    "J": "J",
    "Q": "Q",
    "K": "K",
    "A": "A",
}

SUIT_MAP = {
    "clubs": "c",
    "club": "c",
    "c": "c",
    "diamonds": "d",
    "diamond": "d",
    "d": "d",
    "hearts": "h",
    "heart": "h",
    "h": "h",
    "spades": "s",
    "spade": "s",
    "s": "s",
}


def _error_context(*, frame_id: Optional[str], reason: str, message: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "street": "preflop",
        "context_type": "PreflopContext",
        "source_frame_id": frame_id,
        "hero_hand": [],
        "hero_pos": None,
        "player_count": 0,
        "node_type": None,
        "opener_pos": None,
        "three_bettor_pos": None,
        "four_bettor_pos": None,
        "limpers": 0,
        "callers": 0,
        "action_history": [],
        "errors": [{"reason": reason, "message": message}],
        "warnings": [],
    }


def normalize_pokervision_card(card: Any) -> str:
    """Convert PokerVision card name like A_spades or K_hearts into engine format As/Kh."""
    text = str(card or "").strip()
    if not text:
        raise ValueError("empty card")

    # Already engine-like: As, Kd, Th, 7c
    if len(text) == 2 and text[0].upper() in RANK_MAP and text[1].lower() in SUIT_MAP:
        return RANK_MAP[text[0].upper()] + SUIT_MAP[text[1].lower()]

    parts = text.replace("-", "_").split("_")
    if len(parts) != 2:
        raise ValueError(f"unsupported card format: {text}")

    rank_raw, suit_raw = parts[0].upper(), parts[1].lower()
    if rank_raw not in RANK_MAP:
        raise ValueError(f"unsupported card rank: {rank_raw}")
    if suit_raw not in SUIT_MAP:
        raise ValueError(f"unsupported card suit: {suit_raw}")

    return RANK_MAP[rank_raw] + SUIT_MAP[suit_raw]


def normalize_hero_cards(cards: Any) -> List[str]:
    if not isinstance(cards, list):
        raise ValueError("hero cards must be a list")
    if len(cards) != 2:
        raise ValueError(f"hero must have exactly 2 cards, got {len(cards)}")

    out = [normalize_pokervision_card(card) for card in cards]
    if len(set(out)) != len(out):
        raise ValueError(f"duplicate hero cards: {out}")
    return out


def _amount(value: Any) -> float:
    if value is False or value is None:
        return 0.0
    try:
        return float(value)
    except Exception:
        return 0.0


def _find_hero(players: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    heroes = []
    for pos, pdata in players.items():
        if isinstance(pdata, dict) and pdata.get("hero") is True:
            heroes.append((str(pos), pdata))

    if len(heroes) != 1:
        raise ValueError(f"Clear_JSON must contain exactly one HERO, got {len(heroes)}")

    hero_pos, hero_data = heroes[0]
    if hero_pos not in SUPPORTED_POSITIONS:
        raise ValueError(f"unsupported hero position: {hero_pos}")

    return hero_pos, hero_data


def _positions_before(hero_pos: str, positions: List[str]) -> List[str]:
    if hero_pos not in positions:
        return []
    return positions[: positions.index(hero_pos)]


def _build_from_action_model(model: Dict[str, Any], hero_pos: str) -> Dict[str, Any]:
    opener_pos = model.get("opener_pos")
    three_bettor_pos = model.get("three_bettor_pos")
    four_bettor_pos = model.get("four_bettor_pos")
    limpers = int(model.get("limpers") or 0)
    callers = int(model.get("callers") or 0)
    actions = list(model.get("actions") or [])

    if four_bettor_pos and three_bettor_pos and opener_pos:
        node_type = "threebettor_vs_4bet" if hero_pos == three_bettor_pos else "cold_4bet"
    elif three_bettor_pos and opener_pos:
        node_type = "opener_vs_3bet" if hero_pos == opener_pos else "facing_open"
    elif opener_pos and callers > 0:
        node_type = "facing_open_callers"
    elif opener_pos:
        node_type = "facing_open"
    elif limpers > 0:
        node_type = "facing_limp"
    else:
        node_type = "unopened"

    return {
        "node_type": node_type,
        "opener_pos": opener_pos,
        "three_bettor_pos": three_bettor_pos,
        "four_bettor_pos": four_bettor_pos,
        "limpers": limpers,
        "callers": callers,
        "action_history": actions,
    }


def _infer_simple_from_players(players: Dict[str, Any], hero_pos: str) -> Dict[str, Any]:
    positions = [pos for pos in ["UTG", "MP", "CO", "BTN", "SB", "BB"] if pos in players]
    before_hero = _positions_before(hero_pos, positions)

    limpers: List[str] = []
    raisers: List[Tuple[str, float]] = []

    for pos in before_hero:
        pdata = players.get(pos) or {}
        if not isinstance(pdata, dict):
            continue
        if pdata.get("fold") is True:
            continue
        chips = _amount(pdata.get("chips"))
        if chips <= 0:
            continue
        if chips <= 1.0:
            limpers.append(pos)
        else:
            raisers.append((pos, chips))

    if raisers:
        opener_pos = raisers[0][0]
        callers = 0
        open_amount = raisers[0][1]
        for pos in before_hero:
            if pos == opener_pos:
                continue
            pdata = players.get(pos) or {}
            if not isinstance(pdata, dict) or pdata.get("fold") is True:
                continue
            chips = _amount(pdata.get("chips"))
            if chips == open_amount:
                callers += 1

        return {
            "node_type": "facing_open_callers" if callers > 0 else "facing_open",
            "opener_pos": opener_pos,
            "three_bettor_pos": None,
            "four_bettor_pos": None,
            "limpers": 0,
            "callers": callers,
            "action_history": [
                {"pos": opener_pos, "action": "open_raise", "amount_bb": open_amount}
            ],
        }

    if limpers:
        return {
            "node_type": "facing_limp",
            "opener_pos": None,
            "three_bettor_pos": None,
            "four_bettor_pos": None,
            "limpers": len(limpers),
            "callers": 0,
            "action_history": [
                {"pos": pos, "action": "limp", "amount_bb": _amount((players.get(pos) or {}).get("chips"))}
                for pos in limpers
            ],
        }

    return {
        "node_type": "unopened",
        "opener_pos": None,
        "three_bettor_pos": None,
        "four_bettor_pos": None,
        "limpers": 0,
        "callers": 0,
        "action_history": [],
    }


def build_preflop_engine_context(clear_json: Dict[str, Any]) -> Dict[str, Any]:
    """Build compact preflop engine_context from Clear_JSON-like state."""
    frame_id = clear_json.get("frame_id")

    board = clear_json.get("board") or {}
    street = board.get("street")
    board_cards = board.get("cards") or []

    if street != "preflop" or board_cards:
        return _error_context(
            frame_id=frame_id,
            reason="not_preflop",
            message=f"Expected preflop with empty board, got street={street!r}, cards={board_cards!r}",
        )

    players = clear_json.get("players")
    if not isinstance(players, dict):
        return _error_context(
            frame_id=frame_id,
            reason="players_missing",
            message="Clear_JSON.players must be an object.",
        )

    try:
        hero_pos, hero_data = _find_hero(players)
        hero_hand = normalize_hero_cards(hero_data.get("cards"))
    except Exception as exc:
        return _error_context(
            frame_id=frame_id,
            reason="hero_extract_failed",
            message=str(exc),
        )

    model = clear_json.get("preflop_action_model")
    if isinstance(model, dict):
        inferred = _build_from_action_model(model, hero_pos)
        inference_source = "preflop_action_model"
    else:
        inferred = _infer_simple_from_players(players, hero_pos)
        inference_source = "players_chips_fallback"

    context = {
        "schema_version": SCHEMA_VERSION,
        "status": "ok",
        "street": "preflop",
        "context_type": "PreflopContext",
        "source_frame_id": frame_id,
        "hero_hand": hero_hand,
        "hero_pos": hero_pos,
        "player_count": len(players),
        "node_type": inferred["node_type"],
        "opener_pos": inferred["opener_pos"],
        "three_bettor_pos": inferred["three_bettor_pos"],
        "four_bettor_pos": inferred["four_bettor_pos"],
        "limpers": inferred["limpers"],
        "callers": inferred["callers"],
        "action_history": inferred["action_history"],
        "errors": [],
        "warnings": [],
        "meta": {
            "inference_source": inference_source,
            "total_pot": clear_json.get("Total_pot"),
        },
    }
    return context
