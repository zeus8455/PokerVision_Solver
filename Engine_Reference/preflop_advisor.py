from __future__ import annotations

"""Baseline preflop advisor for 6-max NLHE cash, ~100bb effective.

This file is standalone and does not modify engine.py.
It provides:
- a structured preflop tree for common 6-max cash nodes
- baseline ranges are imported from ranges.py and stay easy to edit
- a hand-class parser and range expander
- an advisor that returns the recommended action for a given hand and spot

Important:
- This is a practical baseline chart, not a solved GTO package.
- Ranges are intentionally readable and editable.
- The tree covers the main preflop decision families the future program can use.
"""

from dataclasses import dataclass
from functools import lru_cache
import random
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from decision_types import PreflopDecision, RangeSource
from engine_core import str_to_card

POSITIONS = ("UTG", "MP", "CO", "BTN", "SB", "BB")
POSITION_ORDER = {pos: i for i, pos in enumerate(POSITIONS)}
RANKS = "AKQJT98765432"
RANK_TO_INDEX = {r: i for i, r in enumerate(RANKS)}
SUITS = "cdhs"


# =========================
# hand utilities
# =========================

def _card_rank(card: str) -> str:
    if len(card) != 2:
        raise ValueError(f"Некорректная карта: {card}")
    rank = card[0].upper()
    suit = card[1].lower()
    if rank not in RANKS or suit not in SUITS:
        raise ValueError(f"Некорректная карта: {card}")
    return rank


def hand_to_class(hand: Sequence[str]) -> str:
    """Convert ['As', 'Kd'] -> 'AKo', ['Ah', 'Kh'] -> 'AKs', ['Td', 'Tc'] -> 'TT'."""
    if len(hand) != 2:
        raise ValueError("В руке должно быть ровно 2 карты")
    c1, c2 = hand[0], hand[1]
    if c1 == c2:
        raise ValueError("В руке не может быть двух одинаковых карт")

    r1, r2 = _card_rank(c1), _card_rank(c2)
    s1, s2 = c1[1].lower(), c2[1].lower()

    if r1 == r2:
        return r1 + r2

    if RANK_TO_INDEX[r1] > RANK_TO_INDEX[r2]:
        hi, lo = r2, r1
        same_suit = s1 == s2
    else:
        hi, lo = r1, r2
        same_suit = s1 == s2

    return hi + lo + ("s" if same_suit else "o")


# =========================
# range parser (169 classes)
# =========================

def _split_range_text(text: str) -> List[str]:
    text = text.replace(",", " ").replace(";", " ")
    return [t for t in text.split() if t]


@lru_cache(maxsize=2048)
def expand_range_text(text: str) -> frozenset[str]:
    if not text or not text.strip():
        return frozenset()

    out = set()
    for token in _split_range_text(text):
        out.update(_expand_token(token))
    return frozenset(out)


@lru_cache(maxsize=4096)
def _expand_token(token: str) -> Tuple[str, ...]:
    token = token.strip()
    if not token:
        return tuple()

    if "-" in token:
        left, right = token.split("-", 1)
        return tuple(_expand_dash(left, right))

    if token.endswith("+"):
        return tuple(_expand_plus(token[:-1]))

    return tuple(_expand_single(token))


def _expand_single(token: str) -> List[str]:
    token = token.upper()
    if len(token) == 2:
        a, b = token[0], token[1]
        if a == b and a in RANKS:
            return [token]
        if a in RANKS and b in RANKS:
            hi, lo = _sort_ranks(a, b)
            return [hi + lo + "s", hi + lo + "o"]

    if len(token) == 3:
        a, b, suffix = token[0], token[1], token[2].lower()
        if a in RANKS and b in RANKS and suffix in ("s", "o"):
            hi, lo = _sort_ranks(a, b)
            if hi == lo:
                raise ValueError(f"Некорректный токен диапазона: {token}")
            return [hi + lo + suffix]

    raise ValueError(f"Не удалось распарсить токен диапазона: {token}")


def _expand_plus(base: str) -> List[str]:
    base = base.upper()

    if len(base) == 2 and base[0] == base[1]:
        start = RANKS.index(base[0])
        # RANKS задан в порядке от старших к младшим: AKQJT98765432.
        # Поэтому для 22+ нужно идти "вверх" к старшим парам: 22, 33, ..., AA.
        return [RANKS[i] * 2 for i in range(start, -1, -1)]

    if len(base) == 3 and base[2].lower() in ("s", "o"):
        hi, lo, suffix = base[0], base[1], base[2].lower()
        hi, lo = _sort_ranks(hi, lo)
        if hi == lo:
            raise ValueError(f"Некорректный плюс-токен: {base}+")
        hi_idx = RANKS.index(hi)
        lo_idx = RANKS.index(lo)
        # ATo+ -> ATo AJo AQo AKo
        # A5s+ -> A5s A4s A3s A2s
        return [hi + RANKS[i] + suffix for i in range(lo_idx, hi_idx, -1)]

    raise ValueError(f"Не удалось распарсить плюс-токен: {base}+")


def _expand_dash(left: str, right: str) -> List[str]:
    left = left.upper()
    right = right.upper()

    if len(left) == 2 and len(right) == 2 and left[0] == left[1] and right[0] == right[1]:
        l_idx = RANKS.index(left[0])
        r_idx = RANKS.index(right[0])
        a, b = sorted((l_idx, r_idx))
        return [RANKS[i] * 2 for i in range(a, b + 1)]

    if len(left) == 3 and len(right) == 3 and left[2].lower() == right[2].lower():
        suffix = left[2].lower()
        l_hi, l_lo = _sort_ranks(left[0], left[1])
        r_hi, r_lo = _sort_ranks(right[0], right[1])

        if l_hi != r_hi:
            raise ValueError(f"Dash-диапазон должен иметь одинаковую старшую карту: {left}-{right}")
        hi = l_hi
        idx1 = RANKS.index(l_lo)
        idx2 = RANKS.index(r_lo)
        a, b = sorted((idx1, idx2))
        return [hi + RANKS[i] + suffix for i in range(a, b + 1) if RANKS[i] != hi]

    raise ValueError(f"Не удалось распарсить dash-диапазон: {left}-{right}")


