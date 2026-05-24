from __future__ import annotations

"""Postflop range filtering layer built on top of preflop_advisor.py and equity.py.

Current version:
- does NOT modify engine.py
- gets villain preflop range from preflop_advisor.py
- passes the range street-by-street: preflop -> flop -> turn -> river
- filters the range mainly by logical hand categories relative to the board
- keeps the public API readable for external launcher files

Important:
- The main filter is category-based, not equity-based.
- Equity vs Hero is still calculated for reporting/debugging only.
- Adds a conservative weighted bluff/blocker layer for small bets and river pressure.
"""

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from decision_types import PostflopContext, RangeSource
from engine_core import card_to_str, str_to_card
from equity import combo_to_str, hand_vs_hand, parse_range
from preflop_advisor import RANKS, build_range_source, get_action_range_source_for_spot, hand_to_class

WeightedCombo = Tuple[Tuple[int, int], float]
RANGE_SOURCE_CONTRACT = "range_source_v1"
STREET_CARD_COUNT = {"flop": 3, "turn": 4, "river": 5}
AGGRESSIVE_ACTIONS = {"bet", "check_raise", "reraise"}
MULTIWAY_BET_EQUIVALENT_ACTIONS = {"bet", "call"}
LINE_CONTINUATION_ACTIONS = {"bet", "call", "check_raise", "reraise"}
RANKS_ASC = "23456789TJQKA"
RANK_VALUE = {rank: index + 2 for index, rank in enumerate(RANKS_ASC)}
STRAIGHTS = [
    {14, 2, 3, 4, 5},
    {2, 3, 4, 5, 6},
    {3, 4, 5, 6, 7},
    {4, 5, 6, 7, 8},
    {5, 6, 7, 8, 9},
    {6, 7, 8, 9, 10},
    {7, 8, 9, 10, 11},
    {8, 9, 10, 11, 12},
    {9, 10, 11, 12, 13},
    {10, 11, 12, 13, 14},
]

# =========================
# category groups for rules
# =========================
STRONG_MADE_TAGS = {
    "two_pair",
    "set",
    "trips",
    "straight",
    "flush",
    "full_house",
    "quads",
    "straight_flush",
}
PAIR_TAGS = {
    "pocket_pair",
    "overpair",
    "underpair",
    "top_pair",
    "middle_pair",
    "bottom_pair",
}
STRONG_PAIR_TAGS = {"overpair", "top_pair"}
DRAW_TAGS = {"gutshot", "oesd", "flush_draw", "backdoor_flush_draw", "combo_draw"}
STRONG_DRAW_TAGS = {"oesd", "flush_draw", "combo_draw"}
HIGH_CARD_TAGS = {"ace_high", "two_overcards", "one_overcard"}
ALL_MEANINGFUL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | HIGH_CARD_TAGS

# Дополнительные теги не ломают старые правила: базовые теги остаются,
# а уточнения используются для более тонких весов и будущей калибровки.
REFINED_PAIR_TAGS = {
    "top_pair_top_kicker",
    "top_pair_good_kicker",
    "top_pair_weak_kicker",
    "middle_pair_good_kicker",
    "middle_pair_weak_kicker",
    "bottom_pair_good_kicker",
    "bottom_pair_weak_kicker",
    "pocket_pair_above_second_card",
    "pocket_pair_below_second_card",
    "weak_showdown",
}
BLOCKER_TAGS = {"nut_flush_blocker", "high_flush_blocker", "straight_blocker"}
BOARD_TEXTURE_TAGS = {
    "board_paired",
    "board_monotone",
    "board_two_tone",
    "board_rainbow",
    "board_connected",
    "board_low_connected",
    "board_dry_high",
    "board_broadway_dynamic",
    "board_ace_high",
    "board_king_high",
    "board_wet_connected",
}
PAIR_TAGS = PAIR_TAGS | REFINED_PAIR_TAGS
STRONG_PAIR_TAGS = STRONG_PAIR_TAGS | {"top_pair_top_kicker", "top_pair_good_kicker"}
DRAW_TAGS = DRAW_TAGS | {"nut_flush_draw"}
STRONG_DRAW_TAGS = STRONG_DRAW_TAGS | {"nut_flush_draw"}
HIGH_CARD_TAGS = HIGH_CARD_TAGS | BLOCKER_TAGS
BLUFF_LAYER_TAGS = {"air", "ace_high", "two_overcards", "one_overcard", "backdoor_flush_draw"} | BLOCKER_TAGS
ALL_MEANINGFUL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | HIGH_CARD_TAGS | BOARD_TEXTURE_TAGS

WIDE_NON_AIR_TAGS = ALL_MEANINGFUL_TAGS - {"air"}
FLOP_MEDIUM_BET_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | STRONG_DRAW_TAGS | {"gutshot", "ace_high", "two_overcards", "backdoor_flush_draw"}
FLOP_BIG_BET_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS | {"gutshot", "top_pair_good_kicker"}
TURN_DELAYED_SMALL_TAGS = WIDE_NON_AIR_TAGS | {"air"}
TURN_DELAYED_BIG_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS | {"middle_pair", "middle_pair_good_kicker", "gutshot"}
TURN_AGGR_SMALL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | {"ace_high", "two_overcards"}
TURN_AGGR_BIG_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS | {"middle_pair_good_kicker", "gutshot"}
STACK_OFF_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS
RIVER_THIN_TAGS = STRONG_MADE_TAGS | PAIR_TAGS
RIVER_BIG_BET_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | {"top_pair_good_kicker"}
RIVER_RAISE_TAGS = STRONG_MADE_TAGS | {"nut_flush_blocker", "high_flush_blocker", "straight_blocker", "ace_high"}


@dataclass(frozen=True)
class PostflopRule:
    street: str
    action: str
    bucket: str
    min_equity: float
    keep_full_range: bool
    reason: str
    filter_mode: str = "tags"
    keep_any_tags: Tuple[str, ...] = tuple()


@dataclass(frozen=True)
class PostflopEvent:
    street: str
    action: str
    bet_pct_pot: float
    is_all_in: bool


# =========================
# bet sizing buckets
# =========================

def classify_bet_size(bet_pct_pot: float, *, is_all_in: bool = False) -> str:
    if bet_pct_pot < 0:
        raise ValueError("bet_pct_pot не может быть отрицательным")
    if is_all_in:
        return "all-in"
    if bet_pct_pot <= 25:
        return "0-25"
    if bet_pct_pot <= 50:
        return "26-50"
    if bet_pct_pot <= 75:
        return "51-75"
    if bet_pct_pot < 100:
        return "76-99"
    return "100+"


def _infer_street_from_board(board: Sequence[str]) -> str:
    count = len(board)
    if count == 3:
        return "flop"
    if count == 4:
        return "turn"
    if count == 5:
        return "river"
    raise ValueError("board должен содержать 3, 4 или 5 карт")


# =========================
# preflop -> postflop bridge
# =========================

def get_preflop_range_source(
    *,
    node_type: str,
    villain_pos: str,
    villain_action: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "opponent",
) -> RangeSource:
    return get_action_range_source_for_spot(
        node_type=node_type,
        hero_pos=villain_pos,
        action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        limpers=limpers,
        range_owner=range_owner,
        actor_name=villain_pos,
    )


def get_preflop_action_range(
    *,
    node_type: str,
    villain_pos: str,
    villain_action: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    range_owner: str = "opponent",
) -> str:
    source = get_preflop_range_source(
        node_type=node_type,
        villain_pos=villain_pos,
        villain_action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
    )
    return str(source.normalized_expr or source.raw_expr or "")


# =========================
# readable range output
# =========================

def _class_sort_key(hand_class: str) -> Tuple[int, int, int, int]:
    if len(hand_class) == 2:
        return (0, RANKS.index(hand_class[0]), 0, 0)
    hi = hand_class[0]
    lo = hand_class[1]
    suited_flag = hand_class[2]
    suited_order = 0 if suited_flag == "s" else 1
    return (1, RANKS.index(hi), RANKS.index(lo), suited_order)


def summarize_weighted_range_by_class(weighted_range: List[WeightedCombo]) -> List[Dict[str, object]]:
    summary: Dict[str, Dict[str, object]] = {}
    for combo, weight in weighted_range:
        combo_text = combo_to_str(combo)
        card_a = combo_text[:2]
        card_b = combo_text[2:]
        hand_class = hand_to_class([card_a, card_b])

        if hand_class not in summary:
            summary[hand_class] = {
                "hand_class": hand_class,
                "combos": 0,
                "weight": 0.0,
            }
        summary[hand_class]["combos"] += 1
        summary[hand_class]["weight"] += float(weight)

    rows = list(summary.values())
    rows.sort(key=lambda row: _class_sort_key(row["hand_class"]))
    return rows


def format_class_summary(weighted_range: List[WeightedCombo], max_items: int = 40) -> str:
    rows = summarize_weighted_range_by_class(weighted_range)
    parts = []
    for row in rows[:max_items]:
        parts.append(f"{row['hand_class']}({row['combos']})")
    if len(rows) > max_items:
        parts.append(f"... +{len(rows) - max_items} classes")
    return " ".join(parts) if parts else "<empty>"


def format_combo_summary(weighted_range: List[WeightedCombo], max_items: int = 20) -> str:
    parts = []
    for combo, weight in weighted_range[:max_items]:
        parts.append(f"{combo_to_str(combo)}:{weight:.3f}")
    if len(weighted_range) > max_items:
        parts.append(f"... +{len(weighted_range) - max_items} combos")
    return " ".join(parts) if parts else "<empty>"


# =========================
# core normalization helpers
# =========================

def _normalize_cards(cards: Sequence[str]) -> List[str]:
    if len(cards) != len(set(cards)):
        raise ValueError("Повторяющиеся карты недопустимы")
    return [str(card) for card in cards]


def _normalize_street(street: str) -> str:
    value = str(street).strip().lower()
    if value not in STREET_CARD_COUNT:
        raise ValueError(f"Некорректная улица: {street}")
    return value




