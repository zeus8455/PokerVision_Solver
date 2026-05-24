"""
test_poker_clear_solver_preview_adapter_unit.py

PokerVision Solver V1.2 — tests for Clear_JSON-safe solver preview adapter.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from logic.clear_json_builder import validate_clear_json_contract
from logic.poker_clear_solver_preview_adapter import build_clear_safe_solver_preview_blocks
from logic.poker_preflop_solver_preview_builder import build_preflop_solver_preview


FIXTURE_ROOT = Path("test_fixtures/solver_context/preflop_clear_json")

FORBIDDEN_KEYS = {
    "errors",
    "warnings",
    "confidence",
    "weighted_combos",
    "runtime_action",
    "solver_action",
    "bbox",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_has_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        if key_name in value:
            return True
        return any(_walk_has_key(v, key_name) for v in value.values())
    if isinstance(value, list):
        return any(_walk_has_key(v, key_name) for v in value)
    return False


def test_clear_safe_solver_preview_blocks_validate_inside_clear_json() -> None:
    files = sorted(FIXTURE_ROOT.glob("*.json"))
    assert len(files) == 16, f"Expected 16 preflop fixtures, got {len(files)}"

    for path in files:
        fixture = _load_json(path)

        clear_json = dict(fixture)
        clear_json.pop("expected_engine_context", None)
        clear_json.pop("preflop_action_model", None)

        solver_preview = build_preflop_solver_preview(fixture)
        blocks = build_clear_safe_solver_preview_blocks(solver_preview)
        assert isinstance(blocks, dict), f"{path.name}: adapter returned no blocks"

        enriched = dict(clear_json)
        enriched.update(blocks)

        validation = validate_clear_json_contract(enriched)
        assert validation["ok"], f"{path.name}: validation failed: {validation}"

        for forbidden_key in FORBIDDEN_KEYS:
            assert not _walk_has_key(blocks, forbidden_key), f"{path.name}: forbidden key leaked: {forbidden_key}"


def main() -> None:
    test_clear_safe_solver_preview_blocks_validate_inside_clear_json()
    print("[RESULT] OK: clear solver preview adapter unit tests passed.")


if __name__ == "__main__":
    main()
