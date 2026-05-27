from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


ROOT = Path(r"C:\PokerVision_Solver\PokerVision V1_2\outputs\ui_display_cycle\current_cycle\Dark_JSON")


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _norm_action(value: Any) -> str:
    return str(value or "").strip().lower()


def _norm_seq(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _extract_plan(data: Dict[str, Any]) -> Dict[str, Any]:
    rt = _as_dict(data.get("runtime_action"))
    plan = _as_dict(rt.get("action_runtime_plan_contract"))
    if plan:
        return plan

    clear_contract = _as_dict(data.get("clear_json_contract"))
    action_decision_contract = _as_dict(clear_contract.get("action_decision_contract"))
    return _as_dict(action_decision_contract.get("action_runtime_plan_contract"))


def main() -> int:
    if not ROOT.exists():
        print(f"[FAILED] Dark_JSON root not found: {ROOT}")
        return 2

    checked = 0
    mismatches: List[Dict[str, Any]] = []
    skipped = 0

    for path in sorted(ROOT.rglob("*.json")):
        data = _load_json(path)
        if not data:
            continue

        rt = _as_dict(data.get("runtime_action"))
        tx = _as_dict(data.get("action_transaction_runtime"))
        action_button = _as_dict(rt.get("action_button"))
        click_result = _as_dict(tx.get("click_result"))
        plan = _extract_plan(data)

        plan_status = str(plan.get("status") or "").strip()
        click_completed = bool(tx.get("click_completed"))

        # V2.5.3 audits only completed action-runtime frames with a saved plan.
        if plan_status != "saved" or not click_completed:
            skipped += 1
            continue

        checked += 1

        plan_action = _norm_action(plan.get("planned_action"))
        click_action = _norm_action(click_result.get("action"))
        action_button_solver_action = _norm_action(action_button.get("solver_action"))

        plan_seq = _norm_seq(plan.get("target_sequence"))
        action_button_seq = _norm_seq(action_button.get("target_sequence"))

        action_mismatch = bool(plan_action and click_action and plan_action != click_action)
        solver_action_mismatch = bool(plan_action and action_button_solver_action and plan_action != action_button_solver_action)
        sequence_mismatch = bool(plan_seq and action_button_seq and plan_seq != action_button_seq)

        if action_mismatch or solver_action_mismatch or sequence_mismatch:
            table = _as_dict(data.get("table")).get("table_id") or data.get("table_id")
            mismatches.append({
                "file": str(path),
                "table": table,
                "plan_source": plan.get("source"),
                "plan_action": plan.get("planned_action"),
                "click_action": click_result.get("action"),
                "action_button_solver_action": action_button.get("solver_action"),
                "plan_target_sequence": plan.get("target_sequence"),
                "action_button_target_sequence": action_button.get("target_sequence"),
                "action_mismatch": action_mismatch,
                "solver_action_mismatch": solver_action_mismatch,
                "sequence_mismatch": sequence_mismatch,
            })

    print("=" * 100)
    print("V2.5.3 RUNTIME CLICK RESULT CONSISTENCY AUDIT")
    print("=" * 100)
    print(f"root: {ROOT}")
    print(f"checked_completed_saved_plan_frames: {checked}")
    print(f"skipped_frames: {skipped}")
    print(f"mismatch_count: {len(mismatches)}")

    if mismatches:
        print("\nMISMATCH EXAMPLES:")
        for item in mismatches[:20]:
            print("-" * 100)
            print(f"file: {item['file']}")
            print(f"table: {item['table']}")
            print(f"plan_source: {item['plan_source']}")
            print(f"plan_action: {item['plan_action']}")
            print(f"click_action: {item['click_action']}")
            print(f"action_button_solver_action: {item['action_button_solver_action']}")
            print(f"plan_target_sequence: {item['plan_target_sequence']}")
            print(f"action_button_target_sequence: {item['action_button_target_sequence']}")
            print(
                "flags: "
                f"action_mismatch={item['action_mismatch']} "
                f"solver_action_mismatch={item['solver_action_mismatch']} "
                f"sequence_mismatch={item['sequence_mismatch']}"
            )

        print("\n[FAILED] Runtime plan and actual click-result are inconsistent.")
        return 1

    print("\n[OK] Runtime plan and actual click-result are consistent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