def _normalize_event(event: Dict[str, object]) -> PostflopEvent:
    if "street" not in event:
        raise ValueError("У события postflop нет поля 'street'")
    if "action" not in event:
        raise ValueError("У события postflop нет поля 'action'")

    street = _normalize_street(str(event["street"]))
    action = _normalize_action(str(event["action"]))
    is_all_in = bool(event.get("is_all_in", False))
    bet_pct_pot = float(event.get("bet_pct_pot", 0.0) or 0.0)

    if bet_pct_pot < 0:
        raise ValueError("bet_pct_pot не может быть отрицательным")

    return PostflopEvent(
        street=street,
        action=action,
        bet_pct_pot=bet_pct_pot,
        is_all_in=is_all_in,
    )


def _merge_range_meta(base_meta: Optional[Dict[str, object]] = None, extra_meta: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    merged: Dict[str, object] = {}
    if base_meta:
        merged.update(dict(base_meta))
    if extra_meta:
        merged.update(dict(extra_meta))
    merged.setdefault("range_contract", RANGE_SOURCE_CONTRACT)
    return merged



def _copy_range_source(
    range_source: RangeSource,
    *,
    source_type: Optional[str] = None,
    extra_meta: Optional[Dict[str, object]] = None,
) -> RangeSource:
    return RangeSource(
        name=range_source.name,
        source_type=str(source_type or range_source.source_type),
        raw_expr=range_source.raw_expr,
        normalized_expr=range_source.normalized_expr,
        weighted_combos=list(range_source.weighted_combos),
        meta=_merge_range_meta(range_source.meta, extra_meta),
    )



def _normalize_range_source(range_source: RangeSource) -> RangeSource:
    if not isinstance(range_source, RangeSource):
        raise TypeError("range_source должен быть объектом RangeSource")
    return _copy_range_source(range_source)


def _build_debug_range_source(
    villain_range: str,
    *,
    villain_pos: Optional[str],
    villain_action: Optional[str],
    range_owner: str,
    include_equity_debug: bool = False,
) -> RangeSource:
    debug_meta = {
        "debug_override": True,
        "villain_pos": villain_pos,
        "villain_action": villain_action,
        "range_owner": str(range_owner).lower(),
        "range_contract": RANGE_SOURCE_CONTRACT,
        "include_equity_debug": bool(include_equity_debug),
    }
    return build_range_source(
        str(villain_range),
        name=villain_pos or "Villain",
        source_type="debug_manual_range",
        meta=debug_meta,
    )


def _build_starting_range_source(
    *,
    range_source: Optional[RangeSource],
    villain_range: Optional[str],
    node_type: Optional[str],
    villain_pos: Optional[str],
    villain_action: Optional[str],
    opener_pos: Optional[str],
    three_bettor_pos: Optional[str],
    four_bettor_pos: Optional[str],
    limpers: int,
    callers: int,
    range_owner: str,
    include_equity_debug: bool = False,
) -> RangeSource:
    if range_source is not None:
        return _normalize_range_source(range_source)
    if villain_range:
        return _build_debug_range_source(
            villain_range,
            villain_pos=villain_pos,
            villain_action=villain_action,
            range_owner=range_owner,
            include_equity_debug=include_equity_debug,
        )
    if not node_type or not villain_pos or not villain_action:
        raise ValueError(
            "Нужно передать боевой range_source или debug-связку villain_range / node_type + villain_pos + villain_action"
        )

    return get_preflop_range_source(
        node_type=node_type,
        villain_pos=villain_pos,
        villain_action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
    )


def _weighted_combos_from_range_source(
    range_source: RangeSource,
    *,
    blocked_cards: Sequence[str],
) -> List[WeightedCombo]:
    source = _normalize_range_source(range_source)
    if source.normalized_expr:
        return parse_range(source.normalized_expr, blocked_cards=blocked_cards)
    if source.raw_expr:
        return parse_range(source.raw_expr, blocked_cards=blocked_cards)

    blocked_ints = {str_to_card(card) for card in blocked_cards}
    out: List[WeightedCombo] = []
    for combo, weight in source.weighted_combos:
        if combo[0] in blocked_ints or combo[1] in blocked_ints or combo[0] == combo[1]:
            continue
        out.append((combo, float(weight)))
    return out


def _range_summary_to_source(
    weighted_range: List[WeightedCombo],
    *,
    base_source: RangeSource,
    source_type: str,
    reason: Optional[str] = None,
    street: Optional[str] = None,
) -> RangeSource:
    meta = _merge_range_meta(
        base_source.meta,
        {
            "parent_source_type": base_source.source_type,
            "combo_count": len(weighted_range),
        },
    )
    if reason is not None:
        meta["reason"] = reason
    if street is not None:
        meta["street"] = street
    return RangeSource(
        name=base_source.name,
        source_type=source_type,
        raw_expr=None,
        normalized_expr=None,
        weighted_combos=list(weighted_range),
        meta=meta,
    )


def _resolve_context_inputs(
    *,
    hero_hand: Optional[Sequence[str]],
    board: Optional[Sequence[str]],
    dead_cards: Optional[Iterable[str]],
    street_context: Optional[PostflopContext],
    villain_in_position: bool,
) -> tuple[List[str], List[str], List[str], bool]:
    if street_context is not None:
        if hero_hand is None:
            hero_hand = street_context.hero_hand
        if board is None:
            board = street_context.board
        if dead_cards is None:
            dead_cards = street_context.dead_cards
        if not villain_in_position:
            villain_in_position = bool(street_context.line_context.get("villain_in_position", False))

    if hero_hand is None or board is None:
        raise ValueError("Нужно передать hero_hand и board либо напрямую, либо через street_context")

    resolved_hero_hand = _normalize_cards(list(hero_hand))
    resolved_board = _normalize_cards(list(board))
    resolved_dead = [] if dead_cards is None else _normalize_cards(list(dead_cards))
    return resolved_hero_hand, resolved_board, resolved_dead, villain_in_position


def _equity_vs_hero(
    villain_combo: Tuple[int, int],
    hero_hand: Sequence[str],
    board: Sequence[str],
    dead_cards: Iterable[str] | None = None,
) -> float:
    result = hand_vs_hand(
        hero_hand,
        villain_combo,
        board=board,
        dead_cards=dead_cards,
        method="exact",
    )
    return float(result["equity2"])


def _detail_equity_sort_value(value: object) -> float:
    if value is None:
        return float('-inf')
    return float(value)


def _format_equity_pct(value: object) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.2f}%"



def _is_aggressive(action: str) -> bool:
    return action in AGGRESSIVE_ACTIONS

def _continues_line_like_bet(action: str) -> bool:
    return action in LINE_CONTINUATION_ACTIONS


def _get_street_event(events: Sequence[PostflopEvent], street: str) -> Optional[PostflopEvent]:
    street = _normalize_street(street)
    for event in reversed(events):
        if event.street == street:
            return event
    return None


def _has_prior_check_raise(events: Sequence[PostflopEvent]) -> bool:
    return any(event.action == "check_raise" for event in events)


# =========================
# hand category engine
# =========================

def _card_rank_value(card: str) -> int:
    return RANK_VALUE[card[0].upper()]


def _card_suit(card: str) -> str:
    return card[1].lower()


def _rank_counter(cards: Sequence[str]) -> Dict[int, int]:
    counter: Dict[int, int] = {}
    for card in cards:
        rank_value = _card_rank_value(card)
        counter[rank_value] = counter.get(rank_value, 0) + 1
    return counter


def _suit_counter(cards: Sequence[str]) -> Dict[str, int]:
    counter: Dict[str, int] = {}
    for card in cards:
        suit = _card_suit(card)
        counter[suit] = counter.get(suit, 0) + 1
    return counter


def _rank_set_with_wheel(rank_values: Set[int]) -> Set[int]:
    out = set(rank_values)
    if 14 in out:
        out.add(1)
    return out


def _has_straight(rank_values: Set[int]) -> bool:
    ranks = _rank_set_with_wheel(rank_values)
    for straight in STRAIGHTS:
        if straight.issubset(ranks):
            return True
    return False


def _straight_draw_type(rank_values: Set[int]) -> Optional[str]:
    ranks = _rank_set_with_wheel(rank_values)
    for straight in STRAIGHTS:
        overlap = straight & ranks
        if len(overlap) != 4:
            continue
        missing = list(straight - overlap)[0]
        straight_min = min(straight)
        straight_max = max(straight)
        if missing == straight_min or missing == straight_max:
            return "oesd"
    for straight in STRAIGHTS:
        overlap = straight & ranks
        if len(overlap) == 4:
            return "gutshot"
    return None


def _best_board_rank_group(board: Sequence[str]) -> List[int]:
    return sorted({_card_rank_value(card) for card in board}, reverse=True)



def _board_texture_tags(board: Sequence[str]) -> Set[str]:
    tags: Set[str] = set()
    if not board:
        return tags
    ranks_desc = sorted({_card_rank_value(card) for card in board}, reverse=True)
    rank_counts = _rank_counter(board)
    suit_counts = _suit_counter(board)
    max_suit_count = max(suit_counts.values(), default=0)

    if any(count >= 2 for count in rank_counts.values()):
        tags.add("board_paired")
    if max_suit_count >= 3:
        tags.add("board_monotone")
    elif max_suit_count == 2:
        tags.add("board_two_tone")
    else:
        tags.add("board_rainbow")

    if ranks_desc and ranks_desc[0] == 14:
        tags.add("board_ace_high")
    elif ranks_desc and ranks_desc[0] == 13:
        tags.add("board_king_high")

    broadways = sum(1 for value in ranks_desc if value >= 10)
    if broadways >= 2:
        tags.add("board_broadway_dynamic")

    if len(ranks_desc) >= 3:
        span = max(ranks_desc) - min(ranks_desc)
        connected = span <= 4 or any(len(set(range(low, low + 5)) & set(ranks_desc)) >= 3 for low in range(2, 11))
        if connected:
            tags.add("board_connected")
        if connected and max(ranks_desc) <= 10:
            tags.add("board_low_connected")
        if connected or max_suit_count >= 2 or broadways >= 2:
            tags.add("board_wet_connected")
        if (not connected) and max_suit_count <= 1 and ranks_desc[0] >= 12 and not any(count >= 2 for count in rank_counts.values()):
            tags.add("board_dry_high")
    return tags