def _sort_ranks(a: str, b: str) -> Tuple[str, str]:
    if a not in RANKS or b not in RANKS:
        raise ValueError(f"Некорректные ранги: {a}, {b}")
    return (a, b) if RANK_TO_INDEX[a] < RANK_TO_INDEX[b] else (b, a)


# =========================
# spot model
# =========================
@dataclass(frozen=True)
class Spot:
    node_type: str
    hero_pos: str
    opener_pos: Optional[str] = None
    three_bettor_pos: Optional[str] = None
    four_bettor_pos: Optional[str] = None
    limpers: int = 0
    callers: int = 0


ACTION_PRIORITY = (
    "5bet_jam",
    "4bet",
    "3bet",
    "iso_raise",
    "raise",
    "call",
    "limp",
    "check",
    "fold",
)


from ranges import (
    BB_VS_SB_LIMP,
    COLD_4BET,
    HERO_BB_VS_SB_LIMP,
    HERO_COLD_4BET,
    HERO_ISO_RAISE,
    HERO_OPENER_VS_3BET,
    HERO_OPEN_LIMP,
    HERO_OVER_LIMP,
    HERO_PREFLOP_CHARTS,
    HERO_RFI_RAISE,
    HERO_SB_FIRST_IN,
    HERO_THREEBETTER_VS_4BET,
    HERO_VS_OPEN,
    HERO_VS_OPEN_CALLERS,
    ISO_RAISE,
    OPENER_VS_3BET,
    OPEN_LIMP,
    OPPONENT_BB_VS_SB_LIMP,
    OPPONENT_COLD_4BET,
    OPPONENT_ISO_RAISE,
    OPPONENT_OPENER_VS_3BET,
    OPPONENT_OPEN_LIMP,
    OPPONENT_OVER_LIMP,
    OPPONENT_PREFLOP_CHARTS,
    OPPONENT_RFI_RAISE,
    OPPONENT_SB_FIRST_IN,
    OPPONENT_THREEBETTER_VS_4BET,
    OPPONENT_VS_OPEN,
    OPPONENT_VS_OPEN_CALLERS,
    OVER_LIMP,
    RANGE_PROFILES,
    RFI_RAISE,
    SB_FIRST_IN,
    THREEBETTER_VS_4BET,
    VS_OPEN,
    VS_OPEN_CALLERS,
)


def _normalize_range_owner(range_owner: str) -> str:
    owner = str(range_owner).strip().lower()
    if owner not in RANGE_PROFILES:
        supported = ", ".join(sorted(RANGE_PROFILES))
        raise ValueError(f"Неизвестный range_owner: {range_owner}. Доступно: {supported}")
    return owner



def get_range_profile(range_owner: str = "hero") -> Dict[str, object]:
    return RANGE_PROFILES[_normalize_range_owner(range_owner)]


# =========================
# advisor helpers
# =========================

def _in_range(hand_class: str, expr: str) -> bool:
    return hand_class in expand_range_text(expr)


def _get_matching_actions(hand_class: str, action_map: Dict[str, str]) -> List[str]:
    matches: List[str] = []
    for action in ACTION_PRIORITY:
        expr = action_map.get(action)
        if expr and _in_range(hand_class, expr):
            matches.append(action)
    return matches


def _pick_action(hand_class: str, action_map: Dict[str, str], rng: Optional[random.Random] = None) -> Tuple[str, List[str]]:
    matches = _get_matching_actions(hand_class, action_map)
    if not matches:
        return "fold", []
    if len(matches) == 1:
        return matches[0], matches
    chooser = rng if rng is not None else random
    return chooser.choice(matches), matches


def _bucket_callers(n: int) -> int:
    return 1 if n <= 1 else 2


def _validate_position(pos: str) -> str:
    pos = pos.upper()
    if pos not in POSITIONS:
        raise ValueError(f"Некорректная позиция: {pos}")
    return pos


def _class_sort_key(hand_class: str) -> Tuple[int, int, int, int]:
    hand_class = str(hand_class).strip().upper()
    if len(hand_class) == 2:
        return (0, RANK_TO_INDEX[hand_class[0]], 0, 0)
    suited_order = 0 if hand_class[2].lower() == "s" else 1
    return (1, RANK_TO_INDEX[hand_class[0]], RANK_TO_INDEX[hand_class[1]], suited_order)


def normalize_range_text(range_expr: str) -> str:
    text = str(range_expr or "").strip()
    if not text:
        return ""
    return " ".join(sorted(expand_range_text(text), key=_class_sort_key))


def _normalize_blocked_cards(blocked_cards: Optional[Sequence[object]]) -> set[int]:
    blocked: set[int] = set()
    for card in blocked_cards or ():
        if isinstance(card, int):
            blocked.add(card)
        else:
            blocked.add(str_to_card(str(card)))
    return blocked


def _hand_class_to_weighted_combos(hand_class: str, blocked_cards: set[int]) -> List[Tuple[Tuple[int, int], float]]:
    hand_class = str(hand_class).strip().upper()
    if not hand_class:
        return []

    combos: List[Tuple[Tuple[int, int], float]] = []
    if len(hand_class) == 2:
        rank = hand_class[0]
        cards = [str_to_card(rank + suit) for suit in SUITS]
        for i in range(len(cards)):
            for j in range(i + 1, len(cards)):
                c1, c2 = cards[i], cards[j]
                if c1 in blocked_cards or c2 in blocked_cards:
                    continue
                combos.append(((c1, c2), 1.0))
        return combos

    if len(hand_class) != 3 or hand_class[2].lower() not in ("s", "o"):
        raise ValueError(f"Некорректный класс руки: {hand_class}")

    hi, lo, suffix = hand_class[0], hand_class[1], hand_class[2].lower()
    if suffix == "s":
        for suit in SUITS:
            c1 = str_to_card(hi + suit)
            c2 = str_to_card(lo + suit)
            if c1 in blocked_cards or c2 in blocked_cards or c1 == c2:
                continue
            combos.append(((c1, c2), 1.0))
        return combos

    for suit1 in SUITS:
        for suit2 in SUITS:
            if suit1 == suit2:
                continue
            c1 = str_to_card(hi + suit1)
            c2 = str_to_card(lo + suit2)
            if c1 in blocked_cards or c2 in blocked_cards or c1 == c2:
                continue
            combos.append(((c1, c2), 1.0))
    return combos


