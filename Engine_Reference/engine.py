from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Optional
import random

from engine_core import (
    HandCore,
    amount_to_ticks_by_unit,
    best_5_of_7,
    build_default_names,
    card_to_str,
    create_deck,
    evaluate_5cards,
    format_action_for_display,
    normalize_cards,
    str_to_card,
)
from equity import (
    combo_to_str,
    deal_random_hands,
    draw_random_board,
    evaluate_multiway_board,
    hand_vs_hand,
    hand_vs_hand_exact,
    hand_vs_hand_monte_carlo,
    multiway_hand_equity_monte_carlo,
    parse_range,
    range_vs_range,
    range_vs_range_exact,
    range_vs_range_monte_carlo,
    weighted_range_to_text,
)
from preflop_advisor import (
    Spot,
    advise_preflop_action,
    advise_preflop_spot,
    describe_all_supported_spots,
    expand_range_text,
    get_action_range,
    get_action_range_for_spot,
    get_chart_for_spot,
    get_range_profile,
    hand_to_class,
    list_supported_node_types,
)

@dataclass(slots=True)
class HandSetup:
    _kwargs: dict[str, Any] = field(default_factory=dict)

    def player_cards(self, mapping: dict[int | str, Iterable[int | str]]) -> "HandSetup":
        self._kwargs["player_cards"] = mapping
        return self

    def stacks(self, mapping: dict[int | str, Any] | list[Any] | tuple[Any, ...]) -> "HandSetup":
        self._kwargs.setdefault("player_overrides", {})
        if isinstance(mapping, dict):
            for player_ref, value in mapping.items():
                self._kwargs["player_overrides"].setdefault(player_ref, {})["stack"] = value
        else:
            self._kwargs["_stack_sequence"] = list(mapping)
        return self

    def board(self, cards: Iterable[int | str]) -> "HandSetup":
        self._kwargs["board"] = cards
        return self

    def runout(self, cards: Iterable[int | str]) -> "HandSetup":
        self._kwargs["runout"] = cards
        return self

    def dead_cards(self, cards: Iterable[int | str]) -> "HandSetup":
        self._kwargs["dead_cards"] = cards
        return self

    def street(self, street_name: str) -> "HandSetup":
        self._kwargs["street"] = street_name
        return self

    def dealer(self, dealer_index: int | str) -> "HandSetup":
        self._kwargs["dealer_index"] = dealer_index
        return self

    def blinds(self, *, sb_index: Optional[int | str] = None, bb_index: Optional[int | str] = None) -> "HandSetup":
        if sb_index is not None:
            self._kwargs["sb_index"] = sb_index
        if bb_index is not None:
            self._kwargs["bb_index"] = bb_index
        return self

    def to_act(self, player_ref: int | str) -> "HandSetup":
        self._kwargs["to_act"] = player_ref
        return self

    def betting(self, *, pot: Any = 0, current_bet: Any = 0, min_raise: Optional[Any] = None) -> "HandSetup":
        self._kwargs["pot"] = pot
        self._kwargs["current_bet"] = current_bet
        if min_raise is not None:
            self._kwargs["min_raise"] = min_raise
        return self

    def overrides(
        self,
        player_overrides: Optional[dict[int | str, dict[str, Any]]] = None,
        **kwargs: dict[str, Any],
    ) -> "HandSetup":
        mapping = {} if player_overrides is None else dict(player_overrides)
        mapping.update(kwargs)
        current = self._kwargs.setdefault("player_overrides", {})
        for player_ref, overrides in mapping.items():
            current.setdefault(player_ref, {}).update(overrides)
        return self

    def options(
        self,
        *,
        reset_players: bool = True,
        preserve_stacks: bool = True,
        hand_number: Optional[int] = None,
        hand_started: bool = True,
        action_log: Optional[list[dict[str, Any]]] = None,
        auto_assign_positions: bool = True,
        shuffle_remaining_deck: bool = False,
        rng: Optional[random.Random] = None,
    ) -> "HandSetup":
        self._kwargs["reset_players"] = reset_players
        self._kwargs["preserve_stacks"] = preserve_stacks
        if hand_number is not None:
            self._kwargs["hand_number"] = hand_number
        self._kwargs["hand_started"] = hand_started
        if action_log is not None:
            self._kwargs["action_log"] = action_log
        self._kwargs["auto_assign_positions"] = auto_assign_positions
        self._kwargs["shuffle_remaining_deck"] = shuffle_remaining_deck
        if rng is not None:
            self._kwargs["rng"] = rng
        return self

    def to_kwargs(self) -> dict[str, Any]:
        kwargs = dict(self._kwargs)
        stack_sequence = kwargs.pop("_stack_sequence", None)
        if stack_sequence is not None:
            kwargs.setdefault("player_overrides", {})
            kwargs["player_overrides"].update({index: {"stack": value} for index, value in enumerate(stack_sequence)})
        return kwargs

    def apply(self, target: "PokerEngine") -> "PokerEngine":
        target.setup_hand(**self.to_kwargs())
        return target