def _refined_pair_tags(hand_cards: Sequence[str], board: Sequence[str], made_tags: Set[str]) -> Set[str]:
    tags: Set[str] = set()
    if not board:
        return tags
    board_unique_desc = _best_board_rank_group(board)
    if not board_unique_desc:
        return tags
    h1_rank = _card_rank_value(hand_cards[0])
    h2_rank = _card_rank_value(hand_cards[1])
    is_pocket_pair = h1_rank == h2_rank

    if is_pocket_pair and "pocket_pair" in made_tags:
        pair_rank = h1_rank
        if len(board_unique_desc) >= 2 and pair_rank > board_unique_desc[1] and "overpair" not in made_tags:
            tags.add("pocket_pair_above_second_card")
        elif "overpair" not in made_tags:
            tags.add("pocket_pair_below_second_card")
            tags.add("weak_showdown")
        return tags

    matched = [rank for rank in (h1_rank, h2_rank) if rank in set(board_unique_desc)]
    if not matched:
        return tags
    matched_rank = max(matched)
    kicker_rank = min(h1_rank, h2_rank) if max(h1_rank, h2_rank) == matched_rank else max(h1_rank, h2_rank)

    if "top_pair" in made_tags:
        if kicker_rank >= 13:
            tags.add("top_pair_top_kicker")
        elif kicker_rank >= 10:
            tags.add("top_pair_good_kicker")
        else:
            tags.add("top_pair_weak_kicker")
            tags.add("weak_showdown")
    elif "middle_pair" in made_tags:
        if kicker_rank >= 12:
            tags.add("middle_pair_good_kicker")
        else:
            tags.add("middle_pair_weak_kicker")
            tags.add("weak_showdown")
    elif "bottom_pair" in made_tags:
        if kicker_rank >= 12:
            tags.add("bottom_pair_good_kicker")
        else:
            tags.add("bottom_pair_weak_kicker")
            tags.add("weak_showdown")
    return tags


def _blocker_tags(hand_cards: Sequence[str], board: Sequence[str], made_tags: Set[str]) -> Set[str]:
    tags: Set[str] = set()
    if len(board) < 5:
        return tags
    if made_tags & {"flush", "straight_flush", "full_house", "quads"}:
        return tags

    board_suits = _suit_counter(board)
    flush_suits = {suit for suit, count in board_suits.items() if count >= 3}
    for card in hand_cards:
        suit = _card_suit(card)
        rank = _card_rank_value(card)
        if suit in flush_suits and rank == 14:
            tags.add("nut_flush_blocker")
        elif suit in flush_suits and rank >= 13:
            tags.add("high_flush_blocker")

    board_ranks = set(_rank_set_with_wheel({_card_rank_value(card) for card in board}))
    hand_ranks = set(_rank_set_with_wheel({_card_rank_value(card) for card in hand_cards}))
    for straight in STRAIGHTS:
        if len(straight & board_ranks) >= 3 and straight & hand_ranks:
            tags.add("straight_blocker")
            break
    return tags


def _hand_made_tags(hand_cards: Sequence[str], board: Sequence[str]) -> Set[str]:
    tags: Set[str] = set()
    all_cards = list(hand_cards) + list(board)
    all_rank_counts = _rank_counter(all_cards)
    board_rank_counts = _rank_counter(board)
    board_unique_desc = _best_board_rank_group(board)

    h1_rank = _card_rank_value(hand_cards[0])
    h2_rank = _card_rank_value(hand_cards[1])
    is_pocket_pair = h1_rank == h2_rank

    all_suit_groups: Dict[str, List[int]] = {}
    for card in all_cards:
        suit = _card_suit(card)
        all_suit_groups.setdefault(suit, []).append(_card_rank_value(card))

    if any(len(suit_ranks) >= 5 and _has_straight(set(suit_ranks)) for suit_ranks in all_suit_groups.values()):
        tags.add("straight_flush")

    count_values = sorted(all_rank_counts.values(), reverse=True)
    if 4 in count_values:
        tags.add("quads")
    elif 3 in count_values and (2 in count_values or count_values.count(3) >= 2):
        tags.add("full_house")

    all_rank_set = {_card_rank_value(card) for card in all_cards}
    if _has_straight(all_rank_set):
        tags.add("straight")

    if any(count >= 5 for count in _suit_counter(all_cards).values()):
        tags.add("flush")

    if is_pocket_pair:
        tags.add("pocket_pair")
        pair_rank = h1_rank
        board_count = board_rank_counts.get(pair_rank, 0)
        if board_count >= 1 and all_rank_counts[pair_rank] == 3:
            tags.add("set")
        elif board_count == 0:
            max_board_rank = max(_card_rank_value(card) for card in board)
            if pair_rank > max_board_rank:
                tags.add("overpair")
            else:
                tags.add("underpair")
    else:
        matched_ranks = []
        for rank_value in {h1_rank, h2_rank}:
            if board_rank_counts.get(rank_value, 0) >= 1:
                matched_ranks.append(rank_value)

        if len(set(matched_ranks)) >= 2:
            tags.add("two_pair")
        elif len(matched_ranks) == 1:
            matched = matched_ranks[0]
            if board_rank_counts.get(matched, 0) >= 2:
                tags.add("trips")
            else:
                highest = board_unique_desc[0]
                lowest = board_unique_desc[-1]
                if matched == highest:
                    tags.add("top_pair")
                elif matched == lowest:
                    tags.add("bottom_pair")
                else:
                    tags.add("middle_pair")

    return tags


def _hand_draw_tags(hand_cards: Sequence[str], board: Sequence[str], made_tags: Set[str]) -> Set[str]:
    tags: Set[str] = set()
    street = _infer_street_from_board(board)
    all_cards = list(hand_cards) + list(board)

    if street in {"flop", "turn"} and not ({"straight", "straight_flush"} & made_tags):
        rank_values = {_card_rank_value(card) for card in all_cards}
        draw_type = _straight_draw_type(rank_values)
        if draw_type == "oesd":
            tags.add("oesd")
        elif draw_type == "gutshot":
            tags.add("gutshot")

    if street in {"flop", "turn"} and not ({"flush", "straight_flush"} & made_tags):
        all_suits = _suit_counter(all_cards)
        hand_suits = _suit_counter(hand_cards)
        board_suits = _suit_counter(board)

        if any(count == 4 for count in all_suits.values()):
            tags.add("flush_draw")
            for suit, count in all_suits.items():
                if count == 4 and hand_suits.get(suit, 0) >= 1:
                    if any(_card_suit(card) == suit and _card_rank_value(card) == 14 for card in hand_cards):
                        tags.add("nut_flush_draw")
                    break
        elif street == "flop":
            for suit, count in all_suits.items():
                if count == 3 and hand_suits.get(suit, 0) >= 1 and board_suits.get(suit, 0) >= 1:
                    tags.add("backdoor_flush_draw")
                    break

    pair_or_better = bool(made_tags & (PAIR_TAGS | STRONG_MADE_TAGS))
    if ("flush_draw" in tags and ("oesd" in tags or "gutshot" in tags)) or (
        pair_or_better and ("flush_draw" in tags or "oesd" in tags)
    ):
        tags.add("combo_draw")

    return tags


def _hand_high_card_tags(hand_cards: Sequence[str], board: Sequence[str], all_existing_tags: Set[str]) -> Set[str]:
    tags: Set[str] = set()
    hand_ranks = [_card_rank_value(card) for card in hand_cards]
    max_board_rank = max(_card_rank_value(card) for card in board)

    has_pair_or_better = bool(all_existing_tags & (PAIR_TAGS | STRONG_MADE_TAGS))
    if not has_pair_or_better:
        if 14 in hand_ranks:
            tags.add("ace_high")

        overcard_count = sum(1 for rank_value in hand_ranks if rank_value > max_board_rank)
        if overcard_count >= 2:
            tags.add("two_overcards")
        elif overcard_count == 1:
            tags.add("one_overcard")

    return tags


def categorize_villain_combo(combo: Tuple[int, int], board: Sequence[str]) -> Set[str]:
    combo_text = combo_to_str(combo)
    hand_cards = [combo_text[:2], combo_text[2:]]
    board = _normalize_cards(list(board))

    tags: Set[str] = set()
    made_tags = _hand_made_tags(hand_cards, board)
    tags.update(made_tags)

    draw_tags = _hand_draw_tags(hand_cards, board, made_tags)
    tags.update(draw_tags)

    high_card_tags = _hand_high_card_tags(hand_cards, board, tags)
    tags.update(high_card_tags)

    tags.update(_board_texture_tags(board))
    tags.update(_refined_pair_tags(hand_cards, board, made_tags))
    tags.update(_blocker_tags(hand_cards, board, made_tags))

    if not (tags - BOARD_TEXTURE_TAGS):
        tags.add("air")

    return tags



# =========================
# HERO postflop profile / Bluff Layer v1
# =========================