def _range_text_to_weighted_combos(range_expr: str, blocked_cards: Optional[Sequence[object]] = None) -> List[Tuple[Tuple[int, int], float]]:
    normalized = normalize_range_text(range_expr)
    if not normalized:
        return []
    blocked = _normalize_blocked_cards(blocked_cards)
    out: List[Tuple[Tuple[int, int], float]] = []
    for hand_class in normalized.split():
        out.extend(_hand_class_to_weighted_combos(hand_class, blocked))
    return out


def build_range_source(
    range_expr: str,
    *,
    name: str,
    source_type: str,
    blocked_cards: Optional[Sequence[str]] = None,
    meta: Optional[Mapping[str, object]] = None,
) -> RangeSource:
    raw_expr = str(range_expr or "").strip()
    normalized_expr = normalize_range_text(raw_expr)
    weighted_combos = _range_text_to_weighted_combos(normalized_expr, blocked_cards=blocked_cards)
    return RangeSource(
        name=name,
        source_type=source_type,
        raw_expr=raw_expr or None,
        normalized_expr=normalized_expr or None,
        weighted_combos=weighted_combos,
        meta=dict(meta or {}),
    )


def get_action_range_source(
    action_map: Dict[str, str],
    action: str,
    *,
    name: str,
    source_type: str = "preflop_action",
    blocked_cards: Optional[Sequence[str]] = None,
    meta: Optional[Mapping[str, object]] = None,
) -> RangeSource:
    selected_expr = get_action_range(action_map, action)
    source_meta = dict(meta or {})
    source_meta.setdefault("action", str(action))
    source_meta.setdefault("action_map", dict(action_map))
    return build_range_source(
        selected_expr,
        name=name,
        source_type=source_type,
        blocked_cards=blocked_cards,
        meta=source_meta,
    )


def build_range_source_from_preflop_decision(
    decision: Mapping[str, object] | PreflopDecision,
    *,
    name: Optional[str] = None,
    source_type: str = "preflop_decision",
    blocked_cards: Optional[Sequence[str]] = None,
    extra_meta: Optional[Mapping[str, object]] = None,
) -> RangeSource:
    if isinstance(decision, PreflopDecision):
        actor_name = decision.actor_name
        actor_pos = decision.actor_pos
        action = decision.action
        action_map = dict(decision.action_map)
        raw_expr = decision.selected_range_expr or ""
        hand_class = decision.hand_class
        source_meta = dict(decision.meta)
    else:
        actor_name = str(decision.get("actor_name") or decision.get("hero_name") or decision.get("hero") or "Hero")
        actor_pos = str(decision.get("hero_pos") or decision.get("actor_pos") or "") or None
        action = str(decision.get("recommended_action") or decision.get("action") or "")
        action_map = dict(decision.get("ranges") or decision.get("action_map") or {})
        raw_expr = str(decision.get("selected_range_expr") or "")
        hand_class = str(decision.get("hand_class") or "")
        source_meta = dict(decision)

    source_meta.update(extra_meta or {})
    source_meta.setdefault("actor_name", actor_name)
    source_meta.setdefault("actor_pos", actor_pos)
    source_meta.setdefault("hand_class", hand_class)
    source_meta.setdefault("recommended_action", action)
    source_meta.setdefault("action_map", action_map)

    return build_range_source(
        raw_expr,
        name=name or actor_name,
        source_type=source_type,
        blocked_cards=blocked_cards,
        meta=source_meta,
    )


def get_action_range_source_for_spot(
    *,
    node_type: str,
    hero_pos: str,
    action: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    callers: int = 0,
    limpers: int = 0,
    range_owner: str = "hero",
    actor_name: Optional[str] = None,
    blocked_cards: Optional[Sequence[str]] = None,
    rng: Optional[random.Random] = None,
) -> RangeSource:
    action_map = get_chart_for_spot(
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        limpers=limpers,
        range_owner=range_owner,
        rng=rng,
    )
    return get_action_range_source(
        action_map,
        action,
        name=actor_name or hero_pos,
        source_type="preflop_spot",
        blocked_cards=blocked_cards,
        meta={
            "node_type": str(node_type).lower(),
            "hero_pos": hero_pos,
            "opener_pos": opener_pos,
            "three_bettor_pos": three_bettor_pos,
            "four_bettor_pos": four_bettor_pos,
            "callers": callers,
            "limpers": limpers,
            "range_owner": _normalize_range_owner(range_owner),
        },
    )


def _build_preflop_decision(result: Mapping[str, object], *, actor_name: str = "Hero") -> PreflopDecision:
    return PreflopDecision(
        action=str(result["recommended_action"]),
        hand_class=str(result["hand_class"]),
        actor_name=actor_name,
        actor_pos=str(result.get("hero_pos") or "") or None,
        is_mixed_action=bool(result.get("is_mixed_action", False)),
        matching_actions=list(result.get("matching_actions") or []),
        selected_range_expr=str(result.get("selected_range_expr") or "") or None,
        action_map=dict(result.get("ranges") or {}),
        range_source=result.get("range_source") if isinstance(result.get("range_source"), RangeSource) else None,
        fallback_reason=str(result.get("fallback_reason") or "") or None,
        meta={
            "description": result.get("description"),
            "node_type": result.get("node_type"),
            "range_owner": result.get("range_owner"),
            "mix_strategy": dict(result.get("mix_strategy") or {}),
        },
    )


# =========================
# public API
# =========================

def list_supported_node_types() -> List[str]:
    return [
        "unopened",
        "facing_limp",
        "bb_vs_sb_limp",
        "facing_open",
        "facing_open_callers",
        "opener_vs_3bet",
        "threebettor_vs_4bet",
        "cold_4bet",
    ]


