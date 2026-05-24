from __future__ import annotations

import itertools
import math
import random
import re
from bisect import bisect_left
from functools import lru_cache
from itertools import accumulate
from typing import Dict, Iterable, List, Sequence, Tuple, Union

from engine_core import card_to_str, create_deck, normalize_cards, str_to_card


RANKS = "23456789TJQKA"
RANK_TO_INDEX = {rank: i for i, rank in enumerate(RANKS)}
SUITS = "cdhs"
FULL_DECK = tuple(create_deck())
CARD_RANK_VALUE = tuple((card % 13) + 2 for card in range(52))
CARD_SUIT_VALUE = tuple(card // 13 for card in range(52))
STRAIGHT_MASKS_DESC = []
for high in range(14, 5, -1):
    mask = 0
    for rank_value in range(high - 4, high + 1):
        mask |= 1 << (rank_value - 2)
    STRAIGHT_MASKS_DESC.append((high, mask))
WHEEL_MASK = (
    (1 << (14 - 2))
    | (1 << (5 - 2))
    | (1 << (4 - 2))
    | (1 << (3 - 2))
    | (1 << (2 - 2))
)

CardLike = Union[int, str]
HandLike = Sequence[CardLike]
Combo = Tuple[int, int]
WeightedCombo = Tuple[Combo, float]
RangeInput = Union[str, Sequence[str], Sequence[Combo], Dict[Union[str, Combo], float]]
PreparedPair = Tuple[Combo, Combo, float, Tuple[int, ...]]


def _normalize_card(card: CardLike) -> int:
    if isinstance(card, int):
        if 0 <= card < 52:
            return card
        raise ValueError(f"Некорректная карта: {card}")
    if isinstance(card, str):
        return str_to_card(card)
    raise TypeError("Карта должна быть int или строкой вида 'As'")



def _normalize_cards_local(cards: Iterable[CardLike]) -> List[int]:
    return normalize_cards(list(cards))



def _normalize_hand(hand: HandLike) -> Combo:
    cards = tuple(_normalize_cards_local(hand))
    if len(cards) != 2:
        raise ValueError(f"В руке должно быть ровно 2 карты, получено {len(cards)}")
    if cards[0] == cards[1]:
        raise ValueError("В руке не может быть двух одинаковых карт")
    return cards



def _normalize_optional_cards(cards: Iterable[CardLike] | None) -> List[int]:
    if not cards:
        return []
    return _normalize_cards_local(cards)



def _assert_unique_cards(cards: Iterable[int], context: str) -> None:
    seen = set()
    for card in cards:
        if card in seen:
            raise ValueError(f"Повторяющаяся карта {card_to_str(card)} в {context}")
        seen.add(card)



def _blocked_key(cards: Iterable[int]) -> Tuple[int, ...]:
    return tuple(sorted(set(cards)))


@lru_cache(maxsize=4096)
def _available_deck_cached(blocked_key: Tuple[int, ...]) -> Tuple[int, ...]:
    blocked = set(blocked_key)
    return tuple(card for card in FULL_DECK if card not in blocked)



def _available_deck(excluded: Iterable[int]) -> List[int]:
    return list(_available_deck_cached(_blocked_key(excluded)))



def _straight_high_from_mask(mask: int) -> int:
    for high, straight_mask in STRAIGHT_MASKS_DESC:
        if mask & straight_mask == straight_mask:
            return high
    if mask & WHEEL_MASK == WHEEL_MASK:
        return 5
    return 0



def _score_7_cards(cards7: Sequence[int]) -> Tuple[int, ...]:
    rank_counts: Dict[int, int] = {}
    suit_ranks = ([], [], [], [])
    rank_mask = 0

    for card in cards7:
        rank_value = CARD_RANK_VALUE[card]
        suit_value = CARD_SUIT_VALUE[card]
        rank_counts[rank_value] = rank_counts.get(rank_value, 0) + 1
        suit_ranks[suit_value].append(rank_value)
        rank_mask |= 1 << (rank_value - 2)

    flush_top5 = None
    for ranks in suit_ranks:
        if len(ranks) >= 5:
            flush_mask = 0
            for rank_value in ranks:
                flush_mask |= 1 << (rank_value - 2)
            straight_flush_high = _straight_high_from_mask(flush_mask)
            if straight_flush_high:
                return (8, straight_flush_high)

            candidate_flush = tuple(sorted(ranks, reverse=True)[:5])
            if flush_top5 is None or candidate_flush > flush_top5:
                flush_top5 = candidate_flush

    quads: List[int] = []
    trips: List[int] = []
    pairs: List[int] = []

    for rank_value, count in rank_counts.items():
        if count == 4:
            quads.append(rank_value)
        elif count == 3:
            trips.append(rank_value)
        elif count == 2:
            pairs.append(rank_value)

    quads.sort(reverse=True)
    trips.sort(reverse=True)
    pairs.sort(reverse=True)

    if quads:
        quad_rank = quads[0]
        kicker = max(rank for rank in rank_counts if rank != quad_rank)
        return (7, quad_rank, kicker)

    if trips and (len(trips) >= 2 or pairs):
        trips_rank = trips[0]
        pair_rank = trips[1] if len(trips) >= 2 else pairs[0]
        return (6, trips_rank, pair_rank)

    if flush_top5 is not None:
        return (5, *flush_top5)

    straight_high = _straight_high_from_mask(rank_mask)
    if straight_high:
        return (4, straight_high)

    if trips:
        trips_rank = trips[0]
        kickers = sorted((rank for rank in rank_counts if rank != trips_rank), reverse=True)[:2]
        return (3, trips_rank, *kickers)

    if len(pairs) >= 2:
        high_pair, low_pair = pairs[:2]
        kicker = max(rank for rank in rank_counts if rank not in (high_pair, low_pair))
        return (2, high_pair, low_pair, kicker)

    if len(pairs) == 1:
        pair_rank = pairs[0]
        kickers = sorted((rank for rank in rank_counts if rank != pair_rank), reverse=True)[:3]
        return (1, pair_rank, *kickers)

    return (0, *sorted(rank_counts.keys(), reverse=True)[:5])



def score_7_cards_fast(cards7: Sequence[int]) -> Tuple[int, ...]:
    """Public fast 7-card scorer used by decision/runtime layers."""
    return _score_7_cards(tuple(cards7))


def _evaluate_heads_up(hand1: Combo, hand2: Combo, board: Sequence[int]) -> int:
    score1 = _score_7_cards((hand1[0], hand1[1], board[0], board[1], board[2], board[3], board[4]))
    score2 = _score_7_cards((hand2[0], hand2[1], board[0], board[1], board[2], board[3], board[4]))
    if score1 > score2:
        return 1
    if score2 > score1:
        return -1
    return 0



def _empty_stats() -> Dict[str, Union[int, float, None, str]]:
    return {
        "wins1": 0,
        "wins2": 0,
        "ties": 0,
        "samples": 0,
        "equity1": 0.0,
        "equity2": 0.0,
        "method": None,
    }



def _finalize_stats(stats: Dict[str, Union[int, float, None, str]], method: str) -> Dict[str, Union[int, float, None, str]]:
    samples = int(stats["samples"])
    if samples <= 0:
        raise ValueError("Нет валидных сэмплов для расчета эквити")
    wins1 = int(stats["wins1"])
    wins2 = int(stats["wins2"])
    ties = int(stats["ties"])
    stats["equity1"] = (wins1 + ties / 2.0) / samples
    stats["equity2"] = (wins2 + ties / 2.0) / samples
    stats["method"] = method
    return stats


# =========================
# hand vs hand
# =========================

def hand_vs_hand_exact(
    hand1: HandLike,
    hand2: HandLike,
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
) -> Dict[str, Union[int, float, None, str]]:
    h1 = _normalize_hand(hand1)
    h2 = _normalize_hand(hand2)
    board_cards = _normalize_optional_cards(board)
    dead = _normalize_optional_cards(dead_cards)

    all_known = list(h1) + list(h2) + board_cards + dead
    _assert_unique_cards(all_known, "hand_vs_hand_exact")

    missing = 5 - len(board_cards)
    if missing < 0:
        raise ValueError("На борде не может быть больше 5 карт")

    stats = _empty_stats()
    if missing == 0:
        result = _evaluate_heads_up(h1, h2, board_cards)
        if result > 0:
            stats["wins1"] += 1
        elif result < 0:
            stats["wins2"] += 1
        else:
            stats["ties"] += 1
        stats["samples"] += 1
        stats["board"] = [card_to_str(card) for card in board_cards]
        return _finalize_stats(stats, method="exact")

    deck = _available_deck(all_known)
    for runout in itertools.combinations(deck, missing):
        full_board = board_cards + list(runout)
        result = _evaluate_heads_up(h1, h2, full_board)
        if result > 0:
            stats["wins1"] += 1
        elif result < 0:
            stats["wins2"] += 1
        else:
            stats["ties"] += 1
        stats["samples"] += 1

    stats["board"] = [card_to_str(card) for card in board_cards]
    return _finalize_stats(stats, method="exact")



def hand_vs_hand_monte_carlo(
    hand1: HandLike,
    hand2: HandLike,
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    trials: int = 50000,
    seed: int | None = None,
) -> Dict[str, Union[int, float, None, str]]:
    if trials <= 0:
        raise ValueError("trials должен быть > 0")

    h1 = _normalize_hand(hand1)
    h2 = _normalize_hand(hand2)
    board_cards = _normalize_optional_cards(board)
    dead = _normalize_optional_cards(dead_cards)

    all_known = list(h1) + list(h2) + board_cards + dead
    _assert_unique_cards(all_known, "hand_vs_hand_monte_carlo")

    missing = 5 - len(board_cards)
    if missing < 0:
        raise ValueError("На борде не может быть больше 5 карт")

    stats = _empty_stats()
    if missing == 0:
        result = _evaluate_heads_up(h1, h2, board_cards)
        if result > 0:
            stats["wins1"] += 1
        elif result < 0:
            stats["wins2"] += 1
        else:
            stats["ties"] += 1
        stats["samples"] += 1
        stats["board"] = [card_to_str(card) for card in board_cards]
        stats["trials"] = 1
        return _finalize_stats(stats, method="monte_carlo")

    deck = _available_deck(all_known)
    rng = random.Random(seed)

    for _ in range(trials):
        runout = rng.sample(deck, missing)
        full_board = board_cards + runout
        result = _evaluate_heads_up(h1, h2, full_board)
        if result > 0:
            stats["wins1"] += 1
        elif result < 0:
            stats["wins2"] += 1
        else:
            stats["ties"] += 1
        stats["samples"] += 1

    stats["board"] = [card_to_str(card) for card in board_cards]
    stats["trials"] = trials
    return _finalize_stats(stats, method="monte_carlo")



def hand_vs_hand(
    hand1: HandLike,
    hand2: HandLike,
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    method: str = "auto",
    trials: int = 50000,
    seed: int | None = None,
    exact_max_boards: int = 50000,
) -> Dict[str, Union[int, float, None, str]]:
    board_cards = _normalize_optional_cards(board)
    missing = 5 - len(board_cards)
    if missing < 0:
        raise ValueError("На борде не может быть больше 5 карт")

    known = list(_normalize_hand(hand1)) + list(_normalize_hand(hand2)) + board_cards + _normalize_optional_cards(dead_cards)
    _assert_unique_cards(known, "hand_vs_hand")
    free_cards = 52 - len(set(known))
    total_boards = math.comb(free_cards, missing)

    if method == "exact":
        return hand_vs_hand_exact(hand1, hand2, board=board_cards, dead_cards=dead_cards)
    if method == "monte_carlo":
        return hand_vs_hand_monte_carlo(hand1, hand2, board=board_cards, dead_cards=dead_cards, trials=trials, seed=seed)
    if method != "auto":
        raise ValueError("method должен быть 'auto', 'exact' или 'monte_carlo'")

    if total_boards <= exact_max_boards:
        return hand_vs_hand_exact(hand1, hand2, board=board_cards, dead_cards=dead_cards)
    return hand_vs_hand_monte_carlo(hand1, hand2, board=board_cards, dead_cards=dead_cards, trials=trials, seed=seed)


# =========================
# multiway fixed-hand helpers
# =========================

def _normalize_hands_input(hands: Sequence[HandLike]) -> List[Combo]:
    if not 2 <= len(hands) <= 6:
        raise ValueError("Поддерживается только 2-6 рук")
    normalized = [_normalize_hand(hand) for hand in hands]
    known_cards = [card for hand in normalized for card in hand]
    _assert_unique_cards(known_cards, "hands")
    return normalized


def _evaluate_multiway_on_board(hands: Sequence[Combo], board: Sequence[int]) -> Tuple[List[Tuple[int, ...]], List[int]]:
    if len(board) != 5:
        raise ValueError("Для оценки победителя нужен полный борд из 5 карт")
    scores = [
        _score_7_cards((hand[0], hand[1], board[0], board[1], board[2], board[3], board[4]))
        for hand in hands
    ]
    best_score = max(scores)
    winners = [index for index, score in enumerate(scores) if score == best_score]
    return scores, winners


def deal_random_hands(
    player_count: int,
    blocked_cards: Iterable[CardLike] | None = None,
    seed: int | None = None,
) -> List[Combo]:
    if not 2 <= player_count <= 6:
        raise ValueError("Поддерживается только 2-6 игроков")

    blocked = _normalize_optional_cards(blocked_cards)
    _assert_unique_cards(blocked, "deal_random_hands")

    deck = _available_deck(blocked)
    need_cards = player_count * 2
    if len(deck) < need_cards:
        raise ValueError("Недостаточно карт для раздачи указанному числу игроков")

    rng = random.Random(seed)
    rng.shuffle(deck)
    hands: List[Combo] = []
    for index in range(player_count):
        card1 = deck[index * 2]
        card2 = deck[index * 2 + 1]
        hands.append((card1, card2))
    return hands


def draw_random_board(
    board: Iterable[CardLike] | None = None,
    blocked_cards: Iterable[CardLike] | None = None,
    total_board_cards: int = 5,
    seed: int | None = None,
) -> List[int]:
    board_cards = _normalize_optional_cards(board)
    blocked = _normalize_optional_cards(blocked_cards)
    if not 0 <= total_board_cards <= 5:
        raise ValueError("total_board_cards должен быть в диапазоне 0..5")
    if len(board_cards) > total_board_cards:
        raise ValueError("Уже задано больше карт борда, чем total_board_cards")

    _assert_unique_cards(board_cards + blocked, "draw_random_board")
    missing = total_board_cards - len(board_cards)
    if missing == 0:
        return list(board_cards)

    deck = _available_deck(board_cards + blocked)
    if len(deck) < missing:
        raise ValueError("Недостаточно карт, чтобы достроить борд")

    rng = random.Random(seed)
    return board_cards + rng.sample(deck, missing)


def evaluate_multiway_board(
    hands: Sequence[HandLike],
    board: Iterable[CardLike],
) -> Dict[str, object]:
    normalized_hands = _normalize_hands_input(hands)
    board_cards = _normalize_optional_cards(board)
    if len(board_cards) != 5:
        raise ValueError("Для оценки борда нужно передать ровно 5 карт")

    known_cards = [card for hand in normalized_hands for card in hand] + board_cards
    _assert_unique_cards(known_cards, "evaluate_multiway_board")

    scores, winners = _evaluate_multiway_on_board(normalized_hands, board_cards)
    return {
        "hand_count": len(normalized_hands),
        "board": [card_to_str(card) for card in board_cards],
        "winner_indexes": winners,
        "winners": winners,
        "scores": scores,
    }


def multiway_hand_equity_monte_carlo(
    hands: Sequence[HandLike],
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    trials: int = 50000,
    seed: int | None = None,
) -> Dict[str, object]:
    if trials <= 0:
        raise ValueError("trials должен быть > 0")

    normalized_hands = _normalize_hands_input(hands)
    board_cards = _normalize_optional_cards(board)
    dead = _normalize_optional_cards(dead_cards)

    known_cards = [card for hand in normalized_hands for card in hand] + board_cards + dead
    _assert_unique_cards(known_cards, "multiway_hand_equity_monte_carlo")

    missing = 5 - len(board_cards)
    if missing < 0:
        raise ValueError("На борде не может быть больше 5 карт")

    deck = _available_deck(known_cards)
    if len(deck) < missing:
        raise ValueError("Недостаточно карт для достройки борда")

    equities = [0.0 for _ in normalized_hands]
    wins = [0 for _ in normalized_hands]
    tie_appearances = [0 for _ in normalized_hands]
    rng = random.Random(seed)

    sample_count = 1 if missing == 0 else trials
    for _ in range(sample_count):
        full_board = list(board_cards) if missing == 0 else board_cards + rng.sample(deck, missing)
        _, winners = _evaluate_multiway_on_board(normalized_hands, full_board)
        share = 1.0 / len(winners)
        if len(winners) == 1:
            wins[winners[0]] += 1
        else:
            for winner_index in winners:
                tie_appearances[winner_index] += 1
        for winner_index in winners:
            equities[winner_index] += share

    return {
        "hand_count": len(normalized_hands),
        "board": [card_to_str(card) for card in board_cards],
        "equities": [value / sample_count for value in equities],
        "wins": wins,
        "tie_appearances": tie_appearances,
        "samples": sample_count,
        "trials": sample_count,
        "method": "monte_carlo",
    }


# =========================
# range parsing
# =========================

def _tokenize_range_text(text: str) -> List[str]:
    tokens = re.split(r"[\s,;]+", text.strip())
    return [token for token in tokens if token]



def _canonical_combo(card1: int, card2: int) -> Combo:
    if card1 == card2:
        raise ValueError("Комбо не может содержать две одинаковые карты")
    return (card1, card2) if card1 < card2 else (card2, card1)


@lru_cache(maxsize=32)
def _cards_of_rank(rank_char: str) -> Tuple[int, ...]:
    return tuple(str_to_card(rank_char + suit) for suit in SUITS)


@lru_cache(maxsize=32)
def _generate_pair_combos(rank_char: str) -> Tuple[Combo, ...]:
    cards = _cards_of_rank(rank_char)
    return tuple(_canonical_combo(a, b) for a, b in itertools.combinations(cards, 2))


@lru_cache(maxsize=256)
def _generate_non_pair_combos(rank1: str, rank2: str, suited_flag: str | None) -> Tuple[Combo, ...]:
    cards1 = _cards_of_rank(rank1)
    cards2 = _cards_of_rank(rank2)
    combos = []
    for c1 in cards1:
        for c2 in cards2:
            same_suit = (c1 // 13) == (c2 // 13)
            if suited_flag == "s" and not same_suit:
                continue
            if suited_flag == "o" and same_suit:
                continue
            combos.append(_canonical_combo(c1, c2))
    return tuple(combos)


@lru_cache(maxsize=256)
def _expand_plus_token(token: str) -> Tuple[str, ...]:
    base = token[:-1]
    if len(base) == 2 and base[0] == base[1]:
        start = RANK_TO_INDEX[base[0]]
        return tuple(RANKS[i] * 2 for i in range(start, len(RANKS)))

    if len(base) == 3 and base[0] != base[1] and base[2] in "so":
        r1, r2, suited = base[0], base[1], base[2]
        hi = RANK_TO_INDEX[r1]
        lo = RANK_TO_INDEX[r2]
        if hi <= lo:
            raise ValueError(f"Некорректный плюс-токен диапазона: {token}")
        return tuple(r1 + RANKS[i] + suited for i in range(lo, hi))

    raise ValueError(f"Неподдерживаемый токен диапазона: {token}")


@lru_cache(maxsize=2048)
def _expand_range_token_cached(token: str) -> Tuple[WeightedCombo, ...]:
    weight = 1.0
    token_value = token
    if ":" in token_value:
        token_value, weight_text = token_value.split(":", 1)
        weight = float(weight_text)
        if weight < 0:
            raise ValueError("Вес диапазона не может быть отрицательным")

    if token_value.endswith("+"):
        weighted = []
        for inner in _expand_plus_token(token_value):
            for combo, inner_weight in _expand_range_token_cached(inner):
                weighted.append((combo, inner_weight * weight))
        return tuple(weighted)

    if len(token_value) == 4 and token_value[0] in RANKS and token_value[1] in SUITS and token_value[2] in RANKS and token_value[3] in SUITS:
        combo = _canonical_combo(str_to_card(token_value[:2]), str_to_card(token_value[2:]))
        return ((combo, weight),)

    if len(token_value) == 2 and token_value[0] in RANKS and token_value[1] in RANKS:
        if token_value[0] != token_value[1]:
            combos = _generate_non_pair_combos(token_value[0], token_value[1], None)
        else:
            combos = _generate_pair_combos(token_value[0])
        return tuple((combo, weight) for combo in combos)

    if len(token_value) == 3 and token_value[0] in RANKS and token_value[1] in RANKS and token_value[2] in "so":
        if token_value[0] == token_value[1]:
            raise ValueError(f"Для пары suited/offsuited не используется: {token_value}")
        combos = _generate_non_pair_combos(token_value[0], token_value[1], token_value[2])
        return tuple((combo, weight) for combo in combos)

    raise ValueError(f"Неподдерживаемый токен диапазона: {token_value}")



def _expand_range_token(token: str) -> List[WeightedCombo]:
    return list(_expand_range_token_cached(token))


@lru_cache(maxsize=512)
def _parse_range_string_cached(text: str, blocked_key: Tuple[int, ...]) -> Tuple[WeightedCombo, ...]:
    blocked = set(blocked_key)
    weighted: Dict[Combo, float] = {}
    for token in _tokenize_range_text(text):
        for combo, weight in _expand_range_token_cached(token):
            if combo[0] in blocked or combo[1] in blocked:
                continue
            weighted[combo] = weighted.get(combo, 0.0) + float(weight)

    result = tuple(sorted(
        ((combo, weight) for combo, weight in weighted.items() if weight > 0),
        key=lambda item: (item[0][0], item[0][1]),
    ))
    if not result:
        raise ValueError("После учета блокеров диапазон пуст")
    return result



def parse_range(range_input: RangeInput, blocked_cards: Iterable[CardLike] | None = None) -> List[WeightedCombo]:
    blocked = _normalize_optional_cards(blocked_cards)
    blocked_set = set(blocked)

    if isinstance(range_input, str):
        return list(_parse_range_string_cached(range_input, _blocked_key(blocked)))

    weighted: Dict[Combo, float] = {}

    if isinstance(range_input, dict):
        items: List[WeightedCombo] = []
        for key, weight in range_input.items():
            if isinstance(key, tuple) and len(key) == 2:
                combo = _canonical_combo(_normalize_card(key[0]), _normalize_card(key[1]))
                items.append((combo, float(weight)))
            else:
                items.extend(_expand_range_token(f"{key}:{weight}"))
    else:
        items = []
        for item in range_input:
            if isinstance(item, tuple) and len(item) == 2 and all(isinstance(x, (int, str)) for x in item):
                combo = _canonical_combo(_normalize_card(item[0]), _normalize_card(item[1]))
                items.append((combo, 1.0))
            elif isinstance(item, str):
                items.extend(_expand_range_token(item))
            else:
                raise TypeError("Элемент диапазона должен быть строкой, комбо из 2 карт или dict")

    for combo, weight in items:
        if combo[0] in blocked_set or combo[1] in blocked_set:
            continue
        weighted[combo] = weighted.get(combo, 0.0) + float(weight)

    result = [(combo, weight) for combo, weight in weighted.items() if weight > 0]
    if not result:
        raise ValueError("После учета блокеров диапазон пуст")
    return sorted(result, key=lambda item: (item[0][0], item[0][1]))


# =========================
# range vs range
# =========================

def _normalize_weighted_combos(weighted_combos: List[WeightedCombo]) -> List[WeightedCombo]:
    total = sum(weight for _, weight in weighted_combos)
    if total <= 0:
        raise ValueError("Суммарный вес диапазона должен быть > 0")
    return [(combo, weight / total) for combo, weight in weighted_combos]



def _valid_combo_pairs(range1: List[WeightedCombo], range2: List[WeightedCombo]) -> List[Tuple[Combo, float, Combo, float]]:
    pairs = []
    for combo1, weight1 in range1:
        c10, c11 = combo1
        for combo2, weight2 in range2:
            c20, c21 = combo2
            if c20 == c10 or c20 == c11 or c21 == c10 or c21 == c11:
                continue
            pairs.append((combo1, weight1, combo2, weight2))
    if not pairs:
        raise ValueError("Не осталось валидных пар комбо после учета пересечений")
    return pairs



def _prepare_pairs(
    range1: List[WeightedCombo],
    range2: List[WeightedCombo],
    board_cards: List[int],
    dead: List[int],
) -> List[PreparedPair]:
    prepared: List[PreparedPair] = []
    shared_blocked = tuple(board_cards + dead)
    for combo1, weight1 in range1:
        c10, c11 = combo1
        for combo2, weight2 in range2:
            c20, c21 = combo2
            if c20 == c10 or c20 == c11 or c21 == c10 or c21 == c11:
                continue
            pair_weight = weight1 * weight2
            deck = _available_deck_cached(_blocked_key(shared_blocked + combo1 + combo2))
            prepared.append((combo1, combo2, pair_weight, deck))
    if not prepared:
        raise ValueError("Не осталось валидных пар комбо после учета пересечений")
    return prepared



def _pick_prepared_pair(prepared_pairs: List[PreparedPair], cumulative_weights: List[float], total_weight: float, rng: random.Random) -> PreparedPair:
    value = rng.random() * total_weight
    index = bisect_left(cumulative_weights, value)
    if index >= len(prepared_pairs):
        index = len(prepared_pairs) - 1
    return prepared_pairs[index]



def range_vs_range_exact(
    range1: RangeInput,
    range2: RangeInput,
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    exact_max_boards_per_pair: int = 2000,
) -> Dict[str, Union[int, float, None, str]]:
    board_cards = _normalize_optional_cards(board)
    dead = _normalize_optional_cards(dead_cards)
    _assert_unique_cards(board_cards + dead, "range_vs_range_exact")

    parsed1 = _normalize_weighted_combos(parse_range(range1, blocked_cards=board_cards + dead))
    parsed2 = _normalize_weighted_combos(parse_range(range2, blocked_cards=board_cards + dead))
    prepared_pairs = _prepare_pairs(parsed1, parsed2, board_cards, dead)

    missing = 5 - len(board_cards)
    if missing < 0:
        raise ValueError("На борде не может быть больше 5 карт")

    weighted_wins1 = 0.0
    weighted_wins2 = 0.0
    weighted_ties = 0.0
    weighted_samples = 0.0

    for combo1, combo2, pair_weight, deck in prepared_pairs:
        if missing == 0:
            result = _evaluate_heads_up(combo1, combo2, board_cards)
            if result > 0:
                weighted_wins1 += pair_weight
            elif result < 0:
                weighted_wins2 += pair_weight
            else:
                weighted_ties += pair_weight
            weighted_samples += pair_weight
            continue

        board_count = math.comb(len(deck), missing)
        if board_count > exact_max_boards_per_pair:
            raise ValueError(
                f"Слишком много точных прогонов для одной пары комбо: {board_count}. "
                f"Увеличь exact_max_boards_per_pair или используй Monte Carlo."
            )

        for runout in itertools.combinations(deck, missing):
            result = _evaluate_heads_up(combo1, combo2, board_cards + list(runout))
            if result > 0:
                weighted_wins1 += pair_weight
            elif result < 0:
                weighted_wins2 += pair_weight
            else:
                weighted_ties += pair_weight
            weighted_samples += pair_weight

    result = {
        "wins1": weighted_wins1,
        "wins2": weighted_wins2,
        "ties": weighted_ties,
        "samples": weighted_samples,
        "combos1": len(parsed1),
        "combos2": len(parsed2),
        "valid_combo_pairs": len(prepared_pairs),
        "board": [card_to_str(card) for card in board_cards],
        "method": "exact",
    }
    if weighted_samples <= 0:
        raise ValueError("Нет валидных выборок для точного range vs range")
    result["equity1"] = (weighted_wins1 + weighted_ties / 2.0) / weighted_samples
    result["equity2"] = (weighted_wins2 + weighted_ties / 2.0) / weighted_samples
    return result



def range_vs_range_monte_carlo(
    range1: RangeInput,
    range2: RangeInput,
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    trials: int = 50000,
    seed: int | None = None,
) -> Dict[str, Union[int, float, None, str]]:
    if trials <= 0:
        raise ValueError("trials должен быть > 0")

    board_cards = _normalize_optional_cards(board)
    dead = _normalize_optional_cards(dead_cards)
    _assert_unique_cards(board_cards + dead, "range_vs_range_monte_carlo")

    parsed1 = _normalize_weighted_combos(parse_range(range1, blocked_cards=board_cards + dead))
    parsed2 = _normalize_weighted_combos(parse_range(range2, blocked_cards=board_cards + dead))
    prepared_pairs = _prepare_pairs(parsed1, parsed2, board_cards, dead)

    missing = 5 - len(board_cards)
    if missing < 0:
        raise ValueError("На борде не может быть больше 5 карт")

    rng = random.Random(seed)
    stats = _empty_stats()

    if missing == 0:
        total_pair_weight = sum(pair_weight for _, _, pair_weight, _ in prepared_pairs)
        for combo1, combo2, pair_weight, _ in prepared_pairs:
            result = _evaluate_heads_up(combo1, combo2, board_cards)
            samples = pair_weight / total_pair_weight
            if result > 0:
                stats["wins1"] += samples
            elif result < 0:
                stats["wins2"] += samples
            else:
                stats["ties"] += samples
            stats["samples"] += samples
        stats["combos1"] = len(parsed1)
        stats["combos2"] = len(parsed2)
        stats["valid_combo_pairs"] = len(prepared_pairs)
        stats["board"] = [card_to_str(card) for card in board_cards]
        stats["trials"] = 1
        stats["equity1"] = (stats["wins1"] + stats["ties"] / 2.0) / stats["samples"]
        stats["equity2"] = (stats["wins2"] + stats["ties"] / 2.0) / stats["samples"]
        stats["method"] = "monte_carlo"
        return stats

    pair_weights = [pair_weight for _, _, pair_weight, _ in prepared_pairs]
    cumulative_weights = list(accumulate(pair_weights))
    total_weight = cumulative_weights[-1]

    for _ in range(trials):
        combo1, combo2, _, deck = _pick_prepared_pair(prepared_pairs, cumulative_weights, total_weight, rng)
        runout = rng.sample(deck, missing)
        result = _evaluate_heads_up(combo1, combo2, board_cards + runout)

        if result > 0:
            stats["wins1"] += 1
        elif result < 0:
            stats["wins2"] += 1
        else:
            stats["ties"] += 1
        stats["samples"] += 1

    stats["combos1"] = len(parsed1)
    stats["combos2"] = len(parsed2)
    stats["valid_combo_pairs"] = len(prepared_pairs)
    stats["board"] = [card_to_str(card) for card in board_cards]
    stats["trials"] = trials
    return _finalize_stats(stats, method="monte_carlo")



def range_vs_range(
    range1: RangeInput,
    range2: RangeInput,
    board: Iterable[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    method: str = "auto",
    trials: int = 50000,
    seed: int | None = None,
    exact_max_combo_pairs: int = 40,
    exact_max_boards_per_pair: int = 2000,
) -> Dict[str, Union[int, float, None, str]]:
    board_cards = _normalize_optional_cards(board)
    dead = _normalize_optional_cards(dead_cards)
    _assert_unique_cards(board_cards + dead, "range_vs_range")

    parsed1 = parse_range(range1, blocked_cards=board_cards + dead)
    parsed2 = parse_range(range2, blocked_cards=board_cards + dead)
    pairs = _valid_combo_pairs(_normalize_weighted_combos(parsed1), _normalize_weighted_combos(parsed2))

    if method == "exact":
        return range_vs_range_exact(
            range1,
            range2,
            board=board_cards,
            dead_cards=dead,
            exact_max_boards_per_pair=exact_max_boards_per_pair,
        )
    if method == "monte_carlo":
        return range_vs_range_monte_carlo(
            range1,
            range2,
            board=board_cards,
            dead_cards=dead,
            trials=trials,
            seed=seed,
        )
    if method != "auto":
        raise ValueError("method должен быть 'auto', 'exact' или 'monte_carlo'")

    missing = 5 - len(board_cards)
    free_cards = 52 - len(set(board_cards + dead)) - 4
    approx_boards = math.comb(free_cards, missing) if free_cards >= missing >= 0 else 0

    if len(pairs) <= exact_max_combo_pairs and approx_boards <= exact_max_boards_per_pair:
        return range_vs_range_exact(
            range1,
            range2,
            board=board_cards,
            dead_cards=dead,
            exact_max_boards_per_pair=exact_max_boards_per_pair,
        )

    return range_vs_range_monte_carlo(
        range1,
        range2,
        board=board_cards,
        dead_cards=dead,
        trials=trials,
        seed=seed,
    )


# =========================
# helpers for readable output
# =========================

def combo_to_str(combo: Combo) -> str:
    return card_to_str(combo[0]) + card_to_str(combo[1])



def weighted_range_to_text(weighted_range: List[WeightedCombo], max_items: int = 20) -> List[str]:
    items = []
    for combo, weight in weighted_range[:max_items]:
        items.append(f"{combo_to_str(combo)}:{weight:.4f}")
    return items


__all__ = [
    "Combo",
    "HandLike",
    "RangeInput",
    "WeightedCombo",
    "combo_to_str",
    "deal_random_hands",
    "draw_random_board",
    "evaluate_multiway_board",
    "hand_vs_hand",
    "hand_vs_hand_exact",
    "hand_vs_hand_monte_carlo",
    "multiway_hand_equity_monte_carlo",
    "parse_range",
    "range_vs_range",
    "range_vs_range_exact",
    "range_vs_range_monte_carlo",
    "weighted_range_to_text",
]

if __name__ == "__main__":
    print("=== HAND VS HAND ===")
    hvh = hand_vs_hand(["As", "Kd"], ["Qh", "Qs"], trials=20000, seed=42)
    print(hvh)

    print("\n=== RANGE VS RANGE ===")
    rvr = range_vs_range(
        "TT+ AQs+ AKo",
        "22+ AJs+ KQs AQo+",
        board=["2c", "7d", "Th"],
        method="auto",
        trials=20000,
        seed=42,
    )
    print(rvr)
