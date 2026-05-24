from __future__ import annotations

"""Decision layer for HERO actions in NLHE cash spots.

This module does not modify engine.py or advisor files.
It sits on top of preflop_advisor.py, postflop_advisor.py and equity.py.

Current integrated factors:
- equity vs one or more villain ranges
- zero fold equity thresholds for HERO sizings
- required fold equity with non-zero showdown equity
- call threshold via pot odds
- explicit handling of IP / OOP
- explicit handling of multiway
- explicit handling of SPR
- sizing-by-sizing EV comparison for HERO
- optional range sourcing from preflop spots or postflop reports

Not modeled yet:
- blockers (baseline tags are supported)
- full nut / range advantage solver model
- rake / ICM / implied odds
"""

import hashlib
import importlib
import json
import random
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from decision_types import HeroDecision, PostflopContext, PostflopDecision, PreflopContext, PreflopDecision, RangeSource
from engine_core import card_to_str, create_deck, str_to_card
from equity import parse_range, score_7_cards_fast
from preflop_advisor import advise_preflop_action, get_action_range_for_spot

RANGE_SOURCE_CONTRACT = "range_source_v1"


def _import_postflop_advisor_module():
    try:
        return importlib.import_module("postflop_advisor"), None
    except Exception as exc:  # pragma: no cover - exercised in runtime fallback environments
        return None, exc


_POSTFLOP_ADVISOR_MODULE, _POSTFLOP_ADVISOR_IMPORT_ERROR = _import_postflop_advisor_module()
analyze_multiway_postflop_line = getattr(_POSTFLOP_ADVISOR_MODULE, "analyze_multiway_postflop_line", None)
analyze_multiway_partial_postflop_line = getattr(_POSTFLOP_ADVISOR_MODULE, "analyze_multiway_partial_postflop_line", None)
analyze_postflop_line = getattr(_POSTFLOP_ADVISOR_MODULE, "analyze_postflop_line", None)
categorize_villain_combo = getattr(_POSTFLOP_ADVISOR_MODULE, "categorize_villain_combo", None)
filter_postflop_range = getattr(_POSTFLOP_ADVISOR_MODULE, "filter_postflop_range", None)
_build_range_summary = getattr(_POSTFLOP_ADVISOR_MODULE, "_build_range_summary", None)
RANGE_SOURCE_CONTRACT = getattr(_POSTFLOP_ADVISOR_MODULE, "RANGE_SOURCE_CONTRACT", RANGE_SOURCE_CONTRACT)


def _identity_json_safe(value: object) -> object:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _identity_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_identity_json_safe(v) for v in value]
    return str(value)


