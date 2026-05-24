"""
audit_current_cycle_json.py

PokerVision V10.2 — current_cycle JSON audit utility.

Purpose:
- Audit outputs/ui_display_cycle/current_cycle after replay or live run.
- Count Dark/Clear/Decision/Action/RuntimePlan/JSON_Complete artifacts.
- Validate JSON_Complete as final clean JSON with click_result and without technical keys.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

try:
    from config import UI_DISPLAY_CYCLE_OUTPUT_DIR, CURRENT_CYCLE_DIR_NAME
except Exception:
    UI_DISPLAY_CYCLE_OUTPUT_DIR = Path("outputs") / "ui_display_cycle"
    CURRENT_CYCLE_DIR_NAME = "current_cycle"


FORBIDDEN_COMPLETE_KEYS = {
    "runtime_action",
    "runtime_event",
    "trigger_ui",
    "table_structure",
    "errors",
    "warnings",
    "clear_json_contract",
    "action_transaction_runtime",
    "action_transaction_decision",
}


def _read_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON root is not an object")
    return data


def _walk(obj: Any, path: str = "$") -> Iterable[Tuple[str, str, Any]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            current_path = f"{path}.{key}"
            yield current_path, str(key), value
            yield from _walk(value, current_path)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from _walk(value, f"{path}[{idx}]")


def _count_json(root: Path, folder: str) -> int:
    return len(list((root / folder).rglob("*.json"))) if (root / folder).exists() else 0


def _index_by_stem(root: Path, folder: str, suffix: str) -> Dict[str, Path]:
    out: Dict[str, Path] = {}
    base = root / folder
    if not base.exists():
        return out
    for path in sorted(base.rglob(f"*{suffix}")):
        name = path.name
        if name.endswith(suffix):
            out[name[: -len(suffix)]] = path
    return out


def _extract_complete_frame_ids(root: Path) -> List[str]:
    out: List[str] = []
    base = root / "JSON_Complete"
    if not base.exists():
        return out
    for path in sorted(base.rglob("*.json")):
        try:
            data = _read_json(path)
        except Exception:
            continue
        frame_id = data.get("frame_id")
        if isinstance(frame_id, str) and frame_id.strip():
            out.append(frame_id.strip())
    return out


def _audit_linked_final_chain(root: Path) -> Dict[str, Any]:
    frame_ids = _extract_complete_frame_ids(root)

    clear_idx = _index_by_stem(root, "Clear_JSON", ".json")
    decision_idx = _index_by_stem(root, "Decision_JSON", ".decision.json")
    action_idx = _index_by_stem(root, "Action_Decision_JSON", ".action.json")
    runtime_idx = _index_by_stem(root, "Action_Runtime_Plan_JSON", ".runtime_plan.json")

    missing_clear: List[str] = []
    missing_decision: List[str] = []
    missing_action_decision: List[str] = []
    missing_runtime_plan: List[str] = []

    for frame_id in frame_ids:
        if frame_id not in clear_idx:
            missing_clear.append(frame_id)
        if frame_id not in decision_idx:
            missing_decision.append(frame_id)
        if frame_id not in action_idx:
            missing_action_decision.append(frame_id)
        if frame_id not in runtime_idx:
            missing_runtime_plan.append(frame_id)

    return {
        "json_complete_frame_ids": len(frame_ids),
        "linked_clear_json": len(frame_ids) - len(missing_clear),
        "linked_decision_json": len(frame_ids) - len(missing_decision),
        "linked_action_decision_json": len(frame_ids) - len(missing_action_decision),
        "linked_action_runtime_plan_json": len(frame_ids) - len(missing_runtime_plan),
        "missing_clear_json": missing_clear[:20],
        "missing_decision_json": missing_decision[:20],
        "missing_action_decision_json": missing_action_decision[:20],
        "missing_action_runtime_plan_json": missing_runtime_plan[:20],
    }


def audit_current_cycle(root: Path) -> Dict[str, Any]:
    files = sorted(root.rglob("*.json")) if root.exists() else []

    bad_json: List[Tuple[str, str]] = []
    validation_failed: List[Tuple[str, str, str]] = []
    runtime_plan_paths: List[Tuple[str, str, str]] = []
    completed_contract_saved = 0
    completed_contract_error = 0

    for path in files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            data = _read_json(path)
        except Exception as exc:
            bad_json.append((rel, str(exc)))
            continue

        for json_path, key, value in _walk(data):
            if key == "runtime_plan_path" and value:
                runtime_plan_paths.append((rel, json_path, str(value)))
            if key == "status" and value == "validation_failed":
                validation_failed.append((rel, json_path, str(value)))

        contract = data.get("completed_json_contract")
        if isinstance(contract, dict):
            if contract.get("status") == "saved":
                completed_contract_saved += 1
            elif contract.get("status") == "error":
                completed_contract_error += 1

    complete_files = sorted((root / "JSON_Complete").rglob("*.json")) if (root / "JSON_Complete").exists() else []
    complete_missing_click: List[str] = []
    complete_forbidden_keys: List[Tuple[str, List[str]]] = []
    complete_key_variants: Counter = Counter()

    for path in complete_files:
        rel = str(path.relative_to(root)).replace("\\", "/")
        try:
            data = _read_json(path)
        except Exception as exc:
            bad_json.append((rel, str(exc)))
            continue

        keys = set(data.keys())
        complete_key_variants[tuple(sorted(keys))] += 1

        if not isinstance(data.get("click_result"), dict):
            complete_missing_click.append(rel)

        forbidden = sorted(keys & FORBIDDEN_COMPLETE_KEYS)
        if forbidden:
            complete_forbidden_keys.append((rel, forbidden))

    return {
        "root": str(root),
        "json_total": len(files),
        "bad_json_total": len(bad_json),
        "counts": {
            "Dark_JSON": _count_json(root, "Dark_JSON"),
            "Clear_JSON": _count_json(root, "Clear_JSON"),
            "Clear_JSON_Pending": _count_json(root, "Clear_JSON_Pending"),
            "Decision_JSON": _count_json(root, "Decision_JSON"),
            "Action_Decision_JSON": _count_json(root, "Action_Decision_JSON"),
            "Action_Runtime_Plan_JSON": _count_json(root, "Action_Runtime_Plan_JSON"),
            "JSON_Complete": _count_json(root, "JSON_Complete"),
        },
        "linked_final_chain": _audit_linked_final_chain(root),
        "runtime_plan_path_hits": len(runtime_plan_paths),
        "validation_failed_hits": len(validation_failed),
        "completed_json_contract_saved": completed_contract_saved,
        "completed_json_contract_error": completed_contract_error,
        "json_complete_missing_click_result": len(complete_missing_click),
        "json_complete_forbidden_key_files": len(complete_forbidden_keys),
        "json_complete_key_variants": {
            ",".join(keys): count for keys, count in complete_key_variants.items()
        },
        "bad_json_examples": bad_json[:20],
        "validation_failed_examples": validation_failed[:20],
        "json_complete_missing_click_examples": complete_missing_click[:20],
        "json_complete_forbidden_key_examples": complete_forbidden_keys[:20],
    }


def print_report(report: Dict[str, Any]) -> int:
    counts = report["counts"]

    print("=" * 100)
    print("POKERVISION CURRENT_CYCLE JSON AUDIT")
    print("=" * 100)
    print(f"ROOT: {report['root']}")
    print(f"JSON_TOTAL: {report['json_total']}")
    print(f"BAD_JSON: {report['bad_json_total']}")
    print()

    print("COUNTS:")
    for key in (
        "Dark_JSON",
        "Clear_JSON",
        "Clear_JSON_Pending",
        "Decision_JSON",
        "Action_Decision_JSON",
        "Action_Runtime_Plan_JSON",
        "JSON_Complete",
    ):
        print(f"  {key}: {counts[key]}")

    print()
    print("LINKED FINAL CHAIN:")
    linked = report["linked_final_chain"]
    print(f"  JSON_Complete frame_ids: {linked['json_complete_frame_ids']}")
    print(f"  linked Clear_JSON: {linked['linked_clear_json']}")
    print(f"  linked Decision_JSON: {linked['linked_decision_json']}")
    print(f"  linked Action_Decision_JSON: {linked['linked_action_decision_json']}")
    print(f"  linked Action_Runtime_Plan_JSON: {linked['linked_action_runtime_plan_json']}")

    print()
    print("CONTRACT AUDIT:")
    print(f"  runtime_plan_path_hits: {report['runtime_plan_path_hits']}")
    print(f"  validation_failed_hits: {report['validation_failed_hits']}")
    print(f"  completed_json_contract_saved: {report['completed_json_contract_saved']}")
    print(f"  completed_json_contract_error: {report['completed_json_contract_error']}")
    print(f"  json_complete_missing_click_result: {report['json_complete_missing_click_result']}")
    print(f"  json_complete_forbidden_key_files: {report['json_complete_forbidden_key_files']}")

    print()
    print("JSON_COMPLETE TOP KEY VARIANTS:")
    variants = report["json_complete_key_variants"]
    if not variants:
        print("  none")
    else:
        for keys, count in variants.items():
            print(f"  {count}: [{keys}]")

    problems = []
    if report["bad_json_total"]:
        problems.append("bad_json")
    if report["json_complete_missing_click_result"]:
        problems.append("json_complete_missing_click_result")
    if report["json_complete_forbidden_key_files"]:
        problems.append("json_complete_forbidden_keys")
    linked = report["linked_final_chain"]
    if counts["Clear_JSON"] > 0 and counts["JSON_Complete"] != counts["Clear_JSON"]:
        problems.append("json_complete_count_mismatch_clear_json")
    if linked["json_complete_frame_ids"] > 0 and linked["linked_clear_json"] != linked["json_complete_frame_ids"]:
        problems.append("linked_clear_json_missing_for_json_complete")
    if linked["json_complete_frame_ids"] > 0 and linked["linked_decision_json"] != linked["json_complete_frame_ids"]:
        problems.append("linked_decision_json_missing_for_json_complete")
    if linked["json_complete_frame_ids"] > 0 and linked["linked_action_decision_json"] != linked["json_complete_frame_ids"]:
        problems.append("linked_action_decision_json_missing_for_json_complete")
    if linked["json_complete_frame_ids"] > 0 and linked["linked_action_runtime_plan_json"] != linked["json_complete_frame_ids"]:
        problems.append("linked_action_runtime_plan_json_missing_for_json_complete")

    if problems:
        print()
        print("[RESULT] WARNING: current_cycle audit found contract problems:")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print()
    print("[RESULT] OK: current_cycle JSON audit passed.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit PokerVision current_cycle JSON artifacts.")
    parser.add_argument(
        "--root",
        default=str(Path(UI_DISPLAY_CYCLE_OUTPUT_DIR) / str(CURRENT_CYCLE_DIR_NAME)),
        help="Path to current_cycle root.",
    )
    parser.add_argument(
        "--json-report",
        default="",
        help="Optional path to save machine-readable audit report JSON.",
    )
    args = parser.parse_args()

    root = Path(args.root)
    report = audit_current_cycle(root)

    if args.json_report:
        out = Path(args.json_report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    return print_report(report)


if __name__ == "__main__":
    raise SystemExit(main())
