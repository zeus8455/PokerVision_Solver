"""
audit_solver_runtime_plan_candidates.py

PokerVision Solver V1.5 — audit published Solver_Action_Runtime_Plan_Candidate_JSON files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

from logic.solver_runtime_plan_candidate import validate_solver_action_runtime_plan_candidate


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not object")
    return data


def _has_hero(clear_json: Dict[str, Any]) -> bool:
    players = clear_json.get("players")
    if not isinstance(players, dict):
        return False
    return any(isinstance(v, dict) and v.get("hero") is True for v in players.values())


def _find_plan_candidate(plan_root: Path, table_id: str, frame_id: str) -> Optional[Path]:
    path = plan_root / table_id / f"{frame_id}.solver_runtime_plan_candidate.json"
    if path.exists():
        return path
    matches = sorted((plan_root / table_id).glob(f"{frame_id}*.json")) if (plan_root / table_id).exists() else []
    return matches[0] if matches else None


def audit_runtime_plan_candidates(root: Path) -> Dict[str, Any]:
    clear_root = root / "Clear_JSON"
    plan_root = root / "Solver_Action_Runtime_Plan_Candidate_JSON"

    counters = Counter()
    errors = []
    examples = []

    for clear_path in sorted(clear_root.rglob("*.json")):
        counters["clear_json_total"] += 1

        try:
            clear_json = _load_json(clear_path)
        except Exception as exc:
            counters["bad_clear_json"] += 1
            errors.append({"path": str(clear_path), "reason": "bad_clear_json", "message": str(exc)})
            continue

        if (clear_json.get("board") or {}).get("street") != "preflop":
            counters["non_preflop_skipped"] += 1
            continue

        if not _has_hero(clear_json):
            counters["preflop_without_hero_skipped"] += 1
            continue

        counters["active_preflop_with_hero"] += 1

        frame_id = str(clear_json.get("frame_id") or "")
        table_id = clear_path.parent.name

        plan_path = _find_plan_candidate(plan_root, table_id, frame_id)
        if plan_path is None:
            counters["missing_runtime_plan_candidate"] += 1
            errors.append({"path": str(clear_path), "frame_id": frame_id, "reason": "missing_runtime_plan_candidate"})
            continue

        counters["runtime_plan_candidate_files_matched"] += 1

        try:
            plan = _load_json(plan_path)
        except Exception as exc:
            counters["bad_runtime_plan_candidate_json"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_runtime_plan_candidate_json", "message": str(exc)})
            continue

        validation = validate_solver_action_runtime_plan_candidate(plan)
        if not validation.get("ok"):
            counters["runtime_plan_candidate_validation_error"] += 1
            errors.append({
                "path": str(plan_path),
                "frame_id": frame_id,
                "reason": "runtime_plan_candidate_validation_error",
                "validation": validation,
            })

        status = str(plan.get("status") or "")
        if status == "ok":
            counters["runtime_plan_status_ok"] += 1
        elif status == "blocked":
            counters["runtime_plan_status_blocked"] += 1
        else:
            counters["runtime_plan_status_other"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_status", "status": status})

        if plan.get("source") != "Solver_Action_Decision_Candidate_JSON":
            counters["bad_source"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_source", "source": plan.get("source")})

        if plan.get("solver_stub") is not False:
            counters["bad_solver_stub"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_solver_stub", "solver_stub": plan.get("solver_stub")})

        if plan.get("diagnostic_candidate") is not True:
            counters["bad_diagnostic_candidate"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_diagnostic_candidate"})

        if plan.get("does_not_replace_runtime_plan") is not True:
            counters["bad_does_not_replace_runtime_plan"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_does_not_replace_runtime_plan"})

        if plan.get("does_not_enable_real_click") is not True:
            counters["bad_does_not_enable_real_click"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_does_not_enable_real_click"})

        if plan.get("real_click_enabled") is not False:
            counters["bad_real_click_enabled"] += 1
            errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "bad_real_click_enabled", "real_click_enabled": plan.get("real_click_enabled")})

        if status == "ok":
            if not isinstance(plan.get("target_sequence"), list) or not plan.get("target_sequence"):
                counters["empty_target_sequence_on_ok"] += 1
                errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "empty_target_sequence_on_ok"})
        elif status == "blocked":
            if not plan.get("blocked_reason"):
                counters["missing_blocked_reason"] += 1
                errors.append({"path": str(plan_path), "frame_id": frame_id, "reason": "missing_blocked_reason"})

        examples.append({
            "frame_id": frame_id,
            "status": status,
            "planned_action": plan.get("planned_action"),
            "target_sequence": plan.get("target_sequence"),
            "blocked_reason": plan.get("blocked_reason"),
        })

    return {
        "root": str(root),
        "counters": dict(counters),
        "errors": errors,
        "examples": examples[:50],
    }


def print_report(report: Dict[str, Any]) -> int:
    counters = Counter(report.get("counters") or {})

    print("=" * 100)
    print("POKERVISION SOLVER ACTION RUNTIME PLAN CANDIDATE AUDIT")
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
        "runtime_plan_candidate_files_matched",
        "missing_runtime_plan_candidate",
        "bad_runtime_plan_candidate_json",
        "runtime_plan_candidate_validation_error",
        "runtime_plan_status_ok",
        "runtime_plan_status_blocked",
        "runtime_plan_status_other",
        "bad_source",
        "bad_solver_stub",
        "bad_diagnostic_candidate",
        "bad_does_not_replace_runtime_plan",
        "bad_does_not_enable_real_click",
        "bad_real_click_enabled",
        "empty_target_sequence_on_ok",
        "missing_blocked_reason",
    ]:
        print(f"  {key}: {counters.get(key, 0)}")

    print()
    print("EXAMPLES:")
    for item in report.get("examples", [])[:20]:
        print(
            f"  {item.get('frame_id')} | status={item.get('status')} "
            f"| action={item.get('planned_action')} "
            f"| sequence={item.get('target_sequence')} "
            f"| blocked={item.get('blocked_reason')}"
        )

    errors = report.get("errors") or []
    if errors:
        print()
        print("ERRORS:")
        for item in errors[:20]:
            print(f"  {item}")
        print()
        print("[RESULT] FAILED: solver runtime plan candidate audit found errors.")
        return 1

    print()
    print("[RESULT] OK: solver runtime plan candidate audit passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Solver_Action_Runtime_Plan_Candidate_JSON files.")
    parser.add_argument(
        "--root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle"),
        help="current_cycle root containing Clear_JSON and Solver_Action_Runtime_Plan_Candidate_JSON.",
    )
    args = parser.parse_args()
    return print_report(audit_runtime_plan_candidates(Path(args.root)))


if __name__ == "__main__":
    raise SystemExit(main())