HERO_BUCKET_STRONG_MADE_ORDER = (
    "straight_flush",
    "quads",
    "full_house",
    "flush",
    "straight",
    "set",
    "trips",
    "two_pair",
)
HERO_BUCKET_THIN_VALUE_ORDER = (
    "overpair",
    "top_pair_top_kicker",
    "top_pair_good_kicker",
    "top_pair",
    "middle_pair_good_kicker",
    "pocket_pair_above_second_card",
)
HERO_BUCKET_MEDIUM_SHOWDOWN_ORDER = (
    "middle_pair",
    "bottom_pair",
    "underpair",
    "pocket_pair",
    "top_pair_weak_kicker",
    "middle_pair_weak_kicker",
    "bottom_pair_weak_kicker",
    "pocket_pair_below_second_card",
    "weak_showdown",
)
HERO_BUCKET_STRONG_DRAW_ORDER = ("combo_draw", "nut_flush_draw", "flush_draw", "oesd")
HERO_BUCKET_WEAK_DRAW_ORDER = ("gutshot", "backdoor_flush_draw")
HERO_BUCKET_BLOCKER_ORDER = ("nut_flush_blocker", "high_flush_blocker", "straight_blocker")
HERO_BUCKET_HIGH_CARD_ORDER = ("ace_high", "two_overcards", "one_overcard")
HERO_BUCKET_NAMES = (
    "VALUE",
    "THIN_VALUE",
    "SEMI_BLUFF",
    "BLOCKER_BLUFF",
    "BLUFF_CATCHER",
    "SHOWDOWN_CHECK",
    "GIVE_UP",
)


def _first_matching_tag(tags: Set[str], ordered_tags: Sequence[str]) -> Optional[str]:
    for tag in ordered_tags:
        if tag in tags:
            return tag
    return None


def _profile_card_to_str(card: object) -> str:
    if isinstance(card, int):
        return card_to_str(card)
    value = str(card).strip()
    if not value:
        raise ValueError("Карта не может быть пустой")
    return value


def _normalize_profile_cards(cards: Sequence[object], *, expected_len: Optional[int], label: str) -> List[str]:
    normalized = [_profile_card_to_str(card) for card in cards]
    if expected_len is not None and len(normalized) != expected_len:
        raise ValueError(f"{label} должен содержать {expected_len} карт(ы), получено {len(normalized)}")
    if len(normalized) != len(set(normalized)):
        raise ValueError(f"{label} содержит повторяющиеся карты")
    for card in normalized:
        # str_to_card validates rank/suit and keeps this public helper strict.
        str_to_card(card)
    return normalized


def _build_hero_tag_components(hero_hand: Sequence[object], board: Sequence[object]) -> Dict[str, Set[str]]:
    hand_cards = _normalize_profile_cards(list(hero_hand), expected_len=2, label="hero_hand")
    board_cards = _normalize_profile_cards(list(board), expected_len=None, label="board")
    if len(board_cards) not in {3, 4, 5}:
        raise ValueError("board должен содержать 3, 4 или 5 карт")
    if set(hand_cards) & set(board_cards):
        raise ValueError("hero_hand и board пересекаются")

    made_tags = _hand_made_tags(hand_cards, board_cards)
    draw_tags = _hand_draw_tags(hand_cards, board_cards, made_tags)
    tags: Set[str] = set(made_tags)
    tags.update(draw_tags)
    high_card_tags = _hand_high_card_tags(hand_cards, board_cards, tags)
    tags.update(high_card_tags)
    board_texture_tags = _board_texture_tags(board_cards)
    refined_pair_tags = _refined_pair_tags(hand_cards, board_cards, made_tags)
    blocker_tags = _blocker_tags(hand_cards, board_cards, made_tags)
    tags.update(board_texture_tags)
    tags.update(refined_pair_tags)
    tags.update(blocker_tags)
    if not (tags - BOARD_TEXTURE_TAGS):
        tags.add("air")

    return {
        "all": tags,
        "made": made_tags | refined_pair_tags,
        "draw": draw_tags,
        "blocker": blocker_tags,
        "high_card": high_card_tags,
        "board_texture": board_texture_tags,
    }


def build_hero_postflop_profile(
    hero_hand: Sequence[object],
    board: Sequence[object],
    *,
    facing_bet: bool = False,
) -> Dict[str, object]:
    """Official HERO hand profile for Bluff Layer v1.

    postflop_advisor owns the hand/category understanding. hero_decision can
    consume this payload and only decide which legal action to take.
    """
    hand_cards = _normalize_profile_cards(list(hero_hand), expected_len=2, label="hero_hand")
    board_cards = _normalize_profile_cards(list(board), expected_len=None, label="board")
    components = _build_hero_tag_components(hand_cards, board_cards)
    tags = set(components["all"])
    street = _infer_street_from_board(board_cards)

    made_hand_class = (
        _first_matching_tag(tags, HERO_BUCKET_STRONG_MADE_ORDER)
        or _first_matching_tag(tags, HERO_BUCKET_THIN_VALUE_ORDER)
        or _first_matching_tag(tags, HERO_BUCKET_MEDIUM_SHOWDOWN_ORDER)
        or "none"
    )
    draw_class = (
        _first_matching_tag(tags, HERO_BUCKET_STRONG_DRAW_ORDER)
        or _first_matching_tag(tags, HERO_BUCKET_WEAK_DRAW_ORDER)
        or "none"
    )
    blocker_class = _first_matching_tag(tags, HERO_BUCKET_BLOCKER_ORDER) or "none"

    has_strong_made = bool(tags & set(HERO_BUCKET_STRONG_MADE_ORDER))
    has_thin_value = bool(tags & set(HERO_BUCKET_THIN_VALUE_ORDER))
    has_medium_showdown = bool(tags & set(HERO_BUCKET_MEDIUM_SHOWDOWN_ORDER))
    has_strong_draw = bool(tags & set(HERO_BUCKET_STRONG_DRAW_ORDER))
    has_weak_draw = bool(tags & set(HERO_BUCKET_WEAK_DRAW_ORDER))
    has_blocker = bool(tags & set(HERO_BUCKET_BLOCKER_ORDER))
    has_high_card = bool(tags & set(HERO_BUCKET_HIGH_CARD_ORDER))
    has_air = "air" in tags or not (
        has_strong_made
        or has_thin_value
        or has_medium_showdown
        or has_strong_draw
        or has_weak_draw
        or has_blocker
        or has_high_card
    )

    if has_strong_made:
        hero_bucket = "VALUE"
        showdown_value = "strong"
        selected_reason = "strong made hand"
    elif has_thin_value:
        hero_bucket = "THIN_VALUE"
        showdown_value = "medium_strong"
        selected_reason = "thin value made hand"
    elif has_strong_draw or (has_weak_draw and has_high_card):
        hero_bucket = "SEMI_BLUFF"
        showdown_value = "low"
        selected_reason = "draw with equity"
    elif has_blocker and not has_medium_showdown:
        hero_bucket = "BLOCKER_BLUFF"
        showdown_value = "low"
        selected_reason = "blocker without clear showdown value"
    elif has_medium_showdown or has_high_card:
        hero_bucket = "BLUFF_CATCHER" if bool(facing_bet) else "SHOWDOWN_CHECK"
        showdown_value = "medium" if has_medium_showdown else "weak"
        selected_reason = "showdown value facing bet" if bool(facing_bet) else "showdown value prefers pot control"
    else:
        hero_bucket = "GIVE_UP"
        showdown_value = "none"
        selected_reason = "no equity, no blocker, no showdown value"

    if hero_bucket == "VALUE":
        preferred_size_pct = 70.0 if ("board_wet_connected" in tags or "board_monotone" in tags or street == "river") else 50.0
    elif hero_bucket == "THIN_VALUE":
        preferred_size_pct = 33.0
    elif hero_bucket == "SEMI_BLUFF":
        preferred_size_pct = 50.0 if street == "flop" else 70.0
    elif hero_bucket == "BLOCKER_BLUFF":
        preferred_size_pct = 70.0 if street == "river" else 33.0
    else:
        preferred_size_pct = None

    return {
        "contract_version": "hero_postflop_profile_v1",
        "source": "postflop_advisor.build_hero_postflop_profile",
        "hero_hand": list(hand_cards),
        "board": list(board_cards),
        "street": street,
        "facing_bet": bool(facing_bet),
        "hero_tags": tuple(sorted(tags)),
        "made_tags": tuple(sorted(components["made"])),
        "draw_tags": tuple(sorted(components["draw"])),
        "blocker_tags": tuple(sorted(components["blocker"])),
        "high_card_tags": tuple(sorted(components["high_card"])),
        "board_texture": tuple(sorted(components["board_texture"])),
        "hero_bucket": hero_bucket,
        "made_hand_class": made_hand_class,
        "draw_class": draw_class,
        "blocker_class": blocker_class,
        "showdown_value": showdown_value,
        "preferred_size_pct": preferred_size_pct,
        "selected_reason": selected_reason,
        "flags": {
            "has_strong_made": has_strong_made,
            "has_thin_value": has_thin_value,
            "has_medium_showdown": has_medium_showdown,
            "has_strong_draw": has_strong_draw,
            "has_weak_draw": has_weak_draw,
            "has_blocker": has_blocker,
            "has_high_card": has_high_card,
            "has_air": has_air,
        },
    }

# =========================
# rule helpers
# =========================



def get_postflop_bet_rule(bet_pct_pot: float, *, is_all_in: bool = False) -> PostflopRule:
    """Backward-compatible helper for old code paths: interpret as flop bet."""
    return resolve_postflop_rule(
        street="flop",
        action="bet",
        bet_pct_pot=bet_pct_pot,
        is_all_in=is_all_in,
        previous_events=[],
        villain_in_position=False,
    )




# =========================
# filtering core
# =========================

def _build_range_summary(weighted_range: List[WeightedCombo]) -> Dict[str, object]:
    return {
        "combo_count": len(weighted_range),
        "class_count": len(summarize_weighted_range_by_class(weighted_range)),
        "class_summary": format_class_summary(weighted_range),
        "combo_summary": format_combo_summary(weighted_range),
        "weighted_combos": weighted_range,
    }


