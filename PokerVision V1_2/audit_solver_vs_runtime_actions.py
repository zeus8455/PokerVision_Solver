"""
audit_solver_vs_runtime_actions.py

PokerVision Solver V1.3 — compare solver preview action vs current Action_Decision / Runtime Plan.

This audit is diagnostic only:
- does not modify JSON
- does not change click source
- does not affect runtime execution
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not object")
    return data


def _has_hero(clear_json: Dict[str, Any]) -> bool:
    players = clear_json.get("players")
    if not isinstance(players, dict):
        return False
    return any(isinstance(player, dict) and bool(player.get("hero")) for player in players.values())


def _normalize_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    value = action.strip().lower()
    if not value:
        return None

    aliases = {
        "check/fold": "check_fold",
        "check-fold": "check_fold",
        "check_fold": "check_fold",
        "fold": "fold",
        "call": "call",
        "check": "check",
        "raise": "raise",
        "bet": "raise",
        "all_in": "raise",
        "all-in": "raise",
        "4bet": "raise",
        "3bet": "raise",
        "5bet": "raise",
        "iso_raise": "raise",
    }
    return aliases.get(value, value)


def _find_json_by_frame(root: Path, folder: str, table_id: str, frame_id: str, suffix: str) -> Optional[Path]:
    candidate = root / folder / table_id / f"{frame_id}{suffix}"
    if candidate.exists():
        return candidate
    matches = sorted((root / folder / table_id).glob(f"{frame_id}*.json")) if (root / folder / table_id).exists() else []
    return matches[0] if matches else None


def audit_solver_vs_runtime(root: Path) -> Dict[str, Any]:
    clear_root = root / "Clear_JSON"
    clear_files = sorted(clear_root.rglob("*.json"))

    counters = Counter()
    pairs = []
    errors = []

    for clear_path in clear_files:
        counters["clear_json_total"] += 1

        try:
            clear_json = _load_json(clear_path)
        except Exception as exc:
            counters["bad_clear_json"] += 1
            errors.append({"path": str(clear_path), "reason": "bad_clear_json", "message": str(exc)})
            continue

        board = clear_json.get("board") or {}
        if board.get("street") != "preflop":
            counters["non_preflop_skipped"] += 1
            continue
        if not _has_hero(clear_json):
            counters["preflop_without_hero_skipped"] += 1
            continue

        counters["active_preflop_with_hero"] += 1

        frame_id = clear_json.get("frame_id")
        table_id = clear_path.parent.name

        engine_preview = clear_json.get("engine_decision_preview")
        if not isinstance(engine_preview, dict):
            counters["missing_engine_decision_preview"] += 1
            errors.append({"path": str(clear_path), "frame_id": frame_id, "reason": "missing_engine_decision_preview"})
            continue

        solver_action_raw = engine_preview.get("engine_action")
        solver_action = _normalize_action(solver_action_raw)

        action_path = _find_json_by_frame(root, "Action_Decision_JSON", table_id, str(frame_id), ".action.json")
        runtime_path = _find_json_by_frame(root, "Action_Runtime_Plan_JSON", table_id, str(frame_id), ".runtime_plan.json")

        action_json = None
        runtime_json = None

        if action_path is None:
            counters["missing_action_decision_json"] += 1
        else:
            action_json = _load_json(action_path)

        if runtime_path is None:
            counters["missing_runtime_plan_json"] += 1
        else:
            runtime_json = _load_json(runtime_path)

        action_decision_raw = action_json.get("action") if isinstance(action_json, dict) else None
        runtime_plan_raw = runtime_json.get("planned_action") if isinstance(runtime_json, dict) else None

        action_decision = _normalize_action(action_decision_raw)
        runtime_plan = _normalize_action(runtime_plan_raw)

        solver_stub = bool(action_json.get("solver_stub")) if isinstance(action_json, dict) else False
        runtime_solver_stub = bool(runtime_json.get("solver_stub")) if isinstance(runtime_json, dict) else False

        if solver_stub or runtime_solver_stub:
            counters["stub_runtime_count"] += 1

        if solver_action and action_decision:
            if solver_action == action_decision:
                counters["solver_vs_action_decision_match"] += 1
            else:
                counters["solver_vs_action_decision_mismatch"] += 1

        if solver_action and runtime_plan:
            if solver_action == runtime_plan:
                counters["solver_vs_runtime_plan_match"] += 1
            else:
                counters["solver_vs_runtime_plan_mismatch"] += 1

        pairs.append({
            "frame_id": frame_id,
            "table_id": table_id,
            "solver_action": solver_action_raw,
            "action_decision": action_decision_raw,
            "runtime_plan": runtime_plan_raw,
            "solver_stub": solver_stub,
            "runtime_solver_stub": runtime_solver_stub,
            "node_type": (clear_json.get("engine_context") or {}).get("node_type"),
        })

    return {
        "root": str(root),
        "counters": dict(counters),
        "pairs": pairs,
        "errors": errors,
    }


def print_report(report: Dict[str, Any]) -> int:
    counters = Counter(report.get("counters") or {})

    print("=" * 100)
    print("POKERVISION SOLVER VS RUNTIME ACTION AUDIT")
    print("=" * 100)
    print("ROOT:", report["root"])
    print()

    print("COUNTS:")
    for key in [
        "clear_json_total",
        "bad_clear_json",
        "non_preflop_skipped",
        "preflop_without_hero_skipped",
        "active_preflop_with_hero",
        "missing_engine_decision_preview",
        "missing_action_decision_json",
        "missing_runtime_plan_json",
        "stub_runtime_count",
        "solver_vs_action_decision_match",
        "solver_vs_action_decision_mismatch",
        "solver_vs_runtime_plan_match",
        "solver_vs_runtime_plan_mismatch",
    ]:
        print(f"  {key}: {counters.get(key, 0)}")

    print()
    print("PAIRS:")
    for item in report.get("pairs", [])[:30]:
        print(
            f"  {item.get('frame_id')} | node={item.get('node_type')} "
            f"| solver={item.get('solver_action')} "
            f"| action_decision={item.get('action_decision')} "
            f"| runtime_plan={item.get('runtime_plan')} "
            f"| stub={item.get('solver_stub') or item.get('runtime_solver_stub')}"
        )

    errors = report.get("errors") or []
    if errors:
        print()
        print("ERRORS:")
        for item in errors[:20]:
            print(f"  {item}")
        print()
        print("[RESULT] WARNING: audit completed with missing/error records.")
        return 1

    print()
    print("[RESULT] OK: solver vs runtime action audit completed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare solver preview action vs current runtime action.")
    parser.add_argument(
        "--root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle"),
        help="Path to current_cycle root containing Clear_JSON, Action_Decision_JSON and Action_Runtime_Plan_JSON.",
    )
    args = parser.parse_args()
    report = audit_solver_vs_runtime(Path(args.root))
    return print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