class PokerEngine:
    def __init__(
        self,
        names: Optional[list[str]] = None,
        start_stack: Any = 100,
        small_blind: Any = 0.5,
        big_blind: Any = 1,
        *,
        player_count: Optional[int] = None,
        stacks: Optional[Any] = None,
        _core: Optional[HandCore] = None,
    ):
        self._core = _core or HandCore(
            names=names,
            player_count=player_count,
            start_stack=start_stack,
            stacks=stacks,
            small_blind=small_blind,
            big_blind=big_blind,
        )

    @classmethod
    def cash(
        cls,
        *,
        player_count: int = 6,
        names: Optional[list[str]] = None,
        start_stack: Any = 100,
        stacks: Optional[Any] = None,
        small_blind: Any = 0.5,
        big_blind: Any = 1,
    ) -> "PokerEngine":
        return cls(
            names=names,
            player_count=player_count,
            start_stack=start_stack,
            stacks=stacks,
            small_blind=small_blind,
            big_blind=big_blind,
        )

    @classmethod
    def six_max(
        cls,
        names: Optional[list[str]] = None,
        start_stack: Any = 100,
        small_blind: Any = 0.5,
        big_blind: Any = 1,
        *,
        stacks: Optional[Any] = None,
    ) -> "PokerEngine":
        return cls(
            names=names or build_default_names(6),
            start_stack=start_stack,
            stacks=stacks,
            small_blind=small_blind,
            big_blind=big_blind,
        )

    def __len__(self) -> int:
        return self.max_players

    def __getitem__(self, key: str) -> Any:
        return self.snapshot()[key]

    @property
    def hand_number(self) -> int:
        return self._core.hand_number

    @property
    def max_players(self) -> int:
        return self._core.max_players

    @property
    def player_names(self) -> list[str]:
        return self._core.player_names

    @property
    def state(self) -> dict[str, Any]:
        return self.snapshot()

    @property
    def table(self) -> dict[str, Any]:
        return self.snapshot()["table"]

    @property
    def players(self) -> list[dict[str, Any]]:
        return self.snapshot()["players"]

    def hand(self) -> HandSetup:
        return HandSetup()

    def scenario(self) -> HandSetup:
        return self.hand()

    def snapshot(self, reveal_all_hole_cards: bool = True) -> dict[str, Any]:
        return self._core.snapshot(reveal_all_hole_cards=reveal_all_hole_cards)

    def player(self, player_ref: int | str, reveal_cards: bool = True) -> dict[str, Any]:
        index = self._core.player_index(player_ref)
        return self._core.players[index].snapshot(self._core.table, reveal_cards=reveal_cards)

    def player_cards(self, player_ref: int | str) -> list[str]:
        return self.player(player_ref)["cards"]

    def start_hand(self, rng: Optional[random.Random] = None) -> "PokerEngine":
        self._core.start_new_hand(rng=rng)
        return self

    def setup_hand(self, **kwargs: Any) -> "PokerEngine":
        self._core.setup_hand(**kwargs)
        return self

    def configure_player(self, player_ref: int | str, **overrides: Any) -> "PokerEngine":
        self._core.configure_player(player_ref, **overrides)
        return self

    def set_player_stacks(self, stacks: dict[int | str, Any] | list[Any] | tuple[Any, ...]) -> "PokerEngine":
        self._core.set_player_stacks(stacks)
        return self

    def set_player_hole_cards(self, player_ref: int | str, cards: Iterable[int | str]) -> "PokerEngine":
        self._core.set_player_hole_cards(player_ref, cards)
        return self

    def set_board_cards(self, cards: Iterable[int | str]) -> "PokerEngine":
        self._core.set_board_cards(cards)
        return self

    def rebuild_deck(
        self,
        runout_cards: Optional[Iterable[int | str]] = None,
        dead_cards: Optional[Iterable[int | str]] = None,
        shuffle_remaining: bool = False,
        rng: Optional[random.Random] = None,
    ) -> "PokerEngine":
        self._core.rebuild_deck(
            runout_cards=runout_cards,
            dead_cards=dead_cards,
            shuffle_remaining=shuffle_remaining,
            rng=rng,
        )
        return self

    def legal_actions(self) -> list[dict[str, Any]]:
        return self._core.legal_actions()

    def can_any_player_act(self) -> bool:
        return self._core.can_any_player_act()

    def act(self, action_or_type: str | dict[str, Any], **kwargs: Any) -> "PokerEngine":
        if isinstance(action_or_type, dict):
            action = dict(action_or_type)
        else:
            action = {"type": action_or_type}
            action.update(kwargs)
        self._core.apply_action(action)
        return self

    def next_street(self) -> "PokerEngine":
        self._core.move_to_next_street()
        return self

    def side_pots(self) -> list[dict[str, Any]]:
        raw_pots = self._core.build_side_pots()
        return [
            {
                "amount": self._core.ticks_to_amount(pot["amount"]),
                "amount_ticks": pot["amount"],
                "eligible_players": list(pot["eligible_players"]),
                "eligible_names": [self._core.players[index].name for index in pot["eligible_players"]],
            }
            for pot in raw_pots
        ]

    def resolve_showdown(self) -> "PokerEngine":
        self._core.resolve_showdown()
        return self

    def action_history_by_street(self) -> dict[str, list[dict[str, Any]]]:
        return self._core.action_history_by_street()

    def summary_dict(self, reveal_all_hole_cards: bool = True) -> dict[str, Any]:
        return self._core.build_hand_summary(reveal_all_hole_cards=reveal_all_hole_cards)

    def summary_text(self, reveal_all_hole_cards: bool = True) -> str:
        return self._core.format_hand_summary(reveal_all_hole_cards=reveal_all_hole_cards)

    def current_actor(self) -> dict[str, Any]:
        return self.player(self._core.table.to_act)