def _identity_hash(prefix: str, payload: object) -> str:
    digest = hashlib.sha1()
    digest.update(prefix.encode("utf-8"))
    digest.update(b"|")
    digest.update(json.dumps(_identity_json_safe(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


def _latest_frame_id_from_actions(actions: Sequence[dict[str, object]] | None) -> Optional[str]:
    if not actions:
        return None
    for item in reversed(list(actions)):
        frame_id = item.get("frame_id")
        if frame_id not in (None, ""):
            return str(frame_id)
    return None


def _build_decision_identity(
    *,
    street: str,
    engine_action: str,
    raw_action: str,
    context_meta: Optional[Dict[str, object]] = None,
    identity_meta: Optional[Dict[str, object]] = None,
) -> tuple[str, str, Optional[str]]:
    meta = {} if context_meta is None else dict(context_meta)
    ident = {} if identity_meta is None else dict(identity_meta)
    source_frame_id = None
    direct_source_frame_id = meta.get("source_frame_id")
    if direct_source_frame_id not in (None, ""):
        source_frame_id = str(direct_source_frame_id)
    else:
        source_frame_id = _latest_frame_id_from_actions(meta.get("actions_seen"))
    fingerprint_payload = {
        "street": street,
        "engine_action": engine_action,
        "raw_action": raw_action,
        "hero_hand": meta.get("hero_hand"),
        "board": meta.get("board"),
        "hand_id": meta.get("hand_id"),
        "hero_original_position": meta.get("hero_original_position"),
        "node_type": ident.get("node_type"),
        "opener_pos": ident.get("opener_pos"),
        "three_bettor_pos": ident.get("three_bettor_pos"),
        "four_bettor_pos": ident.get("four_bettor_pos"),
        "limpers": ident.get("limpers"),
        "callers": ident.get("callers"),
        "actions_seen": meta.get("actions_seen"),
        "line_context": meta.get("line_context"),
        "source_frame_id": source_frame_id,
    }
    solver_fingerprint = _identity_hash("solver_fingerprint_v1", fingerprint_payload)
    decision_payload = {
        "solver_fingerprint": solver_fingerprint,
        "street": street,
        "engine_action": engine_action,
        "raw_action": raw_action,
        "size_pct": meta.get("size_pct"),
        "amount_to": meta.get("amount_to"),
        "source_frame_id": source_frame_id,
    }
    decision_id = _identity_hash("decision_id_v1", decision_payload)[:24]
    return solver_fingerprint, decision_id, source_frame_id


def _raise_missing_postflop_analysis(board_cards: Sequence[CardLike]) -> None:
    card_count = len(list(board_cards or []))
    resolved_street = STREET_BY_BOARD_COUNT.get(card_count, f"board_{card_count}")
    if _POSTFLOP_ADVISOR_IMPORT_ERROR is not None:
        raise RuntimeError(
            f"postflop_advisor import failed; cannot build official {resolved_street} narrowing report"
        ) from _POSTFLOP_ADVISOR_IMPORT_ERROR
    raise RuntimeError(
        f"postflop_advisor does not expose an official narrowing builder for {resolved_street}"
    )

CardLike = Union[int, str]
Combo = Tuple[int, int]
WeightedCombo = Tuple[Combo, float]
RangeInput = Union[str, Sequence[str], Sequence[Combo], Dict[Union[str, Combo], float], List[WeightedCombo]]

STREET_BY_BOARD_COUNT = {0: "preflop", 3: "flop", 4: "turn", 5: "river"}
DEFAULT_BET_SIZES_PCT = (33.0, 50.0, 70.0)
RANKS_DESC = "AKQJT98765432"
RANKS_ASC = RANKS_DESC[::-1]
RANK_TO_STRENGTH = {r: i for i, r in enumerate(RANKS_DESC)}
BROKEN_TOKEN_REPLACEMENTS = {
    "53s-98s": "53s 64s 75s 86s 97s 98s",
    "54s-98s": "54s 65s 76s 87s 98s",
    "64s-98s": "64s 75s 86s 97s 98s",
    "65s-98s": "65s 76s 87s 98s",
    "QJo-JTo": "QJo JTo",
}


def _build_range_source_from_expr(range_expr: str, *, name: str, source_type: str, meta: Optional[Dict[str, object]] = None, blocked_cards: Optional[Sequence[CardLike]] = None) -> RangeSource:
    raw_expr = str(range_expr or "").strip()
    normalized_expr = normalize_range_for_equity(raw_expr) if raw_expr else None
    weighted_combos = _parse_range_flex(normalized_expr or raw_expr, blocked_cards=blocked_cards or [])
    return RangeSource(
        name=name,
        source_type=source_type,
        raw_expr=raw_expr or None,
        normalized_expr=normalized_expr,
        weighted_combos=weighted_combos,
        meta={} if meta is None else dict(meta),
    )


def _advise_preflop_decision_bridge(
    hero_hand: Sequence[CardLike],
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
        list(hero_hand),
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
    range_source = None
    expr = result.get("selected_range_expr")
    if expr:
        range_source = _build_range_source_from_expr(
            str(expr),
            name=actor_name,
            source_type="preflop_action_range",
            meta={
                "node_type": node_type,
                "hero_pos": hero_pos,
                "opener_pos": opener_pos,
                "three_bettor_pos": three_bettor_pos,
                "four_bettor_pos": four_bettor_pos,
                "limpers": limpers,
                "callers": callers,
                "range_owner": range_owner,
                "description": result.get("description"),
            },
        )
    return PreflopDecision(
        action=str(result.get("recommended_action") or "fold"),
        hand_class=str(result.get("hand_class") or ""),
        actor_name=actor_name,
        actor_pos=hero_pos,
        is_mixed_action=bool(result.get("is_mixed_action")),
        matching_actions=list(result.get("matching_actions") or []),
        selected_range_expr=result.get("selected_range_expr"),
        action_map=dict(result.get("ranges") or {}),
        range_source=range_source,
        fallback_reason=result.get("fallback_reason"),
        meta={"description": result.get("description", "")},
    )


def _get_action_range_source_for_spot_bridge(
    *,
    node_type: str,
    hero_pos: str,
    action: str,
    opener_pos: Optional[str] = None,
    three_bettor_pos: Optional[str] = None,
    four_bettor_pos: Optional[str] = None,
    callers: int = 0,
    limpers: int = 0,
    range_owner: str = "opponent",
    actor_name: str = "Villain",
    blocked_cards: Optional[Sequence[CardLike]] = None,
) -> RangeSource:
    expr = get_action_range_for_spot(
        node_type=node_type,
        hero_pos=hero_pos,
        action=action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        limpers=limpers,
        range_owner=range_owner,
    )
    return _build_range_source_from_expr(
        expr,
        name=actor_name,
        source_type="preflop_spot_action_range",
        meta={
            "node_type": node_type,
            "hero_pos": hero_pos,
            "action": action,
            "opener_pos": opener_pos,
            "three_bettor_pos": three_bettor_pos,
            "four_bettor_pos": four_bettor_pos,
            "callers": callers,
            "limpers": limpers,
            "range_owner": range_owner,
        },
        blocked_cards=blocked_cards,
    )


# =========================
# low-level helpers
# =========================

def _normalize_cards(cards: Iterable[CardLike]) -> List[int]:
    out: List[int] = []
    for card in cards:
        if isinstance(card, int):
            if not (0 <= card < 52):
                raise ValueError(f"Некорректная карта: {card}")
            out.append(card)
        elif isinstance(card, str):
            out.append(str_to_card(card))
        else:
            raise TypeError("Карты должны быть int или строками вида 'As'")
    if len(out) != len(set(out)):
        raise ValueError("Обнаружены повторяющиеся карты")
    return out


def _street_from_board(board: Sequence[CardLike]) -> str:
    count = len(board)
    if count not in STREET_BY_BOARD_COUNT:
        raise ValueError("board должен содержать 0, 3, 4 или 5 карт")
    return STREET_BY_BOARD_COUNT[count]


def _size_pct_to_fraction(size_pct: float) -> float:
    value = float(size_pct)
    if value < 0:
        raise ValueError("size_pct не может быть отрицательным")
    return value / 100.0 if value > 10 else value


# =========================
# range normalization bridge
# =========================

def _sanitize_broken_tokens(text: str) -> str:
    fixed = str(text)
    for bad, replacement in BROKEN_TOKEN_REPLACEMENTS.items():
        fixed = fixed.replace(bad, replacement)
        fixed = fixed.replace(bad.upper(), replacement)
    return fixed


def _range_sort_key(hand_class: str) -> Tuple[int, int, int, int]:
    if len(hand_class) == 2:
        return (0, RANK_TO_STRENGTH[hand_class[0]], 0, 0)
    suited_order = 0 if hand_class[2] == "s" else 1
    return (1, RANK_TO_STRENGTH[hand_class[0]], RANK_TO_STRENGTH[hand_class[1]], suited_order)


def _ordered_pair_range(a: str, b: str) -> List[str]:
    start = RANKS_ASC.index(a)
    end = RANKS_ASC.index(b)
    lo, hi = sorted((start, end))
    return [RANKS_ASC[i] * 2 for i in range(lo, hi + 1)]


def _vary_low_same_high(hi: str, low_a: str, low_b: str, suffix: str) -> List[str]:
    hi_strength = RANK_TO_STRENGTH[hi]
    candidates = [r for r in RANKS_ASC if RANK_TO_STRENGTH[r] > hi_strength]
    start = candidates.index(low_a)
    end = candidates.index(low_b)
    lo, hi_idx = sorted((start, end))
    return [hi + candidates[i] + suffix for i in range(lo, hi_idx + 1)]


def _vary_high_same_low(high_a: str, high_b: str, low: str, suffix: str) -> List[str]:
    low_strength = RANK_TO_STRENGTH[low]
    candidates = [r for r in RANKS_DESC if RANK_TO_STRENGTH[r] < low_strength]
    start = candidates.index(high_a)
    end = candidates.index(high_b)
    lo, hi_idx = sorted((start, end))
    return [candidates[i] + low + suffix for i in range(lo, hi_idx + 1)]


def _expand_single_token(token: str) -> List[str]:
    token = token.strip()
    if len(token) == 2:
        a, b = token[0].upper(), token[1].upper()
        if a == b and a in RANK_TO_STRENGTH:
            return [a + b]
        if a in RANK_TO_STRENGTH and b in RANK_TO_STRENGTH and a != b:
            hi, lo = sorted((a, b), key=lambda r: RANK_TO_STRENGTH[r])
            return [hi + lo + "s", hi + lo + "o"]
    if len(token) == 3:
        a, b, suf = token[0].upper(), token[1].upper(), token[2].lower()
        if suf not in ("s", "o"):
            raise ValueError(f"Некорректный токен диапазона: {token}")
        if a == b:
            raise ValueError(f"Карманная пара не должна иметь суффикс s/o: {token}")
        hi, lo = sorted((a, b), key=lambda r: RANK_TO_STRENGTH[r])
        return [hi + lo + suf]
    raise ValueError(f"Некорректный токен диапазона: {token}")


def _expand_plus_token(token: str) -> List[str]:
    base = token[:-1]
    if len(base) == 2 and base[0].upper() == base[1].upper():
        start_rank = base[0].upper()
        start = RANKS_ASC.index(start_rank)
        return [RANKS_ASC[i] * 2 for i in range(start, len(RANKS_ASC))]
    if len(base) == 3:
        hi, lo, suf = base[0].upper(), base[1].upper(), base[2].lower()
        if suf not in ("s", "o") or hi == lo:
            raise ValueError(f"Некорректный плюс-токен: {token}")
        hi_strength = RANK_TO_STRENGTH[hi]
        candidates = [r for r in RANKS_ASC if RANK_TO_STRENGTH[r] > hi_strength]
        if lo not in candidates:
            raise ValueError(f"Некорректный плюс-токен: {token}")
        start = candidates.index(lo)
        return [hi + candidates[i] + suf for i in range(start, len(candidates))]
    raise ValueError(f"Некорректный плюс-токен: {token}")


def _expand_dash_token(token: str) -> List[str]:
    left, right = token.split("-", 1)
    left = left.strip()
    right = right.strip()
    if len(left) == 2 and len(right) == 2 and left[0].upper() == left[1].upper() and right[0].upper() == right[1].upper():
        return _ordered_pair_range(left[0].upper(), right[0].upper())
    if len(left) == 3 and len(right) == 3 and left[2].lower() == right[2].lower():
        a1, b1, suf = left[0].upper(), left[1].upper(), left[2].lower()
        a2, b2 = right[0].upper(), right[1].upper()
        if a1 == a2 and b1 != b2:
            return _vary_low_same_high(a1, b1, b2, suf)
        if b1 == b2 and a1 != a2:
            return _vary_high_same_low(a1, a2, b1, suf)
    raise ValueError(f"Некорректный dash-токен диапазона: {token}")


def expand_range_text_for_equity(range_expr: str) -> List[str]:
    range_expr = _sanitize_broken_tokens(range_expr)
    out: List[str] = []
    seen = set()
    for raw_token in range_expr.replace(",", " ").replace(";", " ").split():
        token = raw_token.strip()
        if not token:
            continue
        if token.endswith("+"):
            expanded = _expand_plus_token(token)
        elif "-" in token:
            expanded = _expand_dash_token(token)
        else:
            expanded = _expand_single_token(token)
        for item in expanded:
            if item not in seen:
                seen.add(item)
                out.append(item)
    return sorted(out, key=_range_sort_key)


def normalize_range_for_equity(range_expr: str) -> str:
    return " ".join(expand_range_text_for_equity(range_expr))


def _parse_range_flex(range_input: RangeInput, blocked_cards: Iterable[CardLike] | None = None) -> List[WeightedCombo]:
    blocked = [] if blocked_cards is None else list(blocked_cards)
    if isinstance(range_input, str):
        try:
            return parse_range(range_input, blocked_cards=blocked)
        except Exception:
            normalized = normalize_range_for_equity(range_input)
            return parse_range(normalized, blocked_cards=blocked)

    if isinstance(range_input, list) and range_input:
        first = range_input[0]
        if (
            isinstance(first, tuple)
            and len(first) == 2
            and isinstance(first[0], tuple)
            and len(first[0]) == 2
        ):
            blocked_ints = set(_normalize_cards(blocked))
            out: List[WeightedCombo] = []
            for combo, weight in range_input:  # type: ignore[misc]
                c1, c2 = combo
                if c1 in blocked_ints or c2 in blocked_ints or c1 == c2:
                    continue
                out.append(((int(c1), int(c2)), float(weight)))
            return out

    return parse_range(range_input, blocked_cards=blocked)


# =========================
# range sources from project files
# =========================

def _build_range_source_from_preflop_spot(villain: Dict[str, object], *, index: int) -> RangeSource:
    node_type = str(villain["node_type"]).lower()
    villain_pos = str(villain["villain_pos"]).upper()
    villain_action = str(villain["villain_action"]).lower()
    opener_pos = str(villain.get("opener_pos") or "").upper() or None
    three_bettor_pos = str(villain.get("three_bettor_pos") or "").upper() or None
    four_bettor_pos = str(villain.get("four_bettor_pos") or "").upper() or None
    callers = int(villain.get("callers", 0) or 0)
    limpers = int(villain.get("limpers", 0) or 0)
    range_owner = str(villain.get("range_owner") or "opponent")
    villain_name = str(villain.get("name") or f"Villain{index}")

    source = _get_action_range_source_for_spot_bridge(
        node_type=node_type,
        hero_pos=villain_pos,
        action=villain_action,
        opener_pos=opener_pos,
        three_bettor_pos=three_bettor_pos,
        four_bettor_pos=four_bettor_pos,
        callers=callers,
        limpers=limpers,
        range_owner=range_owner,
        actor_name=villain_name,
    )
    return RangeSource(
        name=villain_name,
        source_type=source.source_type,
        raw_expr=source.raw_expr,
        normalized_expr=source.normalized_expr,
        weighted_combos=list(source.weighted_combos),
        meta={**dict(source.meta), **dict(villain), "limpers": limpers},
    )


def build_villain_ranges_from_preflop_spots(villains: Sequence[Dict[str, object]]) -> List[RangeSource]:
    result: List[RangeSource] = []
    for index, villain in enumerate(villains, start=1):
        result.append(_build_range_source_from_preflop_spot(villain, index=index))
    return result


def _require_range_source(value: object, *, label: str) -> RangeSource:
    if isinstance(value, RangeSource):
        return value
    raise RuntimeError(f"{label} must be a RangeSource")


def _clone_range_source_with_meta(source: RangeSource, *, name: Optional[str] = None, extra_meta: Optional[Dict[str, object]] = None) -> RangeSource:
    merged_meta = dict(source.meta)
    if extra_meta:
        merged_meta.update(extra_meta)
    return RangeSource(
        name=name or source.name,
        source_type=source.source_type,
        raw_expr=source.raw_expr,
        normalized_expr=source.normalized_expr,
        weighted_combos=list(source.weighted_combos),
        meta=merged_meta,
    )


def _analyze_postflop_players_via_official_builder(
    *,
    hero_hand: Sequence[CardLike],
    board_runout: Sequence[CardLike],
    players: Sequence[Dict[str, object]],
    dead_cards: Iterable[CardLike] | None = None,
) -> Dict[str, object]:
    board_cards = list(board_runout)
    dead = [] if dead_cards is None else list(dead_cards)
    board_len = len(board_cards)

    if board_len == 5 and callable(analyze_multiway_postflop_line):
        return analyze_multiway_postflop_line(
            hero_hand=list(hero_hand),
            board_runout=board_cards,
            players=players,
            dead_cards=dead,
        )

    if board_len in {3, 4}:
        if callable(analyze_multiway_partial_postflop_line):
            return analyze_multiway_partial_postflop_line(
                hero_hand=list(hero_hand),
                board=board_cards,
                players=players,
                dead_cards=dead,
            )
        if callable(filter_postflop_range):
            results: List[Dict[str, object]] = []
            resolved_street = STREET_BY_BOARD_COUNT.get(board_len, "turn")

            def _summary_from_source(source: RangeSource) -> Dict[str, object]:
                if callable(_build_range_summary):
                    try:
                        return _build_range_summary(list(source.weighted_combos))
                    except Exception:
                        pass
                return {
                    "combo_count": len(source.weighted_combos),
                    "class_count": 0,
                    "class_summary": "",
                    "combo_summary": "",
                    "total_weight": float(sum(weight for _, weight in source.weighted_combos)),
                    "weighted_combos": list(source.weighted_combos),
                    "kept_details": [],
                    "removed_details": [],
                }

            for index, player in enumerate(players, start=1):
                if not isinstance(player, dict):
                    raise ValueError("Каждый элемент players должен быть словарем с настройками игрока")
                player_name = str(player.get("name") or f"Villain{index}")
                current_source = player.get("range_source")
                if not isinstance(current_source, RangeSource):
                    raw_expr = str(player.get("villain_range") or "").strip()
                    if raw_expr:
                        current_source = _build_range_source_from_expr(
                            raw_expr,
                            name=player_name,
                            source_type="postflop_player_start",
                            meta={
                                "villain_pos": player.get("villain_pos"),
                                "villain_action": player.get("villain_action"),
                            },
                            blocked_cards=list(hero_hand) + list(board_cards) + list(dead),
                        )
                    else:
                        current_source = _build_range_source_from_preflop_spot(player, index=index)
                starting_source = _clone_range_source_with_meta(current_source, name=player_name)
                previous_events: List[Dict[str, object]] = []
                steps: List[Dict[str, object]] = []
                last_report = None
                for event in player.get("events") or []:
                    street_name = str(event.get("street") or resolved_street).lower()
                    if street_name == "flop":
                        event_board = list(board_cards[:3])
                    elif street_name == "turn":
                        event_board = list(board_cards[:4])
                    elif street_name == "river":
                        event_board = list(board_cards[:5])
                    else:
                        continue
                    report = filter_postflop_range(
                        hero_hand=list(hero_hand),
                        board=event_board,
                        range_source=current_source,
                        bet_pct_pot=float(event.get("bet_pct_pot", 0.0) or 0.0),
                        is_all_in=bool(event.get("is_all_in", False)),
                        action=str(event.get("action") or "bet"),
                        dead_cards=dead,
                        previous_events=list(previous_events),
                        villain_in_position=bool(player.get("villain_in_position", False)),
                        range_owner=str(player.get("range_owner", "opponent")),
                    )
                    current_source = _require_range_source(
                        report.get("range_after_source"),
                        label=f"official partial range_after_source for {player_name}",
                    )
                    steps.append({
                        "street": street_name,
                        "action": event.get("action"),
                        "bet_pct_pot": float(event.get("bet_pct_pot", 0.0) or 0.0),
                        "is_all_in": bool(event.get("is_all_in", False)),
                        "range_before": report.get("range_before"),
                        "range_after": report.get("range_after"),
                        "range_before_source": report.get("range_before_source"),
                        "range_after_source": report.get("range_after_source"),
                    })
                    previous_events.append({
                        "street": street_name,
                        "action": str(event.get("action") or "bet"),
                        "bet_pct_pot": float(event.get("bet_pct_pot", 0.0) or 0.0),
                        "is_all_in": bool(event.get("is_all_in", False)),
                    })
                    last_report = report
                final_source = _clone_range_source_with_meta(
                    current_source,
                    name=player_name,
                    extra_meta={
                        "range_build_path": "postflop_players_partial_board",
                        "resolved_street": resolved_street,
                    },
                )
                starting_summary = _summary_from_source(starting_source)
                final_summary = _summary_from_source(final_source)
                player_report = {
                    "starting_range_expr": str(starting_source.normalized_expr or starting_source.raw_expr or ""),
                    "starting_range_source": starting_source,
                    "starting_range": last_report.get("range_before") if last_report is not None else starting_summary,
                    "steps": steps,
                    "final_range": last_report.get("range_after") if last_report is not None else final_summary,
                    "final_range_source": final_source,
                }
                results.append({
                    "name": player_name,
                    "villain_pos": player.get("villain_pos"),
                    "villain_action": player.get("villain_action"),
                    "starting_range_source": starting_source,
                    "final_range_source": final_source,
                    "range_source": player.get("range_source") or starting_source,
                    "report": player_report,
                })
            return {
                "hero_hand": list(hero_hand),
                "board": list(board_cards),
                "resolved_street": resolved_street,
                "dead_cards": list(dead),
                "player_count": len(results) + 1,
                "range_contract": RANGE_SOURCE_CONTRACT,
                "villain_reports": results,
            }

    _raise_missing_postflop_analysis(board_cards)


def build_villain_ranges_from_postflop_players(
    *,
    hero_hand: Sequence[CardLike],
    board_runout: Sequence[CardLike],
    players: Sequence[Dict[str, object]],
    dead_cards: Iterable[CardLike] | None = None,
) -> Tuple[List[RangeSource], Dict[str, object]]:
    report = _analyze_postflop_players_via_official_builder(
        hero_hand=list(hero_hand),
        board_runout=list(board_runout),
        players=players,
        dead_cards=[] if dead_cards is None else list(dead_cards),
    )
    ranges: List[RangeSource] = []
    for item in report.get("villain_reports", []):
        player_report = item.get("report") or {}
        final_source = item.get("final_range_source") or player_report.get("final_range_source")
        final_source = _require_range_source(
            final_source,
            label=f"final_range_source for {item.get('name')}",
        )
        ranges.append(
            _clone_range_source_with_meta(
                final_source,
                name=str(item.get("name") or final_source.name),
                extra_meta={
                    "villain_pos": item.get("villain_pos"),
                    "villain_action": item.get("villain_action"),
                    "range_contract": report.get("range_contract", RANGE_SOURCE_CONTRACT),
                },
            )
        )
    return ranges, report


# =========================
# formula layer
# =========================

def calculate_zero_fe(size_pct: float) -> float:
    b = _size_pct_to_fraction(size_pct)
    return 0.0 if b == 0 else b / (1.0 + b)


def calculate_zero_fe_for_raise(pot_before_hero: float, total_risk: float) -> float:
    pot = float(pot_before_hero)
    risk = float(total_risk)
    if pot < 0 or risk < 0:
        raise ValueError("pot и risk должны быть >= 0")
    if risk == 0:
        return 0.0
    return risk / (pot + risk)


def calculate_required_fe_bet(pot_before_hero: float, bet_amount: float, equity: float) -> float:
    pot = float(pot_before_hero)
    bet = float(bet_amount)
    eq = max(0.0, min(1.0, float(equity)))
    denominator = pot + bet - eq * (pot + 2.0 * bet)
    numerator = bet - eq * (pot + 2.0 * bet)
    if abs(denominator) < 1e-12:
        return 0.0 if numerator <= 0 else 1.0
    return max(0.0, min(1.0, numerator / denominator))


def calculate_required_fe_raise(pot_before_hero: float, to_call: float, raise_extra: float, equity: float) -> float:
    pot = float(pot_before_hero)
    call_amount = float(to_call)
    extra = float(raise_extra)
    risk = call_amount + extra
    final_pot_if_called = pot + call_amount + 2.0 * extra
    eq = max(0.0, min(1.0, float(equity)))
    denominator = pot + risk - eq * final_pot_if_called
    numerator = risk - eq * final_pot_if_called
    if abs(denominator) < 1e-12:
        return 0.0 if numerator <= 0 else 1.0
    return max(0.0, min(1.0, numerator / denominator))


def calculate_call_equity_threshold(pot_before_hero: float, to_call: float) -> float:
    pot = float(pot_before_hero)
    call_amount = float(to_call)
    if pot < 0 or call_amount < 0:
        raise ValueError("pot и to_call должны быть >= 0")
    if call_amount == 0:
        return 0.0
    return call_amount / (pot + call_amount)


def calculate_spr(effective_stack: float | None, pot_before_hero: float) -> Optional[float]:
    if effective_stack is None:
        return None
    pot = float(pot_before_hero)
    stack = float(effective_stack)
    if pot <= 0:
        return None
    return stack / pot


def ev_bet(pot_before_hero: float, bet_amount: float, fold_probability: float, equity: float) -> float:
    pot = float(pot_before_hero)
    bet = float(bet_amount)
    fe = max(0.0, min(1.0, float(fold_probability)))
    eq = max(0.0, min(1.0, float(equity)))
    return fe * pot + (1.0 - fe) * (eq * (pot + 2.0 * bet) - bet)


def ev_raise(pot_before_hero: float, to_call: float, raise_extra: float, fold_probability: float, equity: float) -> float:
    pot = float(pot_before_hero)
    call_amount = float(to_call)
    extra = float(raise_extra)
    risk = call_amount + extra
    fe = max(0.0, min(1.0, float(fold_probability)))
    eq = max(0.0, min(1.0, float(equity)))
    final_pot_if_called = pot + call_amount + 2.0 * extra
    return fe * pot + (1.0 - fe) * (eq * final_pot_if_called - risk)


def ev_call(pot_before_hero: float, to_call: float, equity: float) -> float:
    pot = float(pot_before_hero)
    call_amount = float(to_call)
    eq = max(0.0, min(1.0, float(equity)))
    return eq * (pot + call_amount) - call_amount


# =========================
# equity layer
# =========================

def _weighted_sample_combo(valid_weighted_range: List[WeightedCombo], rng: random.Random) -> Combo:
    if not valid_weighted_range:
        raise ValueError("Нет доступных комбо для сэмплирования")
    weights = [max(0.0, float(weight)) for _combo, weight in valid_weighted_range]
    total = sum(weights)
    if total <= 0:
        return rng.choice(valid_weighted_range)[0]
    threshold = rng.random() * total
    running = 0.0
    for combo, weight in valid_weighted_range:
        running += max(0.0, float(weight))
        if running >= threshold:
            return combo
    return valid_weighted_range[-1][0]


def _score_seven(cards7: Sequence[int]) -> Tuple[int, ...]:
    return tuple(score_7_cards_fast(tuple(cards7)))


def compute_multiway_hero_equity(
    *,
    hero_hand: Sequence[CardLike],
    villain_ranges: Sequence[RangeInput],
    board: Sequence[CardLike] | None = None,
    dead_cards: Iterable[CardLike] | None = None,
    trials: int = 6000,
    seed: int | None = None,
) -> Dict[str, object]:
    hero = _normalize_cards(hero_hand)
    if len(hero) != 2:
        raise ValueError("hero_hand должен содержать ровно 2 карты")
    board_cards = [] if board is None else _normalize_cards(board)
    if len(board_cards) not in (0, 3, 4, 5):
        raise ValueError("board должен содержать 0, 3, 4 или 5 карт")
    dead = [] if dead_cards is None else _normalize_cards(dead_cards)
    known = hero + board_cards + dead
    if len(known) != len(set(known)):
        raise ValueError("hero_hand / board / dead_cards пересекаются")

    blocked = [card_to_str(c) for c in known]
    parsed_ranges: List[List[WeightedCombo]] = []
    for vr in villain_ranges:
        parsed = _parse_range_flex(vr, blocked_cards=blocked)
        if not parsed:
            raise ValueError("Один из villain_ranges оказался пустым после parse_range")
        parsed_ranges.append(parsed)

    missing = 5 - len(board_cards)
    deck = [card for card in create_deck() if card not in set(known)]
    rng = random.Random(seed)

    hero_share_total = 0.0
    villain_share_totals = [0.0 for _ in parsed_ranges]
    sample_count = 0

    for _ in range(int(trials)):
        used = set(known)
        villain_hands: List[Combo] = []
        for parsed in parsed_ranges:
            valid = [(combo, weight) for combo, weight in parsed if combo[0] not in used and combo[1] not in used]
            if not valid:
                villain_hands = []
                break
            combo = _weighted_sample_combo(valid, rng)
            villain_hands.append(combo)
            used.add(combo[0])
            used.add(combo[1])
        if not villain_hands:
            continue

        remaining = [card for card in deck if card not in used]
        runout_tail = rng.sample(remaining, missing) if missing > 0 else []
        full_board = board_cards + runout_tail

        scores = [_score_seven(hero + full_board)]
        for combo in villain_hands:
            scores.append(_score_seven([combo[0], combo[1], *full_board]))

        best_score = max(scores)
        winners = [i for i, score in enumerate(scores) if score == best_score]
        share = 1.0 / len(winners)

        if 0 in winners:
            hero_share_total += share
        for villain_index in range(len(villain_hands)):
            if villain_index + 1 in winners:
                villain_share_totals[villain_index] += share
        sample_count += 1

    if sample_count == 0:
        raise RuntimeError("Не удалось набрать ни одного валидного multiway-сэмпла")

    return {
        "hero_equity": hero_share_total / sample_count,
        "villain_equities": [value / sample_count for value in villain_share_totals],
        "samples": sample_count,
        "board": [card_to_str(card) for card in board_cards],
        "player_count": len(parsed_ranges) + 1,
    }


# =========================
# decision modifiers
# =========================

def estimate_realization_factor(*, street: str, hero_in_position: bool, player_count: int, spr: Optional[float]) -> float:
    street = street.lower()
    base = {"preflop": 0.88, "flop": 0.92, "turn": 0.96, "river": 1.00}[street]
    factor = base
    factor += 0.04 if hero_in_position else -0.04
    factor -= 0.03 * max(0, int(player_count) - 2)
    if spr is not None:
        if spr <= 3.0:
            factor += 0.02
        elif spr >= 8.0 and not hero_in_position:
            factor -= 0.03
    return max(0.70, min(1.05, factor))




def _hero_has_initiative(line_context: Optional[Dict[str, object]]) -> bool:
    ctx = {} if line_context is None else dict(line_context)
    if "hero_has_initiative" in ctx:
        return bool(ctx.get("hero_has_initiative"))
    if "hero_last_aggressor" in ctx:
        return bool(ctx.get("hero_last_aggressor"))
    return False


def _clone_range_source(source: RangeSource) -> RangeSource:
    return RangeSource(
        name=source.name,
        source_type=source.source_type,
        raw_expr=source.raw_expr,
        normalized_expr=source.normalized_expr,
        weighted_combos=list(source.weighted_combos),
        meta=dict(source.meta),
    )


def _sanitize_range_sources_for_equity(
    range_sources: Sequence[RangeSource],
) -> Tuple[List[RangeSource], List[Dict[str, object]]]:
    kept: List[RangeSource] = []
    dropped: List[Dict[str, object]] = []
    for source in range_sources:
        cloned = _clone_range_source(source)
        if cloned.weighted_combos:
            kept.append(cloned)
            continue
        dropped.append(
            {
                "name": cloned.name,
                "source_type": cloned.source_type,
                "reason": "empty_weighted_combos",
                "raw_expr": cloned.raw_expr,
                "normalized_expr": cloned.normalized_expr,
                "meta": dict(cloned.meta),
            }
        )
    return kept, dropped


def _build_passive_fallback_report(
    *,
    hero: Sequence[str],
    board_cards: Sequence[str],
    pot_before_hero: float,
    to_call: float,
    effective_stack: float | None,
    hero_in_position: bool,
    line_context: Optional[Dict[str, object]],
    hero_tags: set[str],
    reason: str,
    range_sources: Sequence[RangeSource],
    dropped_range_sources: Sequence[Dict[str, object]],
) -> Dict[str, object]:
    street = _street_from_board(board_cards)
    spr = calculate_spr(effective_stack, pot_before_hero)
    passive_action = "fold" if float(to_call) > 0 else "check"
    passive_option = {
        "action": passive_action,
        "ev": 0.0,
        "legal": True,
        "kind": "passive",
        "gate_status": "fallback",
        "fallback_reason": reason,
        "amount_to": None,
    }
    return {
        "hero_hand": list(hero),
        "board": list(board_cards),
        "street": street,
        "pot_before_hero": float(pot_before_hero),
        "to_call": float(to_call),
        "effective_stack": None if effective_stack is None else float(effective_stack),
        "spr": spr,
        "hero_in_position": bool(hero_in_position),
        "player_count": len(range_sources) + 1,
        "line_context": {} if line_context is None else dict(line_context),
        "line_adjustments": build_line_adjustments(line_context, player_count=len(range_sources) + 1),
        "spot_type": _infer_spot_type(
            street=street,
            hero_in_position=bool(hero_in_position),
            to_call=float(to_call),
            line_context=line_context,
        ),
        "hero_has_initiative": _hero_has_initiative(line_context),
        "range_sources": [
            {
                "name": src.name,
                "source_type": src.source_type,
                "raw_expr": src.raw_expr,
                "normalized_expr": src.normalized_expr,
                "combo_count": len(src.weighted_combos),
                "meta": src.meta,
            }
            for src in range_sources
        ],
        "dropped_range_sources": [dict(item) for item in dropped_range_sources],
        "hero_tags": tuple(sorted(hero_tags)),
        "bluff_layer": _build_bluff_layer_profile(
            hero_tags=hero_tags,
            street=street,
            to_call=float(to_call),
            pot_before_hero=float(pot_before_hero),
            hero_in_position=bool(hero_in_position),
            player_count=len(range_sources) + 1,
            line_context=line_context,
            spot_type=_infer_spot_type(
                street=street,
                hero_in_position=bool(hero_in_position),
                to_call=float(to_call),
                line_context=line_context,
            ),
            spr=spr,
            raw_equity=0.0,
            realized_equity=0.0,
            call_equity=0.0,
            best_option=passive_option,
        ),
        "equity": {
            "raw_multiway_hero_equity": 0.0,
            "realization_factor": 0.0,
            "realized_equity": 0.0,
            "call_equity": 0.0,
            "multiway_detail": {
                "hero_equity": 0.0,
                "villain_equities": [],
                "samples": 0,
                "board": list(board_cards),
                "player_count": len(range_sources) + 1,
                "fallback_reason": reason,
            },
        },
        "thresholds": {
            "call_break_even_equity": calculate_call_equity_threshold(pot_before_hero, to_call) if float(to_call) > 0 else 0.0,
            "safety_margin_vs_passive": 0.0,
            "hard_call_gate": {
                "allowed": passive_action != "fold",
                "required_equity": 0.0,
                "margin": 0.0,
                "equity_used": 0.0,
                "reason": reason,
            },
        },
        "size_reports": [],
        "options": [passive_option],
        "recommended_action": passive_action,
        "recommended_option": passive_option,
        "fallback_reason": reason,
    }







def _ranks_from_cards(cards: Sequence[str]) -> list[int]:
    values = {r:i+2 for i,r in enumerate("23456789TJQKA")}
    return [values[c[0].upper()] for c in cards]

def _simple_straight(ranks: set[int]) -> bool:
    wheels = {14,2,3,4,5}
    if wheels.issubset(ranks):
        return True
    for high in range(14,5,-1):
        if set(range(high-4, high+1)).issubset(ranks):
            return True
    return False

def _simple_straight_draw_info(ranks: set[int]) -> tuple[bool,bool]:
    outs = 0
    for add in range(2,15):
        rr = set(ranks)
        rr.add(add)
        if _simple_straight(rr):
            outs += 1
    return outs >= 2, outs == 1



def _board_texture_tags_simple(board_cards: Sequence[str]) -> set[str]:
    tags: set[str] = set()
    if not board_cards:
        return tags
    from collections import Counter
    ranks = sorted(set(_ranks_from_cards(board_cards)), reverse=True)
    suits = [card[1].lower() for card in board_cards]
    rc = Counter(_ranks_from_cards(board_cards))
    sc = Counter(suits)
    max_suit = max(sc.values(), default=0)

    if any(count >= 2 for count in rc.values()):
        tags.add("board_paired")
    if max_suit >= 3:
        tags.add("board_monotone")
    elif max_suit == 2:
        tags.add("board_two_tone")
    else:
        tags.add("board_rainbow")

    if ranks and ranks[0] == 14:
        tags.add("board_ace_high")
    elif ranks and ranks[0] == 13:
        tags.add("board_king_high")
    broadways = sum(1 for value in ranks if value >= 10)
    if broadways >= 2:
        tags.add("board_broadway_dynamic")
    if len(ranks) >= 3:
        span = max(ranks) - min(ranks)
        connected = span <= 4 or any(len(set(range(low, low + 5)) & set(ranks)) >= 3 for low in range(2, 11))
        if connected:
            tags.add("board_connected")
        if connected and max(ranks) <= 10:
            tags.add("board_low_connected")
        if connected or max_suit >= 2 or broadways >= 2:
            tags.add("board_wet_connected")
        if (not connected) and max_suit <= 1 and ranks[0] >= 12 and not any(count >= 2 for count in rc.values()):
            tags.add("board_dry_high")
    return tags


def _add_refined_pair_tags_simple(tags: set[str], hero_ranks: list[int], board_ranks: list[int]) -> None:
    if not board_ranks:
        return
    board_unique_desc = sorted(set(board_ranks), reverse=True)
    if not board_unique_desc:
        return
    is_pocket_pair = len(hero_ranks) == 2 and hero_ranks[0] == hero_ranks[1]
    if is_pocket_pair and "pocket_pair" in tags:
        pair_rank = hero_ranks[0]
        if len(board_unique_desc) >= 2 and pair_rank > board_unique_desc[1] and "overpair" not in tags:
            tags.add("pocket_pair_above_second_card")
        elif "overpair" not in tags:
            tags.add("pocket_pair_below_second_card")
            tags.add("weak_showdown")
        return
    matched = [rank for rank in hero_ranks if rank in set(board_unique_desc)]
    if not matched:
        return
    matched_rank = max(matched)
    kicker_rank = min(hero_ranks) if max(hero_ranks) == matched_rank else max(hero_ranks)
    if "top_pair" in tags:
        if kicker_rank >= 13:
            tags.add("top_pair_top_kicker")
        elif kicker_rank >= 10:
            tags.add("top_pair_good_kicker")
        else:
            tags.add("top_pair_weak_kicker")
            tags.add("weak_showdown")
    elif "middle_pair" in tags:
        if kicker_rank >= 12:
            tags.add("middle_pair_good_kicker")
        else:
            tags.add("middle_pair_weak_kicker")
            tags.add("weak_showdown")
    elif "bottom_pair" in tags:
        if kicker_rank >= 12:
            tags.add("bottom_pair_good_kicker")
        else:
            tags.add("bottom_pair_weak_kicker")
            tags.add("weak_showdown")


def _add_blocker_tags_simple(tags: set[str], hero_hand: Sequence[str], board_cards: Sequence[str]) -> None:
    if len(board_cards) < 5 or tags & {"flush", "straight_flush", "full_house", "quads"}:
        return
    from collections import Counter
    board_suits = Counter(card[1].lower() for card in board_cards)
    flush_suits = {suit for suit, count in board_suits.items() if count >= 3}
    rank_values = {r: i + 2 for i, r in enumerate("23456789TJQKA")}
    for card in hero_hand:
        suit = card[1].lower()
        rank = rank_values[card[0].upper()]
        if suit in flush_suits and rank == 14:
            tags.add("nut_flush_blocker")
        elif suit in flush_suits and rank >= 13:
            tags.add("high_flush_blocker")
    board_rank_set = set(_ranks_from_cards(board_cards))
    hero_rank_set = set(_ranks_from_cards(hero_hand))
    if 14 in board_rank_set:
        board_rank_set.add(1)
    if 14 in hero_rank_set:
        hero_rank_set.add(1)
    for high in range(5, 15):
        straight = set(range(high - 4, high + 1))
        if len(straight & board_rank_set) >= 3 and straight & hero_rank_set:
            tags.add("straight_blocker")
            break

def _categorize_hand_tags_simple(hero_hand: Sequence[str], board_cards: Sequence[str]) -> set[str]:
    tags = set()
    all_cards = list(hero_hand) + list(board_cards)
    ranks = _ranks_from_cards(all_cards)
    board_ranks = _ranks_from_cards(board_cards)
    hero_ranks = _ranks_from_cards(hero_hand)
    suits = [c[1].lower() for c in all_cards]
    from collections import Counter
    rc = Counter(ranks)
    sc = Counter(suits)
    board_unique_desc = sorted(set(board_ranks), reverse=True)

    if max(sc.values(), default=0) >= 5:
        tags.add("flush")
    elif len(board_cards) < 5 and max(sc.values(), default=0) == 4:
        tags.add("flush_draw")
    elif len(board_cards) == 3 and max(sc.values(), default=0) == 3:
        tags.add("backdoor_flush_draw")

    rank_set = set(ranks)
    if _simple_straight(rank_set):
        tags.add("straight")
    elif len(board_cards) < 5:
        oesd, gut = _simple_straight_draw_info(rank_set)
        if oesd:
            tags.add("oesd")
        elif gut:
            tags.add("gutshot")

    counts = sorted(rc.values(), reverse=True)
    if counts and counts[0] == 4:
        tags.add("quads")
    elif counts and counts[0] == 3 and 2 in counts[1:]:
        tags.add("full_house")
    elif counts and counts[0] == 3:
        hero_pair = hero_ranks[0] == hero_ranks[1]
        if hero_pair and hero_ranks[0] in board_ranks:
            tags.add("set")
        else:
            tags.add("trips")
    elif counts.count(2) >= 2:
        tags.add("two_pair")

    if not (tags & {"quads","full_house","trips","set","two_pair","straight","flush"}):
        hero_pair = hero_ranks[0] == hero_ranks[1]
        if hero_pair:
            tags.add("pocket_pair")
            if board_unique_desc:
                if hero_ranks[0] > board_unique_desc[0]:
                    tags.add("overpair")
                else:
                    tags.add("underpair")
        else:
            matched = [r for r in hero_ranks if r in board_ranks]
            if matched and board_unique_desc:
                m = max(matched)
                if m == board_unique_desc[0]:
                    tags.add("top_pair")
                elif len(board_unique_desc) > 1 and m == board_unique_desc[1]:
                    tags.add("middle_pair")
                else:
                    tags.add("bottom_pair")

    if not any(t in tags for t in ["top_pair","middle_pair","bottom_pair","two_pair","set","trips","straight","flush","full_house","quads","overpair","underpair","pocket_pair"]):
        if 14 in hero_ranks:
            tags.add("ace_high")
        if board_unique_desc:
            hi_board = board_unique_desc[0]
            overcards = sum(1 for r in hero_ranks if r > hi_board)
            if overcards >= 2:
                tags.add("two_overcards")
            elif overcards == 1:
                tags.add("one_overcard")

    if (tags & {"flush_draw","oesd"}) and any(t in tags for t in ["top_pair","middle_pair","bottom_pair","overpair","underpair","pocket_pair","gutshot"]):
        tags.add("combo_draw")
    tags.update(_board_texture_tags_simple(board_cards))
    _add_refined_pair_tags_simple(tags, hero_ranks, board_ranks)
    _add_blocker_tags_simple(tags, hero_hand, board_cards)

    board_texture_tags = {
        "board_paired", "board_monotone", "board_two_tone", "board_rainbow",
        "board_connected", "board_low_connected", "board_dry_high",
        "board_broadway_dynamic", "board_ace_high", "board_king_high", "board_wet_connected",
    }
    if not (tags - board_texture_tags):
        tags.add("air")
    return tags

def _hero_postflop_tags(hero_hand: Sequence[str], board_cards: Sequence[str]) -> set[str]:
    if len(board_cards) < 3:
        return set()
    if categorize_villain_combo is not None:
        try:
            combo = tuple(_normalize_cards(hero_hand))
            return set(categorize_villain_combo(combo, list(board_cards)))  # type: ignore[misc]
        except Exception:
            pass
    return _categorize_hand_tags_simple(list(hero_hand), list(board_cards))


def _build_hero_postflop_profile_bridge(
    hero_hand: Sequence[str],
    board_cards: Sequence[str],
    *,
    facing_bet: bool = False,
) -> Optional[Dict[str, object]]:
    """Use the official postflop_advisor HERO profile when available.

    This keeps hand/bucket classification centralized in postflop_advisor.py,
    while hero_decision.py remains responsible for EV/action selection.
    """
    builder = getattr(_POSTFLOP_ADVISOR_MODULE, "build_hero_postflop_profile", None)
    if not callable(builder) or len(board_cards) < 3:
        return None
    try:
        profile = builder(
            hero_hand=list(hero_hand),
            board=list(board_cards),
            facing_bet=bool(facing_bet),
        )
    except TypeError:
        try:
            profile = builder(list(hero_hand), list(board_cards))
        except Exception:
            return None
    except Exception:
        return None
    if isinstance(profile, dict):
        return dict(profile)
    return None


def _hero_bet_fe_modifier(hero_tags: set[str], *, street: str, hero_in_position: bool, player_count: int, line_context: Optional[Dict[str, object]], spot_type: str) -> float:
    ctx = {} if line_context is None else dict(line_context)
    mod = 1.0
    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair"}
    medium_value = {"middle_pair", "bottom_pair", "underpair", "pocket_pair"}
    strong_draws = {"combo_draw", "flush_draw", "oesd"}
    weak_draws = {"gutshot", "backdoor_flush_draw"}
    high_card = {"ace_high", "two_overcards", "one_overcard"}
    if spot_type == "oop_donk_spot":
        if hero_tags & strong_made:
            mod *= 0.72
        elif hero_tags & strong_value:
            mod *= 0.50
        elif hero_tags & strong_draws:
            mod *= 0.46
        elif hero_tags & medium_value:
            mod *= 0.22
        elif hero_tags & weak_draws:
            mod *= 0.18
        elif hero_tags & high_card:
            mod *= 0.12
        else:
            mod *= 0.10
    elif spot_type == "cbet_spot":
        if hero_tags & strong_made:
            mod *= 1.16
        elif hero_tags & strong_value:
            mod *= 1.10
        elif hero_tags & strong_draws:
            mod *= 1.02
        elif hero_tags & medium_value:
            mod *= 0.98
        elif hero_tags & weak_draws:
            mod *= 0.90
        elif hero_tags & high_card:
            mod *= 0.84
        else:
            mod *= 0.78
    elif spot_type == "delayed_probe_spot":
        if hero_tags & strong_made:
            mod *= 1.00
        elif hero_tags & strong_value:
            mod *= 0.94
        elif hero_tags & strong_draws:
            mod *= 0.88
        elif hero_tags & medium_value:
            mod *= 0.82
        elif hero_tags & weak_draws:
            mod *= 0.72
        elif hero_tags & high_card:
            mod *= 0.68
        else:
            mod *= 0.62
    elif spot_type == "ip_check_through_spot":
        if hero_tags & strong_made:
            mod *= 1.04
        elif hero_tags & strong_value:
            mod *= 0.98
        elif hero_tags & strong_draws:
            mod *= 0.92
        elif hero_tags & medium_value:
            mod *= 0.86
        elif hero_tags & weak_draws:
            mod *= 0.76
        elif hero_tags & high_card:
            mod *= 0.72
        else:
            mod *= 0.64
    else:
        mod *= 0.84 if hero_in_position else 0.72
    if street == "turn":
        mod *= 0.88
    elif street == "river":
        mod *= 0.72
    if not hero_in_position:
        mod *= 0.86
    if player_count > 2:
        mod *= max(0.30, 1.0 - 0.16 * (player_count - 2))
    if ctx.get("prior_aggression"):
        mod *= 0.82
    return max(0.05, min(0.98, mod))




def _bet_caution_penalty(hero_tags: set[str], *, street: str, hero_in_position: bool, player_count: int, line_context: Optional[Dict[str, object]], pot_before_hero: float, spot_type: str) -> float:
    pot = float(pot_before_hero)
    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair"}
    medium_value = {"middle_pair", "bottom_pair", "underpair", "pocket_pair"}
    strong_draws = {"combo_draw", "flush_draw", "oesd"}
    weak_draws = {"gutshot", "backdoor_flush_draw"}
    high_card = {"ace_high", "two_overcards", "one_overcard"}
    ctx = {} if line_context is None else dict(line_context)
    if hero_tags & strong_made:
        penalty = 0.0
    elif hero_tags & strong_value:
        penalty = 0.03 * pot
    elif hero_tags & strong_draws:
        penalty = 0.05 * pot
    elif hero_tags & medium_value:
        penalty = 0.08 * pot
    elif hero_tags & weak_draws:
        penalty = 0.12 * pot
    elif hero_tags & high_card:
        penalty = 0.20 * pot
    else:
        penalty = 0.28 * pot
    if spot_type == "oop_donk_spot":
        penalty += 0.14 * pot
    elif spot_type == "delayed_probe_spot":
        penalty -= 0.01 * pot
    elif spot_type == "ip_check_through_spot":
        penalty -= 0.05 * pot
    elif spot_type == "cbet_spot":
        penalty -= 0.10 * pot
    if street == "turn":
        penalty += 0.05 * pot
    elif street == "river":
        penalty += 0.09 * pot
    if not hero_in_position:
        penalty += 0.03 * pot
    if player_count > 2:
        penalty += 0.03 * pot * (player_count - 2)
    if ctx.get("prior_aggression"):
        penalty += 0.03 * pot
    return penalty




def _hero_raise_fe_modifier(hero_tags: set[str], *, street: str, hero_in_position: bool, player_count: int, line_context: Optional[Dict[str, object]]) -> float:
    """Conservative FE modifier for raises.

    Goal: Hero should prefer call much more often, and reserve raises for stronger value and stronger draws.
    """
    ctx = {} if line_context is None else dict(line_context)
    mod = 1.0

    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_pair = {"overpair", "top_pair"}
    medium_pair = {"middle_pair"}
    weak_pairs = {"underpair", "bottom_pair", "pocket_pair"}
    strong_draws = {"combo_draw", "flush_draw", "oesd"}
    weak_draws = {"gutshot", "backdoor_flush_draw"}
    high_card = {"ace_high", "two_overcards", "one_overcard"}

    if hero_tags & strong_made:
        mod *= 0.95
    elif hero_tags & strong_pair:
        mod *= 0.68
    elif hero_tags & strong_draws:
        mod *= 0.54
    elif hero_tags & medium_pair:
        mod *= 0.30
    elif hero_tags & weak_pairs:
        mod *= 0.18
    elif hero_tags & weak_draws:
        mod *= 0.24
    elif hero_tags & high_card:
        mod *= 0.16
    else:
        mod *= 0.12

    if street == "turn":
        mod *= 0.72
    elif street == "river":
        mod *= 0.55

    if not hero_in_position:
        mod *= 0.78
    if player_count > 2:
        mod *= max(0.30, 1.0 - 0.18 * (player_count - 2))
    if ctx.get("prior_aggression"):
        mod *= 0.74
    if ctx.get("facing_raise"):
        mod *= 0.55

    return max(0.05, min(0.95, mod))




def _raise_caution_penalty(hero_tags: set[str], *, street: str, hero_in_position: bool, player_count: int, to_call: float, line_context: Optional[Dict[str, object]], pot_before_hero: float) -> float:
    ctx = {} if line_context is None else dict(line_context)
    pot = float(pot_before_hero)
    if to_call <= 0:
        return 0.0

    very_strong = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair"}
    strong_draws = {"combo_draw", "flush_draw", "oesd"}
    medium = {"middle_pair", "gutshot"}
    weak = {"bottom_pair", "underpair", "pocket_pair", "backdoor_flush_draw", "ace_high", "two_overcards", "one_overcard"}

    if hero_tags & very_strong:
        penalty = 0.0
    elif hero_tags & strong_value:
        penalty = 0.05 * pot
    elif hero_tags & strong_draws:
        penalty = 0.10 * pot
    elif hero_tags & medium:
        penalty = 0.18 * pot
    elif hero_tags & weak:
        penalty = 0.28 * pot
    else:
        penalty = 0.35 * pot

    if street == "turn":
        penalty += 0.08 * pot
    elif street == "river":
        penalty += 0.12 * pot
    if not hero_in_position:
        penalty += 0.05 * pot
    if player_count > 2:
        penalty += 0.04 * pot * (player_count - 2)
    if ctx.get("prior_aggression"):
        penalty += 0.05 * pot
    if ctx.get("facing_raise"):
        penalty += 0.08 * pot
    return penalty


# =========================
# high-level decision API
# =========================

def _normalize_fe_assumptions(assumed_fold_probs_by_size: Optional[Dict[float, float]]) -> Dict[float, float]:
    if not assumed_fold_probs_by_size:
        return {}
    return {float(key): float(value) for key, value in assumed_fold_probs_by_size.items()}





def _preflop_engine_action(action: str) -> str:
    normalized = str(action).lower()
    if normalized in {"fold", "check", "call"}:
        return normalized
    if normalized == "limp":
        return "call"
    if normalized in {"raise", "iso_raise", "3bet", "4bet", "5bet"}:
        return "raise"
    if normalized in {"jam", "all_in", "all-in"}:
        return "all_in"
    return normalized


def _postflop_engine_action(action: str) -> str:
    normalized = str(action).lower()
    if normalized in {"fold", "check", "call"}:
        return normalized
    if normalized.startswith("bet_"):
        return "bet"
    if normalized.startswith("raise_"):
        return "raise"
    if normalized in {"jam", "all_in", "all-in"}:
        return "all_in"
    return normalized


def solve_hero_preflop(
    context: PreflopContext,
    *,
    actor_name: str = "Hero",
    rng: Optional[random.Random] = None,
) -> HeroDecision:
    decision = _advise_preflop_decision_bridge(
        context.hero_hand,
        node_type=context.node_type,
        hero_pos=context.hero_pos,
        opener_pos=context.opener_pos,
        three_bettor_pos=context.three_bettor_pos,
        four_bettor_pos=context.four_bettor_pos,
        limpers=context.limpers,
        callers=context.callers,
        range_owner=context.range_owner,
        actor_name=actor_name,
        rng=rng,
    )
    context_meta = dict(context.meta)
    context_meta.setdefault("hero_hand", list(context.hero_hand))
    identity_meta = {
        "node_type": context.node_type,
        "opener_pos": context.opener_pos,
        "three_bettor_pos": context.three_bettor_pos,
        "four_bettor_pos": context.four_bettor_pos,
        "limpers": context.limpers,
        "callers": context.callers,
    }
    solver_fingerprint, decision_id, source_frame_id = _build_decision_identity(
        street="preflop",
        engine_action=_preflop_engine_action(decision.action),
        raw_action=str(decision.action),
        context_meta=context_meta,
        identity_meta=identity_meta,
    )
    return HeroDecision(
        street="preflop",
        engine_action=_preflop_engine_action(decision.action),
        actor_name=actor_name,
        actor_pos=context.hero_pos,
        reason=f"preflop:{decision.action}",
        confidence=1.0 if not decision.is_mixed_action else 0.7,
        source="hero_decision.preflop",
        solver_fingerprint=solver_fingerprint,
        decision_id=decision_id,
        source_frame_id=source_frame_id,
        preflop=decision,
        debug={
            "node_type": context.node_type,
            "opener_pos": context.opener_pos,
            "three_bettor_pos": context.three_bettor_pos,
            "four_bettor_pos": context.four_bettor_pos,
            "limpers": context.limpers,
            "callers": context.callers,
            "range_owner": context.range_owner,
            "matching_actions": list(decision.matching_actions),
            "fallback_reason": decision.fallback_reason,
            "solver_fingerprint": solver_fingerprint,
            "decision_id": decision_id,
            "source_frame_id": source_frame_id,
            "recommended_action": str(decision.action),
            "engine_action": _preflop_engine_action(decision.action),
            "street": "preflop",
            "meta": context_meta,
        },
    )


def solve_hero_postflop(
    context: PostflopContext,
    *,
    villain_sources: Optional[Sequence[RangeSource]] = None,
    villain_preflop_spots: Optional[Sequence[Dict[str, object]]] = None,
    villain_postflop_players: Optional[Sequence[Dict[str, object]]] = None,
    villain_ranges: Optional[Sequence[RangeInput]] = None,
    hero_in_position: Optional[bool] = None,
    bet_sizes_pct: Sequence[float] = DEFAULT_BET_SIZES_PCT,
    assumed_fold_probs_by_size: Optional[Dict[float, float]] = None,
    trials: int = 6000,
    seed: int | None = None,
    actor_name: str = "Hero",
) -> HeroDecision:
    report_meta: Dict[str, object] = {}
    if villain_sources is not None:
        resolved_sources = [
            RangeSource(
                name=src.name,
                source_type=src.source_type,
                raw_expr=src.raw_expr,
                normalized_expr=src.normalized_expr,
                weighted_combos=list(src.weighted_combos),
                meta=dict(src.meta),
            )
            for src in villain_sources
        ]
    elif villain_postflop_players is not None:
        resolved_sources, report_meta = build_villain_ranges_from_postflop_players(
            hero_hand=context.hero_hand,
            board_runout=context.board,
            players=villain_postflop_players,
            dead_cards=context.dead_cards,
        )
    elif villain_preflop_spots is not None:
        resolved_sources = build_villain_ranges_from_preflop_spots(villain_preflop_spots)
    elif villain_ranges is not None:
        resolved_sources = []
        blocked = list(context.hero_hand) + list(context.board) + list(context.dead_cards)
        for index, vr in enumerate(villain_ranges, start=1):
            raw_expr = vr if isinstance(vr, str) else None
            normalized = None
            if isinstance(vr, str):
                try:
                    normalized = normalize_range_for_equity(vr)
                except Exception:
                    normalized = None
            weighted = _parse_range_flex(vr, blocked_cards=blocked)
            resolved_sources.append(
                RangeSource(
                    name=f"Villain{index}",
                    source_type="direct_input",
                    raw_expr=raw_expr,
                    normalized_expr=normalized,
                    weighted_combos=weighted,
                    meta={},
                )
            )
    else:
        raise ValueError("Для постфлоп-решения нужно передать villain_sources, villain_postflop_players, villain_preflop_spots или villain_ranges")

    if hero_in_position is None:
        hero_pos = context.hero_position
        villain_positions = list(context.villain_positions)
        if hero_pos and villain_positions:
            order = ["SB", "BB", "UTG", "MP", "CO", "BTN"]
            hero_idx = order.index(hero_pos) if hero_pos in order else -1
            villain_indices = [order.index(pos) for pos in villain_positions if pos in order]
            hero_in_position = bool(villain_indices) and hero_idx > max(villain_indices)
        else:
            hero_in_position = True

    report = solve_hero_decision(
        hero_hand=context.hero_hand,
        board=context.board,
        pot_before_hero=float(context.pot_before_hero),
        to_call=float(context.to_call),
        effective_stack=context.effective_stack,
        hero_in_position=bool(hero_in_position),
        range_sources=resolved_sources,
        bet_sizes_pct=bet_sizes_pct,
        assumed_fold_probs_by_size=assumed_fold_probs_by_size,
        line_context=dict(context.line_context),
        dead_cards=context.dead_cards,
        trials=trials,
        seed=seed,
    )
    best_option = dict(report["recommended_option"])
    postflop_decision = PostflopDecision(
        action=str(report["recommended_action"]),
        street=str(report["street"]),
        actor_name=actor_name,
        actor_pos=context.hero_position,
        size_pct=best_option.get("size_pct"),
        amount_to=best_option.get("amount_to"),
        hero_equity=float(report["equity"]["raw_multiway_hero_equity"]),
        realized_equity=float(report["equity"]["realized_equity"]),
        villain_sources=resolved_sources,
        report=report,
        fallback_reason=report.get("fallback_reason"),
        meta={"postflop_report_meta": report_meta, "context_meta": dict(context.meta)},
    )
    confidence = 1.0
    if postflop_decision.action in {"fold", "check"} and float(best_option.get("ev", 0.0)) <= 0.0:
        confidence = 0.7
    context_meta = dict(context.meta)
    context_meta.setdefault("hero_hand", list(context.hero_hand))
    context_meta.setdefault("board", list(context.board))
    context_meta.setdefault("line_context", dict(context.line_context))
    context_meta.setdefault("amount_to", postflop_decision.amount_to)
    context_meta.setdefault("size_pct", postflop_decision.size_pct)
    identity_meta = {
        "node_type": context.meta.get("node_type") if isinstance(context.meta, dict) else None,
        "opener_pos": context.meta.get("opener_pos") if isinstance(context.meta, dict) else None,
        "three_bettor_pos": context.meta.get("three_bettor_pos") if isinstance(context.meta, dict) else None,
        "four_bettor_pos": context.meta.get("four_bettor_pos") if isinstance(context.meta, dict) else None,
        "limpers": context.meta.get("limpers") if isinstance(context.meta, dict) else None,
        "callers": context.meta.get("callers") if isinstance(context.meta, dict) else None,
    }
    solver_fingerprint, decision_id, source_frame_id = _build_decision_identity(
        street=str(report["street"]),
        engine_action=_postflop_engine_action(postflop_decision.action),
        raw_action=str(postflop_decision.action),
        context_meta=context_meta,
        identity_meta=identity_meta,
    )
    return HeroDecision(
        street=str(report["street"]),
        engine_action=_postflop_engine_action(postflop_decision.action),
        amount_to=postflop_decision.amount_to,
        size_pct=postflop_decision.size_pct,
        actor_name=actor_name,
        actor_pos=context.hero_position,
        reason=f"postflop:{postflop_decision.action}",
        confidence=confidence,
        source="hero_decision.postflop",
        solver_fingerprint=solver_fingerprint,
        decision_id=decision_id,
        source_frame_id=source_frame_id,
        postflop=postflop_decision,
        villain_sources=resolved_sources,
        debug={
            "recommended_option": best_option,
            "bluff_layer": dict(report.get("bluff_layer") or {}),
            "report_meta": report_meta,
            "solver_fingerprint": solver_fingerprint,
            "decision_id": decision_id,
            "source_frame_id": source_frame_id,
            "engine_action": _postflop_engine_action(postflop_decision.action),
            "recommended_action": str(postflop_decision.action),
            "street": str(report["street"]),
            "meta": context_meta,
        },
    )


def solve_hero_action(
    *,
    preflop_context: Optional[PreflopContext] = None,
    postflop_context: Optional[PostflopContext] = None,
    **kwargs: object,
) -> HeroDecision:
    if (preflop_context is None) == (postflop_context is None):
        raise ValueError("Нужно передать ровно один контекст: preflop_context или postflop_context")
    if preflop_context is not None:
        return solve_hero_preflop(preflop_context, **kwargs)
    return solve_hero_postflop(postflop_context, **kwargs)



__all__ = [
    "RangeSource",
    "build_villain_ranges_from_preflop_spots",
    "build_villain_ranges_from_postflop_players",
    "solve_hero_decision",
    "solve_hero_preflop",
    "solve_hero_postflop",
    "solve_hero_action",
    "format_hero_decision_report",
    "calculate_zero_fe",
    "calculate_zero_fe_for_raise",
    "calculate_required_fe_bet",
    "calculate_required_fe_raise",
    "calculate_call_equity_threshold",
    "calculate_spr",
    "ev_bet",
    "ev_raise",
    "ev_call",
    "_hero_postflop_tags",
]


# =========================
# Conservative override block (2026-04)
# =========================

_HARD_CALL_MARGIN_BY_STREET = {
    "flop": {"hu": 0.03, "multiway": 0.05},
    "turn": {"hu": 0.05, "multiway": 0.07},
    "river": {"hu": 0.06, "multiway": 0.08},
}
_HARD_RAISE_EXTRA_MARGIN = 0.03


def _safety_margin_vs_passive(*, street: str, pot_before_hero: float, line_adjustments: Optional[Dict[str, float]] = None) -> float:
    pot = max(0.0, float(pot_before_hero))
    street = str(street or "flop").lower()
    base = {"flop": 0.03, "turn": 0.04, "river": 0.05}.get(street, 0.04)
    mult = 1.0
    if line_adjustments:
        try:
            mult = float(line_adjustments.get("safety_margin_multiplier", 1.0) or 1.0)
        except Exception:
            mult = 1.0
    return pot * base * max(0.70, min(1.60, mult))


def build_line_adjustments(line_context: Optional[Dict[str, object]], *, player_count: int) -> Dict[str, float]:
    ctx = {} if line_context is None else dict(line_context)
    preflop_family = str(ctx.get("preflop_family") or "single_raised_pot")

    fe_multiplier = 1.0
    call_penalty = 0.0
    passive_bonus = 0.0
    safety_margin_multiplier = 1.0

    if preflop_family == "limped_pot":
        fe_multiplier *= 0.70
        call_penalty += 0.020
        safety_margin_multiplier *= 1.20
    elif preflop_family == "iso_pot":
        fe_multiplier *= 0.88
        call_penalty += 0.010
        safety_margin_multiplier *= 1.08
    elif preflop_family == "3bet_pot":
        fe_multiplier *= 0.86
        call_penalty += 0.014
        safety_margin_multiplier *= 1.10

    if ctx.get("prior_aggression"):
        fe_multiplier *= 0.78
        call_penalty += 0.012
        safety_margin_multiplier *= 1.08
    if ctx.get("facing_raise"):
        fe_multiplier *= 0.55
        call_penalty += 0.030
        safety_margin_multiplier *= 1.20
    if ctx.get("delayed_spot"):
        fe_multiplier *= 0.92
    if ctx.get("street_checked_through"):
        fe_multiplier *= 0.90
        passive_bonus += 0.010
    if ctx.get("facing_oop_check"):
        passive_bonus += 0.020
    if ctx.get("facing_ip_check_back"):
        passive_bonus += 0.012
    if player_count > 2:
        fe_multiplier *= max(0.28, 1.0 - 0.22 * (player_count - 2))
        call_penalty += 0.016 * (player_count - 2)
        safety_margin_multiplier *= 1.0 + 0.10 * (player_count - 2)

    return {
        "fe_multiplier": max(0.0, min(1.00, fe_multiplier)),
        "call_penalty": max(0.0, min(0.25, call_penalty)),
        "passive_bonus": max(0.0, min(0.10, passive_bonus)),
        "safety_margin_multiplier": max(0.80, min(1.60, safety_margin_multiplier)),
        "preflop_family": preflop_family,
    }


def _infer_spot_type(*, street: str, hero_in_position: bool, to_call: float, line_context: Optional[Dict[str, object]]) -> str:
    ctx = {} if line_context is None else dict(line_context)
    if float(to_call) > 0:
        return "facing_raise_spot" if ctx.get("facing_raise") else "facing_bet_spot"
    if ctx.get("facing_oop_check"):
        return "facing_oop_check"
    if ctx.get("facing_ip_check_back"):
        return "facing_ip_check_back"
    if ctx.get("delayed_spot"):
        return "delayed_probe_spot"
    if _hero_has_initiative(ctx):
        return "cbet_spot"
    if ctx.get("checked_to_hero") and hero_in_position:
        return "ip_check_through_spot"
    if not hero_in_position:
        return "check_as_default_oop"
    return "ip_check_through_spot"


def _estimate_check_ev(*, pot_before_hero: float, realized_equity: float, hero_tags: set[str], street: str, hero_in_position: bool, player_count: int, line_context: Optional[Dict[str, object]], spot_type: str) -> float:
    pot = float(pot_before_hero)
    eq = max(0.0, min(1.0, float(realized_equity)))
    ctx = {} if line_context is None else dict(line_context)
    line_adj = build_line_adjustments(ctx, player_count=player_count)

    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair"}
    medium_value = {"middle_pair", "bottom_pair", "underpair", "pocket_pair"}
    strong_draws = {"combo_draw", "flush_draw", "oesd"}
    weak_draws = {"gutshot", "backdoor_flush_draw"}
    high_card = {"ace_high", "two_overcards", "one_overcard"}

    if hero_tags & strong_made:
        realization = 0.90
    elif hero_tags & strong_value:
        realization = 0.82
    elif hero_tags & medium_value:
        realization = 0.74
    elif hero_tags & strong_draws:
        realization = 0.66
    elif hero_tags & weak_draws:
        realization = 0.55
    elif hero_tags & high_card:
        realization = 0.44
    else:
        realization = 0.38

    mode = "check_as_default_oop"
    if spot_type == "facing_ip_check_back":
        mode = "check_back_ip"
    elif spot_type in {"facing_raise_spot", "facing_bet_spot", "cbet_spot"} or ctx.get("prior_aggression"):
        mode = "check_after_aggression"
    elif spot_type == "delayed_probe_spot" or ctx.get("delayed_spot"):
        mode = "check_in_delayed_spot"
    elif hero_in_position:
        mode = "check_back_ip"

    if mode == "check_back_ip":
        realization += 0.01
    elif mode == "check_after_aggression":
        realization -= 0.05
    elif mode == "check_in_delayed_spot":
        realization -= 0.01
    else:
        realization += 0.02

    if street == "turn":
        realization += 0.03
    elif street == "river":
        realization += 0.06

    if hero_in_position:
        realization += 0.02
    else:
        realization -= 0.02

    if player_count > 2:
        realization -= 0.03 * (player_count - 2)
    realization += float(line_adj.get("passive_bonus", 0.0) or 0.0)
    realization = max(0.16, min(1.02, realization))

    missed_value_penalty = 0.0
    protection_penalty = 0.0
    rio_penalty = 0.0
    if hero_tags & strong_made:
        missed_value_penalty += 0.04 * pot
    elif hero_tags & strong_value:
        missed_value_penalty += 0.03 * pot
    elif hero_tags & medium_value and street != "river":
        protection_penalty += 0.02 * pot
    elif hero_tags & strong_draws:
        rio_penalty += 0.01 * pot

    if mode == "check_after_aggression":
        missed_value_penalty *= 0.85
    elif mode == "check_back_ip":
        protection_penalty *= 0.70

    return max(-pot, (pot * eq * realization) - missed_value_penalty - protection_penalty - rio_penalty)


def _hero_bet_allowed(hero_tags: set[str], *, street: str, hero_in_position: bool, to_call: float, line_context: Optional[Dict[str, object]], spot_type: str) -> bool:
    if float(to_call) > 0:
        return False
    ctx = {} if line_context is None else dict(line_context)
    preflop_family = str(ctx.get("preflop_family") or "single_raised_pot")
    very_strong = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair", "top_pair_top_kicker", "top_pair_good_kicker"}
    medium_value = {"middle_pair", "middle_pair_good_kicker", "bottom_pair", "underpair", "pocket_pair", "pocket_pair_above_second_card"}
    weak_showdown = {"top_pair_weak_kicker", "middle_pair_weak_kicker", "bottom_pair_weak_kicker", "pocket_pair_below_second_card", "weak_showdown"}
    strong_draws = {"combo_draw", "nut_flush_draw", "flush_draw", "oesd"}
    weak_draws = {"gutshot", "backdoor_flush_draw"}
    high_card = {"ace_high", "two_overcards", "one_overcard"}
    dry_good_cbet = bool(hero_tags & {"board_dry_high", "board_ace_high", "board_king_high", "board_paired"})
    wet_bad_cbet = bool(hero_tags & {"board_wet_connected", "board_low_connected", "board_monotone"})

    if hero_tags & very_strong:
        return True

    if preflop_family == "limped_pot":
        if hero_tags & (strong_draws | strong_value) and street in {"flop", "turn", "river"}:
            return True
        if street in {"flop", "turn"} and hero_tags & weak_draws and dry_good_cbet:
            return True
        return False

    if spot_type == "cbet_spot":
        if hero_tags & (strong_value | medium_value | strong_draws):
            return True
        if street in {"flop", "turn"} and hero_tags & weak_draws and not (wet_bad_cbet and not hero_in_position):
            return True
        if dry_good_cbet and hero_tags & high_card:
            return True
        if dry_good_cbet and "air" in hero_tags and hero_in_position and street == "flop":
            return True
        return False

    if spot_type in {"facing_oop_check", "ip_check_through_spot", "delayed_probe_spot"}:
        if hero_tags & (strong_value | medium_value | strong_draws):
            return True
        if street in {"flop", "turn"} and hero_tags & weak_draws:
            return True
        if street == "flop" and dry_good_cbet and hero_tags & high_card:
            return True
        return False

    if spot_type == "check_as_default_oop":
        if hero_tags & strong_draws:
            return True
        if street in {"turn", "river"} and hero_tags & strong_value:
            return True
        if street == "flop" and dry_good_cbet and hero_tags & (weak_draws | high_card) and not wet_bad_cbet:
            return True
        return False

    return bool(hero_tags & (strong_value | medium_value | weak_showdown | strong_draws))

def _bet_size_preference_adjustment(hero_tags: set[str], *, street: str, hero_in_position: bool, spot_type: str, size_pct: float, pot_before_hero: float) -> float:
    pot = float(pot_before_hero)
    size = float(size_pct)
    nuts_like = {"straight_flush", "quads", "full_house"}
    strong_made = {"flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair", "top_pair_top_kicker", "top_pair_good_kicker"}
    medium_value = {"middle_pair", "middle_pair_good_kicker", "bottom_pair", "underpair", "pocket_pair", "pocket_pair_above_second_card"}
    weak_showdown = {"top_pair_weak_kicker", "middle_pair_weak_kicker", "bottom_pair_weak_kicker", "pocket_pair_below_second_card", "weak_showdown"}
    strong_draws = {"combo_draw", "nut_flush_draw", "flush_draw", "oesd"}
    weak_draws = {"gutshot", "backdoor_flush_draw"}
    high_card = {"ace_high", "two_overcards", "one_overcard"}
    dry_good_cbet = bool(hero_tags & {"board_dry_high", "board_ace_high", "board_king_high", "board_paired"})
    wet_bad_cbet = bool(hero_tags & {"board_wet_connected", "board_low_connected", "board_monotone"})

    adj = 0.0
    if spot_type == "check_as_default_oop" and size >= 70:
        adj -= 0.06 * pot

    if hero_tags & nuts_like:
        if size <= 33:
            adj -= 0.01 * pot
        elif size <= 50:
            adj += 0.03 * pot
        else:
            adj += 0.04 * pot
    elif hero_tags & strong_made:
        if size <= 33:
            adj += 0.00 * pot
        elif size <= 50:
            adj += 0.05 * pot
        else:
            adj += 0.02 * pot
    elif hero_tags & strong_value:
        if size <= 33:
            adj += 0.04 * pot
        elif size <= 50:
            adj += 0.04 * pot
        else:
            adj -= 0.02 * pot if not wet_bad_cbet else 0.05 * pot
    elif hero_tags & medium_value:
        if size <= 33:
            adj += 0.065 * pot
        elif size <= 50:
            adj += 0.015 * pot
        else:
            adj -= 0.11 * pot
    elif hero_tags & weak_showdown:
        if size <= 33:
            adj += 0.035 * pot
        elif size <= 50:
            adj -= 0.015 * pot
        else:
            adj -= 0.13 * pot
    elif hero_tags & strong_draws:
        if street == "flop":
            if size <= 33:
                adj += 0.01 * pot
            elif size <= 50:
                adj += 0.05 * pot
            else:
                adj += 0.01 * pot
        else:
            if size <= 33:
                adj += 0.00 * pot
            elif size <= 50:
                adj += 0.03 * pot
            else:
                adj -= 0.02 * pot
    elif hero_tags & weak_draws:
        if size <= 33:
            adj += 0.04 * pot
        elif size <= 50:
            adj += 0.00 * pot
        else:
            adj -= 0.08 * pot
    elif hero_tags & high_card:
        if size <= 33 and dry_good_cbet:
            adj += 0.045 * pot
        elif size <= 33:
            adj += 0.02 * pot
        elif size <= 50:
            adj -= 0.015 * pot
        else:
            adj -= 0.11 * pot
    else:
        if size <= 33 and dry_good_cbet and hero_in_position:
            adj += 0.025 * pot
        elif size >= 70:
            adj -= 0.06 * pot

    if wet_bad_cbet and size >= 70 and not (hero_tags & (nuts_like | strong_made | strong_draws)):
        adj -= 0.045 * pot
    if spot_type in {"facing_oop_check", "delayed_probe_spot"} and size >= 70 and not (hero_tags & (nuts_like | strong_made)):
        adj -= 0.03 * pot
    return adj

def _hero_raise_allowed(hero_tags: set[str], *, street: str, hero_in_position: bool, to_call: float, line_context: Optional[Dict[str, object]]) -> bool:
    if float(to_call) <= 0:
        return False
    ctx = {} if line_context is None else dict(line_context)
    very_strong = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair_top_kicker", "top_pair_good_kicker"}
    strong_draws = {"combo_draw", "nut_flush_draw", "flush_draw", "oesd"}
    protected_second_pair = {"middle_pair_good_kicker", "pocket_pair_above_second_card"}
    preflop_family = str(ctx.get("preflop_family") or "single_raised_pot")
    dry_board = bool(hero_tags & {"board_dry_high", "board_paired"})

    if hero_tags & very_strong:
        return True
    if ctx.get("facing_raise"):
        return False

    if preflop_family == "limped_pot":
        if street in {"flop", "turn"} and hero_tags & (strong_draws | strong_value):
            return True
        if street == "flop" and dry_board and hero_tags & protected_second_pair and hero_in_position:
            return True
        return False

    if street in {"flop", "turn"} and hero_tags & strong_draws:
        return True
    if street == "flop" and hero_tags & strong_value and not ctx.get("prior_aggression"):
        return True
    if street == "flop" and hero_in_position and dry_board and hero_tags & protected_second_pair and not ctx.get("prior_aggression"):
        return True
    return False


def _hard_call_gate(*, street: str, call_equity: float, call_threshold: float, player_count: int, facing_raise: bool, hero_tags: Optional[set[str]] = None) -> Dict[str, object]:
    bucket = "hu" if int(player_count) <= 2 else "multiway"
    margin = _HARD_CALL_MARGIN_BY_STREET.get(str(street).lower(), _HARD_CALL_MARGIN_BY_STREET["turn"])[bucket]
    hero_tags = set(hero_tags or set())
    strong_made = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_draws = {"combo_draw", "nut_flush_draw", "flush_draw", "oesd"}
    weak_bluffcatcher = {"bottom_pair", "bottom_pair_weak_kicker", "pocket_pair_below_second_card", "weak_showdown", "ace_high"}
    if hero_tags & strong_made:
        margin -= 0.015
    if str(street).lower() in {"flop", "turn"} and hero_tags & strong_draws:
        margin -= 0.012
    if "combo_draw" in hero_tags or "nut_flush_draw" in hero_tags:
        margin -= 0.008
    if str(street).lower() == "river" and hero_tags & weak_bluffcatcher and not (hero_tags & strong_made):
        margin += 0.018
    if facing_raise:
        margin += 0.03
    margin = max(0.0, margin)
    required = max(0.0, min(1.0, float(call_threshold) + margin))
    allowed = float(call_equity) >= required
    return {"allowed": allowed, "required_equity": required, "margin": margin, "equity_used": float(call_equity)}


def _hard_raise_gate(*, hero_tags: set[str], street: str, assumed_fe: float, required_fe: float, spr: Optional[float], line_context: Optional[Dict[str, object]]) -> Dict[str, object]:
    ctx = {} if line_context is None else dict(line_context)
    very_strong = {"straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair"}
    strong_value = {"overpair", "top_pair_top_kicker", "top_pair_good_kicker"}
    strong_draws = {"combo_draw", "nut_flush_draw", "flush_draw", "oesd"}
    protected_second_pair = {"middle_pair_good_kicker", "pocket_pair_above_second_card"}
    dry_board = bool(hero_tags & {"board_dry_high", "board_paired"})
    extra_margin = _HARD_RAISE_EXTRA_MARGIN
    low_spr_ok = spr is not None and float(spr) <= 2.5

    if hero_tags & very_strong:
        return {"allowed": True, "reason": "strong_made", "required_fe": required_fe, "assumed_fe": assumed_fe, "margin": extra_margin}
    if ctx.get("facing_raise"):
        return {"allowed": False, "reason": "facing_raise_block", "required_fe": required_fe, "assumed_fe": assumed_fe, "margin": extra_margin}
    if hero_tags & strong_draws:
        if float(assumed_fe) >= float(required_fe) + extra_margin or low_spr_ok or "combo_draw" in hero_tags or "nut_flush_draw" in hero_tags:
            return {"allowed": True, "reason": "strong_draw", "required_fe": required_fe, "assumed_fe": assumed_fe, "margin": extra_margin}
    if street == "flop" and hero_tags & strong_value and not ctx.get("prior_aggression"):
        return {"allowed": True, "reason": "narrow_value_flop", "required_fe": required_fe, "assumed_fe": assumed_fe, "margin": extra_margin}
    if street == "flop" and dry_board and hero_tags & protected_second_pair and not ctx.get("prior_aggression"):
        return {"allowed": True, "reason": "protected_second_pair_dry_board", "required_fe": required_fe, "assumed_fe": assumed_fe, "margin": extra_margin}
    return {"allowed": False, "reason": "conservative_block", "required_fe": required_fe, "assumed_fe": assumed_fe, "margin": extra_margin}


# =========================
# Bluff layer debug profile (v1)
# =========================

_BLUFF_LAYER_STRONG_MADE = {
    "straight_flush", "quads", "full_house", "flush", "straight", "set", "trips", "two_pair",
}
_BLUFF_LAYER_THIN_VALUE = {
    "overpair", "top_pair_top_kicker", "top_pair_good_kicker", "top_pair",
    "middle_pair_good_kicker", "pocket_pair_above_second_card",
}
_BLUFF_LAYER_MEDIUM_SHOWDOWN = {
    "middle_pair", "bottom_pair", "underpair", "pocket_pair",
    "top_pair_weak_kicker", "middle_pair_weak_kicker", "bottom_pair_weak_kicker",
    "pocket_pair_below_second_card", "weak_showdown",
}
_BLUFF_LAYER_STRONG_DRAWS = {"combo_draw", "nut_flush_draw", "flush_draw", "oesd"}
_BLUFF_LAYER_WEAK_DRAWS = {"gutshot", "backdoor_flush_draw"}
_BLUFF_LAYER_BLOCKERS = {"nut_flush_blocker", "high_flush_blocker", "straight_blocker"}
_BLUFF_LAYER_HIGH_CARDS = {"ace_high", "two_overcards", "one_overcard"}
_BLUFF_LAYER_BOARD_TEXTURES = {
    "board_paired", "board_monotone", "board_two_tone", "board_rainbow",
    "board_connected", "board_low_connected", "board_dry_high", "board_broadway_dynamic",
    "board_ace_high", "board_king_high", "board_wet_connected",
}


def _bluff_layer_first_tag(hero_tags: set[str], candidates: set[str]) -> Optional[str]:
    for tag in sorted(candidates):
        if tag in hero_tags:
            return tag
    return None


def _facing_bet_size_profile(*, pot_before_hero: float, to_call: float) -> Dict[str, object]:
    call_amount = max(0.0, float(to_call or 0.0))
    pot = max(0.0, float(pot_before_hero or 0.0))
    if call_amount <= 0.0:
        return {
            "facing_bet": False,
            "bet_pct_pot": 0.0,
            "bet_size_bucket": "none",
            "is_small_bet": False,
            "is_medium_bet": False,
            "is_big_bet": False,
            "is_huge_bet": False,
        }

    # Runtime pot_before_hero normally means the pot HERO can win before calling,
    # so it already includes villain's bet. Removing to_call estimates the pre-bet
    # pot and makes 1/3, 1/2 and 2/3 bets fall into the intended buckets.
    estimated_pre_bet_pot = pot - call_amount
    if estimated_pre_bet_pot <= 0.0:
        estimated_pre_bet_pot = pot if pot > 0.0 else call_amount
    bet_pct_pot = 100.0 * call_amount / max(estimated_pre_bet_pot, 1e-9)

    if bet_pct_pot <= 33.0:
        bucket = "small"
    elif bet_pct_pot <= 66.0:
        bucket = "medium"
    elif bet_pct_pot <= 90.0:
        bucket = "big"
    else:
        bucket = "huge"

    return {
        "facing_bet": True,
        "bet_pct_pot": float(bet_pct_pot),
        "bet_size_bucket": bucket,
        "is_small_bet": bucket == "small",
        "is_medium_bet": bucket == "medium",
        "is_big_bet": bucket == "big",
        "is_huge_bet": bucket == "huge",
    }


def _bluff_layer_context_bool(ctx: Dict[str, object], keys: Sequence[str], *, default: bool = False) -> bool:
    for key in keys:
        if key not in ctx:
            continue
        value = ctx.get(key)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"1", "true", "yes", "y", "on", "capped", "weak", "fold", "folding"}:
                return True
            if normalized in {"0", "false", "no", "n", "off", "none", "null", "uncapped", "strong"}:
                return False
        return bool(value)
    return bool(default)


def _bluff_layer_context_has_any(ctx: Dict[str, object], keys: Sequence[str]) -> bool:
    return any(key in ctx for key in keys)


def _build_multiway_bluff_strict_calibration(
    *,
    hero_bucket: str,
    hero_tags: set[str],
    street: str,
    facing_bet: bool,
    hero_in_position: bool,
    player_count: int,
    line_context: Optional[Dict[str, object]],
    spr: Optional[float],
    bet_size_bucket: Optional[str] = None,
) -> Dict[str, object]:
    """Strict multiway rules for Bluff Layer v1.

    Multiway pots are conservative: value may bet; thin value is small-control;
    semi-bluff needs combo/nut/very strong draw quality; blocker-only bluff and
    air are blocked; bluff-catcher calls only small bets.
    """
    ctx = {} if line_context is None else dict(line_context)
    tags = set(hero_tags or set())
    bucket = str(hero_bucket or "").upper()
    street = str(street or "flop").lower()
    bet_bucket = str(bet_size_bucket or "none").lower()
    is_multiway = int(player_count or 2) > 2

    has_strong_made = bool(tags & _BLUFF_LAYER_STRONG_MADE)
    has_thin_value = bool(tags & _BLUFF_LAYER_THIN_VALUE)
    has_medium_showdown = bool(tags & _BLUFF_LAYER_MEDIUM_SHOWDOWN)
    has_combo_draw = "combo_draw" in tags
    has_nut_flush_draw = "nut_flush_draw" in tags
    has_flush_draw = "flush_draw" in tags
    has_oesd = "oesd" in tags
    has_two_overcards = "two_overcards" in tags
    has_blocker = bool(tags & _BLUFF_LAYER_BLOCKERS)
    has_air = "air" in tags or bucket == "GIVE_UP"
    board_wet = bool(tags & {"board_wet_connected", "board_monotone", "board_low_connected", "board_broadway_dynamic"})
    board_dry = bool(tags & {"board_dry_high", "board_rainbow", "board_paired"}) and not board_wet
    prior_aggression = _bluff_layer_context_bool(ctx, ("prior_aggression", "villain_prior_aggression", "opponent_prior_aggression", "strong_line"), default=False)
    facing_raise = _bluff_layer_context_bool(ctx, ("facing_raise", "facing_reraise"), default=False)
    low_spr = bool(spr is not None and float(spr) <= 1.50)

    strong_multiway_draw = bool(
        has_combo_draw
        or has_nut_flush_draw
        or (has_flush_draw and has_oesd)
        or (has_flush_draw and has_two_overcards)
        or (has_oesd and has_two_overcards)
    )
    small_bet = bet_bucket in {"small", "0-25", "26-50"}
    medium_or_bigger = bet_bucket in {"medium", "big", "huge", "51-75", "76-99", "100+"}

    bet_forbidden: list[str] = []
    raise_forbidden: list[str] = []
    call_forbidden: list[str] = []
    general_forbidden: list[str] = []
    preferred_size_pct: Optional[float] = None

    if not is_multiway:
        return {
            "contract_version": "multiway_bluff_strict_calibration_v1",
            "enabled": False,
            "applies": False,
            "reason": "not_multiway",
            "allow_bet": True,
            "allow_raise": True,
            "allow_call": True,
            "preferred_size_pct": None,
            "selected_reason": "not multiway; strict multiway gates not applied",
            "forbidden_reasons": [],
            "bet_forbidden_reasons": [],
            "raise_forbidden_reasons": [],
            "call_forbidden_reasons": [],
            "conditions": {"player_count": int(player_count or 0), "hero_bucket": bucket, "street": street},
        }

    if bucket == "VALUE":
        allow_bet = True
        allow_raise = has_strong_made and not facing_raise
        allow_call = True
        preferred_size_pct = 70.0 if board_wet or street == "river" else 50.0
        selected_reason = "multiway value is allowed; extract value but avoid thin non-nut reraises"
        if facing_raise and not (tags & {"straight_flush", "quads", "full_house", "flush", "straight"}):
            raise_forbidden.append("multiway_value_reraise_requires_near_nuts")
    elif bucket == "THIN_VALUE":
        soft_conditions = bool((board_dry or hero_in_position) and not prior_aggression and not low_spr and street in {"flop", "turn"})
        allow_bet = (not facing_bet) and soft_conditions
        allow_raise = False
        allow_call = bool(facing_bet and small_bet and not facing_raise)
        preferred_size_pct = 33.0
        selected_reason = "multiway thin value is small-control only"
        if not allow_bet and not facing_bet:
            bet_forbidden.append("multiway_thin_value_prefers_check")
        raise_forbidden.append("multiway_thin_value_no_raise")
        if facing_bet and not allow_call:
            call_forbidden.append("multiway_thin_value_call_only_vs_small_bet")
    elif bucket == "SEMI_BLUFF":
        allow_bet = (not facing_bet) and strong_multiway_draw and street in {"flop", "turn"} and not low_spr
        allow_raise = bool(facing_bet and strong_multiway_draw and not facing_raise and not low_spr and street in {"flop", "turn"})
        allow_call = bool(facing_bet and strong_multiway_draw and not medium_or_bigger)
        preferred_size_pct = 50.0 if street == "flop" else 70.0
        selected_reason = "multiway semi-bluff requires combo/nut/very strong draw"
        if not strong_multiway_draw:
            general_forbidden.append("multiway_requires_strong_draw")
            bet_forbidden.append("multiway_semi_bluff_bet_requires_combo_nut_or_strong_draw")
            raise_forbidden.append("multiway_semi_bluff_raise_requires_combo_nut_or_strong_draw")
            call_forbidden.append("multiway_semi_bluff_call_requires_strong_draw")
        if low_spr:
            general_forbidden.append("multiway_low_spr_no_bluff")
        if street == "river":
            general_forbidden.append("multiway_no_river_semi_bluff")
    elif bucket == "BLOCKER_BLUFF":
        allow_bet = False
        allow_raise = False
        allow_call = False
        selected_reason = "multiway blocker-only bluff is forbidden"
        general_forbidden.append("multiway_no_blocker_bluff")
        bet_forbidden.append("multiway_no_blocker_bluff_bet")
        raise_forbidden.append("multiway_no_blocker_bluff_raise")
        call_forbidden.append("multiway_blocker_bluff_no_call")
    elif bucket in {"BLUFF_CATCHER", "SHOWDOWN_CHECK"}:
        allow_bet = False
        allow_raise = False
        allow_call = bool(facing_bet and small_bet and (has_medium_showdown or has_blocker or has_thin_value))
        preferred_size_pct = None
        selected_reason = "multiway bluff-catcher is passive; call only small bets"
        bet_forbidden.append("multiway_bluff_catcher_no_bet")
        raise_forbidden.append("multiway_bluff_catcher_no_raise")
        if facing_bet and not allow_call:
            call_forbidden.append("multiway_bluff_catcher_call_only_vs_small_bet")
    else:
        allow_bet = False
        allow_raise = False
        allow_call = False
        selected_reason = "multiway air/give-up has no bluff or call permission"
        general_forbidden.append("multiway_no_air_or_blocker_bluff")
        bet_forbidden.append("multiway_no_air_bet")
        raise_forbidden.append("multiway_no_air_raise")
        call_forbidden.append("multiway_air_no_call")

    if facing_raise and bucket != "VALUE":
        allow_raise = False
        raise_forbidden.append("multiway_no_non_value_reraise")
    if low_spr and bucket in {"SEMI_BLUFF", "BLOCKER_BLUFF", "GIVE_UP"}:
        allow_bet = False
        allow_raise = False
        bet_forbidden.append("multiway_low_spr_no_bluff_bet")
        raise_forbidden.append("multiway_low_spr_no_bluff_raise")

    def _dedupe(items: Sequence[object]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            value = str(item)
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    return {
        "contract_version": "multiway_bluff_strict_calibration_v1",
        "enabled": True,
        "applies": True,
        "allow_bet": bool(allow_bet),
        "allow_raise": bool(allow_raise),
        "allow_call": bool(allow_call),
        "preferred_size_pct": preferred_size_pct,
        "selected_reason": selected_reason,
        "forbidden_reasons": _dedupe(general_forbidden),
        "bet_forbidden_reasons": _dedupe(bet_forbidden + general_forbidden),
        "raise_forbidden_reasons": _dedupe(raise_forbidden + general_forbidden),
        "call_forbidden_reasons": _dedupe(call_forbidden),
        "conditions": {
            "player_count": int(player_count or 0),
            "hero_bucket": bucket,
            "street": street,
            "facing_bet": bool(facing_bet),
            "hero_in_position": bool(hero_in_position),
            "bet_size_bucket": bet_bucket,
            "has_strong_made": has_strong_made,
            "has_thin_value": has_thin_value,
            "has_medium_showdown": has_medium_showdown,
            "has_combo_draw": has_combo_draw,
            "has_nut_flush_draw": has_nut_flush_draw,
            "has_flush_draw": has_flush_draw,
            "has_oesd": has_oesd,
            "has_two_overcards": has_two_overcards,
            "has_blocker": has_blocker,
            "has_air": has_air,
            "strong_multiway_draw": strong_multiway_draw,
            "board_wet": board_wet,
            "board_dry": board_dry,
            "prior_aggression": prior_aggression,
            "facing_raise": facing_raise,
            "low_spr": low_spr,
        },
    }


def _build_river_blocker_bluff_calibration(
    *,
    hero_bucket: str,
    hero_tags: set[str],
    street: str,
    facing_bet: bool,
    hero_in_position: bool,
    player_count: int,
    line_context: Optional[Dict[str, object]],
    spr: Optional[float],
    bet_size_bucket: Optional[str] = None,
) -> Dict[str, object]:
    """Strict river blocker-bluff rules shared by checked-to-HERO and facing-bet paths."""
    ctx = {} if line_context is None else dict(line_context)
    tags = set(hero_tags or set())
    bucket = str(hero_bucket or "").upper()
    street = str(street or "").lower()
    bet_bucket = str(bet_size_bucket or "none").lower()

    has_nut_flush_blocker = "nut_flush_blocker" in tags
    has_high_flush_blocker = "high_flush_blocker" in tags
    has_straight_blocker = "straight_blocker" in tags
    has_any_blocker = bool(tags & _BLUFF_LAYER_BLOCKERS)
    has_made_or_showdown = bool(tags & (_BLUFF_LAYER_STRONG_MADE | _BLUFF_LAYER_THIN_VALUE | _BLUFF_LAYER_MEDIUM_SHOWDOWN))
    # High-card tags can coexist with nut/high blockers.  For this calibration,
    # "showdown value" means made-hand or explicit weak-showdown tags; ace-high
    # blocker candidates remain eligible when the official bucket is BLOCKER_BLUFF.
    has_showdown_value = has_made_or_showdown
    is_multiway = int(player_count or 2) > 2
    is_heads_up = not is_multiway
    low_spr = bool(spr is not None and float(spr) <= 1.50)
    pot_committed = _bluff_layer_context_bool(
        ctx,
        ("pot_committed", "villain_pot_committed", "opponent_pot_committed", "all_in_pressure"),
        default=False,
    ) or low_spr
    facing_raise = _bluff_layer_context_bool(ctx, ("facing_raise", "facing_reraise"), default=False)
    prior_aggression = _bluff_layer_context_bool(
        ctx,
        (
            "prior_aggression",
            "villain_prior_aggression",
            "opponent_prior_aggression",
            "villain_showed_strength",
            "opponent_showed_strength",
            "bet_bet_big_bet",
            "bet_bet_big",
            "triple_barrel",
            "double_barrel_big",
            "strong_line",
            "villain_strong_line",
            "opponent_strong_line",
        ),
        default=False,
    )
    call_heavy = _bluff_layer_context_bool(
        ctx,
        (
            "station_line",
            "call_heavy",
            "villain_call_heavy",
            "opponent_call_heavy",
            "sticky_range",
            "station",
            "villain_station",
            "opponent_station",
        ),
        default=False,
    )
    uncapped_or_strong_range = _bluff_layer_context_bool(
        ctx,
        (
            "opponent_uncapped",
            "villain_uncapped",
            "range_uncapped",
            "uncapped_range",
            "opponent_strong_range",
            "villain_strong_range",
        ),
        default=False,
    )
    capped_keys = (
        "opponent_capped",
        "villain_capped",
        "range_capped",
        "capped_range",
        "line_is_capped",
        "is_capped",
        "villain_range_capped",
        "opponent_range_capped",
    )
    capped_key_present = _bluff_layer_context_has_any(ctx, capped_keys)
    opponent_capped = _bluff_layer_context_bool(ctx, capped_keys, default=False)
    fold_equity_ok = (
        not prior_aggression
        and not facing_raise
        and not call_heavy
        and not uncapped_or_strong_range
        and (opponent_capped or not capped_key_present)
    )

    if has_nut_flush_blocker:
        blocker_quality = "nut_flush_blocker"
    elif has_high_flush_blocker:
        blocker_quality = "high_flush_blocker"
    elif has_straight_blocker:
        blocker_quality = "straight_blocker"
    else:
        blocker_quality = "none"

    paired_board_reduces_story = "board_paired" in tags and blocker_quality == "straight_blocker" and not opponent_capped
    blocker_quality_ok = bool(
        has_nut_flush_blocker
        or has_high_flush_blocker
        or (has_straight_blocker and not paired_board_reduces_story)
    )

    applies = street == "river" and bucket == "BLOCKER_BLUFF"
    if not applies:
        return {
            "contract_version": "river_blocker_bluff_calibration_v1",
            "enabled": False,
            "applies": False,
            "reason": "not_river_blocker_bluff_bucket",
            "allow_bet": False,
            "allow_raise_vs_bet": False,
            "preferred_size_pct": None,
            "blocker_quality": blocker_quality,
            "forbidden_reasons": [],
            "bet_forbidden_reasons": [],
            "raise_forbidden_reasons": [],
            "conditions": {
                "street": street,
                "hero_bucket": bucket,
                "has_blocker": has_any_blocker,
            },
        }

    base_forbidden: list[str] = []
    if not has_any_blocker:
        base_forbidden.append("river_blocker_bluff_requires_blocker")
    if not blocker_quality_ok:
        base_forbidden.append("river_blocker_bluff_blocker_quality_too_weak")
    if has_showdown_value:
        base_forbidden.append("river_blocker_bluff_requires_no_showdown_value")
    if not is_heads_up:
        base_forbidden.append("river_blocker_bluff_heads_up_only")
    if not bool(hero_in_position):
        base_forbidden.append("river_blocker_bluff_ip_only")
    if not fold_equity_ok:
        base_forbidden.append("river_blocker_bluff_fold_equity_not_clean")
    if prior_aggression:
        base_forbidden.append("river_blocker_bluff_blocked_by_strong_line")
    if facing_raise:
        base_forbidden.append("river_blocker_bluff_no_reraise")
    if call_heavy:
        base_forbidden.append("river_blocker_bluff_blocked_vs_call_heavy_line")
    if uncapped_or_strong_range:
        base_forbidden.append("river_blocker_bluff_blocked_vs_uncapped_range")
    if pot_committed:
        base_forbidden.append("river_blocker_bluff_blocked_when_pot_committed")
    if paired_board_reduces_story:
        base_forbidden.append("river_blocker_bluff_straight_blocker_weak_on_paired_board")

    bet_forbidden = list(base_forbidden)
    raise_forbidden = list(base_forbidden)
    if facing_bet and bet_bucket in {"huge"}:
        raise_forbidden.append("river_blocker_bluff_no_raise_vs_huge_bet")
    if facing_bet and bet_bucket in {"big"} and not has_nut_flush_blocker:
        raise_forbidden.append("river_blocker_bluff_big_bet_requires_nut_blocker")

    allow_bet = not facing_bet and not bet_forbidden
    allow_raise_vs_bet = bool(facing_bet) and not raise_forbidden
    if has_nut_flush_blocker or has_high_flush_blocker:
        preferred_size_pct: Optional[float] = 70.0
    elif has_straight_blocker:
        preferred_size_pct = 50.0
    else:
        preferred_size_pct = None

    if allow_bet:
        selected_reason = "river IP HU blocker bluff allowed with clean fold-equity conditions"
    elif allow_raise_vs_bet:
        selected_reason = "river IP HU blocker bluff raise allowed versus non-huge bet"
    else:
        selected_reason = "river blocker bluff blocked by calibration gates"

    return {
        "contract_version": "river_blocker_bluff_calibration_v1",
        "enabled": True,
        "applies": True,
        "allow_bet": bool(allow_bet),
        "allow_raise_vs_bet": bool(allow_raise_vs_bet),
        "preferred_size_pct": preferred_size_pct,
        "blocker_quality": blocker_quality,
        "selected_reason": selected_reason,
        "forbidden_reasons": list(dict.fromkeys(base_forbidden)),
        "bet_forbidden_reasons": list(dict.fromkeys(bet_forbidden)),
        "raise_forbidden_reasons": list(dict.fromkeys(raise_forbidden)),
        "conditions": {
            "heads_up": bool(is_heads_up),
            "hero_in_position": bool(hero_in_position),
            "has_blocker": bool(has_any_blocker),
            "has_showdown_value": bool(has_showdown_value),
            "opponent_capped": bool(opponent_capped),
            "opponent_capped_explicit": bool(capped_key_present),
            "fold_equity_ok": bool(fold_equity_ok),
            "prior_aggression": bool(prior_aggression),
            "facing_raise": bool(facing_raise),
            "call_heavy": bool(call_heavy),
            "uncapped_or_strong_range": bool(uncapped_or_strong_range),
            "pot_committed": bool(pot_committed),
            "low_spr": bool(low_spr),
            "paired_board_reduces_story": bool(paired_board_reduces_story),
            "bet_size_bucket": bet_bucket,
        },
    }


def _build_facing_bet_layer_profile(
    *,
    hero_bucket: str,
    hero_tags: set[str],
    street: str,
    pot_before_hero: float,
    to_call: float,
    hero_in_position: bool,
    player_count: int,
    line_context: Optional[Dict[str, object]],
    spr: Optional[float],
    call_equity: float,
) -> Dict[str, object]:
    """Hard Facing Bet Layer for call / fold / raise decisions.

    The generic Bluff Layer decides whether HERO may bluff.  This layer decides
    what HERO may do when villain has already bet: continue as call/raise or
    surrender as fold.
    """
    size_profile = _facing_bet_size_profile(
        pot_before_hero=float(pot_before_hero or 0.0),
        to_call=float(to_call or 0.0),
    )
    if not bool(size_profile.get("facing_bet")):
        return {
            "contract_version": "facing_bet_layer_v1",
            "enabled": False,
            "reason": "not_facing_bet",
            **size_profile,
        }

    ctx = {} if line_context is None else dict(line_context)
    bucket = str(hero_bucket or "").upper()
    street = str(street or "flop").lower()
    tags = set(hero_tags or set())
    multiway = int(player_count or 2) > 2
    facing_raise = bool(ctx.get("facing_raise"))
    prior_aggression = bool(ctx.get("prior_aggression"))
    pot_committed = bool(ctx.get("pot_committed")) or (spr is not None and float(spr) <= 1.25)

    strong_made = set(_BLUFF_LAYER_STRONG_MADE)
    thin_value = set(_BLUFF_LAYER_THIN_VALUE)
    medium_showdown = set(_BLUFF_LAYER_MEDIUM_SHOWDOWN)
    strong_draws = set(_BLUFF_LAYER_STRONG_DRAWS)
    weak_draws = set(_BLUFF_LAYER_WEAK_DRAWS)
    blockers = set(_BLUFF_LAYER_BLOCKERS)
    high_cards = set(_BLUFF_LAYER_HIGH_CARDS)

    has_strong_made = bool(tags & strong_made)
    has_thin_value = bool(tags & thin_value)
    has_medium_showdown = bool(tags & medium_showdown)
    has_strong_draw = bool(tags & strong_draws)
    has_weak_draw = bool(tags & weak_draws)
    has_blocker = bool(tags & blockers)
    has_high_card = bool(tags & high_cards)
    has_combo_or_nut_draw = bool(tags & {"combo_draw", "nut_flush_draw"})
    has_oesd_plus = "oesd" in tags and (has_high_card or "flush_draw" in tags or "backdoor_flush_draw" in tags)
    has_raise_quality_draw = has_combo_or_nut_draw or has_oesd_plus
    has_strong_blocker = bool(tags & {"nut_flush_blocker", "high_flush_blocker", "straight_blocker"})

    call_threshold = calculate_call_equity_threshold(float(pot_before_hero or 0.0), float(to_call or 0.0))
    call_margin = float(call_equity) - float(call_threshold)
    small_bet = bool(size_profile.get("is_small_bet"))
    medium_bet = bool(size_profile.get("is_medium_bet"))
    big_bet = bool(size_profile.get("is_big_bet"))
    huge_bet = bool(size_profile.get("is_huge_bet"))

    allow_call = False
    allow_raise = False
    allow_fold = True
    preferred_passive_action = "fold"
    selected_reason = "facing bet default fold"
    call_reasons: list[str] = []
    raise_reasons: list[str] = []
    fold_reasons: list[str] = []
    river_blocker_calibration: Dict[str, object] = _build_river_blocker_bluff_calibration(
        hero_bucket=bucket,
        hero_tags=tags,
        street=street,
        facing_bet=True,
        hero_in_position=bool(hero_in_position),
        player_count=int(player_count or 2),
        line_context=ctx,
        spr=spr,
        bet_size_bucket=str(size_profile.get("bet_size_bucket") or "none"),
    )
    multiway_calibration: Dict[str, object] = _build_multiway_bluff_strict_calibration(
        hero_bucket=bucket,
        hero_tags=tags,
        street=street,
        facing_bet=True,
        hero_in_position=bool(hero_in_position),
        player_count=int(player_count or 2),
        line_context=ctx,
        spr=spr,
        bet_size_bucket=str(size_profile.get("bet_size_bucket") or "none"),
    )

    if bucket == "VALUE":
        allow_call = True
        allow_fold = False
        preferred_passive_action = "call"
        selected_reason = "value hand continues versus bet"
        if has_strong_made:
            allow_raise = not (facing_raise and not (tags & {"straight_flush", "quads", "full_house", "flush", "straight"}))
        else:
            allow_raise = False
        if not allow_raise:
            raise_reasons.append("value_raise_needs_stronger_made_hand")
        fold_reasons.append("value_never_auto_fold_vs_bet")

    elif bucket == "THIN_VALUE":
        allow_raise = False
        raise_reasons.append("thin_value_no_raise_vs_bet")
        if small_bet:
            allow_call = True
            selected_reason = "thin value calls small bet"
        elif medium_bet:
            allow_call = call_margin >= (0.02 + (0.02 if multiway else 0.0) + (0.02 if facing_raise else 0.0))
            selected_reason = "thin value medium bet uses equity margin"
        else:
            premium_thin = bool(tags & {"overpair", "top_pair_top_kicker", "top_pair_good_kicker"})
            allow_call = premium_thin and call_margin >= (0.08 + (0.04 if huge_bet else 0.0))
            selected_reason = "thin value big bet requires premium pair and equity margin"
        preferred_passive_action = "call" if allow_call else "fold"
        if not allow_call:
            call_reasons.append("thin_value_call_price_too_high")

    elif bucket == "SEMI_BLUFF":
        if street == "river":
            allow_call = False
            allow_raise = False
            selected_reason = "river missed semi bluff becomes fold unless blocker layer applies"
            call_reasons.append("river_no_semi_bluff_call_without_showdown_value")
            raise_reasons.append("river_no_semi_bluff_raise")
        else:
            if has_strong_draw:
                allow_call = small_bet or call_margin >= (0.00 if medium_bet else 0.06)
            elif has_weak_draw:
                allow_call = small_bet and call_margin >= -0.02
            allow_raise = (
                has_raise_quality_draw
                and not facing_raise
                and not pot_committed
                and (not multiway or has_combo_or_nut_draw)
            )
            selected_reason = "semi bluff continues only with draw equity"
            if not allow_call:
                call_reasons.append("semi_bluff_not_enough_equity_to_call")
            if not allow_raise:
                raise_reasons.append("semi_bluff_raise_requires_combo_nut_or_oesd_plus")
        preferred_passive_action = "call" if allow_call else "fold"

    elif bucket == "BLOCKER_BLUFF":
        allow_call = False
        allow_raise = bool(river_blocker_calibration.get("allow_raise_vs_bet"))
        # Tiny/small calls with A-high blocker can happen only when equity is not
        # clearly below pot odds. Otherwise blocker-only hands fold versus bets.
        if small_bet and has_high_card and has_strong_blocker and call_margin >= -0.01:
            allow_call = True
        selected_reason = str(
            river_blocker_calibration.get("selected_reason")
            or "blocker bluff versus bet is mostly fold; river IP can raise"
        )
        preferred_passive_action = "call" if allow_call else "fold"
        if not allow_call:
            call_reasons.append("blocker_bluff_no_showdown_call")
        if not allow_raise:
            raise_reasons.extend(list(river_blocker_calibration.get("raise_forbidden_reasons") or []))
            raise_reasons.append("blocker_raise_requires_river_hu_ip_uncapped_fold_equity")

    elif bucket in {"BLUFF_CATCHER", "SHOWDOWN_CHECK"}:
        allow_raise = False
        raise_reasons.append("bluff_catcher_no_raise")
        if small_bet:
            allow_call = True
            selected_reason = "bluff catcher calls small bet"
        elif medium_bet:
            required_margin = 0.02 if has_blocker else 0.05
            allow_call = call_margin >= required_margin or (has_blocker and call_margin >= -0.01)
            selected_reason = "bluff catcher medium bet uses equity/blocker margin"
        else:
            required_margin = 0.10 if has_blocker else 0.14
            allow_call = call_margin >= required_margin and (has_blocker or has_medium_showdown)
            selected_reason = "bluff catcher big bet requires strong margin"
        preferred_passive_action = "call" if allow_call else "fold"
        if not allow_call:
            call_reasons.append("bluff_catcher_price_too_high")

    elif bucket == "GIVE_UP":
        allow_call = False
        allow_raise = False
        selected_reason = "give up folds versus bet"
        preferred_passive_action = "fold"
        call_reasons.append("give_up_no_call_vs_bet")
        raise_reasons.append("give_up_no_raise_vs_bet")

    else:
        allow_call = call_margin >= 0.04 and not huge_bet
        allow_raise = False
        preferred_passive_action = "call" if allow_call else "fold"
        selected_reason = "unknown bucket uses conservative call margin"
        if not allow_call:
            call_reasons.append("unknown_bucket_call_margin_failed")
        raise_reasons.append("unknown_bucket_no_raise")

    if multiway and bucket in {"BLOCKER_BLUFF", "GIVE_UP"}:
        allow_raise = False
        raise_reasons.append("multiway_no_blocker_or_air_raise")
    if multiway and bucket == "SEMI_BLUFF" and not has_combo_or_nut_draw:
        allow_raise = False
        raise_reasons.append("multiway_semi_bluff_raise_requires_combo_or_nut_draw")
    if bool(multiway_calibration.get("applies")):
        if not bool(multiway_calibration.get("allow_call")):
            allow_call = False
            call_reasons.extend(list(multiway_calibration.get("call_forbidden_reasons") or []))
        if not bool(multiway_calibration.get("allow_raise")):
            allow_raise = False
            raise_reasons.extend(list(multiway_calibration.get("raise_forbidden_reasons") or []))
    if facing_raise and bucket not in {"VALUE"}:
        allow_raise = False
        raise_reasons.append("facing_raise_no_non_value_reraise")
    if (big_bet or huge_bet) and bucket in {"BLUFF_CATCHER", "SHOWDOWN_CHECK", "THIN_VALUE"} and not allow_call:
        call_reasons.append("large_bet_defense_failed")
    if pot_committed and bucket in {"BLOCKER_BLUFF", "GIVE_UP"}:
        allow_raise = False
        raise_reasons.append("pot_committed_no_low_equity_bluff_raise")

    if not allow_call and preferred_passive_action == "call":
        preferred_passive_action = "fold"

    return {
        "contract_version": "facing_bet_layer_v1",
        "enabled": True,
        **size_profile,
        "hero_bucket": bucket,
        "street": street,
        "is_multiway": multiway,
        "hero_in_position": bool(hero_in_position),
        "facing_raise": facing_raise,
        "pot_committed": pot_committed,
        "spr": None if spr is None else float(spr),
        "call_threshold": float(call_threshold),
        "call_equity": float(call_equity),
        "call_margin": float(call_margin),
        "allow_call": bool(allow_call),
        "allow_raise": bool(allow_raise),
        "allow_fold": bool(allow_fold),
        "preferred_passive_action": preferred_passive_action,
        "selected_reason": selected_reason,
        "river_blocker_bluff_calibration": dict(river_blocker_calibration),
        "multiway_bluff_strict_calibration": dict(multiway_calibration),
        "call_forbidden_reasons": list(dict.fromkeys(call_reasons)),
        "raise_forbidden_reasons": list(dict.fromkeys(raise_reasons)),
        "fold_forbidden_reasons": list(dict.fromkeys(fold_reasons)),
        "flags": {
            "has_strong_made": has_strong_made,
            "has_thin_value": has_thin_value,
            "has_medium_showdown": has_medium_showdown,
            "has_strong_draw": has_strong_draw,
            "has_weak_draw": has_weak_draw,
            "has_blocker": has_blocker,
            "has_high_card": has_high_card,
            "has_raise_quality_draw": has_raise_quality_draw,
            "has_combo_or_nut_draw": has_combo_or_nut_draw,
            "has_strong_blocker": has_strong_blocker,
        },
    }


def _build_bluff_layer_profile(
    *,
    hero_tags: set[str],
    street: str,
    to_call: float,
    pot_before_hero: float,
    hero_in_position: bool,
    player_count: int,
    line_context: Optional[Dict[str, object]],
    spot_type: str,
    spr: Optional[float],
    raw_equity: float,
    realized_equity: float,
    call_equity: float,
    best_option: Optional[Dict[str, object]] = None,
    hero_profile: Optional[Dict[str, object]] = None,
) -> Dict[str, object]:
    """Human-readable HERO postflop bucket used for debug only.

    This profile deliberately does not veto, boost or override any action.
    It is a calibration layer: inspect it in render/hand JSON first, then later
    use the same fields as hard gates after the buckets are verified on hands.
    """
    official_profile = {} if hero_profile is None else dict(hero_profile)
    profile_tags = official_profile.get("hero_tags")
    if isinstance(profile_tags, (list, tuple, set)):
        tags = {str(tag) for tag in profile_tags if str(tag)}
    else:
        tags = set(hero_tags or set())
    ctx = {} if line_context is None else dict(line_context)
    street = str(street or "flop").lower()
    facing_bet = float(to_call or 0.0) > 0.0
    multiway = int(player_count or 2) > 2
    board_texture = sorted(tags & _BLUFF_LAYER_BOARD_TEXTURES)

    made_hand_class = (
        _bluff_layer_first_tag(tags, _BLUFF_LAYER_STRONG_MADE)
        or _bluff_layer_first_tag(tags, _BLUFF_LAYER_THIN_VALUE)
        or _bluff_layer_first_tag(tags, _BLUFF_LAYER_MEDIUM_SHOWDOWN)
        or "none"
    )
    draw_class = (
        _bluff_layer_first_tag(tags, _BLUFF_LAYER_STRONG_DRAWS)
        or _bluff_layer_first_tag(tags, _BLUFF_LAYER_WEAK_DRAWS)
        or "none"
    )
    blocker_class = _bluff_layer_first_tag(tags, _BLUFF_LAYER_BLOCKERS) or "none"

    has_strong_made = bool(tags & _BLUFF_LAYER_STRONG_MADE)
    has_thin_value = bool(tags & _BLUFF_LAYER_THIN_VALUE)
    has_medium_showdown = bool(tags & _BLUFF_LAYER_MEDIUM_SHOWDOWN)
    has_strong_draw = bool(tags & _BLUFF_LAYER_STRONG_DRAWS)
    has_weak_draw = bool(tags & _BLUFF_LAYER_WEAK_DRAWS)
    has_blocker = bool(tags & _BLUFF_LAYER_BLOCKERS)
    has_high_card = bool(tags & _BLUFF_LAYER_HIGH_CARDS)
    has_air = "air" in tags or not (has_strong_made or has_thin_value or has_medium_showdown or has_strong_draw or has_weak_draw or has_blocker or has_high_card)

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
        if facing_bet:
            hero_bucket = "BLUFF_CATCHER"
            selected_reason = "showdown value facing bet"
        else:
            hero_bucket = "SHOWDOWN_CHECK"
            selected_reason = "showdown value prefers pot control"
        showdown_value = "medium" if has_medium_showdown else "weak"
    else:
        hero_bucket = "GIVE_UP"
        showdown_value = "none"
        selected_reason = "no equity, no blocker, no showdown value"

    if official_profile:
        hero_bucket = str(official_profile.get("hero_bucket") or hero_bucket).upper()
        made_hand_class = str(official_profile.get("made_hand_class") or made_hand_class)
        draw_class = str(official_profile.get("draw_class") or draw_class)
        blocker_class = str(official_profile.get("blocker_class") or blocker_class)
        showdown_value = str(official_profile.get("showdown_value") or showdown_value)
        selected_reason = str(official_profile.get("selected_reason") or selected_reason)
        profile_board_texture = official_profile.get("board_texture")
        if isinstance(profile_board_texture, (list, tuple, set)):
            board_texture = sorted(str(tag) for tag in profile_board_texture if str(tag))

    bet_size_profile = _facing_bet_size_profile(
        pot_before_hero=float(pot_before_hero or 0.0),
        to_call=float(to_call or 0.0),
    )
    river_blocker_calibration = _build_river_blocker_bluff_calibration(
        hero_bucket=hero_bucket,
        hero_tags=tags,
        street=street,
        facing_bet=facing_bet,
        hero_in_position=bool(hero_in_position),
        player_count=int(player_count or 2),
        line_context=ctx,
        spr=spr,
        bet_size_bucket=str(bet_size_profile.get("bet_size_bucket") or "none"),
    )
    multiway_calibration = _build_multiway_bluff_strict_calibration(
        hero_bucket=hero_bucket,
        hero_tags=tags,
        street=street,
        facing_bet=facing_bet,
        hero_in_position=bool(hero_in_position),
        player_count=int(player_count or 2),
        line_context=ctx,
        spr=spr,
        bet_size_bucket=str(bet_size_profile.get("bet_size_bucket") or "none"),
    )

    forbidden_reasons: list[str] = []
    if multiway and hero_bucket in {"BLOCKER_BLUFF", "GIVE_UP"}:
        forbidden_reasons.append("multiway_no_air_or_blocker_bluff")
    if multiway and hero_bucket == "SEMI_BLUFF" and not has_strong_draw:
        forbidden_reasons.append("multiway_requires_strong_draw")
    if street == "river" and hero_bucket in {"SEMI_BLUFF", "GIVE_UP"}:
        forbidden_reasons.append("river_no_equity_bluff_without_blocker")
    if street == "river" and hero_bucket == "BLOCKER_BLUFF" and not has_blocker:
        forbidden_reasons.append("river_bluff_requires_blocker")
    if not bool(hero_in_position) and hero_bucket in {"BLOCKER_BLUFF", "GIVE_UP"}:
        forbidden_reasons.append("oop_pure_bluff_restricted")
    if bool(ctx.get("prior_aggression")) and hero_bucket in {"BLOCKER_BLUFF", "GIVE_UP"}:
        forbidden_reasons.append("prior_aggression_reduces_fold_equity")
    if spr is not None and float(spr) <= 1.5 and hero_bucket in {"BLOCKER_BLUFF", "GIVE_UP"}:
        forbidden_reasons.append("low_spr_bluff_restricted")
    if bool(river_blocker_calibration.get("applies")):
        if facing_bet:
            forbidden_reasons.extend(list(river_blocker_calibration.get("raise_forbidden_reasons") or []))
        elif not bool(river_blocker_calibration.get("allow_bet")):
            forbidden_reasons.extend(list(river_blocker_calibration.get("bet_forbidden_reasons") or []))
        selected_reason = str(river_blocker_calibration.get("selected_reason") or selected_reason)
    if bool(multiway_calibration.get("applies")):
        if facing_bet:
            # Facing-bet call/fold is enforced by facing_bet_layer; top-level
            # reasons here stay aggression-focused to avoid accidentally making
            # a valid multiway call illegal.
            forbidden_reasons.extend(list(multiway_calibration.get("raise_forbidden_reasons") or []))
        elif not bool(multiway_calibration.get("allow_bet")):
            forbidden_reasons.extend(list(multiway_calibration.get("bet_forbidden_reasons") or []))
        selected_reason = str(multiway_calibration.get("selected_reason") or selected_reason)

    facing_bet_layer: Dict[str, object] = {
        "contract_version": "facing_bet_layer_v1",
        "enabled": False,
        "reason": "not_facing_bet",
    }
    if facing_bet:
        facing_bet_layer = _build_facing_bet_layer_profile(
            hero_bucket=hero_bucket,
            hero_tags=tags,
            street=street,
            pot_before_hero=float(pot_before_hero or 0.0),
            to_call=float(to_call or 0.0),
            hero_in_position=bool(hero_in_position),
            player_count=int(player_count or 2),
            line_context=line_context,
            spr=spr,
            call_equity=float(call_equity or 0.0),
        )

    allow_bet_debug = not facing_bet and hero_bucket in {"VALUE", "THIN_VALUE", "SEMI_BLUFF", "BLOCKER_BLUFF"} and not forbidden_reasons
    allow_raise_debug = facing_bet and hero_bucket in {"VALUE", "SEMI_BLUFF", "BLOCKER_BLUFF"} and not forbidden_reasons
    allow_call_debug = facing_bet and hero_bucket in {"VALUE", "THIN_VALUE", "SEMI_BLUFF", "BLUFF_CATCHER", "SHOWDOWN_CHECK"}
    if bool(multiway_calibration.get("applies")):
        if not facing_bet:
            allow_bet_debug = allow_bet_debug and bool(multiway_calibration.get("allow_bet"))
        allow_raise_debug = allow_raise_debug and bool(multiway_calibration.get("allow_raise"))
        if facing_bet:
            allow_call_debug = allow_call_debug and bool(multiway_calibration.get("allow_call"))
    if facing_bet and bool(facing_bet_layer.get("enabled")):
        allow_raise_debug = bool(facing_bet_layer.get("allow_raise"))
        allow_call_debug = bool(facing_bet_layer.get("allow_call"))
        if bool(multiway_calibration.get("applies")):
            allow_raise_debug = allow_raise_debug and bool(multiway_calibration.get("allow_raise"))
            allow_call_debug = allow_call_debug and bool(multiway_calibration.get("allow_call"))

    if hero_bucket == "VALUE":
        preferred_size_pct = 70.0 if ("board_wet_connected" in tags or "board_monotone" in tags or street == "river") else 50.0
    elif hero_bucket == "THIN_VALUE":
        preferred_size_pct = 33.0
    elif hero_bucket == "SEMI_BLUFF":
        preferred_size_pct = 50.0 if street == "flop" else 70.0
    elif hero_bucket == "BLOCKER_BLUFF":
        calibrated_size = river_blocker_calibration.get("preferred_size_pct") if bool(river_blocker_calibration.get("applies")) else None
        if calibrated_size is not None:
            try:
                preferred_size_pct = float(calibrated_size)
            except (TypeError, ValueError):
                preferred_size_pct = 70.0 if street == "river" else 33.0
        else:
            preferred_size_pct = 70.0 if street == "river" else 33.0
    else:
        preferred_size_pct = None

    if official_profile and official_profile.get("preferred_size_pct") is not None:
        try:
            preferred_size_pct = float(official_profile.get("preferred_size_pct"))
        except (TypeError, ValueError):
            pass
    if bool(multiway_calibration.get("applies")) and multiway_calibration.get("preferred_size_pct") is not None:
        try:
            preferred_size_pct = float(multiway_calibration.get("preferred_size_pct"))
        except (TypeError, ValueError):
            pass
    if hero_bucket == "BLOCKER_BLUFF" and bool(river_blocker_calibration.get("applies")):
        calibrated_size = river_blocker_calibration.get("preferred_size_pct")
        if calibrated_size is not None:
            try:
                preferred_size_pct = float(calibrated_size)
            except (TypeError, ValueError):
                pass

    selected_action = None if best_option is None else best_option.get("action")
    selected_size_pct = None if best_option is None else best_option.get("size_pct")
    selected_gate_status = None if best_option is None else best_option.get("gate_status")

    return {
        "contract_version": "bluff_layer_debug_v1",
        "decision_influence": "debug_only_no_action_override",
        "hero_bucket": hero_bucket,
        "made_hand_class": made_hand_class,
        "draw_class": draw_class,
        "blocker_class": blocker_class,
        "showdown_value": showdown_value,
        "board_texture": board_texture,
        "hero_tags": tuple(sorted(tags)),
        "hero_profile_source": official_profile.get("source"),
        "hero_profile_contract_version": official_profile.get("contract_version"),
        "street": street,
        "position_context": "IP" if bool(hero_in_position) else "OOP",
        "is_multiway": multiway,
        "player_count": int(player_count or 0),
        "facing_bet": facing_bet,
        "facing_bet_layer": dict(facing_bet_layer),
        "river_blocker_bluff_calibration": dict(river_blocker_calibration),
        "multiway_bluff_strict_calibration": dict(multiway_calibration),
        "spot_type": spot_type,
        "spr": None if spr is None else float(spr),
        "raw_equity": float(raw_equity),
        "realized_equity": float(realized_equity),
        "call_equity": float(call_equity),
        # Public gate fields expected by render/debug/test consumers.
        # Keep the *_debug aliases for backward compatibility with older code paths.
        "allow_bet": bool(allow_bet_debug),
        "allow_raise": bool(allow_raise_debug),
        "allow_call": bool(allow_call_debug),
        "allow_bet_debug": bool(allow_bet_debug),
        "allow_raise_debug": bool(allow_raise_debug),
        "allow_call_debug": bool(allow_call_debug),
        "preferred_size_pct": preferred_size_pct,
        "forbidden_reasons": list(dict.fromkeys(forbidden_reasons)),
        "selected_reason": selected_reason,
        "current_solver_choice": {
            "action": selected_action,
            "size_pct": selected_size_pct,
            "gate_status": selected_gate_status,
        },
    }

def _bluff_layer_soft_gate_required(bluff_layer: Dict[str, object], mode: str) -> tuple[bool, list[str]]:
    """Return whether an aggressive option must be vetoed by Bluff Layer v2.

    Step 2 is intentionally conservative: it only blocks aggression that is
    clearly a bad bluff candidate.  It never vetoes fold/check/call and it never
    downgrades clear VALUE or THIN_VALUE buckets.
    """
    profile = {} if bluff_layer is None else dict(bluff_layer)
    bucket = str(profile.get("hero_bucket") or "").upper()
    reasons = [str(item) for item in list(profile.get("forbidden_reasons") or [])]
    mode = str(mode or "").lower()

    if mode not in {"bet", "raise"}:
        return False, []
    if bucket in {"VALUE", "THIN_VALUE"}:
        return False, []

    veto_reasons: list[str] = []

    # Pure give-up hands should not be turned into automatic aggression.
    if bucket == "GIVE_UP":
        veto_reasons.append("bluff_layer_give_up_no_aggression")

    # Showdown hands should not be converted into a bluff at this step.
    if bucket in {"SHOWDOWN_CHECK", "BLUFF_CATCHER"}:
        veto_reasons.append("bluff_layer_showdown_value_no_bluff")

    # Semi-bluffs and blocker bluffs are allowed only if the debug profile says
    # the current context is clean enough for that aggressive mode.
    if mode == "bet" and bucket in {"SEMI_BLUFF", "BLOCKER_BLUFF"} and not bool(profile.get("allow_bet_debug")):
        veto_reasons.append("bluff_layer_bet_not_allowed")
    if mode == "raise" and bucket in {"SEMI_BLUFF", "BLOCKER_BLUFF"} and not bool(profile.get("allow_raise_debug")):
        veto_reasons.append("bluff_layer_raise_not_allowed")

    veto_reasons.extend(reasons)
    deduped: list[str] = []
    seen: set[str] = set()
    for reason in veto_reasons:
        if not reason or reason in seen:
            continue
        seen.add(reason)
        deduped.append(reason)
    return bool(deduped), deduped


def _apply_bluff_layer_soft_gates(
    *,
    bluff_layer: Dict[str, object],
    options: List[Dict[str, object]],
    size_reports: List[Dict[str, object]],
    passive_reference_ev: float,
    pot_before_hero: float,
) -> Dict[str, object]:
    """Soft-veto bad bluff aggression before the final option is selected.

    Only bet_* / raise_* options can be vetoed.  Passive options stay untouched.
    This keeps Step 2 safe: it blocks bad bluffs but does not invent new actions.
    """
    penalty_floor = max(0.50, 0.35 * float(pot_before_hero or 0.0))
    vetoed_actions: list[str] = []
    veto_reasons_by_action: dict[str, list[str]] = {}

    def _apply_to_item(item: Dict[str, object]) -> None:
        mode = str(item.get("mode") or item.get("kind") or "").lower()
        action = str(item.get("action") or "")
        should_veto, reasons = _bluff_layer_soft_gate_required(bluff_layer, mode)
        if not should_veto:
            item.setdefault("bluff_layer_gate_status", "not_applied")
            return
        item["bluff_layer_gate_status"] = "vetoed"
        item["bluff_layer_gate_reasons"] = list(reasons)
        item["gate_status"] = "vetoed"
        try:
            current_ev = float(item.get("ev", passive_reference_ev))
        except (TypeError, ValueError):
            current_ev = float(passive_reference_ev)
        item["ev_before_bluff_layer_gate"] = current_ev
        item["ev"] = min(current_ev, float(passive_reference_ev) - penalty_floor)
        if action:
            vetoed_actions.append(action)
            veto_reasons_by_action[action] = list(reasons)

    for item in size_reports:
        _apply_to_item(item)
    for item in options:
        mode = str(item.get("mode") or item.get("kind") or "").lower()
        if mode in {"bet", "raise"}:
            _apply_to_item(item)

    unique_actions: list[str] = []
    seen_actions: set[str] = set()
    for action in vetoed_actions:
        if action in seen_actions:
            continue
        seen_actions.add(action)
        unique_actions.append(action)

    return {
        "contract_version": "bluff_layer_soft_gates_v1",
        "enabled": True,
        "scope": "aggressive_options_only",
        "veto_count": len(unique_actions),
        "vetoed_actions": unique_actions,
        "veto_reasons_by_action": veto_reasons_by_action,
    }



def _option_action_name(option: Optional[Dict[str, object]]) -> str:
    if not option:
        return ""
    return str(option.get("action") or "").lower()


def _option_mode(option: Optional[Dict[str, object]]) -> str:
    if not option:
        return ""
    mode = str(option.get("mode") or option.get("kind") or "").lower()
    action = _option_action_name(option)
    if action in {"check", "fold", "call"}:
        return action
    if mode in {"bet", "raise"}:
        return mode
    if action.startswith("bet_"):
        return "bet"
    if action.startswith("raise_"):
        return "raise"
    if mode == "passive":
        return action or mode
    return mode


def _option_size_pct(option: Optional[Dict[str, object]]) -> Optional[float]:
    if not option:
        return None
    value = option.get("size_pct")
    if value is None:
        action = _option_action_name(option)
        if "_" in action:
            try:
                return float(action.split("_", 1)[1])
            except (TypeError, ValueError):
                return None
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _option_is_eligible(option: Dict[str, object]) -> bool:
    if not bool(option.get("legal", True)):
        return False
    if str(option.get("gate_status", "allowed")).lower() == "vetoed":
        return False
    if str(option.get("bluff_layer_gate_status", "")).lower() == "vetoed":
        return False
    return True


def _find_option_by_action(options: Sequence[Dict[str, object]], action: str) -> Optional[Dict[str, object]]:
    wanted = str(action or "").lower()
    for option in options:
        if _option_action_name(option) == wanted and _option_is_eligible(option):
            return option
    return None


def _bluff_layer_size_gate_required(bluff_layer: Dict[str, object], option: Optional[Dict[str, object]]) -> tuple[bool, list[str]]:
    profile = {} if bluff_layer is None else dict(bluff_layer)
    bucket = str(profile.get("hero_bucket") or "").upper()
    street = str(profile.get("street") or "").lower()
    mode = _option_mode(option)
    size = _option_size_pct(option)
    reasons: list[str] = []

    if mode not in {"bet", "raise"} or size is None:
        return False, []

    is_multiway = bool(profile.get("is_multiway"))
    if bucket == "THIN_VALUE" and size > 50.0:
        reasons.append("thin_value_size_above_50_blocked")
    if is_multiway and bucket == "THIN_VALUE" and size > 33.0:
        reasons.append("multiway_thin_value_size_above_33_blocked")
    if is_multiway and bucket == "BLOCKER_BLUFF":
        reasons.append("multiway_blocker_bluff_no_sizing")
    if bucket == "SEMI_BLUFF" and street == "river":
        reasons.append("river_semi_bluff_blocked")
    if bucket == "BLOCKER_BLUFF" and size > 70.0:
        reasons.append("blocker_bluff_size_above_70_blocked")
    if bucket in {"GIVE_UP", "SHOWDOWN_CHECK", "BLUFF_CATCHER"}:
        reasons.append(f"{bucket.lower()}_no_aggression")

    return bool(reasons), reasons


def _bluff_layer_action_gate_required(bluff_layer: Dict[str, object], option: Optional[Dict[str, object]]) -> tuple[bool, list[str]]:
    profile = {} if bluff_layer is None else dict(bluff_layer)
    mode = _option_mode(option)
    action = _option_action_name(option)
    bucket = str(profile.get("hero_bucket") or "").upper()
    reasons = [str(item) for item in list(profile.get("forbidden_reasons") or []) if str(item)]
    facing_bet = bool(profile.get("facing_bet"))
    facing_layer_raw = profile.get("facing_bet_layer")
    facing_layer = dict(facing_layer_raw) if isinstance(facing_layer_raw, dict) else {}

    gate_reasons: list[str] = []
    if mode == "bet" and not bool(profile.get("allow_bet", profile.get("allow_bet_debug", False))):
        gate_reasons.append("bluff_layer_bet_not_allowed")
    if mode == "raise" and not bool(profile.get("allow_raise", profile.get("allow_raise_debug", False))):
        gate_reasons.append("bluff_layer_raise_not_allowed")
    if action == "call" and not bool(profile.get("allow_call", profile.get("allow_call_debug", False))):
        gate_reasons.append("bluff_layer_call_not_allowed")

    if facing_bet and bool(facing_layer.get("enabled")):
        if action == "fold" and not bool(facing_layer.get("allow_fold", True)):
            gate_reasons.extend(str(item) for item in list(facing_layer.get("fold_forbidden_reasons") or []) if str(item))
            gate_reasons.append("facing_bet_layer_fold_not_allowed")
        if action == "call" and not bool(facing_layer.get("allow_call", False)):
            gate_reasons.extend(str(item) for item in list(facing_layer.get("call_forbidden_reasons") or []) if str(item))
            gate_reasons.append("facing_bet_layer_call_not_allowed")
        if mode == "raise" and not bool(facing_layer.get("allow_raise", False)):
            gate_reasons.extend(str(item) for item in list(facing_layer.get("raise_forbidden_reasons") or []) if str(item))
            gate_reasons.append("facing_bet_layer_raise_not_allowed")

    if mode in {"bet", "raise"} and bucket in {"GIVE_UP", "SHOWDOWN_CHECK", "BLUFF_CATCHER"}:
        gate_reasons.append(f"{bucket.lower()}_no_aggression")

    # Generic bluff-forbidden reasons are aggression gates. They should not make
    # passive fold/check illegal, but they can still block call when the bucket is
    # a low-equity bluff candidate versus a bet.
    if mode in {"bet", "raise"} or action == "call":
        gate_reasons.extend(reasons)

    deduped: list[str] = []
    seen: set[str] = set()
    for reason in gate_reasons:
        if not reason or reason in seen:
            continue
        seen.add(reason)
        deduped.append(reason)
    return bool(deduped), deduped


def _apply_facing_bet_layer_gates(
    *,
    bluff_layer: Dict[str, object],
    options: List[Dict[str, object]],
    size_reports: List[Dict[str, object]],
    passive_reference_ev: float,
    pot_before_hero: float,
    to_call: float,
) -> Dict[str, object]:
    profile = {} if bluff_layer is None else dict(bluff_layer)
    facing_layer_raw = profile.get("facing_bet_layer")
    facing_layer = dict(facing_layer_raw) if isinstance(facing_layer_raw, dict) else {}
    if not bool(facing_layer.get("enabled")) or float(to_call or 0.0) <= 0.0:
        return {
            "contract_version": "facing_bet_layer_gate_v1",
            "enabled": False,
            "reason": "not_facing_bet",
            "vetoed_actions": [],
            "restored_actions": [],
        }

    penalty_floor = max(0.50, 0.35 * float(pot_before_hero or 0.0), 0.90 * float(to_call or 0.0))
    passive_ev = float(passive_reference_ev or 0.0)
    allow_call = bool(facing_layer.get("allow_call"))
    allow_raise = bool(facing_layer.get("allow_raise"))
    allow_fold = bool(facing_layer.get("allow_fold", True))
    preferred_passive_action = str(facing_layer.get("preferred_passive_action") or "fold").lower()
    bucket = str(facing_layer.get("hero_bucket") or profile.get("hero_bucket") or "").upper()

    vetoed_actions: list[str] = []
    restored_actions: list[str] = []
    reasons_by_action: dict[str, list[str]] = {}

    def _dedupe(items: Sequence[object]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            value = str(item)
            if not value or value in seen:
                continue
            seen.add(value)
            out.append(value)
        return out

    def _veto(item: Dict[str, object], reasons: Sequence[object]) -> None:
        action = _option_action_name(item)
        if not action:
            return
        deduped = _dedupe(reasons)
        item["facing_bet_layer_gate_status"] = "vetoed"
        item["facing_bet_layer_gate_reasons"] = deduped
        item["gate_status"] = "vetoed"
        try:
            current_ev = float(item.get("ev", passive_ev))
        except (TypeError, ValueError):
            current_ev = passive_ev
        item["ev_before_facing_bet_layer_gate"] = current_ev
        item["ev"] = min(current_ev, passive_ev - penalty_floor)
        vetoed_actions.append(action)
        reasons_by_action[action] = deduped

    def _restore_call(item: Dict[str, object]) -> None:
        action = _option_action_name(item)
        if action != "call":
            return
        try:
            current_ev = float(item.get("ev", passive_ev))
        except (TypeError, ValueError):
            current_ev = passive_ev
        item["facing_bet_layer_gate_status"] = "allowed"
        item["facing_bet_layer_gate_reasons"] = []
        if str(item.get("gate_status", "allowed")).lower() == "vetoed":
            item["gate_status_before_facing_bet_layer_restore"] = "vetoed"
            restored_actions.append(action)
        item["gate_status"] = "allowed"
        bonus = 0.01
        if bucket == "VALUE":
            bonus = max(0.03, 0.02 * float(to_call or 0.0))
        elif preferred_passive_action == "call":
            bonus = max(0.01, 0.005 * float(to_call or 0.0))
        item["ev_before_facing_bet_layer_floor"] = current_ev
        item["ev"] = max(current_ev, passive_ev + bonus)

    def _apply(item: Dict[str, object]) -> None:
        action = _option_action_name(item)
        mode = _option_mode(item)
        if action == "fold" and not allow_fold:
            _veto(item, list(facing_layer.get("fold_forbidden_reasons") or []) + ["facing_bet_layer_fold_not_allowed"])
            return
        if action == "call":
            if allow_call:
                _restore_call(item)
            else:
                _veto(item, list(facing_layer.get("call_forbidden_reasons") or []) + ["facing_bet_layer_call_not_allowed"])
            return
        if mode == "raise":
            if allow_raise:
                item.setdefault("facing_bet_layer_gate_status", "allowed")
            else:
                _veto(item, list(facing_layer.get("raise_forbidden_reasons") or []) + ["facing_bet_layer_raise_not_allowed"])

    for item in options:
        _apply(item)
    for item in size_reports:
        if _option_mode(item) == "raise":
            _apply(item)

    unique_vetoed: list[str] = []
    seen_vetoed: set[str] = set()
    for action in vetoed_actions:
        if action in seen_vetoed:
            continue
        seen_vetoed.add(action)
        unique_vetoed.append(action)

    unique_restored: list[str] = []
    seen_restored: set[str] = set()
    for action in restored_actions:
        if action in seen_restored:
            continue
        seen_restored.add(action)
        unique_restored.append(action)

    return {
        "contract_version": "facing_bet_layer_gate_v1",
        "enabled": True,
        "hero_bucket": bucket,
        "bet_size_bucket": facing_layer.get("bet_size_bucket"),
        "bet_pct_pot": facing_layer.get("bet_pct_pot"),
        "preferred_passive_action": preferred_passive_action,
        "allow_call": allow_call,
        "allow_raise": allow_raise,
        "allow_fold": allow_fold,
        "veto_count": len(unique_vetoed),
        "vetoed_actions": unique_vetoed,
        "restored_actions": unique_restored,
        "veto_reasons_by_action": reasons_by_action,
    }


def _find_sizing_downgrade_option(
    *,
    bluff_layer: Dict[str, object],
    original_option: Dict[str, object],
    options: Sequence[Dict[str, object]],
) -> Optional[Dict[str, object]]:
    mode = _option_mode(original_option)
    if mode not in {"bet", "raise"}:
        return None
    original_size = _option_size_pct(original_option)
    preferred = bluff_layer.get("preferred_size_pct")
    try:
        preferred_size = float(preferred) if preferred is not None else None
    except (TypeError, ValueError):
        preferred_size = None

    candidates: list[Dict[str, object]] = []
    for option in options:
        if not _option_is_eligible(option):
            continue
        if _option_mode(option) != mode:
            continue
        size = _option_size_pct(option)
        if size is None:
            continue
        if original_size is not None and size >= original_size:
            continue
        action_blocked, _ = _bluff_layer_action_gate_required(bluff_layer, option)
        size_blocked, _ = _bluff_layer_size_gate_required(bluff_layer, option)
        if action_blocked or size_blocked:
            continue
        candidates.append(option)

    if not candidates:
        return None

    if preferred_size is not None:
        candidates.sort(key=lambda opt: (abs((_option_size_pct(opt) or 0.0) - preferred_size), -float(opt.get("ev", 0.0))))
    else:
        candidates.sort(key=lambda opt: (-float(opt.get("ev", 0.0)), -(_option_size_pct(opt) or 0.0)))
    return candidates[0]


def _apply_bluff_layer_gates(
    *,
    bluff_layer: Dict[str, object],
    best_option: Dict[str, object],
    options: Sequence[Dict[str, object]],
    to_call: float,
) -> tuple[Dict[str, object], Dict[str, object]]:
    original = dict(best_option)
    original_action = _option_action_name(original)
    final_option = dict(best_option)
    reasons: list[str] = []

    action_blocked, action_reasons = _bluff_layer_action_gate_required(bluff_layer, original)
    size_blocked, size_reasons = _bluff_layer_size_gate_required(bluff_layer, original)
    reasons.extend(action_reasons)
    reasons.extend(size_reasons)

    replacement: Optional[Dict[str, object]] = None
    if size_blocked and _option_mode(original) in {"bet", "raise"}:
        replacement = _find_sizing_downgrade_option(
            bluff_layer=bluff_layer,
            original_option=original,
            options=options,
        )
        if replacement is not None:
            final_option = dict(replacement)

    if replacement is None and (action_blocked or size_blocked):
        mode = _option_mode(original)
        if mode == "bet":
            replacement = _find_option_by_action(options, "check")
        elif mode == "raise":
            if bool(bluff_layer.get("allow_call", bluff_layer.get("allow_call_debug", False))):
                replacement = _find_option_by_action(options, "call")
            if replacement is None:
                replacement = _find_option_by_action(options, "fold")
        elif mode == "call":
            replacement = _find_option_by_action(options, "fold")
        elif original_action == "fold" and float(to_call or 0.0) > 0:
            if bool(bluff_layer.get("allow_call", bluff_layer.get("allow_call_debug", False))):
                replacement = _find_option_by_action(options, "call")
            if replacement is None:
                replacement = _find_option_by_action(options, "fold")
        else:
            replacement = _find_option_by_action(options, "check" if float(to_call or 0.0) <= 0 else "fold")
        if replacement is not None:
            final_option = dict(replacement)

    # Final safety net if an expected passive action was not found.
    if action_blocked or size_blocked:
        final_mode = _option_mode(final_option)
        final_action_blocked, final_action_reasons = _bluff_layer_action_gate_required(bluff_layer, final_option)
        final_size_blocked, final_size_reasons = _bluff_layer_size_gate_required(bluff_layer, final_option)
        if final_action_blocked or final_size_blocked:
            passive_name = "check" if float(to_call or 0.0) <= 0 else "fold"
            passive = _find_option_by_action(options, passive_name)
            if passive is not None:
                final_option = dict(passive)
                reasons.extend(final_action_reasons)
                reasons.extend(final_size_reasons)

    deduped: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        if not reason or reason in seen:
            continue
        seen.add(reason)
        deduped.append(reason)

    final_action = _option_action_name(final_option)
    status = "allowed" if final_action == original_action and not deduped else "downgraded"
    gate = {
        "contract_version": "bluff_layer_final_gates_v1",
        "enabled": True,
        "status": status,
        "original_action": original_action,
        "final_action": final_action,
        "reasons": deduped,
        "bucket": str(bluff_layer.get("hero_bucket") or ""),
    }
    if final_action != original_action:
        gate["replacement_action"] = final_action
        gate["replacement_size_pct"] = _option_size_pct(final_option)

    return final_option, gate


def solve_hero_decision(
    *,
    hero_hand: Sequence[CardLike],
    board: Sequence[CardLike] | None = None,
    pot_before_hero: float,
    to_call: float = 0.0,
    effective_stack: float | None = None,
    hero_in_position: bool,
    range_sources: Optional[Sequence[RangeSource]] = None,
    villain_ranges: Optional[Sequence[RangeInput]] = None,
    villain_preflop_spots: Optional[Sequence[Dict[str, object]]] = None,
    bet_sizes_pct: Sequence[float] = DEFAULT_BET_SIZES_PCT,
    assumed_fold_probs_by_size: Optional[Dict[float, float]] = None,
    line_context: Optional[Dict[str, object]] = None,
    dead_cards: Iterable[CardLike] | None = None,
    trials: int = 6000,
    seed: int | None = None,
) -> Dict[str, object]:
    hero = [card_to_str(c) if isinstance(c, int) else str(c) for c in hero_hand]
    board_cards = [] if board is None else [card_to_str(c) if isinstance(c, int) else str(c) for c in board]
    dead = [] if dead_cards is None else [card_to_str(c) if isinstance(c, int) else str(c) for c in dead_cards]

    if range_sources is None and villain_ranges is None and villain_preflop_spots is None:
        raise ValueError("Нужно передать range_sources, villain_ranges или villain_preflop_spots")

    if range_sources is not None:
        range_sources = [_clone_range_source(src) for src in range_sources]
    elif villain_preflop_spots is not None:
        range_sources = build_villain_ranges_from_preflop_spots(villain_preflop_spots)
    else:
        range_sources = []
        for index, vr in enumerate(villain_ranges or [], start=1):
            raw_expr = vr if isinstance(vr, str) else None
            normalized = None
            if isinstance(vr, str):
                try:
                    normalized = normalize_range_for_equity(vr)
                except Exception:
                    normalized = None
            weighted = _parse_range_flex(vr, blocked_cards=hero + board_cards + dead)
            range_sources.append(
                RangeSource(
                    name=f"Villain{index}",
                    source_type="direct_input",
                    raw_expr=raw_expr,
                    normalized_expr=normalized,
                    weighted_combos=weighted,
                    meta={},
                )
            )

    hero_profile = _build_hero_postflop_profile_bridge(
        hero,
        board_cards,
        facing_bet=float(to_call or 0.0) > 0.0,
    )
    if hero_profile and isinstance(hero_profile.get("hero_tags"), (list, tuple, set)):
        hero_tags = {str(tag) for tag in hero_profile.get("hero_tags") or [] if str(tag)}
    else:
        hero_tags = _hero_postflop_tags(hero, board_cards)
    range_sources, dropped_range_sources = _sanitize_range_sources_for_equity(range_sources)
    if not range_sources:
        return _build_passive_fallback_report(
            hero=hero,
            board_cards=board_cards,
            pot_before_hero=float(pot_before_hero),
            to_call=float(to_call),
            effective_stack=effective_stack,
            hero_in_position=bool(hero_in_position),
            line_context=line_context,
            hero_tags=hero_tags,
            reason="no_valid_villain_ranges",
            range_sources=range_sources,
            dropped_range_sources=dropped_range_sources,
        )

    player_count = len(range_sources) + 1
    street = _street_from_board(board_cards)
    spr = calculate_spr(effective_stack, pot_before_hero)
    try:
        raw_multiway = compute_multiway_hero_equity(
            hero_hand=hero,
            villain_ranges=[src.weighted_combos for src in range_sources],
            board=board_cards,
            dead_cards=dead,
            trials=trials,
            seed=seed,
        )
    except (RuntimeError, ValueError) as exc:
        return _build_passive_fallback_report(
            hero=hero,
            board_cards=board_cards,
            pot_before_hero=float(pot_before_hero),
            to_call=float(to_call),
            effective_stack=effective_stack,
            hero_in_position=bool(hero_in_position),
            line_context=line_context,
            hero_tags=hero_tags,
            reason=f"multiway_equity_unavailable:{exc}",
            range_sources=range_sources,
            dropped_range_sources=dropped_range_sources,
        )
    raw_equity = float(raw_multiway["hero_equity"])
    realization_factor = estimate_realization_factor(
        street=street,
        hero_in_position=hero_in_position,
        player_count=player_count,
        spr=spr,
    )
    line_adj = build_line_adjustments(line_context, player_count=player_count)
    spot_type = _infer_spot_type(street=street, hero_in_position=bool(hero_in_position), to_call=float(to_call), line_context=line_context)
    hero_has_initiative = _hero_has_initiative(line_context)
    realized_equity = max(0.0, min(1.0, raw_equity * realization_factor))
    call_equity = max(0.0, min(1.0, realized_equity - line_adj["call_penalty"]))

    normalized_fe_inputs = _normalize_fe_assumptions(assumed_fold_probs_by_size)
    passive_ev = 0.0 if float(to_call) > 0 else _estimate_check_ev(
        pot_before_hero=float(pot_before_hero),
        realized_equity=realized_equity,
        hero_tags=hero_tags,
        street=street,
        hero_in_position=bool(hero_in_position),
        player_count=player_count,
        line_context=line_context,
        spot_type=spot_type,
    )

    passive_action = "fold" if float(to_call) > 0 else "check"
    options: List[Dict[str, object]] = [{
        "action": passive_action,
        "ev": passive_ev,
        "legal": True,
        "kind": "passive",
        "gate_status": "baseline",
    }]

    call_threshold = 0.0
    hard_call_gate = {"allowed": True, "required_equity": 0.0, "margin": 0.0, "equity_used": call_equity}
    safety_margin = _safety_margin_vs_passive(street=street, pot_before_hero=float(pot_before_hero), line_adjustments=line_adj)
    passive_reference_ev = passive_ev

    if float(to_call) > 0:
        call_threshold = calculate_call_equity_threshold(pot_before_hero, to_call)
        hard_call_gate = _hard_call_gate(
            street=street,
            call_equity=call_equity,
            call_threshold=call_threshold,
            player_count=player_count,
            facing_raise=bool((line_context or {}).get("facing_raise")),
            hero_tags=hero_tags,
        )
        call_ev = ev_call(pot_before_hero, to_call, call_equity)
        call_ev_advantage = call_ev - passive_reference_ev
        call_safety_pass = call_ev_advantage >= safety_margin
        if not hard_call_gate["allowed"]:
            call_ev -= max(0.50 * float(pot_before_hero), float(to_call))
        if not call_safety_pass:
            call_ev -= max(0.30 * float(pot_before_hero), safety_margin)
        options.append(
            {
                "action": "call",
                "ev": call_ev,
                "legal": True,
                "kind": "passive",
                "equity_threshold": call_threshold,
                "equity_used": call_equity,
                "hard_call_gate": dict(hard_call_gate),
                "safety_margin_required": safety_margin,
                "safety_margin_passed": call_safety_pass,
                "gate_status": "allowed" if hard_call_gate["allowed"] and call_safety_pass else "vetoed",
            }
        )

    size_reports: List[Dict[str, object]] = []
    for size_pct in bet_sizes_pct:
        frac = _size_pct_to_fraction(size_pct)
        label = int(round(float(size_pct) if float(size_pct) > 10 else frac * 100))
        if float(to_call) > 0:
            raise_extra = float(pot_before_hero) * frac
            risk = float(to_call) + raise_extra
            zero_fe = calculate_zero_fe_for_raise(pot_before_hero, risk)
            req_fe = calculate_required_fe_raise(pot_before_hero, to_call, raise_extra, realized_equity)
            assumed_fe = normalized_fe_inputs.get(float(size_pct), normalized_fe_inputs.get(float(label), zero_fe))
            raise_fe_mod = _hero_raise_fe_modifier(hero_tags, street=street, hero_in_position=hero_in_position, player_count=player_count, line_context=line_context)
            assumed_fe = max(0.0, min(0.99, assumed_fe * line_adj["fe_multiplier"] * raise_fe_mod))
            raise_allowed = _hero_raise_allowed(hero_tags, street=street, hero_in_position=hero_in_position, to_call=float(to_call), line_context=line_context)
            hard_raise_gate = _hard_raise_gate(hero_tags=hero_tags, street=street, assumed_fe=assumed_fe, required_fe=req_fe, spr=spr, line_context=line_context)
            ev_value = ev_raise(pot_before_hero, to_call, raise_extra, assumed_fe, realized_equity)
            caution_penalty = _raise_caution_penalty(
                hero_tags,
                street=street,
                hero_in_position=hero_in_position,
                player_count=player_count,
                to_call=float(to_call),
                line_context=line_context,
                pot_before_hero=float(pot_before_hero),
            )
            ev_value -= caution_penalty
            if not raise_allowed:
                ev_value -= max(0.45 * float(pot_before_hero), float(to_call) * 0.90)
            if not hard_raise_gate["allowed"]:
                ev_value -= max(0.40 * float(pot_before_hero), float(to_call) * 0.70)
            safety_pass = (ev_value - passive_reference_ev) >= safety_margin
            if not safety_pass:
                ev_value -= max(0.25 * float(pot_before_hero), safety_margin)
            action_name = f"raise_{label}"
            size_report = {
                "action": action_name,
                "size_pct": float(label),
                "mode": "raise",
                "risk": risk,
                "raise_extra": raise_extra,
                "zero_fe": zero_fe,
                "required_fe": req_fe,
                "assumed_fe": assumed_fe,
                "equity_used": realized_equity,
                "hero_tags": tuple(sorted(hero_tags)),
                "raise_allowed": raise_allowed,
                "hard_raise_gate": dict(hard_raise_gate),
                "raise_fe_modifier": raise_fe_mod,
                "raise_caution_penalty": caution_penalty,
                "safety_margin_required": safety_margin,
                "safety_margin_passed": safety_pass,
                "gate_status": "allowed" if raise_allowed and hard_raise_gate["allowed"] and safety_pass else "vetoed",
                "amount_to": float(to_call) + raise_extra,
                "ev": ev_value,
            }
        else:
            bet_amount = float(pot_before_hero) * frac
            zero_fe = calculate_zero_fe(size_pct)
            req_fe = calculate_required_fe_bet(pot_before_hero, bet_amount, realized_equity)
            assumed_fe = normalized_fe_inputs.get(float(size_pct), normalized_fe_inputs.get(float(label), zero_fe))
            bet_fe_mod = _hero_bet_fe_modifier(
                hero_tags,
                street=street,
                hero_in_position=bool(hero_in_position),
                player_count=player_count,
                line_context=line_context,
                spot_type=spot_type,
            )
            assumed_fe = max(0.0, min(0.99, assumed_fe * line_adj["fe_multiplier"] * bet_fe_mod))
            bet_allowed = _hero_bet_allowed(
                hero_tags,
                street=street,
                hero_in_position=bool(hero_in_position),
                to_call=float(to_call),
                line_context=line_context,
                spot_type=spot_type,
            )
            ev_value = ev_bet(pot_before_hero, bet_amount, assumed_fe, realized_equity)
            caution_penalty = _bet_caution_penalty(
                hero_tags,
                street=street,
                hero_in_position=bool(hero_in_position),
                player_count=player_count,
                line_context=line_context,
                pot_before_hero=float(pot_before_hero),
                spot_type=spot_type,
            )
            size_preference = _bet_size_preference_adjustment(
                hero_tags,
                street=street,
                hero_in_position=bool(hero_in_position),
                spot_type=spot_type,
                size_pct=float(label),
                pot_before_hero=float(pot_before_hero),
            )
            ev_value -= caution_penalty
            ev_value += size_preference
            if not bet_allowed:
                ev_value -= max(0.35 * float(pot_before_hero), 0.80 * bet_amount)
            safety_pass = (ev_value - passive_reference_ev) >= safety_margin
            if not safety_pass:
                ev_value -= max(0.22 * float(pot_before_hero), safety_margin)
            action_name = f"bet_{label}"
            size_report = {
                "action": action_name,
                "size_pct": float(label),
                "mode": "bet",
                "risk": bet_amount,
                "zero_fe": zero_fe,
                "required_fe": req_fe,
                "assumed_fe": assumed_fe,
                "equity_used": realized_equity,
                "bet_allowed": bet_allowed,
                "bet_fe_modifier": bet_fe_mod,
                "bet_caution_penalty": caution_penalty,
                "bet_size_preference": size_preference,
                "spot_type": spot_type,
                "safety_margin_required": safety_margin,
                "safety_margin_passed": safety_pass,
                "gate_status": "allowed" if bet_allowed and safety_pass else "vetoed",
                "amount_to": bet_amount,
                "ev": ev_value,
            }
        size_reports.append(size_report)
        options.append({"action": action_name, "ev": ev_value, "legal": True, "kind": size_report["mode"], **size_report})

    preliminary_bluff_layer = _build_bluff_layer_profile(
        hero_tags=hero_tags,
        street=street,
        to_call=float(to_call),
        pot_before_hero=float(pot_before_hero),
        hero_in_position=bool(hero_in_position),
        player_count=player_count,
        line_context=line_context,
        spot_type=spot_type,
        spr=spr,
        raw_equity=raw_equity,
        realized_equity=realized_equity,
        call_equity=call_equity,
        best_option=None,
        hero_profile=hero_profile,
    )
    facing_bet_layer_gate = _apply_facing_bet_layer_gates(
        bluff_layer=preliminary_bluff_layer,
        options=options,
        size_reports=size_reports,
        passive_reference_ev=passive_reference_ev,
        pot_before_hero=float(pot_before_hero),
        to_call=float(to_call),
    )
    bluff_layer_soft_gate = _apply_bluff_layer_soft_gates(
        bluff_layer=preliminary_bluff_layer,
        options=options,
        size_reports=size_reports,
        passive_reference_ev=passive_reference_ev,
        pot_before_hero=float(pot_before_hero),
    )

    eligible_options = [opt for opt in options if opt.get("legal", False) and str(opt.get("gate_status", "allowed")) != "vetoed"]
    if not eligible_options:
        eligible_options = [options[0]]
    pre_final_best_option = max(eligible_options, key=lambda item: (float(item["ev"]), item["action"] not in {"fold", "check"}))
    bluff_layer = _build_bluff_layer_profile(
        hero_tags=hero_tags,
        street=street,
        to_call=float(to_call),
        pot_before_hero=float(pot_before_hero),
        hero_in_position=bool(hero_in_position),
        player_count=player_count,
        line_context=line_context,
        spot_type=spot_type,
        spr=spr,
        raw_equity=raw_equity,
        realized_equity=realized_equity,
        call_equity=call_equity,
        best_option=pre_final_best_option,
        hero_profile=hero_profile,
    )
    best_option, final_gate = _apply_bluff_layer_gates(
        bluff_layer=bluff_layer,
        best_option=pre_final_best_option,
        options=options,
        to_call=float(to_call),
    )
    best_action = best_option["action"]
    bluff_layer["contract_version"] = "bluff_layer_gates_v1"
    bluff_layer["decision_influence"] = "hard_gates_v1_final_action_filter"
    bluff_layer["facing_bet_layer_gate"] = dict(facing_bet_layer_gate)
    bluff_layer["soft_gate"] = dict(bluff_layer_soft_gate)
    bluff_layer["final_gate"] = dict(final_gate)
    bluff_layer["pre_final_solver_choice"] = {
        "action": pre_final_best_option.get("action"),
        "size_pct": pre_final_best_option.get("size_pct"),
        "gate_status": pre_final_best_option.get("gate_status"),
        "ev": pre_final_best_option.get("ev"),
    }
    bluff_layer["current_solver_choice"] = {
        "action": best_option.get("action"),
        "size_pct": best_option.get("size_pct"),
        "gate_status": best_option.get("gate_status"),
    }
    return {
        "hero_hand": hero,
        "board": board_cards,
        "street": street,
        "pot_before_hero": float(pot_before_hero),
        "to_call": float(to_call),
        "effective_stack": None if effective_stack is None else float(effective_stack),
        "spr": spr,
        "hero_in_position": bool(hero_in_position),
        "player_count": player_count,
        "line_context": {} if line_context is None else dict(line_context),
        "line_adjustments": line_adj,
        "spot_type": spot_type,
        "hero_has_initiative": hero_has_initiative,
        "dropped_range_sources": dropped_range_sources,
        "range_sources": [
            {
                "name": src.name,
                "source_type": src.source_type,
                "raw_expr": src.raw_expr,
                "normalized_expr": src.normalized_expr,
                "combo_count": len(src.weighted_combos),
                "meta": src.meta,
            }
            for src in range_sources
        ],
        "hero_tags": tuple(sorted(hero_tags)),
        "bluff_layer": bluff_layer,
        "equity": {
            "raw_multiway_hero_equity": raw_equity,
            "realization_factor": realization_factor,
            "realized_equity": realized_equity,
            "call_equity": call_equity,
            "multiway_detail": raw_multiway,
        },
        "thresholds": {
            "call_break_even_equity": call_threshold,
            "safety_margin_vs_passive": safety_margin,
            "hard_call_gate": dict(hard_call_gate),
        },
        "size_reports": size_reports,
        "options": options,
        "recommended_action": best_action,
        "recommended_option": best_option,
    }


def format_hero_decision_report(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("=== HERO DECISION REPORT ===")
    lines.append(f"Hero hand: {' '.join(report['hero_hand'])}")
    lines.append(f"Board: {' '.join(report['board']) if report['board'] else '<preflop>'}")
    lines.append(
        f"Street: {report['street']} | Pot: {report['pot_before_hero']:.2f} | To call: {report['to_call']:.2f} | "
        f"SPR: {report['spr'] if report['spr'] is not None else 'N/A'}"
    )
    lines.append(f"Position: {'IP' if report['hero_in_position'] else 'OOP'} | Players: {report['player_count']}")
    if report.get('hero_tags'):
        lines.append(f"Hero tags: {', '.join(report['hero_tags'])}")
    eq = report['equity']
    lines.append(
        f"Equity raw={eq['raw_multiway_hero_equity'] * 100:.2f}% | realization={eq['realization_factor']:.3f} | "
        f"realized={eq['realized_equity'] * 100:.2f}% | call_eq={eq['call_equity'] * 100:.2f}%"
    )
    th = report.get('thresholds', {})
    lines.append(f"Call BE equity: {th.get('call_break_even_equity', 0.0) * 100:.2f}%")
    if 'safety_margin_vs_passive' in th:
        lines.append(f"Safety margin vs passive: {float(th['safety_margin_vs_passive']):.4f} BB")
    if 'hard_call_gate' in th and isinstance(th['hard_call_gate'], dict):
        gate = th['hard_call_gate']
        lines.append(
            f"Hard call gate: {'PASS' if gate.get('allowed') else 'BLOCK'} | required_eq={float(gate.get('required_equity', 0.0)) * 100:.2f}% | used={float(gate.get('equity_used', 0.0)) * 100:.2f}%"
        )
    lines.append("")
    lines.append("Villain ranges:")
    for item in report['range_sources']:
        lines.append(
            f"  - {item['name']}: {item['source_type']} | combos={item['combo_count']} | raw={item['raw_expr'] if item['raw_expr'] else '<weighted/direct>'}"
        )
    lines.append("")
    lines.append("Options:")
    for option in report['options']:
        gate_status = option.get('gate_status')
        gate_text = f" | gate={gate_status}" if gate_status else ""
        if option['action'] in {'fold', 'check', 'call'}:
            extra = ""
            if option['action'] == 'call' and isinstance(option.get('hard_call_gate'), dict):
                g = option['hard_call_gate']
                extra = f" | hard_call={'PASS' if g.get('allowed') else 'BLOCK'}"
            if 'safety_margin_passed' in option:
                extra += f" | safety={'PASS' if option.get('safety_margin_passed') else 'BLOCK'}"
            lines.append(f"  {option['action']:<9} EV={option['ev']:.4f}{gate_text}{extra}")
        else:
            extra = f" | zeroFE={option['zero_fe'] * 100:.2f}% | reqFE={option['required_fe'] * 100:.2f}% | assumedFE={option['assumed_fe'] * 100:.2f}%"
            if 'hard_raise_gate' in option and isinstance(option['hard_raise_gate'], dict):
                extra += f" | hard_raise={'PASS' if option['hard_raise_gate'].get('allowed') else 'BLOCK'}"
            if 'safety_margin_passed' in option:
                extra += f" | safety={'PASS' if option.get('safety_margin_passed') else 'BLOCK'}"
            lines.append(f"  {option['action']:<9} EV={option['ev']:.4f}{gate_text}{extra}")
    lines.append("")
    lines.append(f"Recommended: {report['recommended_action']}")
    return "\n".join(lines)
