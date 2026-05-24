"""
test_poker_preflop_context_builder_unit.py

PokerVision Solver V0.5.1 — unit tests for Clear_JSON -> preflop engine_context builder.
"""

from __future__ import annotations

import json
from pathlib import Path

from logic.poker_preflop_context_builder import (
    build_preflop_engine_context,
    normalize_pokervision_card,
)


FIXTURE_ROOT = Path("test_fixtures/solver_context/preflop_clear_json")


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_card_normalization() -> None:
    assert normalize_pokervision_card("A_spades") == "As"
    assert normalize_pokervision_card("K_diamonds") == "Kd"
    assert normalize_pokervision_card("T_hearts") == "Th"
    assert normalize_pokervision_card("10_hearts") == "Th"
    assert normalize_pokervision_card("7_clubs") == "7c"
    assert normalize_pokervision_card("As") == "As"
    assert normalize_pokervision_card("8c") == "8c"


def test_all_preflop_clear_json_fixtures_match_expected_engine_context() -> None:
    files = sorted(FIXTURE_ROOT.glob("*.json"))
    assert files, f"No fixtures found in {FIXTURE_ROOT}"

    checked = 0
    for path in files:
        payload = _load_json(path)
        expected = payload.get("expected_engine_context")
        assert isinstance(expected, dict), f"{path.name}: missing expected_engine_context"

        got = build_preflop_engine_context(payload)
        assert got["status"] == "ok", f"{path.name}: builder returned error: {got}"

        keys = [
            "street",
            "hero_hand",
            "hero_pos",
            "player_count",
            "node_type",
            "opener_pos",
            "three_bettor_pos",
            "four_bettor_pos",
            "limpers",
            "callers",
        ]

        for key in keys:
            assert got.get(key) == expected.get(key), (
                f"{path.name}: key={key!r}, expected={expected.get(key)!r}, got={got.get(key)!r}"
            )

        assert got["schema_version"] == "poker_engine_context_v1"
        assert got["context_type"] == "PreflopContext"
        assert got["source_frame_id"] == payload["frame_id"]
        assert isinstance(got["action_history"], list)
        assert got["errors"] == []
        assert isinstance(got["warnings"], list)
        checked += 1

    assert checked == len(files)


def test_non_preflop_returns_structured_error() -> None:
    payload = {
        "frame_id": "bad_flop_fixture",
        "board": {"cards": ["A_spades", "K_hearts", "2_clubs"], "street": "flop"},
        "players": {},
    }

    got = build_preflop_engine_context(payload)

    assert got["status"] == "error"
    assert got["source_frame_id"] == "bad_flop_fixture"
    assert got["errors"][0]["reason"] == "not_preflop"


def test_missing_hero_returns_structured_error() -> None:
    payload = {
        "frame_id": "bad_missing_hero",
        "board": {"cards": [], "street": "preflop"},
        "players": {
            "BTN": {"stack": 100.0, "fold": False, "chips": False},
            "SB": {"stack": 99.5, "fold": False, "chips": 0.5},
            "BB": {"stack": 99.0, "fold": False, "chips": 1.0},
        },
    }

    got = build_preflop_engine_context(payload)

    assert got["status"] == "error"
    assert got["source_frame_id"] == "bad_missing_hero"
    assert got["errors"][0]["reason"] == "hero_extract_failed"


def test_bad_hero_card_count_returns_structured_error() -> None:
    payload = {
        "frame_id": "bad_hero_card_count",
        "board": {"cards": [], "street": "preflop"},
        "players": {
            "BTN": {
                "hero": True,
                "cards": ["A_spades"],
                "stack": 100.0,
                "fold": False,
                "chips": False,
            },
            "SB": {"stack": 99.5, "fold": False, "chips": 0.5},
            "BB": {"stack": 99.0, "fold": False, "chips": 1.0},
        },
    }

    got = build_preflop_engine_context(payload)

    assert got["status"] == "error"
    assert got["source_frame_id"] == "bad_hero_card_count"
    assert got["errors"][0]["reason"] == "hero_extract_failed"


def main() -> None:
    test_card_normalization()
    test_all_preflop_clear_json_fixtures_match_expected_engine_context()
    test_non_preflop_returns_structured_error()
    test_missing_hero_returns_structured_error()
    test_bad_hero_card_count_returns_structured_error()
    print("[RESULT] OK: poker preflop context builder unit tests passed.")


if __name__ == "__main__":
    main()
