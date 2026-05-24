"""
audit_clear_json_solver_blocks.py

PokerVision Solver V1.2.2 — audit solver preview blocks in final Clear_JSON.

Checks that active preflop final Clear_JSON files contain:
- engine_context
- engine_decision_preview
- engine_decision_preview.engine_action
- valid Clear_JSON contract
- no forbidden technical keys inside solver blocks
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from logic.clear_json_builder import validate_clear_json_contract


FORBIDDEN_SOLVER_BLOCK_KEYS = {
    "errors",
    "warnings",
    "confidence",
    "weighted_combos",
    "runtime_action",
    "solver_action",
    "bbox",
    "raw_bbox",
    "bbox_xyxy",
}


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not an object")
    return data


def _has_hero(clear_json: Dict[str, Any]) -> bool:
    players = clear_json.get("players")
    if not isinstance(players, dict):
        return False
    return any(isinstance(player, dict) and bool(player.get("hero")) for player in players.values())


def _walk_has_key(value: Any, key_name: str) -> bool:
    if isinstance(value, dict):
        if key_name in value:
            return True
        return any(_walk_has_key(v, key_name) for v in value.values())
    if isinstance(value, list):
        return any(_walk_has_key(v, key_name) for v in value)
    return False


def audit_solver_blocks(root: Path) -> Dict[str, Any]:
    files = sorted(root.rglob("*.json"))

    counters = Counter()
    node_counter = Counter()
    action_counter = Counter()
    errors = []
    examples = []

    for path in files:
        counters["json_total"] += 1

        try:
            clear_json = _load_json(path)
        except Exception as exc:
            counters["bad_json"] += 1
            errors.append({"path": str(path), "reason": "bad_json", "message": str(exc)})
            continue

        board = clear_json.get("board") or {}
        if board.get("street") != "preflop":
            counters["non_preflop_skipped"] += 1
            continue

        if not _has_hero(clear_json):
            counters["preflop_without_hero_skipped"] += 1
            continue

        counters["active_preflop_with_hero"] += 1

        validation = validate_clear_json_contract(clear_json)
        if not isinstance(validation, dict) or not validation.get("ok"):
            counters["validation_error"] += 1
            errors.append({
                "path": str(path),
                "frame_id": clear_json.get("frame_id"),
                "reason": "validation_error",
                "validation": validation,
            })

        engine_context = clear_json.get("engine_context")
        decision_preview = clear_json.get("engine_decision_preview")

        if not isinstance(engine_context, dict):
            counters["missing_engine_context"] += 1
            errors.append({
                "path": str(path),
                "frame_id": clear_json.get("frame_id"),
                "reason": "missing_engine_context",
            })
            continue

        if not isinstance(decision_preview, dict):
            counters["missing_engine_decision_preview"] += 1
            errors.append({
                "path": str(path),
                "frame_id": clear_json.get("frame_id"),
                "reason": "missing_engine_decision_preview",
            })
            continue

        counters["with_engine_context"] += 1
        counters["with_engine_decision_preview"] += 1

        engine_action = decision_preview.get("engine_action")
        node_type = engine_context.get("node_type")

        if not isinstance(engine_action, str) or not engine_action.strip():
            counters["missing_engine_action"] += 1
            errors.append({
                "path": str(path),
                "frame_id": clear_json.get("frame_id"),
                "reason": "missing_engine_action",
            })

        for forbidden_key in FORBIDDEN_SOLVER_BLOCK_KEYS:
            if _walk_has_key(engine_context, forbidden_key) or _walk_has_key(decision_preview, forbidden_key):
                counters["forbidden_solver_key"] += 1
                errors.append({
                    "path": str(path),
                    "frame_id": clear_json.get("frame_id"),
                    "reason": "forbidden_solver_key",
                    "key": forbidden_key,
                })

        node_counter[str(node_type)] += 1
        action_counter[str(engine_action)] += 1

        examples.append({
            "path": str(path),
            "frame_id": clear_json.get("frame_id"),
            "node_type": node_type,
            "engine_action": engine_action,
            "decision_id": decision_preview.get("decision_id"),
            "solver_fingerprint": decision_preview.get("solver_fingerprint"),
        })

    return {
        "root": str(root),
        "counters": dict(counters),
        "node_counter": dict(node_counter),
        "action_counter": dict(action_counter),
        "errors": errors,
        "examples": examples[:50],
    }


def print_report(report: Dict[str, Any]) -> int:
    counters = Counter(report.get("counters") or {})

    print("=" * 100)
    print("POKERVISION CLEAR_JSON SOLVER BLOCKS AUDIT")
    print("=" * 100)
    print("ROOT:", report["root"])
    print()

    print("COUNTS:")
    for key in [
        "json_total",
        "bad_json",
        "non_preflop_skipped",
        "preflop_without_hero_skipped",
        "active_preflop_with_hero",
        "with_engine_context",
        "with_engine_decision_preview",
        "missing_engine_context",
        "missing_engine_decision_preview",
        "missing_engine_action",
        "validation_error",
        "forbidden_solver_key",
    ]:
        print(f"  {key}: {counters.get(key, 0)}")

    print()
    print("NODE_TYPES:")
    for key, value in sorted((report.get("node_counter") or {}).items()):
        print(f"  {key}: {value}")

    print()
    print("ENGINE_ACTIONS:")
    for key, value in sorted((report.get("action_counter") or {}).items()):
        print(f"  {key}: {value}")

    print()
    print("EXAMPLES:")
    for item in report.get("examples", [])[:20]:
        print(f"  {item.get('frame_id')} | node={item.get('node_type')} | action={item.get('engine_action')}")

    errors = report.get("errors") or []
    if errors:
        print()
        print("ERRORS:")
        for item in errors[:20]:
            print(f"  {item}")

    if errors:
        print()
        print("[RESULT] FAILED: Clear_JSON solver blocks audit found errors.")
        return 1

    print()
    print("[RESULT] OK: Clear_JSON solver blocks audit passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit solver blocks in final Clear_JSON files.")
    parser.add_argument(
        "--root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle" / "Clear_JSON"),
        help="Path to final Clear_JSON root.",
    )
    args = parser.parse_args()

    report = audit_solver_blocks(Path(args.root))
    return print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