def _filter_weighted_range(
    weighted_range: List[WeightedCombo],
    *,
    hero_hand: Sequence[str],
    board: Sequence[str],
    dead_cards: Sequence[str],
    rule: PostflopRule,
    include_equity_debug: bool = False,
) -> Dict[str, object]:
    kept: List[WeightedCombo] = []
    removed: List[WeightedCombo] = []
    kept_details: List[Dict[str, object]] = []
    removed_details: List[Dict[str, object]] = []

    if rule.keep_full_range:
        kept = list(weighted_range)
        for combo, weight in kept:
            combo_text = combo_to_str(combo)
            tags = sorted(categorize_villain_combo(combo, board))
            kept_details.append({
                "combo": combo_text,
                "hand_class": hand_to_class([combo_text[:2], combo_text[2:]]),
                "weight": float(weight),
                "equity_vs_hero": None,
                "kept": True,
                "tags": tags,
            })
    else:
        allowed = set(rule.keep_any_tags)
        for combo, weight in weighted_range:
            combo_text = combo_to_str(combo)
            tags = sorted(categorize_villain_combo(combo, board))
            equity_vs_hero = (
                _equity_vs_hero(combo, hero_hand, board, dead_cards=dead_cards)
                if include_equity_debug
                else None
            )
            keep_combo = bool(allowed.intersection(tags))
            detail = {
                "combo": combo_text,
                "hand_class": hand_to_class([combo_text[:2], combo_text[2:]]),
                "weight": float(weight),
                "equity_vs_hero": equity_vs_hero,
                "kept": keep_combo,
                "tags": tags,
            }
            if keep_combo:
                weight_multiplier = _postflop_range_weight_multiplier(set(tags), rule=rule)
                adjusted_weight = float(weight) * float(weight_multiplier)
                detail["weight_original"] = float(weight)
                detail["range_weight_multiplier"] = float(weight_multiplier)
                detail["weight"] = float(adjusted_weight)
                if adjusted_weight > 0.0:
                    kept.append((combo, adjusted_weight))
                    kept_details.append(detail)
                else:
                    detail["kept"] = False
                    removed.append((combo, weight))
                    removed_details.append(detail)
            else:
                removed.append((combo, weight))
                removed_details.append(detail)

        kept_details.sort(key=lambda item: (-_detail_equity_sort_value(item["equity_vs_hero"]), _class_sort_key(item["hand_class"])))
        removed_details.sort(key=lambda item: (_detail_equity_sort_value(item["equity_vs_hero"]), _class_sort_key(item["hand_class"])))

    return {
        "range_before": _build_range_summary(weighted_range),
        "range_after": _build_range_summary(kept),
        "removed": _build_range_summary(removed),
        "kept_details": kept_details,
        "removed_details": removed_details,
    }


# =========================
# public APIs
# =========================

def filter_postflop_range(
    hero_hand: Optional[Sequence[str]] = None,
    board: Optional[Sequence[str]] = None,
    *,
    range_source: Optional[RangeSource] = None,
    street_context: Optional[PostflopContext] = None,
    bet_pct_pot: float,
    include_equity_debug: bool = False,
    is_all_in: bool = False,
    action: str = "bet",
    villain_range: Optional[str] = None,
    node_type: Optional[str] = None,
    villain_pos: Optional[str] = None,
    villain_action: Optional[str] = None,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    dead_cards: Iterable[str] | None = None,
    previous_events: Optional[Sequence[Dict[str, object]]] = None,
    villain_in_position: bool = False,
    range_owner: str = "opponent",
) -> Dict[str, object]:
    hero_hand, board, dead_cards, villain_in_position = _resolve_context_inputs(
        hero_hand=hero_hand,
        board=board,
        dead_cards=dead_cards,
        street_context=street_context,
        villain_in_position=villain_in_position,
    )

    if len(hero_hand) != 2:
        raise ValueError("hero_hand должен содержать ровно 2 карты")
    if not (3 <= len(board) <= 5):
        raise ValueError("board должен содержать от 3 до 5 карт")

    all_known = hero_hand + list(board) + list(dead_cards)
    if len(all_known) != len(set(all_known)):
        raise ValueError("hero_hand / board / dead_cards пересекаются")

    street = _infer_street_from_board(board)
    prev = [_normalize_event(event) for event in (previous_events or [])]
    rule = resolve_postflop_rule(
        street=street,
        action=action,
        bet_pct_pot=bet_pct_pot,
        is_all_in=is_all_in,
        previous_events=prev,
        villain_in_position=villain_in_position,
    )

    starting_source = _build_starting_range_source(
        range_source=range_source,
        villain_range=villain_range,
        node_type=node_type,
        villain_pos=villain_pos,
        villain_action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
        include_equity_debug=include_equity_debug,
    )

    blocked_cards = hero_hand + list(board) + list(dead_cards)
    range_before = _weighted_combos_from_range_source(starting_source, blocked_cards=blocked_cards)
    filtered = _filter_weighted_range(
        range_before,
        hero_hand=hero_hand,
        board=board,
        dead_cards=dead_cards,
        rule=rule,
        include_equity_debug=include_equity_debug,
    )

    range_before_source = _range_summary_to_source(
        filtered["range_before"]["weighted_combos"],
        base_source=starting_source,
        source_type="postflop_range_before",
        reason=rule.reason,
        street=street,
    )
    range_after_source = _range_summary_to_source(
        filtered["range_after"]["weighted_combos"],
        base_source=starting_source,
        source_type="postflop_range_after",
        reason=rule.reason,
        street=street,
    )

    report = {
        "street": street,
        "action": action,
        "hero_hand": hero_hand,
        "board": list(board),
        "dead_cards": list(dead_cards),
        "bet_pct_pot": float(bet_pct_pot),
        "bet_bucket": rule.bucket,
        "is_all_in": bool(is_all_in),
        "range_owner": str(range_owner).lower(),
        "equity_threshold": float(rule.min_equity),
        "keep_full_range": bool(rule.keep_full_range),
        "filter_mode": rule.filter_mode,
        "allowed_tags": list(rule.keep_any_tags),
        "reason": rule.reason,
        "starting_range_expr": str(starting_source.normalized_expr or starting_source.raw_expr or ""),
        "starting_range_source": starting_source,
        "range_before_source": range_before_source,
        "range_after_source": range_after_source,
        "range_contract": RANGE_SOURCE_CONTRACT,
        "include_equity_debug": bool(include_equity_debug),
        **filtered,
    }
    return report


def _analyze_postflop_line_core(
    *,
    hero_hand: Optional[Sequence[str]] = None,
    board_target: Optional[Sequence[str]] = None,
    range_source: Optional[RangeSource] = None,
    street_context: Optional[PostflopContext] = None,
    events: Sequence[Dict[str, object]],
    include_equity_debug: bool = False,
    villain_range: Optional[str] = None,
    node_type: Optional[str] = None,
    villain_pos: Optional[str] = None,
    villain_action: Optional[str] = None,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    dead_cards: Iterable[str] | None = None,
    villain_in_position: bool = False,
    range_owner: str = "opponent",
    require_full_runout: bool,
) -> Dict[str, object]:
    context_board = None if street_context is None else street_context.board
    board_input = context_board if context_board is not None else board_target
    hero_hand, resolved_board, dead_cards, villain_in_position = _resolve_context_inputs(
        hero_hand=hero_hand,
        board=board_input,
        dead_cards=dead_cards,
        street_context=street_context,
        villain_in_position=villain_in_position,
    )
    board_cards = resolved_board if board_target is None else _normalize_cards(list(board_target))

    if len(hero_hand) != 2:
        raise ValueError("hero_hand должен содержать ровно 2 карты")
    if require_full_runout:
        if len(board_cards) != 5:
            raise ValueError("board_runout должен содержать ровно 5 карт")
    elif len(board_cards) not in (3, 4):
        raise ValueError("partial board должен содержать 3 или 4 карты")

    all_known = hero_hand + list(board_cards) + list(dead_cards)
    if len(all_known) != len(set(all_known)):
        raise ValueError("hero_hand / board / dead_cards пересекаются")

    current_street = _infer_street_from_board(board_cards)
    current_board_count = len(board_cards)
    normalized_events = [_normalize_event(event) for event in events]
    applicable_events: List[PostflopEvent] = []
    skipped_events: List[Dict[str, object]] = []
    for event in normalized_events:
        required_board = STREET_CARD_COUNT[event.street]
        if required_board > current_board_count:
            skipped_events.append(
                {
                    "street": event.street,
                    "action": event.action,
                    "bet_pct_pot": float(event.bet_pct_pot),
                    "is_all_in": bool(event.is_all_in),
                    "reason": "event_street_not_available_on_current_board",
                }
            )
            continue
        applicable_events.append(event)

    starting_source = _build_starting_range_source(
        range_source=range_source,
        villain_range=villain_range,
        node_type=node_type,
        villain_pos=villain_pos,
        villain_action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        range_owner=range_owner,
        include_equity_debug=include_equity_debug,
    )

    blocked_cards = hero_hand + list(board_cards) + list(dead_cards)
    current_range = _weighted_combos_from_range_source(starting_source, blocked_cards=blocked_cards)
    starting_range_summary = _build_range_summary(current_range)

    steps: List[Dict[str, object]] = []
    previous_events: List[PostflopEvent] = []

    for event in applicable_events:
        board = board_cards[:STREET_CARD_COUNT[event.street]]
        rule = resolve_postflop_rule(
            street=event.street,
            action=event.action,
            bet_pct_pot=event.bet_pct_pot,
            is_all_in=event.is_all_in,
            previous_events=previous_events,
            villain_in_position=villain_in_position,
        )
        filtered = _filter_weighted_range(
            current_range,
            hero_hand=hero_hand,
            board=board,
            dead_cards=dead_cards,
            rule=rule,
            include_equity_debug=include_equity_debug,
        )
        step_before_source = _range_summary_to_source(
            filtered["range_before"]["weighted_combos"],
            base_source=starting_source,
            source_type="postflop_step_before",
            reason=rule.reason,
            street=event.street,
        )
        step_after_source = _range_summary_to_source(
            filtered["range_after"]["weighted_combos"],
            base_source=starting_source,
            source_type="postflop_step_after",
            reason=rule.reason,
            street=event.street,
        )
        step = {
            "street": event.street,
            "action": event.action,
            "bet_pct_pot": float(event.bet_pct_pot),
            "bet_bucket": rule.bucket,
            "is_all_in": bool(event.is_all_in),
            "keep_full_range": bool(rule.keep_full_range),
            "filter_mode": rule.filter_mode,
            "allowed_tags": list(rule.keep_any_tags),
            "equity_threshold": float(rule.min_equity),
            "reason": rule.reason,
            "effective_action_for_rule": _rule_action(event.action),
            "range_before_source": step_before_source,
            "range_after_source": step_after_source,
            **filtered,
        }
        steps.append(step)
        current_range = filtered["range_after"]["weighted_combos"]
        previous_events.append(event)

    final_range_source = _range_summary_to_source(
        current_range,
        base_source=starting_source,
        source_type="postflop_final_range",
        street=current_street,
    )

    result = {
        "hero_hand": hero_hand,
        "dead_cards": list(dead_cards),
        "resolved_street": current_street,
        "range_owner": str(range_owner).lower(),
        "starting_range_expr": str(starting_source.normalized_expr or starting_source.raw_expr or ""),
        "starting_range_source": starting_source,
        "starting_range": starting_range_summary,
        "steps": steps,
        "final_range": _build_range_summary(current_range),
        "final_range_source": final_range_source,
        "range_contract": RANGE_SOURCE_CONTRACT,
    }
    if require_full_runout:
        result["board_runout"] = list(board_cards)
    else:
        result["board"] = list(board_cards)
        result["board_card_count"] = len(board_cards)
    if skipped_events:
        result["warnings"] = [
            f"Skipped {len(skipped_events)} future postflop event(s) beyond current board"
        ]
        result["skipped_events"] = skipped_events
    else:
        result["warnings"] = []
        result["skipped_events"] = []
    return result


