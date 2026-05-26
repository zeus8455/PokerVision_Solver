from __future__ import annotations

"""
export_v214_preflop_real_click_candidates.py

PokerVision Solver V2.1.4 — export strict preflop real-click candidate report.

Reads saved Action_Runtime_Plan_JSON files and exports only V21 preflight-eligible
preflop runtime plans into a diagnostic JSON report.

Diagnostic-only.
Does not modify runtime plans.
Does not enable or execute real clicks.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable


DEFAULT_ROOT = Path(r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output")
DEFAULT_EXPORT_PATH = DEFAULT_ROOT / "reports" / "v214_preflop_real_click_candidates.json"


def _iter_runtime_plan_json(root: Path) -> Iterable[Path]:
    if not root.exists():
        return []
    return root.rglob("*.runtime_plan.json")


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _infer_table_id_from_path(path: Path) -> str:
    for part in path.parts:
        part = str(part)
        if part.startswith("table_"):
            return part
    return ""


def _infer_table_id_from_payload(payload: Dict[str, Any]) -> str:
    for key in (
        "table_id",
        "source_action_decision_frame_id",
        "source_solver_candidate_frame_id",
        "source_clear_frame_id",
        "source_frame_id",
        "frame_id",
    ):
        value = str(payload.get(key) or "")
        if value.startswith("table_"):
            parts = value.split("_")
            if len(parts) >= 2:
                return f"{parts[0]}_{parts[1]}"

    decision_context = payload.get("decision_context")
    if isinstance(decision_context, dict):
        value = str(decision_context.get("table_id") or "")
        if value:
            return value

    return ""


def build_export(root: Path = DEFAULT_ROOT) -> Dict[str, Any]:
    counters = Counter()
    action_counter = Counter()
    allowed_kind_counter = Counter()
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for path in _iter_runtime_plan_json(root):
        payload = _read_json(path)
        if payload is None:
            counters["runtime_plan_unreadable"] += 1
            continue

        counters["runtime_plan_json_checked"] += 1

        preflight = payload.get("v21_preflop_real_click_preflight_gate")
        validation = payload.get("v21_preflop_real_click_preflight_gate_validation")

        if not isinstance(preflight, dict):
            counters["skipped_without_v21_preflight"] += 1
            continue

        if not isinstance(validation, dict) or validation.get("ok") is not True:
            counters["skipped_invalid_v21_validation"] += 1
            errors.append({
                "path": str(path),
                "reason": "invalid_v21_preflight_validation",
                "validation": validation,
            })
            continue

        if preflight.get("ok") is not True or preflight.get("allowed") is not True:
            counters["skipped_not_allowed_by_v21_preflight"] += 1
            skipped.append({
                "path": str(path),
                "reason": "not_allowed_by_v21_preflight",
                "preflight_errors": preflight.get("errors"),
            })
            continue

        if preflight.get("real_click_enabled") is True or payload.get("real_click_enabled") is True:
            counters["forbidden_real_click_enabled_true"] += 1
            errors.append({
                "path": str(path),
                "reason": "real_click_enabled_true_forbidden",
            })
            continue

        if str(preflight.get("street") or "").lower() != "preflop":
            counters["skipped_non_preflop"] += 1
            continue

        allowed_kind = preflight.get("allowed_kind")
        planned_action = str(preflight.get("planned_action") or payload.get("planned_action") or "")
        target_sequence = _safe_list(preflight.get("target_sequence"))

        if allowed_kind not in {"simple_preflop_action", "preflop_raise_98_sequence"}:
            counters["skipped_unsupported_allowed_kind"] += 1
            skipped.append({
                "path": str(path),
                "reason": "unsupported_allowed_kind",
                "allowed_kind": allowed_kind,
            })
            continue

        decision_context = payload.get("decision_context") if isinstance(payload.get("decision_context"), dict) else {}
        decision_context = dict(decision_context)

        table_id = str(decision_context.get("table_id") or payload.get("table_id") or _infer_table_id_from_payload(payload) or _infer_table_id_from_path(path) or "")
        if table_id:
            decision_context["table_id"] = table_id

        candidate = {
            "schema_version": "v214_preflop_real_click_candidate_v1",
            "source_runtime_plan_path": str(path),
            "table_id": table_id,
            "source": payload.get("source"),
            "source_action_decision_frame_id": payload.get("source_action_decision_frame_id"),
            "source_solver_candidate_frame_id": payload.get("source_solver_candidate_frame_id"),
            "planned_action": planned_action,
            "allowed_kind": allowed_kind,
            "target_sequence": target_sequence,
            "target_sequences": _safe_list(payload.get("target_sequences")),
            "runtime_branch": payload.get("runtime_branch"),
            "dry_run": payload.get("dry_run"),
            "real_click_enabled": payload.get("real_click_enabled"),
            "decision_context": decision_context,
            "v21_preflight": {
                "ok": preflight.get("ok"),
                "allowed": preflight.get("allowed"),
                "allowed_kind": preflight.get("allowed_kind"),
                "street": preflight.get("street"),
                "planned_action": preflight.get("planned_action"),
                "target_sequence": preflight.get("target_sequence"),
                "real_click_enabled": preflight.get("real_click_enabled"),
                "errors": preflight.get("errors"),
            },
            "diagnostic_only": True,
            "does_not_enable_real_click": True,
        }

        candidates.append(candidate)
        counters["candidate_exported_total"] += 1
        action_counter[planned_action] += 1
        allowed_kind_counter[allowed_kind] += 1

    ok = (
        counters.get("candidate_exported_total", 0) > 0
        and counters.get("forbidden_real_click_enabled_true", 0) == 0
        and not errors
    )

    return {
        "schema_version": "v214_preflop_real_click_candidate_export_v1",
        "root": str(root),
        "ok": ok,
        "diagnostic_only": True,
        "does_not_enable_real_click": True,
        "counters": dict(counters),
        "action_counter": dict(action_counter),
        "allowed_kind_counter": dict(allowed_kind_counter),
        "errors": errors,
        "skipped_examples": skipped[:20],
        "candidates": candidates,
    }


def write_export(report: Dict[str, Any], export_path: Path = DEFAULT_EXPORT_PATH) -> Path:
    export_path.parent.mkdir(parents=True, exist_ok=True)
    export_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return export_path


def main() -> int:
    report = build_export()
    export_path = write_export(report)

    print("V2.1.4 PREFLOP REAL-CLICK CANDIDATE EXPORT")
    print("=" * 100)
    print("ROOT =", report["root"])
    print("EXPORT =", export_path)

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("ACTION_COUNTER:", report["action_counter"])
    print("ALLOWED_KIND_COUNTER:", report["allowed_kind_counter"])

    print()
    print("CANDIDATE EXAMPLES:")
    for item in report["candidates"][:20]:
        print(
            f"  action={item['planned_action']} | kind={item['allowed_kind']} "
            f"| seq={item['target_sequence']} | real_click={item['real_click_enabled']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:20]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.1.4 preflop real-click candidate export")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
