from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from fractions import Fraction
from typing import Any, Iterable, Optional
import math
import random

from perf_runtime import profile_function


RANKS = "23456789TJQKA"
SUITS = "cdhs"
STREETS = ("preflop", "flop", "turn", "river", "showdown")
STREET_TO_BOARD_COUNT = {
    "preflop": 0,
    "flop": 3,
    "turn": 4,
    "river": 5,
    "showdown": 5,
}
BOARD_COUNT_TO_STREET = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
POSITION_LABELS_BY_COUNT = {
    2: ["BTN", "BB"],
    3: ["BTN", "SB", "BB"],
    4: ["BTN", "SB", "BB", "CO"],
    5: ["BTN", "SB", "BB", "UTG", "CO"],
    6: ["BTN", "SB", "BB", "UTG", "MP", "CO"],
}
_PLAYER_AMOUNT_FIELDS = {"stack", "bet_total", "bet_street"}


def validate_player_count(player_count: int) -> None:
    if not 2 <= player_count <= 6:
        raise ValueError("Движок поддерживает только 2-6 игроков")


def build_default_names(player_count: int) -> list[str]:
    validate_player_count(player_count)
    return ["Hero"] + [f"V{index}" for index in range(1, player_count)]


def normalize_player_names(names: Optional[Iterable[str]] = None, player_count: Optional[int] = None) -> list[str]:
    if names is None:
        if player_count is None:
            raise ValueError("Нужно передать names или player_count")
        names_list = build_default_names(player_count)
    else:
        names_list = [str(name) for name in names]
        if player_count is not None and len(names_list) != player_count:
            raise ValueError("player_count должен совпадать с количеством имён")
    validate_player_count(len(names_list))
    if any(not name for name in names_list):
        raise ValueError("Имя игрока не может быть пустым")
    if len(set(names_list)) != len(names_list):
        raise ValueError("Имена игроков должны быть уникальными")
    return names_list


def normalize_start_stacks(names: list[str], start_stack: Any, stacks: Optional[Any] = None) -> list[Any]:
    if stacks is None:
        return [start_stack for _ in names]
    if isinstance(stacks, dict):
        resolved = []
        for index, name in enumerate(names):
            if index in stacks:
                value = stacks[index]
            elif name in stacks:
                value = stacks[name]
            else:
                value = start_stack
            resolved.append(value)
        return resolved
    if isinstance(stacks, (list, tuple)):
        if len(stacks) != len(names):
            raise ValueError("Количество стеков должно совпадать с количеством игроков")
        return list(stacks)
    raise TypeError("stacks должен быть list, tuple, dict или None")


def validate_blinds(small_blind: Any, big_blind: Any) -> None:
    sb = _value_to_fraction(small_blind)
    bb = _value_to_fraction(big_blind)
    if sb <= 0 or bb <= 0:
        raise ValueError("Блайнды должны быть положительными")
    if sb >= bb:
        raise ValueError("small_blind должен быть меньше big_blind")


def create_deck() -> list[int]:
    return list(range(52))


def card_rank(card: int) -> int:
    return card % 13


def card_suit(card: int) -> int:
    return card // 13


def card_to_str(card: int) -> str:
    return f"{RANKS[card_rank(card)]}{SUITS[card_suit(card)]}"


def str_to_card(card_str: str) -> int:
    if len(card_str) != 2:
        raise ValueError(f"Некорректная строка карты: {card_str}")
    rank_char, suit_char = card_str[0], card_str[1]
    return SUITS.index(suit_char) * 13 + RANKS.index(rank_char)