def analyze_postflop_line(
    *,
    hero_hand: Optional[Sequence[str]] = None,
    board_runout: Optional[Sequence[str]] = None,
    range_source: Optional[RangeSource] = None,
    street_context: Optional[PostflopContext] = None,
    events: Sequence[Dict[str, object]],
    include_equity_debug: bool = False,
    villain_range: Optional[str] = None,
    node_type: Optional[str] = None,
    villain_pos: Optional[str] = None,
    villain_action: Optional[str] = None,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    dead_cards: Iterable[str] | None = None,
    villain_in_position: bool = False,
    range_owner: str = "opponent",
) -> Dict[str, object]:
    return _analyze_postflop_line_core(
        hero_hand=hero_hand,
        board_target=board_runout,
        range_source=range_source,
        street_context=street_context,
        events=events,
        include_equity_debug=include_equity_debug,
        villain_range=villain_range,
        node_type=node_type,
        villain_pos=villain_pos,
        villain_action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        dead_cards=dead_cards,
        villain_in_position=villain_in_position,
        range_owner=range_owner,
        require_full_runout=True,
    )


def analyze_partial_postflop_line(
    *,
    hero_hand: Optional[Sequence[str]] = None,
    board: Optional[Sequence[str]] = None,
    range_source: Optional[RangeSource] = None,
    street_context: Optional[PostflopContext] = None,
    events: Sequence[Dict[str, object]],
    include_equity_debug: bool = False,
    villain_range: Optional[str] = None,
    node_type: Optional[str] = None,
    villain_pos: Optional[str] = None,
    villain_action: Optional[str] = None,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    limpers: int = 0,
    callers: int = 0,
    dead_cards: Iterable[str] | None = None,
    villain_in_position: bool = False,
    range_owner: str = "opponent",
) -> Dict[str, object]:
    return _analyze_postflop_line_core(
        hero_hand=hero_hand,
        board_target=board,
        range_source=range_source,
        street_context=street_context,
        events=events,
        include_equity_debug=include_equity_debug,
        villain_range=villain_range,
        node_type=node_type,
        villain_pos=villain_pos,
        villain_action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        limpers=limpers,
        callers=callers,
        dead_cards=dead_cards,
        villain_in_position=villain_in_position,
        range_owner=range_owner,
        require_full_runout=False,
    )


# =========================
# multiway public API
# =========================


def analyze_multiway_partial_postflop_line(
    *,
    hero_hand: Sequence[str],
    board: Sequence[str],
    players: Sequence[Dict[str, object]],
    dead_cards: Iterable[str] | None = None,
    include_equity_debug: bool = False,
) -> Dict[str, object]:
    hero_hand = _normalize_cards(list(hero_hand))
    board = _normalize_cards(list(board))
    dead_cards = [] if dead_cards is None else _normalize_cards(list(dead_cards))

    if len(hero_hand) != 2:
        raise ValueError("hero_hand должен содержать ровно 2 карты")
    if len(board) not in (3, 4):
        raise ValueError("partial board должен содержать 3 или 4 карты")
    if not players:
        raise ValueError("Для multiway анализа нужно передать хотя бы одного оппонента")

    results: List[Dict[str, object]] = []
    for index, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            raise ValueError("Каждый элемент players должен быть словарем с настройками игрока")

        player_name = str(player.get("name") or f"Villain{index}")
        player_report = analyze_partial_postflop_line(
            hero_hand=hero_hand,
            board=board,
            range_source=player.get("range_source"),
            events=player.get("events") or [],
            include_equity_debug=bool(player.get("include_equity_debug", include_equity_debug)),
            villain_range=player.get("villain_range"),
            node_type=player.get("node_type"),
            villain_pos=player.get("villain_pos"),
            villain_action=player.get("villain_action"),
            opener_pos=player.get("opener_pos"),
            three_bettor_pos=player.get("three_bettor_pos"),
            four_bettor_pos=player.get("four_bettor_pos"),
            limpers=int(player.get("limpers", 0) or 0),
            callers=int(player.get("callers", 0) or 0),
            dead_cards=dead_cards,
            villain_in_position=bool(player.get("villain_in_position", False)),
            range_owner=str(player.get("range_owner", "opponent")),
        )
        results.append({
            "name": player_name,
            "villain_pos": player.get("villain_pos"),
            "villain_action": player.get("villain_action"),
            "range_source": player.get("range_source") or player_report.get("starting_range_source"),
            "starting_range_source": player_report.get("starting_range_source"),
            "final_range_source": player_report.get("final_range_source"),
            "report": player_report,
        })

    return {
        "hero_hand": hero_hand,
        "board": list(board),
        "resolved_street": _infer_street_from_board(board),
        "dead_cards": list(dead_cards),
        "player_count": len(results) + 1,
        "range_contract": RANGE_SOURCE_CONTRACT,
        "villain_reports": results,
    }


# =========================
# multiway public API
# =========================

def analyze_multiway_postflop_line(
    *,
    hero_hand: Sequence[str],
    board_runout: Sequence[str],
    players: Sequence[Dict[str, object]],
    dead_cards: Iterable[str] | None = None,
    include_equity_debug: bool = False,
) -> Dict[str, object]:
    hero_hand = _normalize_cards(list(hero_hand))
    board_runout = _normalize_cards(list(board_runout))
    dead_cards = [] if dead_cards is None else _normalize_cards(list(dead_cards))

    if len(hero_hand) != 2:
        raise ValueError("hero_hand должен содержать ровно 2 карты")
    if len(board_runout) != 5:
        raise ValueError("board_runout должен содержать ровно 5 карт")
    if not players:
        raise ValueError("Для multiway анализа нужно передать хотя бы одного оппонента")

    results: List[Dict[str, object]] = []
    for index, player in enumerate(players, start=1):
        if not isinstance(player, dict):
            raise ValueError("Каждый элемент players должен быть словарем с настройками игрока")

        player_name = str(player.get("name") or f"Villain{index}")
        player_report = analyze_postflop_line(
            hero_hand=hero_hand,
            board_runout=board_runout,
            range_source=player.get("range_source"),
            events=player.get("events") or [],
            include_equity_debug=bool(player.get("include_equity_debug", include_equity_debug)),
            villain_range=player.get("villain_range"),
            node_type=player.get("node_type"),
            villain_pos=player.get("villain_pos"),
            villain_action=player.get("villain_action"),
            opener_pos=player.get("opener_pos"),
            three_bettor_pos=player.get("three_bettor_pos"),
            four_bettor_pos=player.get("four_bettor_pos"),
            limpers=int(player.get("limpers", 0) or 0),
            callers=int(player.get("callers", 0) or 0),
            dead_cards=dead_cards,
            villain_in_position=bool(player.get("villain_in_position", False)),
            range_owner=str(player.get("range_owner", "opponent")),
        )
        results.append({
            "name": player_name,
            "villain_pos": player.get("villain_pos"),
            "villain_action": player.get("villain_action"),
            "range_source": player.get("range_source") or player_report.get("starting_range_source"),
            "starting_range_source": player_report.get("starting_range_source"),
            "final_range_source": player_report.get("final_range_source"),
            "report": player_report,
        })

    return {
        "hero_hand": hero_hand,
        "board_runout": list(board_runout),
        "dead_cards": list(dead_cards),
        "player_count": len(results) + 1,
        "range_contract": RANGE_SOURCE_CONTRACT,
        "villain_reports": results,
    }