# -------- legacy/procedural wrappers --------

def create_manual_hand_config() -> HandSetup:
    return HandSetup()


def create_hand_state(
    names: Optional[list[str]] = None,
    start_stack: Any = 100,
    small_blind: Any = 0.5,
    big_blind: Any = 1,
    *,
    player_count: Optional[int] = None,
    stacks: Optional[Any] = None,
) -> PokerEngine:
    return PokerEngine(
        names=names,
        player_count=player_count,
        start_stack=start_stack,
        stacks=stacks,
        small_blind=small_blind,
        big_blind=big_blind,
    )


def start_new_hand(state: PokerEngine, rng: Optional[random.Random] = None) -> PokerEngine:
    return state.start_hand(rng=rng)


def setup_manual_hand(state: PokerEngine, **kwargs: Any) -> PokerEngine:
    return state.setup_hand(**kwargs)


def get_legal_actions(state: PokerEngine) -> list[dict[str, Any]]:
    return state.legal_actions()


def move_to_next_street(state: PokerEngine) -> PokerEngine:
    return state.next_street()


def apply_action(state: PokerEngine, action: dict[str, Any]) -> PokerEngine:
    return state.act(action)


def build_side_pots(state: PokerEngine) -> list[dict[str, Any]]:
    return state.side_pots()


def resolve_showdown(state: PokerEngine) -> PokerEngine:
    return state.resolve_showdown()


def action_history_by_street(state: PokerEngine) -> dict[str, list[dict[str, Any]]]:
    return state.action_history_by_street()


def build_hand_summary(state: PokerEngine, reveal_all_hole_cards: bool = True) -> dict[str, Any]:
    return state.summary_dict(reveal_all_hole_cards=reveal_all_hole_cards)


def format_hand_summary(state: PokerEngine, reveal_all_hole_cards: bool = True) -> str:
    return state.summary_text(reveal_all_hole_cards=reveal_all_hole_cards)


def _chip_unit_from_any(table_or_state: Any) -> Fraction:
    if isinstance(table_or_state, PokerEngine):
        return table_or_state._core.chip_unit
    if isinstance(table_or_state, HandCore):
        return table_or_state.chip_unit
    if isinstance(table_or_state, dict):
        if "chip_unit" in table_or_state:
            return Fraction(str(table_or_state["chip_unit"]))
        if "table" in table_or_state and isinstance(table_or_state["table"], dict):
            return Fraction(str(table_or_state["table"]["chip_unit"]))
    raise TypeError("Не удалось определить chip_unit из переданного объекта")


def amount_to_ticks(table_or_state: Any, amount: Any) -> int:
    return amount_to_ticks_by_unit(amount, _chip_unit_from_any(table_or_state))


def ticks_to_amount(table_or_state: Any, ticks: int) -> int | float:
    chip_unit = _chip_unit_from_any(table_or_state)
    product = chip_unit * ticks
    if product.denominator == 1:
        return product.numerator
    return float(product)


__all__ = [
    "HandSetup",
    "PokerEngine",
    "action_history_by_street",
    "amount_to_ticks",
    "apply_action",
    "best_5_of_7",
    "build_hand_summary",
    "build_side_pots",
    "card_to_str",
    "create_deck",
    "create_hand_state",
    "create_manual_hand_config",
    "evaluate_5cards",
    "format_action_for_display",
    "format_hand_summary",
    "get_legal_actions",
    "move_to_next_street",
    "normalize_cards",
    "resolve_showdown",
    "setup_manual_hand",
    "start_new_hand",
    "str_to_card",
    "ticks_to_amount",
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
    "Spot",
    "hand_to_class",
    "expand_range_text",
    "list_supported_node_types",
    "get_range_profile",
    "advise_preflop_action",
    "advise_preflop_spot",
    "get_chart_for_spot",
    "get_action_range",
    "get_action_range_for_spot",
    "describe_all_supported_spots",
]
