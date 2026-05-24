"""
audit_solver_action_decision_candidates.py

PokerVision Solver V1.4.1 — audit published Solver_Action_Decision_Candidate_JSON files.

Diagnostic only:
- checks candidate files against Clear_JSON.engine_decision_preview
- does not modify Action_Decision_JSON
- does not modify Runtime Plan
- does not click
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Optional

from logic.solver_action_decision_candidate import validate_solver_action_decision_candidate


def _load_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not object")
    return data


def _normalize_action(action: Any) -> Optional[str]:
    if not isinstance(action, str):
        return None
    value = action.strip().lower()
    aliases = {
        "check/fold": "check_fold",
        "check-fold": "check_fold",
        "all_in": "raise",
        "all-in": "raise",
        "3bet": "raise",
        "4bet": "raise",
        "5bet": "raise",
        "iso_raise": "raise",
        "bet": "raise",
    }
    return aliases.get(value, value) if value else None


def _has_hero(clear_json: Dict[str, Any]) -> bool:
    players = clear_json.get("players")
    if not isinstance(players, dict):
        return False
    return any(isinstance(v, dict) and v.get("hero") is True for v in players.values())


def _find_candidate(candidate_root: Path, table_id: str, frame_id: str) -> Optional[Path]:
    path = candidate_root / table_id / f"{frame_id}.solver_candidate.json"
    if path.exists():
        return path
    matches = sorted((candidate_root / table_id).glob(f"{frame_id}*.json")) if (candidate_root / table_id).exists() else []
    return matches[0] if matches else None


def audit_candidates(root: Path) -> Dict[str, Any]:
    clear_root = root / "Clear_JSON"
    candidate_root = root / "Solver_Action_Decision_Candidate_JSON"

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
        engine_preview = clear_json.get("engine_decision_preview")

        if not isinstance(engine_preview, dict):
            counters["missing_engine_decision_preview"] += 1
            errors.append({"path": str(clear_path), "frame_id": frame_id, "reason": "missing_engine_decision_preview"})
            continue

        candidate_path = _find_candidate(candidate_root, table_id, frame_id)
        if candidate_path is None:
            counters["missing_candidate"] += 1
            errors.append({"path": str(clear_path), "frame_id": frame_id, "reason": "missing_candidate"})
            continue

        counters["candidate_files_matched"] += 1

        try:
            candidate = _load_json(candidate_path)
        except Exception as exc:
            counters["bad_candidate_json"] += 1
            errors.append({"path": str(candidate_path), "frame_id": frame_id, "reason": "bad_candidate_json", "message": str(exc)})
            continue

        validation = validate_solver_action_decision_candidate(candidate)
        if not validation.get("ok"):
            counters["candidate_validation_error"] += 1
            errors.append({
                "path": str(candidate_path),
                "frame_id": frame_id,
                "reason": "candidate_validation_error",
                "validation": validation,
            })

        if candidate.get("source") != "Clear_JSON.engine_decision_preview":
            counters["bad_source"] += 1
            errors.append({"path": str(candidate_path), "frame_id": frame_id, "reason": "bad_source", "source": candidate.get("source")})

        if candidate.get("solver_stub") is not False:
            counters["bad_solver_stub"] += 1
            errors.append({"path": str(candidate_path), "frame_id": frame_id, "reason": "bad_solver_stub", "solver_stub": candidate.get("solver_stub")})

        if candidate.get("dry_run_safe") is not True:
            counters["bad_dry_run_safe"] += 1
            errors.append({"path": str(candidate_path), "frame_id": frame_id, "reason": "bad_dry_run_safe", "dry_run_safe": candidate.get("dry_run_safe")})

        if not isinstance(candidate.get("target_button_classes"), list) or not candidate.get("target_button_classes"):
            counters["empty_target_button_classes"] += 1
            errors.append({"path": str(candidate_path), "frame_id": frame_id, "reason": "empty_target_button_classes"})

        solver_action = _normalize_action(engine_preview.get("engine_action"))
        candidate_action = _normalize_action(candidate.get("action"))

        if solver_action != candidate_action:
            counters["action_mismatch"] += 1
            errors.append({
                "path": str(candidate_path),
                "frame_id": frame_id,
                "reason": "action_mismatch",
                "solver_action": engine_preview.get("engine_action"),
                "candidate_action": candidate.get("action"),
            })
        else:
            counters["action_match"] += 1

        examples.append({
            "frame_id": frame_id,
            "candidate_file": candidate_path.name,
            "solver_action": engine_preview.get("engine_action"),
            "candidate_action": candidate.get("action"),
            "target_button_classes": candidate.get("target_button_classes"),
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
    print("POKERVISION SOLVER ACTION DECISION CANDIDATE AUDIT")
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
        "candidate_files_matched",
        "missing_candidate",
        "bad_candidate_json",
        "candidate_validation_error",
        "bad_source",
        "bad_solver_stub",
        "bad_dry_run_safe",
        "empty_target_button_classes",
        "action_match",
        "action_mismatch",
    ]:
        print(f"  {key}: {counters.get(key, 0)}")

    print()
    print("EXAMPLES:")
    for item in report.get("examples", [])[:20]:
        print(
            f"  {item.get('frame_id')} | solver={item.get('solver_action')} "
            f"| candidate={item.get('candidate_action')} "
            f"| buttons={item.get('target_button_classes')}"
        )

    errors = report.get("errors") or []
    if errors:
        print()
        print("ERRORS:")
        for item in errors[:20]:
            print(f"  {item}")
        print()
        print("[RESULT] FAILED: solver action decision candidate audit found errors.")
        return 1

    print()
    print("[RESULT] OK: solver action decision candidate audit passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Solver_Action_Decision_Candidate_JSON files.")
    parser.add_argument(
        "--root",
        default=str(Path("outputs") / "ui_display_cycle" / "current_cycle"),
        help="current_cycle root containing Clear_JSON and Solver_Action_Decision_Candidate_JSON.",
    )
    args = parser.parse_args()

    return print_report(audit_candidates(Path(args.root)))


if __name__ == "__main__":
    raise SystemExit(main())