def format_multiway_postflop_report(report: Dict[str, object], *, max_kept: int = 12, max_removed: int = 8) -> str:
    lines: List[str] = []
    lines.append("=== MULTIWAY POSTFLOP REPORT ===")
    lines.append(f"Hero hand: {' '.join(report['hero_hand'])}")
    lines.append(f"Runout: {' '.join(report['board_runout'])}")
    lines.append(f"Players in hand: {report['player_count']}")
    lines.append("")

    for item in report["villain_reports"]:
        player_report = item["report"]
        lines.append(f"[{item['name']}] pos={item['villain_pos']} preflop={item['villain_action']}")
        lines.append(f"  preflop source: {player_report['starting_range_expr']}")
        lines.append(
            f"  start: combos={player_report['starting_range']['combo_count']} classes={player_report['starting_range']['class_count']}"
        )
        lines.append(f"  classes: {player_report['starting_range']['class_summary']}")
        for step in player_report["steps"]:
            lines.append(
                f"  {step['street'].upper()} {step['action']} {step['bet_pct_pot']:.1f}% -> {step['bet_bucket']} | after {step['range_after']['combo_count']} combos"
            )
            lines.append(f"    rule: {step['reason']}")
            if not step["keep_full_range"]:
                lines.append(f"    tags: {', '.join(step['allowed_tags'])}")
                for kept in step["kept_details"][:max_kept]:
                    lines.append(
                        f"      keep {kept['combo']} {kept['hand_class']} tags={','.join(kept['tags'])}"
                    )
                for removed in step["removed_details"][:max_removed]:
                    lines.append(
                        f"      drop {removed['combo']} {removed['hand_class']} tags={','.join(removed['tags'])}"
                    )
        lines.append(
            f"  final: combos={player_report['final_range']['combo_count']} classes={player_report['final_range']['class_count']}"
        )
        lines.append(f"  final classes: {player_report['final_range']['class_summary']}")
        lines.append("")

    return "\n".join(lines)


# =========================
# formatters
# =========================

def format_postflop_report(report: Dict[str, object], *, max_kept: int = 30, max_removed: int = 20) -> str:
    lines: List[str] = []
    lines.append("=== POSTFLOP RANGE REPORT ===")
    lines.append(f"Hero hand: {' '.join(report['hero_hand'])}")
    lines.append(f"Board: {' '.join(report['board'])}")
    lines.append(f"Bet size: {report['bet_pct_pot']:.1f}% pot")
    lines.append(f"Bucket: {report['bet_bucket']}")
    lines.append(f"Rule: {report['reason']}")
    if report["filter_mode"] != "keep_all":
        lines.append(f"Allowed tags: {', '.join(report['allowed_tags'])}")
    lines.append("")
    lines.append(f"Preflop range source: {report['starting_range_expr']}")
    lines.append("")

    before = report["range_before"]
    after = report["range_after"]
    removed = report["removed"]

    lines.append("Range BEFORE:")
    lines.append(f"  combos={before['combo_count']} classes={before['class_count']}")
    lines.append(f"  classes: {before['class_summary']}")
    lines.append(f"  sample combos: {before['combo_summary']}")
    lines.append("")

    lines.append("Range AFTER:")
    lines.append(f"  combos={after['combo_count']} classes={after['class_count']}")
    lines.append(f"  classes: {after['class_summary']}")
    lines.append(f"  sample combos: {after['combo_summary']}")
    lines.append("")

    if not report["keep_full_range"]:
        lines.append("Top kept combos:")
        for item in report["kept_details"][:max_kept]:
            lines.append(
                f"  {item['combo']}  {item['hand_class']}  tags={','.join(item['tags'])}  eq={_format_equity_pct(item['equity_vs_hero'])}"
            )
        lines.append("")

        lines.append("Removed combos:")
        for item in report["removed_details"][:max_removed]:
            lines.append(
                f"  {item['combo']}  {item['hand_class']}  tags={','.join(item['tags'])}  eq={_format_equity_pct(item['equity_vs_hero'])}"
            )
        if removed["combo_count"] > max_removed:
            lines.append(f"  ... +{removed['combo_count'] - max_removed} combos")
    return "\n".join(lines)


def format_postflop_line_report(line_report: Dict[str, object], *, max_kept: int = 20, max_removed: int = 12) -> str:
    lines: List[str] = []
    lines.append("=== POSTFLOP LINE REPORT ===")
    lines.append(f"Hero hand: {' '.join(line_report['hero_hand'])}")
    lines.append(f"Runout: {' '.join(line_report['board_runout'])}")
    lines.append(f"Preflop range source: {line_report['starting_range_expr']}")
    lines.append("")
    lines.append("Starting range:")
    lines.append(
        f"  combos={line_report['starting_range']['combo_count']} classes={line_report['starting_range']['class_count']}"
    )
    lines.append(f"  classes: {line_report['starting_range']['class_summary']}")
    lines.append("")

    for step in line_report["steps"]:
        lines.append(f"[{step['street'].upper()}] {step['action']} {step['bet_pct_pot']:.1f}% pot -> {step['bet_bucket']}")
        lines.append(f"  filter_mode: {step['filter_mode']}")
        lines.append(f"  rule: {step['reason']}")
        if step["filter_mode"] != "keep_all":
            lines.append(f"  allowed_tags: {', '.join(step['allowed_tags'])}")
        lines.append(
            f"  before: combos={step['range_before']['combo_count']} classes={step['range_before']['class_count']}"
        )
        lines.append(
            f"  after:  combos={step['range_after']['combo_count']} classes={step['range_after']['class_count']}"
        )
        lines.append(f"  classes: {step['range_after']['class_summary']}")
        if not step["keep_full_range"]:
            lines.append("  top_kept:")
            for item in step["kept_details"][:max_kept]:
                lines.append(
                    f"    {item['combo']} {item['hand_class']} tags={','.join(item['tags'])} eq={_format_equity_pct(item['equity_vs_hero'])}"
                )
            if step["removed"]["combo_count"]:
                lines.append("  top_removed:")
                for item in step["removed_details"][:max_removed]:
                    lines.append(
                        f"    {item['combo']} {item['hand_class']} tags={','.join(item['tags'])} eq={_format_equity_pct(item['equity_vs_hero'])}"
                    )
        lines.append("")

    lines.append("Final range:")
    lines.append(
        f"  combos={line_report['final_range']['combo_count']} classes={line_report['final_range']['class_count']}"
    )
    lines.append(f"  classes: {line_report['final_range']['class_summary']}")
    return "\n".join(lines)


__all__ = [
    "PostflopRule",
    "PostflopEvent",
    "classify_bet_size",
    "get_preflop_range_source",
    "get_preflop_action_range",
    "summarize_weighted_range_by_class",
    "format_class_summary",
    "format_combo_summary",
    "categorize_villain_combo",
    "resolve_postflop_rule",
    "filter_postflop_range",
    "analyze_postflop_line",
    "analyze_multiway_postflop_line",
    "format_postflop_report",
    "format_postflop_line_report",
    "format_multiway_postflop_report",
]

if __name__ == "__main__":
    line_report = analyze_postflop_line(
        hero_hand=["As", "Kd"],
        board_runout=["2c", "7d", "Th", "Jh", "Ac"],
        node_type="unopened",
        villain_pos="CO",
        villain_action="raise",
        range_owner="opponent",
        villain_in_position=True,
        events=[
            {"street": "flop", "action": "bet", "bet_pct_pot": 75.0, "is_all_in": False},
            {"street": "turn", "action": "bet", "bet_pct_pot": 80.0, "is_all_in": False},
            {"street": "river", "action": "check_back", "bet_pct_pot": 0.0, "is_all_in": False},
        ],
    )
    print(format_postflop_line_report(line_report))


# =========================
# Conservative override block (2026-04)
# =========================

_FLOP_IP_CHECK_BACK_TAGS = ALL_MEANINGFUL_TAGS | {"air"}
_FLOP_SMALL_BET_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | HIGH_CARD_TAGS | {"air"}
_FLOP_50_BET_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | {"middle_pair", "middle_pair_good_kicker", "pocket_pair_above_second_card"} | STRONG_DRAW_TAGS | {"gutshot", "ace_high", "two_overcards", "backdoor_flush_draw"}
_FLOP_66_BET_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | {"middle_pair_good_kicker"} | STRONG_DRAW_TAGS | {"gutshot", "two_overcards"}
_FLOP_75_BET_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS | {"gutshot", "top_pair_good_kicker"}
_FLOP_MID_BET_TAGS = _FLOP_66_BET_TAGS
_FLOP_CALL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | {"ace_high"}
_TURN_PASSIVE_OOP_CHECK_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | HIGH_CARD_TAGS | {"air"}
_TURN_DELAY_SMALL_TAGS = PAIR_TAGS | DRAW_TAGS | HIGH_CARD_TAGS | {"air"}
_TURN_DELAY_BIG_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS | {"middle_pair", "middle_pair_good_kicker", "gutshot"}
_TURN_AGG_CHECKBACK_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | {"ace_high", "two_overcards"}
_TURN_AGG_SMALL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS | {"ace_high", "two_overcards"}
_TURN_AGG_BIG_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | STRONG_DRAW_TAGS | {"middle_pair_good_kicker", "gutshot"}
_TURN_CALL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | DRAW_TAGS
_RIVER_OOP_CHECK_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | {"ace_high"}
_RIVER_IP_CHECK_BACK_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | {"ace_high"}
_RIVER_SMALL_BET_TAGS = STRONG_MADE_TAGS | PAIR_TAGS | {"top_pair_good_kicker", "middle_pair_good_kicker"}
_RIVER_BIG_BET_TAGS = STRONG_MADE_TAGS | STRONG_PAIR_TAGS | {"top_pair_good_kicker"}
_RIVER_CALL_TAGS = STRONG_MADE_TAGS | PAIR_TAGS
_RIVER_RAISE_TAGS_STRICT = STRONG_MADE_TAGS | {"nut_flush_blocker", "high_flush_blocker", "straight_blocker", "ace_high"}


