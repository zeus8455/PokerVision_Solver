from __future__ import annotations

"""
audit_v229_preflop_arming_config_default_safe.py

PokerVision Solver V2.2.9 — audit config-driven V22 arming default-safe behavior.

Purpose:
- V22 config flags are connected to runtime arming diagnostics.
- Default config must still keep all candidates unarmed.
- No real-click can be enabled by default.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


ROOT = Path(r"C:\PokerVision_Solver\Script_Test_PokerVision_All_files\Test_Replay_Output")


def _read_json(path: Path) -> Dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _iter_runtime_plans(root: Path):
    for path in root.rglob("*.json"):
        if "Action_Runtime_Plan_JSON" in set(path.parts):
            yield path


def audit(root: Path = ROOT) -> Dict[str, Any]:
    counters = Counter()
    errors: list[dict[str, Any]] = []
    examples: list[dict[str, Any]] = []

    for path in _iter_runtime_plans(root):
        payload = _read_json(path)
        if not isinstance(payload, dict):
            counters["runtime_plan_unreadable"] += 1
            continue

        counters["runtime_plan_checked"] += 1

        v22 = payload.get("v22_controlled_real_click_arming_gate")
        if not isinstance(v22, dict):
            counters["v22_missing"] += 1
            continue

        counters["v22_present"] += 1

        if v22.get("armed") is True:
            counters["armed_true"] += 1
            errors.append({"path": str(path), "reason": "default_config_armed_true_forbidden"})

        if v22.get("real_click_enabled") is True:
            counters["v22_real_click_enabled_true"] += 1
            errors.append({"path": str(path), "reason": "v22_real_click_enabled_true_forbidden"})

        if payload.get("real_click_enabled") is True:
            counters["runtime_real_click_enabled_true"] += 1
            errors.append({"path": str(path), "reason": "runtime_real_click_enabled_true_forbidden"})

        if v22.get("diagnostic_only") is not True:
            errors.append({"path": str(path), "reason": "diagnostic_only_not_true", "value": v22.get("diagnostic_only")})

        if v22.get("does_not_enable_real_click") is not True:
            errors.append({"path": str(path), "reason": "does_not_enable_real_click_not_true", "value": v22.get("does_not_enable_real_click")})

        if len(examples) < 20:
            examples.append({
                "file": path.name,
                "action": payload.get("planned_action"),
                "sequence": payload.get("target_sequence"),
                "armed": v22.get("armed"),
                "ok": v22.get("ok"),
                "reason": v22.get("reason"),
                "runtime_real_click": payload.get("real_click_enabled"),
            })

    ok = (
        counters.get("v22_present", 0) > 0
        and counters.get("armed_true", 0) == 0
        and counters.get("v22_real_click_enabled_true", 0) == 0
        and counters.get("runtime_real_click_enabled_true", 0) == 0
        and not errors
    )

    return {
        "schema_version": "v229_preflop_arming_config_default_safe_audit_v1",
        "ok": ok,
        "root": str(root),
        "counters": dict(counters),
        "errors": errors,
        "examples": examples,
    }


def main() -> int:
    report = audit()

    print("V2.2.9 PREFLOP ARMING CONFIG DEFAULT-SAFE AUDIT")
    print("=" * 100)
    print("ROOT =", report["root"])

    print()
    print("COUNTERS:")
    for key, value in report["counters"].items():
        print(f"  {key}: {value}")

    print()
    print("EXAMPLES:")
    for item in report["examples"]:
        print(
            f"  {item['file']} action={item['action']} seq={item['sequence']} "
            f"armed={item['armed']} ok={item['ok']} real_click={item['runtime_real_click']} "
            f"reason={item['reason']}"
        )

    if report["errors"]:
        print()
        print("ERRORS:")
        for item in report["errors"][:30]:
            print(" ", item)

    print()
    print("[RESULT]", "OK" if report["ok"] else "FAILED", "V2.2.9 preflop arming config default-safe audit")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