def advise_preflop_action(
    hero_hand: Sequence[str],
    *,
    node_type: str,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> Dict[str, object]:
    """Return recommended action for the given spot.

    Examples:
        advise_preflop_action(["As", "Kd"], node_type="unopened", hero_pos="CO")
        advise_preflop_action(["As", "Kd"], node_type="facing_open", hero_pos="BTN", opener_pos="CO")
        advise_preflop_action(["Ah", "5h"], node_type="opener_vs_3bet", hero_pos="BTN", three_bettor_pos="SB")
    """
    node_type = node_type.lower()
    hero_pos = _validate_position(hero_pos)
    hand_class = hand_to_class(hero_hand)

    if opener_pos:
        opener_pos = _validate_position(opener_pos)
    if three_bettor_pos:
        three_bettor_pos = _validate_position(three_bettor_pos)
    if four_bettor_pos:
        four_bettor_pos = _validate_position(four_bettor_pos)

    charts = get_range_profile(range_owner)
    rfi_raise = charts["RFI_RAISE"]
    sb_first_in = charts["SB_FIRST_IN"]
    iso_raise = charts["ISO_RAISE"]
    over_limp = charts["OVER_LIMP"]
    open_limp = charts["OPEN_LIMP"]
    bb_vs_sb_limp = charts["BB_VS_SB_LIMP"]
    vs_open = charts["VS_OPEN"]
    vs_open_callers = charts["VS_OPEN_CALLERS"]
    opener_vs_3bet = charts["OPENER_VS_3BET"]
    threebettor_vs_4bet = charts["THREEBETTER_VS_4BET"]
    cold_4bet = charts["COLD_4BET"]

    action_map: Dict[str, str]
    description: str

    if node_type == "unopened":
        if hero_pos == "SB":
            action_map = sb_first_in
            description = "SB first in vs BB"
        elif hero_pos == "BB":
            raise ValueError("Для BB нет unopened spot: BB не может быть first in в 6-max")
        else:
            action_map = {"raise": rfi_raise[hero_pos]}
            open_limp_expr = open_limp.get(hero_pos, "")
            if open_limp_expr:
                action_map["limp"] = open_limp_expr
            description = f"RFI from {hero_pos}"

    elif node_type == "facing_limp":
        if hero_pos == "BB" and limpers == 1 and opener_pos == "SB":
            action_map = bb_vs_sb_limp
            description = "BB vs SB limp"
        else:
            iso = iso_raise.get(hero_pos, "")
            over = over_limp.get(hero_pos, "")
            action_map = {"iso_raise": iso, "call": over}
            description = f"Facing {limpers} limp(s) from {hero_pos}"

    elif node_type == "bb_vs_sb_limp":
        action_map = bb_vs_sb_limp
        description = "BB vs SB limp"

    elif node_type == "facing_open":
        if not opener_pos:
            raise ValueError("Для facing_open нужно указать opener_pos")
        key = (opener_pos, hero_pos)
        if key not in vs_open:
            raise ValueError(f"Нет чарта для spot {key}")
        action_map = vs_open[key]
        description = f"{hero_pos} vs open from {opener_pos}"

    elif node_type == "facing_open_callers":
        if not opener_pos:
            raise ValueError("Для facing_open_callers нужно указать opener_pos")
        bucket = _bucket_callers(callers)
        key = (opener_pos, hero_pos, bucket)
        if key not in vs_open_callers:
            raise ValueError(f"Нет чарта для spot {key}")
        action_map = vs_open_callers[key]
        description = f"{hero_pos} vs open from {opener_pos} and {callers} caller(s)"

    elif node_type == "opener_vs_3bet":
        if not three_bettor_pos:
            raise ValueError("Для opener_vs_3bet нужно указать three_bettor_pos")
        key = (hero_pos, three_bettor_pos)
        if key not in opener_vs_3bet:
            raise ValueError(f"Нет чарта для spot {key}")
        action_map = opener_vs_3bet[key]
        description = f"{hero_pos} opener facing 3bet from {three_bettor_pos}"

    elif node_type == "threebettor_vs_4bet":
        if not four_bettor_pos:
            raise ValueError("Для threebettor_vs_4bet нужно указать four_bettor_pos")
        key = (hero_pos, four_bettor_pos)
        if key not in threebettor_vs_4bet:
            raise ValueError(f"Нет чарта для spot {key}")
        action_map = threebettor_vs_4bet[key]
        description = f"{hero_pos} 3bettor facing 4bet from {four_bettor_pos}"

    elif node_type == "cold_4bet":
        if not opener_pos or not three_bettor_pos:
            raise ValueError("Для cold_4bet нужно указать opener_pos и three_bettor_pos")
        key = (opener_pos, three_bettor_pos, hero_pos)
        if key not in cold_4bet:
            raise ValueError(f"Нет чарта для spot {key}")
        action_map = cold_4bet[key]
        description = f"{hero_pos} cold 4bet spot vs {opener_pos} open and {three_bettor_pos} 3bet"

    else:
        raise ValueError(f"Неизвестный node_type: {node_type}")

    action, matching_actions = _pick_action(hand_class, action_map, rng=rng)
    mix_weights = {candidate: 1.0 / len(matching_actions) for candidate in matching_actions} if matching_actions else {}

    result = {
        "hand": list(hero_hand),
        "hand_class": hand_class,
        "node_type": node_type,
        "hero_pos": hero_pos,
        "description": description,
        "recommended_action": action,
        "selected_range_expr": get_action_range(action_map, action),
        "ranges": action_map,
        "range_owner": _normalize_range_owner(range_owner),
        "matching_actions": matching_actions,
        "is_mixed_action": len(matching_actions) > 1,
        "mix_strategy": mix_weights,
    }
    result["range_source"] = build_range_source_from_preflop_decision(result, name=hero_pos)
    return result


def get_chart_for_spot(
    *,
    node_type: str,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> Dict[str, str]:
    result = advise_preflop_action(
        ["As", "Ac"],
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        range_owner=range_owner,
        rng=rng,
    )
    return dict(result["ranges"])


def describe_all_supported_spots(range_owner: str = "hero") -> List[str]:
    charts = get_range_profile(range_owner)
    spots = []
    for pos in ("UTG", "MP", "CO", "BTN", "SB"):
        spots.append(f"unopened / hero={pos}")
    for pos in ("MP", "CO", "BTN", "SB"):
        spots.append(f"facing_limp / hero={pos}")
    spots.append("bb_vs_sb_limp / hero=BB")
    for opener, hero in sorted(charts["VS_OPEN"]):
        spots.append(f"facing_open / opener={opener} / hero={hero}")
    for opener, hero, callers in sorted(charts["VS_OPEN_CALLERS"]):
        spots.append(f"facing_open_callers / opener={opener} / hero={hero} / callers={callers}+")
    for opener, threebettor in sorted(charts["OPENER_VS_3BET"]):
        spots.append(f"opener_vs_3bet / hero={opener} / 3bettor={threebettor}")
    for threebettor, fourbettor in sorted(charts["THREEBETTER_VS_4BET"]):
        spots.append(f"threebettor_vs_4bet / hero={threebettor} / 4bettor={fourbettor}")
    for opener, threebettor, hero in sorted(charts["COLD_4BET"]):
        spots.append(f"cold_4bet / opener={opener} / 3bettor={threebettor} / hero={hero}")
    return spots


def advise_preflop_spot(
    spot: Spot,
    hero_hand: Sequence[str],
    *,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> Dict[str, object]:
    return advise_preflop_action(
        hero_hand,
        node_type=spot.node_type,
        hero_pos=spot.hero_pos,
        opener_pos=spot.opener_pos,
        three_bettor_pos=spot.three_bettor_pos,
        four_bettor_pos=spot.four_bettor_pos,
        limpers=spot.limpers,
        callers=spot.callers,
        range_owner=range_owner,
        rng=rng,
    )


def advise_preflop_decision(
    hero_hand: Sequence[str],
    *,
    node_type: str,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "hero",
    actor_name: str = "Hero",
    rng: Optional[random.Random] = None,
) -> PreflopDecision:
    result = advise_preflop_action(
        hero_hand,
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
        rng=rng,
    )
    return _build_preflop_decision(result, actor_name=actor_name)


def get_action_range(action_map: Dict[str, str], action: str) -> str:
    return str(action_map.get(str(action), "") or "")


def get_action_range_for_spot(
    *,
    node_type: str,
    hero_pos: str,
    action: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> str:
    action_map = get_chart_for_spot(
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        range_owner=range_owner,
        rng=rng,
    )
    return get_action_range(action_map, action)


__all__ = [
    "Spot",
    "POSITIONS",
    "POSITION_ORDER",
    "hand_to_class",
    "expand_range_text",
    "normalize_range_text",
    "build_range_source",
    "build_range_source_from_preflop_decision",
    "get_action_range_source",
    "get_action_range_source_for_spot",
    "list_supported_node_types",
    "get_range_profile",
    "advise_preflop_action",
    "advise_preflop_decision",
    "advise_preflop_spot",
    "get_chart_for_spot",
    "get_action_range",
    "get_action_range_for_spot",
    "describe_all_supported_spots",
]


# =============================================================================
# Runtime patch block: robust missing-spot handling + limper_vs_iso support
# =============================================================================

def _copy_action_map_entry(action_map: Mapping[str, str]) -> Dict[str, str]:
    return {str(action): str(expr) for action, expr in dict(action_map).items()}


def _position_distance(left: Optional[str], right: Optional[str]) -> int:
    if left is None or right is None:
        return 0
    return abs(POSITION_ORDER.get(left, 99) - POSITION_ORDER.get(right, 99))


def _best_chart_fallback(
    chart_name: str,
    chart: Mapping[object, Mapping[str, str]],
    *,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    callers: int = 0,
) -> tuple[Optional[Dict[str, str]], Optional[str]]:
    if not chart:
        return None, None

    target_bucket = _bucket_callers(callers)
    scored: List[tuple[int, object, Mapping[str, str]]] = []
    for cand_key, cand_map in chart.items():
        if chart_name == "facing_open" and isinstance(cand_key, tuple) and len(cand_key) == 2:
            cand_opener, cand_hero = cand_key
            score = (0 if cand_hero == hero_pos else 100) + 4 * _position_distance(cand_opener, opener_pos) + _position_distance(cand_hero, hero_pos)
        elif chart_name == "limper_vs_iso" and isinstance(cand_key, tuple) and len(cand_key) == 2:
            cand_hero, cand_iso = cand_key
            score = (0 if cand_hero == hero_pos else 100) + 4 * _position_distance(cand_iso, opener_pos) + _position_distance(cand_hero, hero_pos)
        elif chart_name == "facing_open_callers" and isinstance(cand_key, tuple) and len(cand_key) == 3:
            cand_opener, cand_hero, cand_bucket = cand_key
            score = (0 if cand_hero == hero_pos else 100) + 4 * _position_distance(cand_opener, opener_pos) + 2 * abs(int(cand_bucket) - int(target_bucket))
        elif chart_name == "opener_vs_3bet" and isinstance(cand_key, tuple) and len(cand_key) == 2:
            cand_hero, cand_three = cand_key
            score = (0 if cand_hero == hero_pos else 100) + 4 * _position_distance(cand_three, three_bettor_pos)
        elif chart_name == "threebettor_vs_4bet" and isinstance(cand_key, tuple) and len(cand_key) == 2:
            cand_hero, cand_four = cand_key
            score = (0 if cand_hero == hero_pos else 100) + 4 * _position_distance(cand_four, four_bettor_pos)
        elif chart_name == "cold_4bet" and isinstance(cand_key, tuple) and len(cand_key) == 3:
            cand_open, cand_three, cand_hero = cand_key
            score = (
                (0 if cand_hero == hero_pos else 100)
                + 4 * _position_distance(cand_open, opener_pos)
                + 3 * _position_distance(cand_three, three_bettor_pos)
            )
        else:
            continue
        scored.append((score, cand_key, cand_map))

    if not scored:
        return None, None
    scored.sort(key=lambda item: (item[0], str(item[1])))
    _, best_key, best_map = scored[0]
    return _copy_action_map_entry(best_map), f"fallback:{chart_name}:{best_key}"


def list_supported_node_types() -> List[str]:
    return [
        "unopened",
        "facing_limp",
        "bb_vs_sb_limp",
        "limper_vs_iso",
        "facing_open",
        "facing_open_callers",
        "opener_vs_3bet",
        "threebettor_vs_4bet",
        "cold_4bet",
    ]


def advise_preflop_action(
    hero_hand: Sequence[str],
    *,
    node_type: str,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> Dict[str, object]:
    node_type = node_type.lower()
    hero_pos = _validate_position(hero_pos)
    hand_class = hand_to_class(hero_hand)

    if opener_pos:
        opener_pos = _validate_position(opener_pos)
    if three_bettor_pos:
        three_bettor_pos = _validate_position(three_bettor_pos)
    if four_bettor_pos:
        four_bettor_pos = _validate_position(four_bettor_pos)

    charts = get_range_profile(range_owner)
    rfi_raise = charts["RFI_RAISE"]
    sb_first_in = charts["SB_FIRST_IN"]
    iso_raise = charts["ISO_RAISE"]
    over_limp = charts["OVER_LIMP"]
    open_limp = charts["OPEN_LIMP"]
    bb_vs_sb_limp = charts["BB_VS_SB_LIMP"]
    limper_vs_iso = charts.get("LIMPER_VS_ISO", {})
    vs_open = charts["VS_OPEN"]
    vs_open_callers = charts["VS_OPEN_CALLERS"]
    opener_vs_3bet = charts["OPENER_VS_3BET"]
    threebettor_vs_4bet = charts["THREEBETTER_VS_4BET"]
    cold_4bet = charts["COLD_4BET"]

    action_map: Dict[str, str]
    description: str
    resolved_node_type = node_type
    fallback_reason: Optional[str] = None

    if node_type == "unopened":
        if hero_pos == "SB":
            action_map = _copy_action_map_entry(sb_first_in)
            description = "SB first in vs BB"
        elif hero_pos == "BB":
            raise ValueError("Для BB нет unopened spot: BB не может быть first in в 6-max")
        else:
            action_map = {"raise": rfi_raise[hero_pos]}
            open_limp_expr = open_limp.get(hero_pos, "")
            if open_limp_expr:
                action_map["limp"] = open_limp_expr
            description = f"RFI from {hero_pos}"

    elif node_type == "facing_limp":
        if hero_pos == "BB" and limpers == 1 and opener_pos == "SB":
            action_map = _copy_action_map_entry(bb_vs_sb_limp)
            description = "BB vs SB limp"
        else:
            iso = str(iso_raise.get(hero_pos, "") or "")
            over = str(over_limp.get(hero_pos, "") or "")
            action_map = {"iso_raise": iso, "call": over}
            description = f"Facing {limpers} limp(s) from {hero_pos}"

    elif node_type == "bb_vs_sb_limp":
        action_map = _copy_action_map_entry(bb_vs_sb_limp)
        description = "BB vs SB limp"

    elif node_type == "limper_vs_iso":
        if not opener_pos:
            raise ValueError("Для limper_vs_iso нужно указать opener_pos")
        key = (hero_pos, opener_pos)
        if key in limper_vs_iso:
            action_map = _copy_action_map_entry(limper_vs_iso[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "limper_vs_iso",
                limper_vs_iso,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} limper facing iso from {opener_pos}"

    elif node_type == "facing_open":
        if not opener_pos:
            raise ValueError("Для facing_open нужно указать opener_pos")
        key = (opener_pos, hero_pos)
        if key in vs_open:
            action_map = _copy_action_map_entry(vs_open[key])
            description = f"{hero_pos} vs open from {opener_pos}"
        elif (hero_pos, opener_pos) in limper_vs_iso:
            action_map = _copy_action_map_entry(limper_vs_iso[(hero_pos, opener_pos)])
            description = f"{hero_pos} limper facing iso from {opener_pos}"
            resolved_node_type = "limper_vs_iso"
            fallback_reason = "fallback:facing_open->limper_vs_iso"
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "facing_open",
                vs_open,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
            description = f"{hero_pos} vs open from {opener_pos}"

    elif node_type == "facing_open_callers":
        if not opener_pos:
            raise ValueError("Для facing_open_callers нужно указать opener_pos")
        bucket = _bucket_callers(callers)
        key = (opener_pos, hero_pos, bucket)
        if key in vs_open_callers:
            action_map = _copy_action_map_entry(vs_open_callers[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "facing_open_callers",
                vs_open_callers,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
                callers=callers,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} vs open from {opener_pos} and {callers} caller(s)"

    elif node_type == "opener_vs_3bet":
        if not three_bettor_pos:
            raise ValueError("Для opener_vs_3bet нужно указать three_bettor_pos")
        key = (hero_pos, three_bettor_pos)
        if key in opener_vs_3bet:
            action_map = _copy_action_map_entry(opener_vs_3bet[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "opener_vs_3bet",
                opener_vs_3bet,
                hero_pos=hero_pos,
                three_bettor_pos=three_bettor_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} opener facing 3bet from {three_bettor_pos}"

    elif node_type == "threebettor_vs_4bet":
        if not four_bettor_pos:
            raise ValueError("Для threebettor_vs_4bet нужно указать four_bettor_pos")
        key = (hero_pos, four_bettor_pos)
        if key in threebettor_vs_4bet:
            action_map = _copy_action_map_entry(threebettor_vs_4bet[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "threebettor_vs_4bet",
                threebettor_vs_4bet,
                hero_pos=hero_pos,
                four_bettor_pos=four_bettor_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} 3bettor facing 4bet from {four_bettor_pos}"

    elif node_type == "cold_4bet":
        if not opener_pos or not three_bettor_pos:
            raise ValueError("Для cold_4bet нужно указать opener_pos и three_bettor_pos")
        key = (opener_pos, three_bettor_pos, hero_pos)
        if key in cold_4bet:
            action_map = _copy_action_map_entry(cold_4bet[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "cold_4bet",
                cold_4bet,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
                three_bettor_pos=three_bettor_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} cold 4bet spot vs {opener_pos} open and {three_bettor_pos} 3bet"

    else:
        raise ValueError(f"Неизвестный node_type: {node_type}")

    action, matching_actions = _pick_action(hand_class, action_map, rng=rng)
    mix_weights = {candidate: 1.0 / len(matching_actions) for candidate in matching_actions} if matching_actions else {}

    result = {
        "hand": list(hero_hand),
        "hand_class": hand_class,
        "node_type": resolved_node_type,
        "requested_node_type": node_type,
        "hero_pos": hero_pos,
        "description": description,
        "recommended_action": action,
        "selected_range_expr": get_action_range(action_map, action),
        "ranges": action_map,
        "range_owner": _normalize_range_owner(range_owner),
        "matching_actions": matching_actions,
        "is_mixed_action": len(matching_actions) > 1,
        "mix_strategy": mix_weights,
        "fallback_reason": fallback_reason,
    }
    result["range_source"] = build_range_source_from_preflop_decision(result, name=hero_pos)
    return result


def get_chart_for_spot(
    *,
    node_type: str,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> Dict[str, str]:
    result = advise_preflop_action(
        ["As", "Ac"],
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
        rng=rng,
    )
    return dict(result["ranges"])


def get_action_range_for_spot(
    *,
    node_type: str,
    hero_pos: str,
    action: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> str:
    action_map = get_chart_for_spot(
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
        rng=rng,
    )
    return get_action_range(action_map, action)


if __name__ == "__main__":
    examples = [
        advise_preflop_action(["As", "Kd"], node_type="unopened", hero_pos="CO"),
        advise_preflop_action(["As", "Kd"], node_type="facing_open", hero_pos="BTN", opener_pos="CO"),
        advise_preflop_action(["Ah", "5h"], node_type="opener_vs_3bet", hero_pos="BTN", three_bettor_pos="SB"),
        advise_preflop_action(["Qs", "Qh"], node_type="threebettor_vs_4bet", hero_pos="SB", four_bettor_pos="BTN"),
        advise_preflop_action(["7s", "6s"], node_type="bb_vs_sb_limp", hero_pos="BB"),
    ]

    for item in examples:
        print(item["description"])
        print("hand:", item["hand"], "->", item["hand_class"])
        print("action:", item["recommended_action"])
        print("ranges:", item["ranges"])
        print("-" * 70)


# =========================
# Conservative limp-family override block (2026-04)
# =========================

def list_supported_node_types() -> List[str]:
    return [
        "unopened",
        "open_limp_first_in",
        "over_limp_after_1_limper",
        "over_limp_after_2plus_limpers",
        "iso_vs_1_limper",
        "iso_vs_2plus_limpers",
        "facing_limp",
        "bb_vs_sb_limp",
        "limper_vs_iso",
        "limper_vs_iso_ip",
        "limper_vs_iso_oop",
        "facing_open",
        "facing_open_callers",
        "opener_vs_3bet",
        "threebettor_vs_4bet",
        "cold_4bet",
    ]


def _resolve_limp_node_type(node_type: str, *, hero_pos: str, limpers: int) -> str:
    node_type = str(node_type).lower()
    if node_type == "facing_limp":
        return "bb_vs_sb_limp" if hero_pos == "BB" and limpers == 1 else ("iso_vs_1_limper" if limpers <= 1 else "iso_vs_2plus_limpers")
    return node_type


def advise_preflop_action(
    hero_hand: Sequence[str],
    *,
    node_type: str,
    hero_pos: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "hero",
    rng: Optional[random.Random] = None,
) -> Dict[str, object]:
    requested_node_type = str(node_type).lower()
    hero_pos = _validate_position(hero_pos)
    hand_class = hand_to_class(hero_hand)
    node_type = _resolve_limp_node_type(requested_node_type, hero_pos=hero_pos, limpers=int(limpers or 0))

    if opener_pos:
        opener_pos = _validate_position(opener_pos)
    if three_bettor_pos:
        three_bettor_pos = _validate_position(three_bettor_pos)
    if four_bettor_pos:
        four_bettor_pos = _validate_position(four_bettor_pos)

    charts = get_range_profile(range_owner)
    rfi_raise = charts["RFI_RAISE"]
    sb_first_in = charts["SB_FIRST_IN"]
    iso_raise = charts["ISO_RAISE"]
    over_limp = charts["OVER_LIMP"]
    open_limp = charts["OPEN_LIMP"]
    bb_vs_sb_limp = charts["BB_VS_SB_LIMP"]
    limper_vs_iso = charts.get("LIMPER_VS_ISO", {})
    vs_open = charts["VS_OPEN"]
    vs_open_callers = charts["VS_OPEN_CALLERS"]
    opener_vs_3bet = charts["OPENER_VS_3BET"]
    threebettor_vs_4bet = charts["THREEBETTER_VS_4BET"]
    cold_4bet = charts["COLD_4BET"]

    action_map: Dict[str, str]
    description: str
    resolved_node_type = node_type
    fallback_reason: Optional[str] = None

    if node_type == "unopened":
        if hero_pos == "SB":
            action_map = _copy_action_map_entry(sb_first_in)
            description = "SB first in vs BB"
        elif hero_pos == "BB":
            raise ValueError("Для BB нет unopened spot: BB не может быть first in в 6-max")
        else:
            action_map = {"raise": rfi_raise[hero_pos]}
            open_limp_expr = open_limp.get(hero_pos, "")
            if open_limp_expr:
                action_map["limp"] = open_limp_expr
            description = f"RFI from {hero_pos}"

    elif node_type == "open_limp_first_in":
        if hero_pos == "SB":
            action_map = {"limp": sb_first_in.get("limp", ""), "raise": sb_first_in.get("raise", "")}
            description = "SB first-in limp strategy"
        elif hero_pos == "BB":
            raise ValueError("Для BB нет open_limp_first_in spot")
        else:
            limp_expr = str(open_limp.get(hero_pos, "") or "")
            raise_expr = str(rfi_raise.get(hero_pos, "") or "")
            action_map = {"limp": limp_expr}
            if raise_expr:
                action_map["raise"] = raise_expr
            description = f"Open-limp first in from {hero_pos}"

    elif node_type in {"over_limp_after_1_limper", "over_limp_after_2plus_limpers", "iso_vs_1_limper", "iso_vs_2plus_limpers"}:
        limp_count = max(1, int(limpers or 1))
        iso_expr = str(iso_raise.get(hero_pos, "") or "")
        over_expr = str(over_limp.get(hero_pos, "") or open_limp.get(hero_pos, "") or "")
        action_map = {}
        if over_expr:
            action_map["call"] = over_expr
        if iso_expr:
            action_map["raise"] = iso_expr
        if node_type.startswith("over_limp"):
            description = f"Over-limp after {limp_count} limper(s) from {hero_pos}"
        else:
            description = f"ISO vs {limp_count} limper(s) from {hero_pos}"

    elif node_type == "bb_vs_sb_limp":
        action_map = _copy_action_map_entry(bb_vs_sb_limp)
        description = "BB vs SB limp"

    elif node_type in {"limper_vs_iso", "limper_vs_iso_ip", "limper_vs_iso_oop"}:
        if not opener_pos:
            raise ValueError("Для limper_vs_iso нужно указать opener_pos")
        key = (hero_pos, opener_pos)
        if key in limper_vs_iso:
            action_map = _copy_action_map_entry(limper_vs_iso[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "limper_vs_iso",
                limper_vs_iso,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        relation = "IP" if node_type.endswith("_ip") else ("OOP" if node_type.endswith("_oop") else "")
        relation_text = f" ({relation})" if relation else ""
        description = f"{hero_pos} limper facing iso from {opener_pos}{relation_text}"

    elif node_type == "facing_open":
        if not opener_pos:
            raise ValueError("Для facing_open нужно указать opener_pos")
        key = (opener_pos, hero_pos)
        if key in vs_open:
            action_map = _copy_action_map_entry(vs_open[key])
            description = f"{hero_pos} vs open from {opener_pos}"
        elif (hero_pos, opener_pos) in limper_vs_iso:
            action_map = _copy_action_map_entry(limper_vs_iso[(hero_pos, opener_pos)])
            description = f"{hero_pos} limper facing iso from {opener_pos}"
            resolved_node_type = "limper_vs_iso"
            fallback_reason = "fallback:facing_open->limper_vs_iso"
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "facing_open",
                vs_open,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
            description = f"{hero_pos} vs open from {opener_pos}"

    elif node_type == "facing_open_callers":
        if not opener_pos:
            raise ValueError("Для facing_open_callers нужно указать opener_pos")
        bucket = _bucket_callers(callers)
        key = (opener_pos, hero_pos, bucket)
        if key in vs_open_callers:
            action_map = _copy_action_map_entry(vs_open_callers[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "facing_open_callers",
                vs_open_callers,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
                callers=callers,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} vs open from {opener_pos} and {callers} caller(s)"

    elif node_type == "opener_vs_3bet":
        if not three_bettor_pos:
            raise ValueError("Для opener_vs_3bet нужно указать three_bettor_pos")
        key = (hero_pos, three_bettor_pos)
        if key in opener_vs_3bet:
            action_map = _copy_action_map_entry(opener_vs_3bet[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "opener_vs_3bet",
                opener_vs_3bet,
                hero_pos=hero_pos,
                three_bettor_pos=three_bettor_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} opener facing 3bet from {three_bettor_pos}"

    elif node_type == "threebettor_vs_4bet":
        if not four_bettor_pos:
            raise ValueError("Для threebettor_vs_4bet нужно указать four_bettor_pos")
        key = (hero_pos, four_bettor_pos)
        if key in threebettor_vs_4bet:
            action_map = _copy_action_map_entry(threebettor_vs_4bet[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "threebettor_vs_4bet",
                threebettor_vs_4bet,
                hero_pos=hero_pos,
                four_bettor_pos=four_bettor_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} 3bettor facing 4bet from {four_bettor_pos}"

    elif node_type == "cold_4bet":
        if not opener_pos or not three_bettor_pos:
            raise ValueError("Для cold_4bet нужно указать opener_pos и three_bettor_pos")
        key = (opener_pos, three_bettor_pos, hero_pos)
        if key in cold_4bet:
            action_map = _copy_action_map_entry(cold_4bet[key])
        else:
            action_map, fallback_reason = _best_chart_fallback(
                "cold_4bet",
                cold_4bet,
                hero_pos=hero_pos,
                opener_pos=opener_pos,
                three_bettor_pos=three_bettor_pos,
            )
            if action_map is None:
                raise ValueError(f"Нет чарта для spot {key}")
        description = f"{hero_pos} cold 4bet spot vs {opener_pos} open and {three_bettor_pos} 3bet"

    else:
        raise ValueError(f"Неизвестный node_type: {node_type}")

    action, matching_actions = _pick_action(hand_class, action_map, rng=rng)
    mix_weights = {candidate: 1.0 / len(matching_actions) for candidate in matching_actions} if matching_actions else {}

    result = {
        "hand": list(hero_hand),
        "hand_class": hand_class,
        "node_type": resolved_node_type,
        "requested_node_type": requested_node_type,
        "hero_pos": hero_pos,
        "description": description,
        "recommended_action": action,
        "selected_range_expr": get_action_range(action_map, action),
        "ranges": action_map,
        "range_owner": _normalize_range_owner(range_owner),
        "matching_actions": matching_actions,
        "is_mixed_action": len(matching_actions) > 1,
        "mix_strategy": mix_weights,
        "fallback_reason": fallback_reason,
    }
    result["range_source"] = build_range_source_from_preflop_decision(result, name=hero_pos)
    return result


def get_chart_for_spot(*, node_type: str, hero_pos: str, opener_pos: Optional[str] = None, three_bettor_pos: Optional[str] = None, four_bettor_pos: Optional[str] = None, limpers: int = 0, callers: int = 0, range_owner: str = "hero", rng: Optional[random.Random] = None) -> Dict[str, str]:
    result = advise_preflop_action(
        ["As", "Ac"],
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
        rng=rng,
    )
    return dict(result["ranges"])


def get_action_range_for_spot(*, node_type: str, hero_pos: str, action: str, opener_pos: Optional[str] = None, three_bettor_pos: Optional[str] = None, four_bettor_pos: Optional[str] = None, callers: int = 0, limpers: int = 0, range_owner: str = "hero") -> str:
    chart = get_chart_for_spot(
        node_type=node_type,
        hero_pos=hero_pos,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        limpers=limpers,
        range_owner=range_owner,
    )
    normalized_action = str(action).strip().lower()
    if normalized_action not in chart:
        if normalized_action == "iso_raise" and "raise" in chart:
            normalized_action = "raise"
        elif normalized_action == "raise" and "iso_raise" in chart:
            normalized_action = "iso_raise"
        elif normalized_action == "check" and "call" in chart:
            normalized_action = "call"
    return get_action_range(chart, normalized_action)