def _postflop_range_weight_multiplier(tags: Set[str], *, rule: PostflopRule) -> float:
    """Frequency-style adjustment: allowed combos can be kept with partial weight."""
    street = str(rule.street).lower()
    action = str(rule.action).lower()
    bucket = str(rule.bucket).lower()
    bet_pct = 0.0
    try:
        # Buckets are textual, so use conservative bucket groups rather than exact sizing here.
        bet_pct = 100.0 if bucket == "all-in" else 0.0
    except Exception:
        bet_pct = 0.0

    strong_made = bool(tags & STRONG_MADE_TAGS)
    strong_pair = bool(tags & STRONG_PAIR_TAGS)
    medium_pair = bool(tags & {"middle_pair", "middle_pair_good_kicker", "pocket_pair_above_second_card"})
    weak_pair = bool(tags & {"bottom_pair", "underpair", "pocket_pair_below_second_card", "weak_showdown", "top_pair_weak_kicker", "middle_pair_weak_kicker", "bottom_pair_weak_kicker"})
    strong_draw = bool(tags & STRONG_DRAW_TAGS)
    weak_draw = bool(tags & {"gutshot", "backdoor_flush_draw"})
    high_card = bool(tags & {"ace_high", "two_overcards", "one_overcard"})
    blocker = bool(tags & BLOCKER_TAGS)
    air = "air" in tags

    if strong_made:
        return 1.0

    if street == "flop" and action == "bet":
        if bucket in {"0-25", "26-50"}:
            if strong_pair or strong_draw:
                return 1.0
            if medium_pair:
                return 0.70
            if weak_pair:
                return 0.45
            if weak_draw:
                return 0.42
            if high_card:
                return 0.32
            if air:
                return 0.16
        if bucket == "51-75":
            if strong_pair or strong_draw:
                return 1.0
            if medium_pair:
                return 0.45
            if weak_pair:
                return 0.25
            if weak_draw:
                return 0.30
            if high_card:
                return 0.16
        return 1.0 if (strong_pair or strong_draw) else 0.35

    if street == "turn" and action == "bet":
        if bucket in {"0-25", "26-50"}:
            if strong_pair or strong_draw:
                return 1.0
            if medium_pair:
                return 0.62
            if weak_pair:
                return 0.36
            if weak_draw:
                return 0.32
            if high_card:
                return 0.18
            if air:
                return 0.08
        if strong_pair or strong_draw:
            return 1.0
        if medium_pair:
            return 0.42
        if weak_draw:
            return 0.22
        return 0.12

    if street == "river":
        if action in {"check_raise", "reraise"}:
            if blocker and "nut_flush_blocker" in tags:
                return 0.22
            if blocker:
                return 0.12
            if high_card:
                return 0.06
            return 1.0
        if action == "bet":
            if strong_pair:
                return 1.0
            if medium_pair:
                return 0.55
            if weak_pair:
                return 0.25
            if blocker:
                return 0.10
            if high_card:
                return 0.05
    return 1.0

def _normalize_action(action: str) -> str:
    value = str(action).strip().lower()
    aliases = {
        "check": "oop_check",
        "check_back": "ip_check_back",
    }
    value = aliases.get(value, value)
    supported = {"bet", "call", "oop_check", "ip_check_back", "check_raise", "reraise"}
    if value not in supported:
        supported_text = ", ".join(sorted(supported))
        raise ValueError(f"Некорректное postflop действие: {action}. Доступно: {supported_text}")
    return value


def _rule_action(action: str) -> str:
    return action


def _make_rule(*, street: str, action: str, bet_pct_pot: float, is_all_in: bool, reason: str, keep_full_range: bool = False, keep_any_tags: Iterable[str] = ()) -> PostflopRule:
    if action == "ip_check_back":
        bucket = "ip-check-back"
    elif action == "oop_check":
        bucket = "oop-check"
    elif action == "call":
        bucket = "call"
    else:
        bucket = classify_bet_size(bet_pct_pot, is_all_in=is_all_in)
    return PostflopRule(
        street=street,
        action=action,
        bucket=bucket,
        min_equity=0.0,
        keep_full_range=keep_full_range,
        reason=reason,
        filter_mode="keep_all" if keep_full_range else "tags",
        keep_any_tags=tuple(sorted(set(keep_any_tags))),
    )


def resolve_postflop_rule(*, street: str, action: str, bet_pct_pot: float = 0.0, is_all_in: bool = False, previous_events: Optional[Sequence[PostflopEvent]] = None, villain_in_position: bool = False) -> PostflopRule:
    street = _normalize_street(street)
    action = _normalize_action(action)
    previous_events = list(previous_events or [])

    flop_event = _get_street_event(previous_events, "flop")
    turn_event = _get_street_event(previous_events, "turn")
    flop_was_aggressive = bool(flop_event and _continues_line_like_bet(flop_event.action))
    turn_was_aggressive = bool(turn_event and _continues_line_like_bet(turn_event.action))

    if street == "flop":
        if action == "oop_check":
            return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_full_range=True, reason="Flop OOP check -> near-full baseline, диапазон почти не режем.")
        if action == "ip_check_back":
            return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_FLOP_IP_CHECK_BACK_TAGS, reason="Flop IP check-back -> широкий контроль банка: value, pairs, draws, high-card и часть air с малым весом.")
        if action == "call":
            return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_FLOP_CALL_TAGS, reason="Flop call -> made hands, пары, дро и часть ace-high bluffcatcher слоя.")
        if action == "bet":
            if is_all_in or bet_pct_pot > 75:
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=STACK_OFF_TAGS, reason="Flop bet 76%+ / all-in -> сильное вэлью, сильные пары и сильные дро.")
            if bet_pct_pot <= 33:
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_FLOP_SMALL_BET_TAGS, reason="Flop bet 0-33% -> широкий stab/range-bet слой: value, pairs, draws, high-card и часть air/backdoor с малым весом.")
            if bet_pct_pot <= 50:
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_FLOP_50_BET_TAGS, reason="Flop bet 34-50% -> merge/protection: value, strong pair, часть middle/pocket, strong draws, gutshot/high-card backdoor.")
            if bet_pct_pot <= 66:
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_FLOP_66_BET_TAGS, reason="Flop bet 51-66% -> уже сильнее: value, strong pair, strong draws, часть gutshot/two-overcards.")
            return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_FLOP_75_BET_TAGS, reason="Flop bet 67-75% -> value-heavy слой: strong value, strong draws, часть сильных gutshot/top-pair.")
        if action in {"check_raise", "reraise"}:
            return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=STRONG_MADE_TAGS | STRONG_DRAW_TAGS | STRONG_PAIR_TAGS, reason="Flop raise line -> сильное вэлью, сильные дро и strongest one-pair.")

    if street == "turn":
        if not flop_was_aggressive:
            if action == "oop_check":
                return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_TURN_PASSIVE_OOP_CHECK_TAGS, reason="Turn OOP check after passive flop -> широкий showdown/control слой, включая часть air с низким весом.")
            if action == "ip_check_back":
                return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_TURN_DELAY_SMALL_TAGS | STRONG_MADE_TAGS, reason="Turn IP check-back after passive flop -> контроль банка / showdown / missed-stab слой.")
            if action == "call":
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_TURN_CALL_TAGS, reason="Turn call after passive flop -> пары, вэлью и дро.")
            if action == "bet":
                if is_all_in or bet_pct_pot > 75:
                    return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=STACK_OFF_TAGS, reason="Turn delayed 76%+ / jam -> strong value + strong draws.")
                if bet_pct_pot <= 50:
                    return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_TURN_DELAY_SMALL_TAGS, reason="Turn delayed small bet -> пары, дро, high-card и малый air/backdoor слой.")
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_TURN_DELAY_BIG_TAGS, reason="Turn delayed 51-75% -> value + strong draw + часть middle/gutshot.")
            if action in {"check_raise", "reraise"}:
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=STRONG_MADE_TAGS | STRONG_DRAW_TAGS | STRONG_PAIR_TAGS, reason="Turn raise after passive flop -> сильное вэлью, сильные дро и strongest pairs.")
        else:
            if action == "oop_check":
                return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_TURN_AGG_CHECKBACK_TAGS, reason="Turn OOP check after prior aggression -> пары/дро/value и часть high-card, без полного диапазона.")
            if action == "ip_check_back":
                return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_TURN_AGG_CHECKBACK_TAGS, reason="Turn check-back after flop aggression -> пары, дро, value и часть high-card control.")
            if action == "call":
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_TURN_CALL_TAGS, reason="Turn call after aggression -> пары, вэлью и дро.")
            if action == "bet":
                if is_all_in or bet_pct_pot > 50:
                    return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_TURN_AGG_BIG_TAGS, reason="Turn big bet after aggression -> сильное вэлью, сильные пары, сильные дро и малая часть gutshot.")
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_TURN_AGG_SMALL_TAGS, reason="Turn small bet after aggression -> made hands, пары, дро и часть high-card.")
            if action in {"check_raise", "reraise"}:
                return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=STRONG_MADE_TAGS | STRONG_DRAW_TAGS | STRONG_PAIR_TAGS, reason="Turn raise after aggression -> сильное вэлью, сильные дро и strongest pairs.")

    # river
    if action == "oop_check":
        return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_RIVER_OOP_CHECK_TAGS, reason="River OOP check -> showdown/value + часть ace-high bluffcatcher.")
    if action == "ip_check_back":
        return _make_rule(street=street, action=action, bet_pct_pot=0.0, is_all_in=False, keep_any_tags=_RIVER_IP_CHECK_BACK_TAGS, reason="River IP check-back -> showdown / weak value / ace-high showdown.")
    if action == "call":
        return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_RIVER_CALL_TAGS, reason="River call -> showdown/value catch слой.")
    if action in {"check_raise", "reraise"}:
        return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_RIVER_RAISE_TAGS_STRICT, reason="River raise line -> value-heavy, но с маленьким blocker-bluff слоем.")
    if is_all_in or bet_pct_pot >= 50:
        return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=is_all_in, keep_any_tags=_RIVER_BIG_BET_TAGS, reason="River medium/big bet -> strong value + сильные top-pair руки.")
    return _make_rule(street=street, action=action, bet_pct_pot=bet_pct_pot, is_all_in=False, keep_any_tags=_RIVER_SMALL_BET_TAGS, reason="River small bet -> thin value / showdown value слой.")