def _value_to_fraction(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        return Fraction(str(value))
    if isinstance(value, int):
        return Fraction(value, 1)
    return Fraction(str(value))


def _lcm(a: int, b: int) -> int:
    return abs(a * b) // math.gcd(a, b)


def _gcd_fraction(a: Fraction, b: Fraction) -> Fraction:
    common_den = _lcm(a.denominator, b.denominator)
    a_num = a.numerator * (common_den // a.denominator)
    b_num = b.numerator * (common_den // b.denominator)
    return Fraction(math.gcd(abs(a_num), abs(b_num)), common_den)


def get_common_chip_unit(*values: Any) -> Fraction:
    positive = []
    for value in values:
        frac = _value_to_fraction(value)
        if frac > 0:
            positive.append(frac)
    if not positive:
        return Fraction(1, 1)
    unit = positive[0]
    for value in positive[1:]:
        unit = _gcd_fraction(unit, value)
    return unit


def amount_to_ticks_by_unit(amount: Any, chip_unit: Fraction) -> int:
    ticks = _value_to_fraction(amount) / chip_unit
    if ticks.denominator != 1:
        raise ValueError(f"Сумма {amount} не кратна минимальному тику {format_fraction(chip_unit)}")
    return ticks.numerator


def fraction_to_number(value: Fraction) -> int | float:
    if value.denominator == 1:
        return value.numerator
    decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
    text = format(decimal_value.normalize(), "f").rstrip("0").rstrip(".")
    return float(text)


def format_fraction(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
    return format(decimal_value.normalize(), "f").rstrip("0").rstrip(".")


def normalize_card(card: int | str) -> int:
    if isinstance(card, int):
        if 0 <= card < 52:
            return card
        raise ValueError(f"Некорректный номер карты: {card}")
    if isinstance(card, str):
        return str_to_card(card)
    raise TypeError("Карта должна быть int или строкой вида 'Ah'")


def normalize_cards(cards: Iterable[int | str], expected_len: Optional[int] = None) -> list[int]:
    normalized = [normalize_card(card) for card in cards]
    if expected_len is not None and len(normalized) != expected_len:
        raise ValueError(f"Ожидалось {expected_len} карт(ы), получено {len(normalized)}")
    return normalized


def validate_unique_cards(cards: Iterable[int], context_text: str) -> None:
    seen: dict[int, bool] = {}
    for card in cards:
        if card in seen:
            raise ValueError(f"Обнаружена дублирующаяся карта {card_to_str(card)} в {context_text}")
        seen[card] = True


@dataclass(slots=True)
class PlayerState:
    name: str
    stack: int
    cards: list[int] = field(default_factory=list)
    position: str = "OUT"
    in_hand: bool = True
    folded: bool = False
    all_in: bool = False
    bet_total: int = 0
    bet_street: int = 0
    acted: bool = False
    has_acted_since_full_raise: bool = False

    def reset_for_new_hand(self) -> None:
        self.cards = []
        self.position = "OUT"
        self.in_hand = self.stack > 0
        self.folded = False
        self.all_in = False
        self.bet_total = 0
        self.bet_street = 0
        self.acted = False
        self.has_acted_since_full_raise = False

    def reset_for_manual_hand(self, preserve_stack: bool = True) -> None:
        if not preserve_stack:
            self.stack = 0
        self.reset_for_new_hand()

    def set_hole_cards(self, cards: Iterable[int | str]) -> None:
        self.cards = normalize_cards(cards, expected_len=2)
        self.in_hand = True
        self.folded = False
        self.all_in = self.stack == 0

    def configure(self, chip_unit: Fraction, **overrides: Any) -> None:
        explicit_all_in = "all_in" in overrides
        for field_name, value in overrides.items():
            if field_name == "cards":
                self.cards = normalize_cards(value, expected_len=2)
            elif field_name.endswith("_ticks"):
                setattr(self, field_name[:-6], value)
            elif field_name in _PLAYER_AMOUNT_FIELDS:
                setattr(self, field_name, amount_to_ticks_by_unit(value, chip_unit))
            else:
                setattr(self, field_name, value)

        if self.cards:
            self.in_hand = True
            if self.folded:
                raise ValueError(f"Игрок {self.name} не может иметь карты и быть folded одновременно")
        if self.stack == 0 and self.in_hand and not self.folded and not explicit_all_in:
            self.all_in = True

    def post_blind(self, amount_ticks: int, table: "TableState") -> int:
        blind = min(self.stack, amount_ticks)
        self.stack -= blind
        self.bet_street += blind
        self.bet_total += blind
        table.pot += blind
        if self.stack == 0:
            self.all_in = True
        return blind

    def snapshot(self, table: "TableState", reveal_cards: bool = True) -> dict[str, Any]:
        return {
            "name": self.name,
            "stack": table.ticks_to_amount(self.stack),
            "stack_ticks": self.stack,
            "cards": [card_to_str(card) for card in self.cards] if reveal_cards else [],
            "cards_raw": list(self.cards) if reveal_cards else [],
            "position": self.position,
            "in_hand": self.in_hand,
            "folded": self.folded,
            "all_in": self.all_in,
            "bet_total": table.ticks_to_amount(self.bet_total),
            "bet_total_ticks": self.bet_total,
            "bet_street": table.ticks_to_amount(self.bet_street),
            "bet_street_ticks": self.bet_street,
            "acted": self.acted,
            "has_acted_since_full_raise": self.has_acted_since_full_raise,
        }


@dataclass(slots=True)
class TableState:
    chip_unit: Fraction
    sb: int
    bb: int
    deck: list[int] = field(default_factory=list)
    board: list[int] = field(default_factory=list)
    pot: int = 0
    street: str = "preflop"
    dealer_index: int = 0
    current_bet: int = 0
    min_raise: int = 0
    to_act: int = 0
    sb_index: int = 0
    bb_index: int = 0

    def __post_init__(self) -> None:
        if self.min_raise == 0:
            self.min_raise = self.bb

    def amount_to_ticks(self, amount: Any) -> int:
        return amount_to_ticks_by_unit(amount, self.chip_unit)

    def ticks_to_amount(self, ticks: int) -> int | float:
        return fraction_to_number(self.chip_unit * ticks)

    def reset_for_manual_hand(self) -> None:
        self.deck = []
        self.board = []
        self.pot = 0
        self.street = "preflop"
        self.current_bet = 0
        self.min_raise = self.bb
        self.to_act = 0

    def set_board_cards(self, cards: Iterable[int | str]) -> None:
        self.board = normalize_cards(cards)
        if len(self.board) > 5:
            raise ValueError("На борде не может быть больше 5 карт")

    def snapshot(self) -> dict[str, Any]:
        return {
            "board": [card_to_str(card) for card in self.board],
            "board_raw": list(self.board),
            "deck_count": len(self.deck),
            "pot": self.ticks_to_amount(self.pot),
            "pot_ticks": self.pot,
            "street": self.street,
            "dealer_index": self.dealer_index,
            "sb": self.ticks_to_amount(self.sb),
            "bb": self.ticks_to_amount(self.bb),
            "sb_ticks": self.sb,
            "bb_ticks": self.bb,
            "current_bet": self.ticks_to_amount(self.current_bet),
            "current_bet_ticks": self.current_bet,
            "min_raise": self.ticks_to_amount(self.min_raise),
            "min_raise_ticks": self.min_raise,
            "to_act": self.to_act,
            "sb_index": self.sb_index,
            "bb_index": self.bb_index,
            "chip_unit": format_fraction(self.chip_unit),
        }


class HandCore:
    def __init__(
        self,
        names: Optional[list[str]] = None,
        start_stack: Any = 100,
        small_blind: Any = 0.5,
        big_blind: Any = 1,
        *,
        player_count: Optional[int] = None,
        stacks: Optional[Any] = None,
    ):
        validate_blinds(small_blind, big_blind)
        self._names = normalize_player_names(names, player_count=player_count)
        start_stacks = normalize_start_stacks(self._names, start_stack, stacks)
        for value in start_stacks:
            if _value_to_fraction(value) < 0:
                raise ValueError("Стек игрока не может быть отрицательным")
        self._chip_unit = get_common_chip_unit(*start_stacks, small_blind, big_blind)
        self._players = [
            PlayerState(name=name, stack=amount_to_ticks_by_unit(stack_value, self._chip_unit))
            for name, stack_value in zip(self._names, start_stacks)
        ]
        self._table = TableState(
            chip_unit=self._chip_unit,
            sb=amount_to_ticks_by_unit(small_blind, self._chip_unit),
            bb=amount_to_ticks_by_unit(big_blind, self._chip_unit),
        )
        self.hand_number = 1
        self.action_log: list[dict[str, Any]] = []
        self.hand_over = False
        self.winner: Optional[int] = None
        self.winners: list[int] = []
        self.hand_started = False

    @property
    def players(self) -> list[PlayerState]:
        return self._players

    @property
    def table(self) -> TableState:
        return self._table

    @property
    def chip_unit(self) -> Fraction:
        return self._chip_unit

    @property
    def player_names(self) -> list[str]:
        return list(self._names)

    @property
    def max_players(self) -> int:
        return len(self._players)

    def amount_to_ticks(self, amount: Any) -> int:
        return self._table.amount_to_ticks(amount)

    def ticks_to_amount(self, ticks: int) -> int | float:
        return self._table.ticks_to_amount(ticks)

    def snapshot(self, reveal_all_hole_cards: bool = True) -> dict[str, Any]:
        return {
            "hand_number": self.hand_number,
            "hand_started": self.hand_started,
            "hand_over": self.hand_over,
            "winner": None if self.winner is None else self._players[self.winner].name,
            "winner_index": self.winner,
            "winners": [self._players[index].name for index in self.winners],
            "winner_indexes": list(self.winners),
            "table": self._table.snapshot(),
            "players": [player.snapshot(self._table, reveal_cards=reveal_all_hole_cards) for player in self._players],
            "action_log": [dict(item) for item in self.action_log],
        }

    def player_index(self, player_ref: int | str) -> int:
        if isinstance(player_ref, int):
            if 0 <= player_ref < len(self._players):
                return player_ref
            raise IndexError(f"Некорректный индекс игрока: {player_ref}")
        if isinstance(player_ref, str):
            matches = [i for i, player in enumerate(self._players) if player.name == player_ref]
            if not matches:
                raise ValueError(f"Игрок с именем '{player_ref}' не найден")
            if len(matches) > 1:
                raise ValueError(f"Имя игрока '{player_ref}' не уникально, используй индекс")
            return matches[0]
        raise TypeError("player_ref должен быть индексом игрока или его именем")

    def player(self, player_ref: int | str) -> PlayerState:
        return self._players[self.player_index(player_ref)]

    def collect_known_cards(self) -> list[int]:
        cards: list[int] = []
        for player in self._players:
            cards.extend(player.cards)
        cards.extend(self._table.board)
        cards.extend(self._table.deck)
        return cards

    def validate_state_cards_unique(self, extra_cards: Optional[Iterable[int | str]] = None, context_text: str = "manual setup") -> None:
        cards = []
        for player in self._players:
            cards.extend(player.cards)
        cards.extend(self._table.board)
        if extra_cards:
            cards.extend(normalize_cards(extra_cards))
        validate_unique_cards(cards, context_text)

    def reset_for_manual_hand(self, preserve_stacks: bool = True) -> None:
        for player in self._players:
            player.reset_for_manual_hand(preserve_stack=preserve_stacks)
        self._table.reset_for_manual_hand()
        self.action_log = []
        self.hand_over = False
        self.winner = None
        self.winners = []
        self.hand_started = True

    def configure_player(self, player_ref: int | str, **overrides: Any) -> None:
        self.player(player_ref).configure(self._chip_unit, **overrides)

    def set_player_hole_cards(self, player_ref: int | str, cards: Iterable[int | str]) -> None:
        self.player(player_ref).set_hole_cards(cards)

    def set_board_cards(self, cards: Iterable[int | str]) -> None:
        self._table.set_board_cards(cards)

    def set_player_stacks(self, stacks: dict[int | str, Any] | list[Any] | tuple[Any, ...]) -> None:
        if isinstance(stacks, dict):
            items = list(stacks.items())
        else:
            if len(stacks) != len(self._players):
                raise ValueError("Количество стеков должно совпадать с количеством игроков")
            items = list(enumerate(stacks))
        for player_ref, value in items:
            ticks = self.amount_to_ticks(value)
            if ticks < 0:
                raise ValueError("Стек игрока не может быть отрицательным")
            player = self.player(player_ref)
            player.stack = ticks
            if player.stack > 0 and player.all_in:
                player.all_in = False
            if player.stack == 0 and player.in_hand and not player.folded:
                player.all_in = True

    def infer_street_from_board(self, board_cards: Iterable[int]) -> str:
        board_count = len(list(board_cards))
        if board_count not in BOARD_COUNT_TO_STREET:
            raise ValueError(
                f"Нельзя автоматически определить street по {board_count} картам борда. Допустимо только 0, 3, 4 или 5 карт"
            )
        return BOARD_COUNT_TO_STREET[board_count]

    def rebuild_deck(
        self,
        runout_cards: Optional[Iterable[int | str]] = None,
        dead_cards: Optional[Iterable[int | str]] = None,
        shuffle_remaining: bool = False,
        rng: Optional[random.Random] = None,
    ) -> list[int]:
        upcoming = normalize_cards(runout_cards or [])
        dead = normalize_cards(dead_cards or [])
        used_cards: list[int] = []
        for player in self._players:
            used_cards.extend(player.cards)
        used_cards.extend(self._table.board)
        used_cards.extend(upcoming)
        used_cards.extend(dead)
        validate_unique_cards(used_cards, "manual deck rebuild")
        used_set = set(used_cards)
        remaining = [card for card in create_deck() if card not in used_set]
        if shuffle_remaining:
            if rng is None:
                random.shuffle(remaining)
            else:
                rng.shuffle(remaining)
        self._table.deck = remaining + list(reversed(upcoming))
        return self._table.deck

    def set_runout_cards(
        self,
        cards: Iterable[int | str],
        shuffle_remaining: bool = False,
        rng: Optional[random.Random] = None,
        dead_cards: Optional[Iterable[int | str]] = None,
    ) -> list[int]:
        return self.rebuild_deck(cards, dead_cards=dead_cards, shuffle_remaining=shuffle_remaining, rng=rng)

    def _default_blind_indexes_for_current_dealer(self) -> tuple[int, int]:
        active_count = len(self.get_active_player_indexes())
        if active_count < 2:
            raise ValueError("Для определения блайндов нужно минимум 2 активных игрока")
        if active_count == 2:
            sb_index = self._table.dealer_index
            bb_index = self.get_next_active_player_index(self._table.dealer_index)
        else:
            sb_index = self.get_next_active_player_index(self._table.dealer_index)
            bb_index = self.get_next_active_player_index(sb_index)
        return sb_index, bb_index

    def _validate_blind_player_index(self, player_index: int, blind_name: str) -> None:
        player = self._players[player_index]
        if player.stack <= 0:
            raise ValueError(f"{blind_name} должен указывать на игрока с ненулевым стеком")

    def _resolve_manual_blinds(self, sb_index: Optional[int | str], bb_index: Optional[int | str]) -> tuple[int, int]:
        default_sb, default_bb = self._default_blind_indexes_for_current_dealer()
        resolved_sb = default_sb if sb_index is None else self.player_index(sb_index)
        resolved_bb = default_bb if bb_index is None else self.player_index(bb_index)
        if resolved_sb == resolved_bb:
            raise ValueError("SB и BB не могут указывать на одного и того же игрока")
        self._validate_blind_player_index(resolved_sb, "SB")
        self._validate_blind_player_index(resolved_bb, "BB")
        return resolved_sb, resolved_bb

    def _resolve_manual_to_act(self, street: str, to_act: Optional[int | str]) -> int:
        if to_act is not None:
            resolved = self.player_index(to_act)
            if street != "showdown":
                player = self._players[resolved]
                if not player.in_hand or player.folded or player.all_in:
                    raise ValueError("to_act должен указывать на игрока, который реально может действовать")
            return resolved
        if street == "preflop":
            return self.get_first_to_act_preflop()
        return self.get_first_to_act_postflop()

    def setup_hand(
        self,
        *,
        player_cards: Optional[dict[int | str, Iterable[int | str]]] = None,
        board: Optional[Iterable[int | str]] = None,
        runout: Optional[Iterable[int | str]] = None,
        dead_cards: Optional[Iterable[int | str]] = None,
        street: Optional[str] = None,
        dealer_index: Optional[int | str] = None,
        sb_index: Optional[int | str] = None,
        bb_index: Optional[int | str] = None,
        to_act: Optional[int | str] = None,
        pot: Any = 0,
        current_bet: Any = 0,
        min_raise: Optional[Any] = None,
        player_overrides: Optional[dict[int | str, dict[str, Any]]] = None,
        reset_players: bool = True,
        preserve_stacks: bool = True,
        hand_number: Optional[int] = None,
        hand_started: bool = True,
        action_log: Optional[list[dict[str, Any]]] = None,
        auto_assign_positions: bool = True,
        shuffle_remaining_deck: bool = False,
        rng: Optional[random.Random] = None,
    ) -> None:
        if reset_players:
            self.reset_for_manual_hand(preserve_stacks=preserve_stacks)

        if dealer_index is not None:
            self._table.dealer_index = self.player_index(dealer_index)
        if hand_number is not None:
            self.hand_number = hand_number

        self.hand_started = hand_started
        self.action_log = [] if action_log is None else [dict(item) for item in action_log]
        self.hand_over = False
        self.winner = None
        self.winners = []

        if player_overrides:
            for player_ref, overrides in player_overrides.items():
                self.configure_player(player_ref, **overrides)

        if player_cards:
            for player_ref, cards in player_cards.items():
                self.set_player_hole_cards(player_ref, cards)

        board_cards = normalize_cards(board or [])
        self.set_board_cards(board_cards)

        if street is None:
            street = self.infer_street_from_board(board_cards)
        expected_board_count = STREET_TO_BOARD_COUNT.get(street)
        if expected_board_count is None:
            raise ValueError(f"Некорректная street: {street}")
        if len(board_cards) != expected_board_count:
            raise ValueError(
                f"Для street '{street}' нужно ровно {expected_board_count} карт борда, сейчас {len(board_cards)}"
            )
        self._table.street = street

        if auto_assign_positions:
            self.assign_positions(self._table.dealer_index)

        resolved_sb_index, resolved_bb_index = self._resolve_manual_blinds(sb_index, bb_index)
        self._table.sb_index = resolved_sb_index
        self._table.bb_index = resolved_bb_index

        self._table.pot = self.amount_to_ticks(pot)
        self._table.current_bet = self.amount_to_ticks(current_bet)
        self._table.min_raise = self._table.bb if min_raise is None else self.amount_to_ticks(min_raise)
        self._table.to_act = self._resolve_manual_to_act(street, to_act)

        for player in self._players:
            if player.cards and player.stack == 0 and player.in_hand and not player.folded:
                player.all_in = True

        remaining_board_cards = 5 - len(board_cards)
        runout_cards = normalize_cards(runout or [])
        if len(runout_cards) > remaining_board_cards:
            raise ValueError(
                f"Слишком длинный runout: можно задать максимум {remaining_board_cards} карт(ы) для street '{street}'"
            )

        self.validate_state_cards_unique(
            extra_cards=runout_cards + normalize_cards(dead_cards or []),
            context_text="manual hand setup",
        )
        self.rebuild_deck(
            runout_cards=runout_cards,
            dead_cards=dead_cards,
            shuffle_remaining=shuffle_remaining_deck,
            rng=rng,
        )

    def get_active_player_indexes(self) -> list[int]:
        return [i for i, player in enumerate(self._players) if player.stack > 0]

    def get_next_active_player_index(self, start_index: int) -> int:
        n = len(self._players)
        for step in range(1, n + 1):
            index = (start_index + step) % n
            if self._players[index].stack > 0:
                return index
        return start_index

    def get_next_active_in_hand_index(self, start_index: int) -> int:
        n = len(self._players)
        for step in range(1, n + 1):
            index = (start_index + step) % n
            player = self._players[index]
            if player.in_hand and not player.folded and not player.all_in:
                return index
        return start_index

    def get_next_player_who_can_act(self, start_index: int, *, include_start: bool = False) -> Optional[int]:
        n = len(self._players)
        steps = range(0 if include_start else 1, n + 1)
        for step in steps:
            index = (start_index + step) % n
            player = self._players[index]
            if player.in_hand and not player.folded and not player.all_in:
                return index
        return None

    def get_first_active_from(self, start_index: int) -> int:
        if self._players[start_index].stack > 0:
            return start_index
        return self.get_next_active_player_index(start_index)

    def reset_players_for_new_hand(self) -> None:
        for player in self._players:
            player.reset_for_new_hand()

    def assign_positions(self, dealer_index: int) -> None:
        active_indices = self.get_active_player_indexes()
        active_count = len(active_indices)
        for player in self._players:
            player.position = "OUT"
        if active_count == 0:
            return
        labels = POSITION_LABELS_BY_COUNT.get(active_count)
        if labels is None:
            raise ValueError(f"Неподдерживаемое число активных игроков: {active_count}")
        ordered_active = [dealer_index]
        while len(ordered_active) < active_count:
            ordered_active.append(self.get_next_active_player_index(ordered_active[-1]))
        for index, label in zip(ordered_active, labels):
            self._players[index].position = label

    def deal_hole_cards(self) -> None:
        for _ in range(2):
            for player in self._players:
                if player.in_hand:
                    player.cards.append(self._table.deck.pop())

    def get_first_to_act_preflop(self) -> int:
        active_count = len(self.get_active_player_indexes())
        if active_count == 2:
            return self._table.dealer_index
        return self.get_next_active_in_hand_index(self._table.bb_index)

    def get_first_to_act_postflop(self) -> int:
        player_index = self.get_next_player_who_can_act(self._table.dealer_index)
        return self._table.dealer_index if player_index is None else player_index

    def start_new_hand(self, rng: Optional[random.Random] = None) -> None:
        active_indices = self.get_active_player_indexes()
        if len(active_indices) < 2:
            raise ValueError("Нельзя начать новую раздачу: нужно минимум 2 игрока со стеком")

        if self.hand_started:
            self.hand_number += 1
            self._table.dealer_index = self.get_next_active_player_index(self._table.dealer_index)
        else:
            self.hand_started = True
            self.hand_number = 1
            self._table.dealer_index = self.get_first_active_from(self._table.dealer_index)

        self.reset_players_for_new_hand()
        self.assign_positions(self._table.dealer_index)

        self._table.sb_index, self._table.bb_index = self._default_blind_indexes_for_current_dealer()

        self._table.deck = create_deck()
        if rng is None:
            random.shuffle(self._table.deck)
        else:
            rng.shuffle(self._table.deck)

        self._table.board = []
        self._table.pot = 0
        self._table.street = "preflop"
        self._table.current_bet = self._table.bb
        self._table.min_raise = self._table.bb

        self._players[self._table.sb_index].post_blind(self._table.sb, self._table)
        self._players[self._table.bb_index].post_blind(self._table.bb, self._table)
        # Если BB ушёл all-in меньше полного размера большого блайнда,
        # это НЕ уменьшает текущую ставку для остальных игроков.
        # Следующие игроки по-прежнему обязаны коллировать полный BB,
        # а минимальный рейз считается от полного размера BB.
        self._table.current_bet = self._table.bb

        self.deal_hole_cards()
        self._table.to_act = self.get_first_to_act_preflop()

        self.action_log = []
        self.hand_over = False
        self.winner = None
        self.winners = []

    def move_to_next_street(self) -> None:
        if self._table.street == "preflop":
            self._table.street = "flop"
            self._table.board.extend([self._table.deck.pop(), self._table.deck.pop(), self._table.deck.pop()])
        elif self._table.street == "flop":
            self._table.street = "turn"
            self._table.board.append(self._table.deck.pop())
        elif self._table.street == "turn":
            self._table.street = "river"
            self._table.board.append(self._table.deck.pop())
        elif self._table.street == "river":
            self._table.street = "showdown"
            return

        for player in self._players:
            player.bet_street = 0
            player.acted = False
            player.has_acted_since_full_raise = False

        self._table.current_bet = 0
        self._table.min_raise = self._table.bb
        self._table.to_act = self.get_first_to_act_postflop()

    def _player_can_raise_now(self, player: PlayerState) -> bool:
        to_call = self._table.current_bet - player.bet_street
        if to_call <= 0:
            return True
        return not player.has_acted_since_full_raise

    def legal_actions(self) -> list[dict[str, Any]]:
        player = self._players[self._table.to_act]
        if not player.in_hand or player.folded or player.all_in:
            return []

        current_bet = self._table.current_bet
        to_call = current_bet - player.bet_street
        stack = player.stack
        actions: list[dict[str, Any]] = []

        if to_call > 0:
            actions.append({"type": "fold"})
        if to_call == 0:
            actions.append({"type": "check"})
        else:
            call_amount = min(to_call, stack)
            actions.append({"type": "call", "amount": self.ticks_to_amount(call_amount)})

        if stack > to_call and self._player_can_raise_now(player):
            min_raise_to = current_bet + self._table.min_raise
            max_raise_to = player.bet_street + stack
            if min_raise_to <= max_raise_to:
                actions.append(self._build_raise_action(min_raise_to, max_raise_to))
            elif max_raise_to > current_bet:
                actions.append(self._build_raise_action(max_raise_to, max_raise_to, is_short_all_in=True, reopens_action=False))

        return actions

    def _build_raise_action(
        self,
        min_raise_to: int,
        max_raise_to: int,
        is_short_all_in: bool = False,
        reopens_action: bool = True,
    ) -> dict[str, Any]:
        return {
            "type": "raise",
            "min_to": self.ticks_to_amount(min_raise_to),
            "max_to": self.ticks_to_amount(max_raise_to),
            "is_all_in": min_raise_to == max_raise_to,
            "is_short_all_in": is_short_all_in,
            "reopens_action": reopens_action,
        }

    def get_next_player_index(self, start_index: int) -> int:
        player_index = self.get_next_player_who_can_act(start_index)
        return start_index if player_index is None else player_index

    def can_any_player_act(self) -> bool:
        return any(player.in_hand and not player.folded and not player.all_in for player in self._players)

    def _get_odd_chip_winner(self, eligible_players: list[int]) -> int:
        eligible_set = set(eligible_players)
        n = len(self._players)
        for step in range(1, n + 1):
            index = (self._table.dealer_index + step) % n
            if index in eligible_set:
                player = self._players[index]
                if player.in_hand and not player.folded:
                    return index
        return eligible_players[0]

    def _split_pot_amount(self, pot_amount: int, pot_winners: list[int]) -> dict[int, int]:
        winners_count = len(pot_winners)
        base_share = pot_amount // winners_count
        odd_chips = pot_amount % winners_count
        payouts = {player_index: base_share for player_index in pot_winners}
        if odd_chips > 0:
            payouts[self._get_odd_chip_winner(pot_winners)] += odd_chips
        return payouts

    @staticmethod
    def _mark_player_has_acted(player: PlayerState) -> None:
        player.acted = True
        player.has_acted_since_full_raise = True

    def _reset_raise_reopening_state_for_full_raise(self, raiser_index: int) -> None:
        for player in self._players:
            if player.in_hand and not player.folded and not player.all_in:
                player.has_acted_since_full_raise = False
        self._players[raiser_index].has_acted_since_full_raise = True

    def apply_action(self, action: dict[str, Any]) -> None:
        player_index = self._table.to_act
        player = self._players[player_index]

        if not player.in_hand:
            raise ValueError("Игрок вне раздачи и не может принимать решение")
        if player.folded:
            raise ValueError("Игрок уже сфолдил и не может принимать решение")
        if player.all_in:
            raise ValueError("Игрок уже в all-in и не может принимать решение")

        action_type = action["type"]
        current_bet = self._table.current_bet
        to_call = current_bet - player.bet_street
        call_amount = None
        raise_to = None

        if action_type == "fold":
            if to_call <= 0:
                raise ValueError("Нельзя fold, если можно check")
            player.folded = True
            self._mark_player_has_acted(player)

        elif action_type == "check":
            if to_call != 0:
                raise ValueError("Нельзя check, если есть ставка для колла")
            self._mark_player_has_acted(player)

        elif action_type == "call":
            if to_call <= 0:
                raise ValueError("Нельзя call, если нечего уравнивать")
            call_amount = min(to_call, player.stack)
            player.stack -= call_amount
            player.bet_street += call_amount
            player.bet_total += call_amount
            self._table.pot += call_amount
            self._mark_player_has_acted(player)
            if player.stack == 0:
                player.all_in = True

        elif action_type == "raise":
            if not self._player_can_raise_now(player):
                raise ValueError("Торги не переоткрыты для этого игрока")

            raise_to = self.amount_to_ticks(action["to"])
            min_raise_to = current_bet + self._table.min_raise
            max_raise_to = player.bet_street + player.stack

            if raise_to > max_raise_to:
                raise ValueError("Слишком большой raise")

            is_all_in = raise_to == max_raise_to
            is_short_all_in = raise_to < min_raise_to
            old_min_raise = self._table.min_raise

            if is_short_all_in:
                if not is_all_in:
                    raise ValueError("Слишком маленький raise")
                if raise_to <= current_bet:
                    raise ValueError("Short all-in должен быть больше текущей ставки")
            else:
                if raise_to < min_raise_to:
                    raise ValueError("Слишком маленький raise")

            put_amount = raise_to - player.bet_street
            player.stack -= put_amount
            player.bet_street = raise_to
            player.bet_total += put_amount
            self._table.pot += put_amount

            old_current_bet = self._table.current_bet
            raise_size = raise_to - old_current_bet
            reopens_action = raise_size >= old_min_raise

            self._table.current_bet = raise_to
            if reopens_action:
                self._table.min_raise = raise_size
                self._reset_raise_reopening_state_for_full_raise(player_index)
            else:
                player.has_acted_since_full_raise = True
            player.acted = True
            if player.stack == 0:
                player.all_in = True
        else:
            raise ValueError(f"Неподдерживаемое действие: {action_type}")

        log_item = {
            "street": self._table.street,
            "player": player.name,
            "position": player.position,
            "type": action_type,
        }
        if action_type == "call" and call_amount is not None:
            log_item["amount"] = self.ticks_to_amount(call_amount)
        elif action_type == "raise" and raise_to is not None:
            log_item["to"] = self.ticks_to_amount(raise_to)
            log_item["is_all_in"] = player.all_in
            log_item["reopens_action"] = reopens_action
            log_item["is_short_all_in"] = is_short_all_in
        self.action_log.append(log_item)

        self._table.to_act = self.get_next_player_index(player_index)
        self.resolve_after_action()

    def is_betting_round_complete(self) -> bool:
        active_players = []
        can_act_players = []
        for player in self._players:
            if player.in_hand and not player.folded:
                active_players.append(player)
                if not player.all_in:
                    can_act_players.append(player)

        if len(active_players) <= 1 or len(can_act_players) == 0:
            return True

        current_bet = self._table.current_bet
        for player in can_act_players:
            if not player.acted:
                return False
            if player.bet_street != current_bet:
                return False
        return True

    def run_to_showdown_if_needed(self) -> None:
        if self._table.street == "showdown" or self.can_any_player_act():
            return
        while self._table.street != "showdown":
            self.move_to_next_street()
        self.resolve_showdown()

    def resolve_after_action(self) -> None:
        active_count = 0
        last_active_index = None
        for index, player in enumerate(self._players):
            if player.in_hand and not player.folded:
                active_count += 1
                last_active_index = index

        if active_count == 1 and last_active_index is not None:
            self.hand_over = True
            self.winner = last_active_index
            self.winners = [last_active_index]
            self._players[last_active_index].stack += self._table.pot
            self._table.pot = 0
            return

        self.run_to_showdown_if_needed()
        if self.hand_over:
            return

        if self.is_betting_round_complete():
            self.move_to_next_street()
            if self._table.street == "showdown":
                self.resolve_showdown()

    def build_side_pots(self) -> list[dict[str, Any]]:
        contributions = []
        for index, player in enumerate(self._players):
            if player.bet_total > 0:
                contributions.append({
                    "player_index": index,
                    "amount": player.bet_total,
                    "eligible": player.in_hand and not player.folded,
                })
        pots: list[dict[str, Any]] = []
        while True:
            active_contribs = [item for item in contributions if item["amount"] > 0]
            if not active_contribs:
                break
            level = min(item["amount"] for item in active_contribs)
            pot_amount = 0
            eligible_players: list[int] = []
            for item in contributions:
                if item["amount"] > 0:
                    pot_amount += level
                    item["amount"] -= level
                    if item["eligible"]:
                        eligible_players.append(item["player_index"])
            pots.append({"amount": pot_amount, "eligible_players": eligible_players[:]})
        return pots

    def resolve_showdown(self) -> None:
        if len(self._table.board) != 5:
            raise ValueError("Для showdown на борде должно быть ровно 5 карт")

        alive_indexes = [i for i, player in enumerate(self._players) if player.in_hand and not player.folded]
        for index in alive_indexes:
            if len(self._players[index].cards) != 2:
                raise ValueError(f"Игрок {self._players[index].name} должен иметь ровно 2 карты для showdown")

        total_contributions = sum(player.bet_total for player in self._players)
        if total_contributions > 0 and total_contributions != self._table.pot and not self.action_log:
            raise ValueError("pot должен совпадать с суммой bet_total при showdown")

        pots = self.build_side_pots()
        if not pots and self._table.pot > 0:
            pots = [{"amount": self._table.pot, "eligible_players": alive_indexes[:]}]

        self.winner = None
        self.winners = []
        self.hand_over = True
        all_winners: set[int] = set()

        for pot in pots:
            eligible = pot["eligible_players"]
            if not eligible:
                continue
            best_score = get_best_score_among_players(self, eligible)
            pot_winners = []
            for index in eligible:
                score, _ = best_5_of_7(self._players[index].cards + self._table.board)
                if score == best_score:
                    pot_winners.append(index)
            payouts = self._split_pot_amount(pot["amount"], pot_winners)
            for index, payout in payouts.items():
                self._players[index].stack += payout
                all_winners.add(index)

        if all_winners:
            self.winners = sorted(all_winners)
            self.winner = self.winners[0]
        self._table.pot = 0

    def action_history_by_street(self) -> dict[str, list[dict[str, Any]]]:
        grouped = {street: [] for street in STREETS}
        for item in self.action_log:
            grouped.setdefault(item.get("street", "preflop"), []).append(dict(item))
        return grouped

    def build_hand_summary(self, reveal_all_hole_cards: bool = True) -> dict[str, Any]:
        board_cards = list(self._table.board)
        streets = self.action_history_by_street()
        formatted_streets = []
        for street_name in sorted(streets.keys(), key=street_order_key):
            street_board: list[int] = []
            if street_name == "flop":
                street_board = board_cards[:3]
            elif street_name == "turn":
                street_board = board_cards[:4]
            elif street_name == "river":
                street_board = board_cards[:5]
            formatted_streets.append({
                "street": street_name,
                "board": [card_to_str(card) for card in street_board],
                "actions": [dict(item) for item in streets[street_name]],
                "actions_text": [format_action_for_display(item) for item in streets[street_name]],
            })

        players_info = []
        for index, player in enumerate(self._players):
            cards = player.cards if reveal_all_hole_cards else []
            players_info.append({
                "index": index,
                "name": player.name,
                "position": player.position,
                "in_hand": player.in_hand,
                "folded": player.folded,
                "all_in": player.all_in,
                "stack": self.ticks_to_amount(player.stack),
                "bet_total": self.ticks_to_amount(player.bet_total),
                "cards": [card_to_str(card) for card in cards],
            })

        return {
            "hand_number": self.hand_number,
            "hand_over": self.hand_over,
            "street": self._table.street,
            "board": [card_to_str(card) for card in board_cards],
            "pot": self.ticks_to_amount(self._table.pot),
            "players": players_info,
            "streets": formatted_streets,
            "winner": None if self.winner is None else self._players[self.winner].name,
            "winners": [self._players[index].name for index in self.winners],
        }

    def format_hand_summary(self, reveal_all_hole_cards: bool = True) -> str:
        summary = self.build_hand_summary(reveal_all_hole_cards=reveal_all_hole_cards)
        lines = [
            f"HAND #{summary['hand_number']}",
            f"FINAL STREET: {summary['street']}",
            f"BOARD: {' '.join(summary['board']) if summary['board'] else '-'}",
            "",
            "ACTIONS BY STREET:",
        ]
        for street_item in summary["streets"]:
            lines.append(f"[{street_item['street'].upper()}] board: {' '.join(street_item['board']) if street_item['board'] else '-'}")
            if street_item["actions_text"]:
                for action_text in street_item["actions_text"]:
                    lines.append(f"  - {action_text}")
            else:
                lines.append("  - no actions")

        lines.append("")
        lines.append("PLAYERS:")
        for player in summary["players"]:
            cards_text = " ".join(player["cards"]) if player["cards"] else "-"
            if player["folded"]:
                status = "folded"
            elif player["all_in"]:
                status = "all-in"
            elif player["in_hand"]:
                status = "active"
            else:
                status = "out"
            lines.append(
                f"  - {player['name']} ({player['position']}): cards={cards_text} | stack={player['stack']} | invested={player['bet_total']} | status={status}"
            )

        lines.append("")
        if summary["winners"]:
            label = "WINNER" if len(summary["winners"]) == 1 else "WINNERS"
            lines.append(f"{label}: {', '.join(summary['winners'])}")
        else:
            lines.append("WINNER: -")
        return "\n".join(lines)


def rank_to_value(rank: int) -> int:
    return rank + 2


def evaluate_5cards(cards: list[int]) -> tuple[Any, ...]:
    if len(cards) != 5:
        raise ValueError("Нужно ровно 5 карт")

    ranks = [rank_to_value(card_rank(card)) for card in cards]
    suits = [card_suit(card) for card in cards]
    rank_counts: dict[int, int] = {}
    for rank in ranks:
        rank_counts[rank] = rank_counts.get(rank, 0) + 1

    counts = sorted(rank_counts.values(), reverse=True)
    sorted_ranks_desc = sorted(ranks, reverse=True)
    is_flush = len(set(suits)) == 1

    unique_for_straight = sorted(set(ranks))
    is_straight = False
    straight_high = 0
    if len(unique_for_straight) == 5:
        if unique_for_straight[-1] - unique_for_straight[0] == 4:
            is_straight = True
            straight_high = unique_for_straight[-1]
        elif unique_for_straight == [2, 3, 4, 5, 14]:
            is_straight = True
            straight_high = 5

    if is_straight and is_flush:
        return (8, straight_high)
    if counts == [4, 1]:
        quad_rank = max(rank_counts, key=lambda r: rank_counts[r])
        kicker = max(rank for rank in ranks if rank != quad_rank)
        return (7, quad_rank, kicker)
    if counts == [3, 2]:
        trips_rank = max(rank_counts, key=lambda r: (rank_counts[r], r))
        pair_rank = max(rank for rank in rank_counts if rank != trips_rank)
        return (6, trips_rank, pair_rank)
    if is_flush:
        return (5, *sorted_ranks_desc)
    if is_straight:
        return (4, straight_high)
    if counts == [3, 1, 1]:
        trips_rank = max(rank_counts, key=lambda r: rank_counts[r])
        kickers = sorted((rank for rank in ranks if rank != trips_rank), reverse=True)
        return (3, trips_rank, *kickers)
    if counts == [2, 2, 1]:
        pair_ranks = sorted((rank for rank, count in rank_counts.items() if count == 2), reverse=True)
        kicker = max(rank for rank, count in rank_counts.items() if count == 1)
        return (2, pair_ranks[0], pair_ranks[1], kicker)
    if counts == [2, 1, 1, 1]:
        pair_rank = max(rank for rank, count in rank_counts.items() if count == 2)
        kickers = sorted((rank for rank, count in rank_counts.items() if count == 1), reverse=True)
        return (1, pair_rank, *kickers)
    return (0, *sorted_ranks_desc)


def best_5_of_7(cards7: list[int]) -> tuple[tuple[Any, ...], list[int]]:
    if len(cards7) != 7:
        raise ValueError("Нужно ровно 7 карт")
    best_score: Optional[tuple[Any, ...]] = None
    best_hand: Optional[list[int]] = None
    n = len(cards7)
    for a in range(n):
        for b in range(a + 1, n):
            five_cards = [cards7[i] for i in range(n) if i not in (a, b)]
            score = evaluate_5cards(five_cards)
            if best_score is None or score > best_score:
                best_score = score
                best_hand = five_cards[:]
    assert best_score is not None and best_hand is not None
    return best_score, best_hand


def street_order_key(street_name: str) -> int:
    return {"preflop": 0, "flop": 1, "turn": 2, "river": 3, "showdown": 4}.get(street_name, 999)


def format_action_for_display(action_item: dict[str, Any]) -> str:
    prefix = action_item["player"] if not action_item.get("position") else f"{action_item['player']} ({action_item['position']})"
    action_type = action_item["type"]
    if action_type == "raise":
        suffix = f"raise to {action_item['to']}"
        if action_item.get("is_all_in"):
            suffix += " all-in"
        elif action_item.get("is_short_all_in"):
            suffix += " short all-in"
        return f"{prefix}: {suffix}"
    if action_type == "call":
        return f"{prefix}: call {action_item['amount']}"
    if action_type == "check":
        return f"{prefix}: check"
    if action_type == "fold":
        return f"{prefix}: fold"
    return f"{prefix}: {action_type}"


def get_best_score_among_players(core: HandCore, player_indexes: list[int]) -> tuple[Any, ...]:
    best_score: Optional[tuple[Any, ...]] = None
    board = core.table.board
    for index in player_indexes:
        score, _ = best_5_of_7(core.players[index].cards + board)
        if best_score is None or score > best_score:
            best_score = score
    assert best_score is not None
    return best_score


evaluate_5cards = profile_function("engine_core.evaluate_5cards", count_name="engine_core.evaluate_5cards.calls")(evaluate_5cards)
best_5_of_7 = profile_function("engine_core.best_5_of_7", count_name="engine_core.best_5_of_7.calls")(best_5_of_7)
