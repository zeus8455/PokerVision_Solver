from __future__ import annotations

"""
audit_v212_preflop_preflight_output.py

PokerVision Solver V2.1.2 — audit saved replay output for V21 preflop preflight diagnostics.

Diagnostic-only script.
Does not modify JSON files.
Does not enable or execute real clicks.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_ROOT = Path(r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output")


def _iter_json_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return root.rglob("*.json")


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _street(payload: Dict[str, Any]) -> str | None:
    board = payload.get("board") if isinstance(payload.get("board"), dict) else {}
    value = board.get("street")
    return str(value).lower() if value else None


def _is_final_output_path(path: Path) -> bool:
    parts = set(path.parts)
    if "Clear_JSON_Pending" in parts:
        return False
    return (
        "generated_clear_json" in parts
        or "Clear_JSON" in parts
        or "JSON_Complete" in parts
        or "Runtime_Audit" in parts
        or "Action_Runtime_Plan_JSON" in parts
    )


def _find_nested_key(payload: Any, key: str) -> list[Any]:
    found: list[Any] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == key:
                found.append(v)
            found.extend(_find_nested_key(v, key))
    elif isinstance(payload, list):
        for item in payload:
            found.extend(_find_nested_key(item, key))
    return found


def audit(root: Path = DEFAULT_ROOT) -> Dict[str, Any]:
    counters = Counter()
    preflight_ok_counter = Counter()
    allowed_kind_counter = Counter()
    examples: list[dict[str, Any]] = []

    for path in _iter_json_files(root):
        if not _is_final_output_path(path):
            continue

        payload = _read_json(path)
        if payload is None:
            continue

        counters["json_checked"] += 1

        preflight_reports = _find_nested_key(payload, "v21_preflop_real_click_preflight_gate")
        preflight_validations = _find_nested_key(payload, "v21_preflop_real_click_preflight_gate_validation")

        if preflight_reports:
            counters["json_with_v21_preflight_report"] += 1

        if preflight_validations:
            counters["json_with_v21_preflight_validation"] += 1

        for report in preflight_reports:
            if not isinstance(report, dict):
                continue

            preflight_ok_counter[report.get("ok")] += 1
            allowed_kind_counter[report.get("allowed_kind")] += 1

            if len(examples) < 10:
                examples.append({
                    "path": str(path),
                    "ok": report.get("ok"),
                    "allowed": report.get("allowed"),
                    "allowed_kind": report.get("allowed_kind"),
                    "street": report.get("street"),
                    "planned_action": report.get("planned_action"),
                    "target_sequence": report.get("target_sequence"),
                    "real_click_enabled": report.get("real_click_enabled"),
                    "errors": report.get("errors"),
                })

    return {
        "root": str(root),
        "counters": dict(counters),
        "preflight_ok_counter": dict(preflight_ok_counter),
        "allowed_kind_counter": dict(allowed_kind_counter),
        "examples": examples,
        "ok": counters.get("json_with_v21_preflight_report", 0) > 0,
    }


def main() -> None:
    report = audit()

    print("V2.1.2 PREFLOP PREFLIGHT OUTPUT AUDIT")
    print("=" * 100)
    print("ROOT =", report["root"])

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("PREFLIGHT_OK_COUNTER:", report["preflight_ok_counter"])
    print("ALLOWED_KIND_COUNTER:", report["allowed_kind_counter"])

    print()
    print("EXAMPLES:")
    for row in report["examples"]:
        print("- path =", row["path"])
        print("  ok =", row["ok"])
        print("  allowed =", row["allowed"])
        print("  allowed_kind =", row["allowed_kind"])
        print("  street =", row["street"])
        print("  planned_action =", row["planned_action"])
        print("  target_sequence =", row["target_sequence"])
        print("  real_click_enabled =", row["real_click_enabled"])
        print("  errors =", row["errors"])

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.1.2 preflight output audit")


if __name__ == "__main__":
    main()
