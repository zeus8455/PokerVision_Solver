"""
audit_real_clear_json_preflop_solver_preview.py

PokerVision Solver V1.0 — dry-run audit for real live Clear_JSON files.

Reads real Clear_JSON artifacts and builds preflop solver preview without modifying files,
without touching live runtime, and without clicking.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from logic.poker_preflop_solver_preview_builder import build_preflop_solver_preview


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not an object")
    return data


def audit_clear_json_root(root: Path) -> Dict[str, Any]:
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

        counters["preflop_total"] += 1

        result = build_preflop_solver_preview(clear_json)
        if result.get("status") != "ok":
            counters["solver_preview_error"] += 1
            errors.append({
                "path": str(path),
                "frame_id": clear_json.get("frame_id"),
                "reason": "solver_preview_error",
                "errors": result.get("errors"),
            })
            continue

        counters["solver_preview_ok"] += 1

        engine_context = result.get("engine_context") or {}
        preview = result.get("engine_decision_preview") or {}

        node_type = engine_context.get("node_type")
        engine_action = preview.get("engine_action")

        node_counter[str(node_type)] += 1
        action_counter[str(engine_action)] += 1

        examples.append({
            "path": str(path),
            "frame_id": clear_json.get("frame_id"),
            "hero_pos": engine_context.get("hero_pos"),
            "hero_hand": engine_context.get("hero_hand"),
            "node_type": node_type,
            "engine_action": engine_action,
            "decision_id": preview.get("decision_id"),
            "solver_fingerprint": preview.get("solver_fingerprint"),
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
    print("POKERVISION REAL CLEAR_JSON PREFLOP SOLVER PREVIEW AUDIT")
    print("=" * 100)
    print("ROOT:", report["root"])
    print()
    print("COUNTS:")
    for key in [
        "json_total",
        "bad_json",
        "non_preflop_skipped",
        "preflop_total",
        "solver_preview_ok",
        "solver_preview_error",
    ]:
        print(f"  {key}: {counters.get(key, 0)}")

    print()
    print("NODE_TYPES:")
    node_counter = report.get("node_counter") or {}
    if node_counter:
        for key, value in sorted(node_counter.items()):
            print(f"  {key}: {value}")
    else:
        print("  none")

    print()
    print("ENGINE_ACTIONS:")
    action_counter = report.get("action_counter") or {}
    if action_counter:
        for key, value in sorted(action_counter.items()):
            print(f"  {key}: {value}")
    else:
        print("  none")

    print()
    print("EXAMPLES:")
    for item in report.get("examples", [])[:20]:
        print(
            f"  {item.get('frame_id')} | hero={item.get('hero_pos')} {item.get('hero_hand')} "
            f"| node={item.get('node_type')} | action={item.get('engine_action')}"
        )

    errors = report.get("errors") or []
    if errors:
        print()
        print("ERRORS:")
        for item in errors[:20]:
            print(f"  {item}")

    if counters.get("bad_json", 0) or counters.get("solver_preview_error", 0):
        print()
        print("[RESULT] WARNING: real Clear_JSON solver preview audit found errors.")
        return 1

    print()
    print("[RESULT] OK: real Clear_JSON solver preview audit passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit real Clear_JSON files with preflop solver preview.")
    parser.add_argument(
        "--root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle" / "Clear_JSON"),
        help="Path to Clear_JSON root.",
    )
    parser.add_argument("--json-report", default="", help="Optional path to save machine-readable report.")
    args = parser.parse_args()

    report = audit_clear_json_root(Path(args.root))

    if args.json_report:
        out = Path(args.json_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
