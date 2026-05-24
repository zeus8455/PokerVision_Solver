r"""
test_v12_full_regression.py
PokerVision Core V1.1 — full regression launcher.

What it checks:
1. py_compile for key project files.
2. Live no-click config guard.
3. Clear_JSON recovery unit tests.
4. V2.0 early per-table transaction lifecycle gate unit tests.
5. V2.2 duplicate lifecycle block unit tests.
6. V2.3 duplicate Active runtime lifecycle harness unit tests.
7. V2.4 six-slot lifecycle audit unit tests.
8. V2.5 Action_Button_Detector slot ROI guard/audit unit tests.
9. V2.6 runtime action-button slot ROI audit integration unit tests.
10. V2.7 live Dark_JSON Action_Button ROI audit exposure unit tests.
11. V2.9 controlled detected-button test-click runner unit tests.
12. V0.5 Decision_JSON builder unit tests.
6. V0.6 Action_Decision_JSON stub unit tests.
7. V0.7 Action_Runtime_Plan_JSON unit tests.
8. V0.8 live hand continuity unit tests.
9. V0.9 click execution guard unit tests.
10. V1.0 real-click readiness unit tests.
11. V1.1 Action Button Runtime Policy unit tests.
12. V1.1 Controlled Real-Click Scope unit tests.
13. Image replay Dark/Clear/Decision/ActionDecision/ActionRuntimePlan/Recovery/Runtime audit.
14. image_replay_report.json consistency.

Usage:
  cd "C:\PokerVision_Clear_Programing\PokerVision V1_2"
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe .\test_v12_full_regression.py

Fast smoke run:
  C:\Users\user\AppData\Local\Programs\Python\Python312\python.exe .\test_v12_full_regression.py --max-images 3
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


KEY_COMPILE_FILES = [
    "config.py",
    "display_analysis_cycle.py",
    "test_clear_json_recovery_unit.py",
    "test_table_action_transaction_gate_unit.py",
    "test_table_lifecycle_duplicate_block_unit.py",
    "test_duplicate_active_runtime_harness_unit.py",
    "test_six_slot_lifecycle_audit_unit.py",
    "test_action_button_slot_roi_guard_unit.py",
    "test_action_button_runtime_roi_integration_unit.py",
    "test_action_button_roi_audit_exposure_unit.py",
    "test_controlled_detected_button_click_runner_unit.py",
    "test_v40_duplicate_active_hard_stop_unit.py",
    "test_v41_failed_active_finalization_release_unit.py",
    "test_image_replay_cycle_v12.py",
    "test_decision_json_builder_unit.py",
    "test_action_decision_stub_unit.py",
    "test_action_runtime_plan_builder_unit.py",
    "test_live_hand_continuity_unit.py",
    "test_click_execution_guard_unit.py",
    "test_real_click_readiness_unit.py",
    "test_action_button_runtime_policy_unit.py",
    "test_controlled_real_click_scope_unit.py",
    "test_controlled_real_click_preset_unit.py",
    "test_v50_six_table_controlled_click_gate_unit.py",
    "test_v52_multi_click_limit_unit.py",
    "test_v54_multi_target_table_set_unit.py",
    "test_v57_six_click_limit_unit.py",
    "test_v60_trigger_ui_service_runtime_contract_unit.py",
    "test_v66_real_service_dry_run_replay_contract.py",
    "controlled_service_dry_run_smoke_runner.py",
    "test_controlled_service_dry_run_smoke_runner_unit.py",
    "test_v69_service_real_click_guard_unit.py",
    "test_v70_service_first_stop_policy_unit.py",
    "test_v71_multi_table_ordered_service_first_contract_unit.py",
    "test_v72_multi_table_service_dry_run_unit.py",
    "test_v73_active_branch_multi_table_dry_run_unit.py",
    "test_v74_controlled_real_click_readiness_4_6_tables_unit.py",
    "test_v75_controlled_live_click_preset_4_6_tables_unit.py",
    "test_v76_controlled_action_button_executor_4_6_tables_unit.py",
    "test_v77_final_live_mode_launch_contract_unit.py",
    "controlled_live_click_smoke_runner.py",
    "test_controlled_live_click_smoke_runner_unit.py",
    "controlled_test_click_runner.py",
    "test_controlled_test_click_runner_unit.py",
    "controlled_test_click_result_audit.py",
    "test_controlled_test_click_result_audit_unit.py",
    "logic/clear_json_builder.py",
    "logic/live_hand_continuity.py",
    "logic/click_execution_guard.py",
    "logic/real_click_readiness.py",
    "logic/action_button_runtime_policy.py",
    "logic/action_button_slot_roi_guard.py",
    "logic/controlled_real_click_scope.py",
    "logic/decision_json_builder.py",
    "logic/action_decision_stub.py",
    "logic/action_runtime_plan_builder.py",
    "logic/table_action_transaction_gate.py",
    "logic/clear_json_recovery.py",
    "logic/clear_json_state_machine.py",
    "detectors/action_button_detector.py",
    "runtime/v11_stage1_runtime.py",
    "runtime/trigger_ui_service_runtime.py",
    "runtime/action_click_stub.py",
    "runtime/death_card_policy.py",
    "runtime/mouse_human_runtime.py",
    "runtime/table_overlay_status.py",
]

SUMMARY_NUMERIC_KEYS = [
    "saved_json_total",
    "clear_json_saved_total",
    "clear_json_skipped_total",
    "clear_json_pending_total",
    "decision_json_total",
    "action_decision_json_total",
    "action_runtime_plan_json_total",
    "recovery_present_total",
    "recovery_applied_total",
    "runtime_audit_present_total",
    "runtime_real_click_enabled_total",
    "runtime_click_points_total",
    "errors_total",
    "warnings_total",
]


def _project_root() -> Path:
    return Path(__file__).resolve().parent


def _repo_root(project_root: Path) -> Path:
    return project_root.parent


def _report_json_path(project_root: Path) -> Path:
    return (
        _repo_root(project_root)
        / "Script_Test_PokerVision_All_files"
        / "Test_Replay_Output"
        / "reports"
        / "image_replay_report.json"
    )


def _print_header(title: str) -> None:
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def _run_command(args: List[str], *, cwd: Path, title: str) -> int:
    _print_header(f"[RUN] {title}\n{' '.join(args)}")
    started = time.perf_counter()
    proc = subprocess.run(args, cwd=str(cwd))
    elapsed = time.perf_counter() - started
    status = "OK" if proc.returncode == 0 else "FAIL"
    print(f"[{status}] {title} elapsed={elapsed:.2f}s rc={proc.returncode}")
    return int(proc.returncode)


def _compile_key_files(project_root: Path, python_exe: str) -> int:
    _print_header("[RUN] py_compile key files")
    started = time.perf_counter()
    for rel_path in KEY_COMPILE_FILES:
        path = project_root / rel_path
        if not path.exists():
            print(f"[FAIL] missing compile target: {rel_path}")
            return 1
        print(f"[COMPILE] {rel_path}")
        proc = subprocess.run([python_exe, "-m", "py_compile", str(path)], cwd=str(project_root))
        if proc.returncode != 0:
            print(f"[FAIL] py_compile failed: {rel_path}")
            return int(proc.returncode or 1)
    elapsed = time.perf_counter() - started
    print(f"[OK] py_compile key files elapsed={elapsed:.2f}s")
    return 0


def _validate_live_no_click_config(project_root: Path) -> int:
    _print_header("[RUN] Validate live no-click config guard")

    import importlib

    project_root_text = str(project_root)
    inserted = False
    if project_root_text not in sys.path:
        sys.path.insert(0, project_root_text)
        inserted = True

    try:
        config = importlib.import_module("config")
        checks = {
            "V12_LIVE_DATA_CAPTURE_NO_CLICK_MODE": True,
            "V11_REAL_MOUSE_CLICK_ENABLED": False,
            "V11_CLICK_DRY_RUN": True,
            "V11_TRIGGER_UI_SERVICE_REAL_CLICK_ENABLED": False,
            "V11_TRIGGER_UI_SERVICE_DRY_RUN": True,
            "V03_TABLE_ACTION_TRANSACTION_GATE_ENABLED": True,
            "V03_TRANSACTION_DRY_RUN_COUNTS_AS_COMPLETED": True,
            "V03_TRANSACTION_RELEASE_ON_INACTIVE": True,
            "V04_PENDING_FINAL_CLEAR_JSON_ENABLED": True,
            "V04_FINAL_CLEAR_JSON_REQUIRES_CLICK_RESULT": True,
            "V05_DECISION_JSON_ENABLED": True,
            "V06_ACTION_DECISION_ENABLED": True,
            "V07_ACTION_RUNTIME_PLAN_ENABLED": True,
            "V07_RUNTIME_PLAN_DRY_RUN_REQUIRED": True,
            "V08_LIVE_HAND_CONTINUITY_ENABLED": True,
            "V08_INACTIVE_DOES_NOT_RESET_HAND": True,
            "V08_KEEP_LAST_HAND_ON_INVALID_HERO": True,
            "V08_CLEAR_CURRENT_CYCLE_ON_MAIN_START": True,
            "V09_CLICK_EXECUTION_GUARD_ENABLED": True,
            "V09_REAL_CLICK_MASTER_ARMED": False,
            "V09_REQUIRE_SLOT_BOUNDARY_GUARD": True,
            "V09_REQUIRE_NO_REPEAT_DECISION_GUARD": True,
            "V09_REQUIRE_BUTTON_AVAILABILITY_GUARD": True,
            "V09_ALLOW_DRY_RUN_COMPLETION": True,
            "V09_BLOCK_REAL_CLICK_WHEN_LIVE_CAPTURE_NO_CLICK": True,
            "V09_CLICK_CONFIRMATION_REPORT_ENABLED": True,
            "V10_REAL_CLICK_READINESS_VALIDATOR_ENABLED": True,
            "V10_REAL_CLICK_ABORT_ON_UNSAFE_CONFIG": True,
            "V10_REAL_CLICK_ALLOW_ACTION_BUTTON_ONLY": True,
            "V10_REAL_CLICK_REQUIRE_SERVICE_CLICKS_DISABLED": True,
            "V10_REAL_CLICK_REQUIRE_LIVE_NO_CLICK_DISABLED": True,
            "V10_REAL_CLICK_REQUIRE_MASTER_ARMED": True,
            "V10_REAL_CLICK_REQUIRE_MOUSE_REAL_ENABLED": True,
            "V10_REAL_CLICK_REQUIRE_MOUSE_DRY_RUN_DISABLED": True,
        }

        failures: List[str] = []
        for name, expected in checks.items():
            actual = getattr(config, name, None)
            print(f"[CONFIG] {name}={actual!r}")
            if actual is not expected:
                failures.append(f"{name} must be {expected!r}, got {actual!r}")

        if failures:
            for item in failures:
                print(f"[FAIL] {item}")
            return 1

        print("[OK] live no-click config guard validated")
        return 0
    finally:
        if inserted:
            try:
                sys.path.remove(project_root_text)
            except ValueError:
                pass


def _load_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Replay report does not exist: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Replay report root must be a JSON object")
    return data


def _coerce_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except Exception:
        return default


def _extract_results(report: Dict[str, Any]) -> List[Dict[str, Any]]:
    for key in ("results", "items", "per_image_results", "image_results"):
        value = report.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _extract_result_extracted(result: Dict[str, Any]) -> Dict[str, Any]:
    extracted = result.get("extracted")
    return extracted if isinstance(extracted, dict) else {}


def _sum_from_results(results: Iterable[Dict[str, Any]], field_name: str) -> int:
    total = 0
    for item in results:
        extracted = _extract_result_extracted(item)
        value = extracted.get(field_name)
        if isinstance(value, bool):
            total += int(value)
        elif isinstance(value, (int, float)):
            total += int(value)
        elif value:
            total += 1
    return total


def _count_errors(results: Iterable[Dict[str, Any]]) -> int:
    total = 0
    for item in results:
        errors = item.get("errors")
        if isinstance(errors, list):
            total += len(errors)
    return total


def _count_warnings(results: Iterable[Dict[str, Any]]) -> int:
    total = 0
    for item in results:
        warnings = item.get("warnings")
        if isinstance(warnings, list):
            total += len(warnings)
    return total


def _normalize_report_summary(report: Dict[str, Any]) -> Dict[str, int]:
    """
    Accept both report schemas:
    - {"summary": {...}, "results": [...]}
    - flat report root with summary-like keys.
    """
    raw_summary = report.get("summary")
    summary_source = raw_summary if isinstance(raw_summary, dict) else report
    results = _extract_results(report)

    summary: Dict[str, int] = {}
    for key in SUMMARY_NUMERIC_KEYS:
        summary[key] = _coerce_int(summary_source.get(key), 0)

    if results:
        if summary["errors_total"] == 0:
            summary["errors_total"] = _count_errors(results)
        if summary["warnings_total"] == 0:
            summary["warnings_total"] = _count_warnings(results)
        if summary["clear_json_saved_total"] == 0:
            summary["clear_json_saved_total"] = sum(
                1
                for item in results
                if _extract_result_extracted(item).get("clear_json_contract_status") == "saved"
            )
        if summary["clear_json_skipped_total"] == 0:
            summary["clear_json_skipped_total"] = sum(
                1
                for item in results
                if _extract_result_extracted(item).get("clear_json_contract_status") == "skipped"
            )
        if summary["clear_json_pending_total"] == 0:
            summary["clear_json_pending_total"] = _sum_from_results(results, "clear_json_pending_present")
        if summary.get("decision_json_total", 0) == 0:
            summary["decision_json_total"] = _sum_from_results(results, "decision_json_present")
        if summary.get("action_decision_json_total", 0) == 0:
            summary["action_decision_json_total"] = _sum_from_results(results, "action_decision_json_present")
        if summary.get("action_runtime_plan_json_total", 0) == 0:
            summary["action_runtime_plan_json_total"] = _sum_from_results(results, "action_runtime_plan_json_present")
        if summary["recovery_present_total"] == 0:
            summary["recovery_present_total"] = _sum_from_results(results, "recovery_present")
        if summary["recovery_applied_total"] == 0:
            summary["recovery_applied_total"] = _sum_from_results(results, "recovery_applied")
        if summary["runtime_audit_present_total"] == 0:
            summary["runtime_audit_present_total"] = _sum_from_results(results, "runtime_audit_present")
        if summary["runtime_real_click_enabled_total"] == 0:
            summary["runtime_real_click_enabled_total"] = sum(
                _coerce_int(_extract_result_extracted(item).get("runtime_service_real_click_enabled"), 0)
                + _coerce_int(_extract_result_extracted(item).get("runtime_action_button_real_click_enabled"), 0)
                for item in results
            )
        if summary["runtime_click_points_total"] == 0:
            summary["runtime_click_points_total"] = sum(
                _coerce_int(_extract_result_extracted(item).get("runtime_total_click_points_count"), 0)
                for item in results
            )

    return summary


def _find_clicked_runtime_statuses(report: Dict[str, Any]) -> List[str]:
    clicked: List[str] = []
    for item in _extract_results(report):
        image_name = str(item.get("image_name") or item.get("source_name") or "unknown_image")
        extracted = _extract_result_extracted(item)
        for field in ("runtime_service_status", "runtime_action_button_status", "runtime_status"):
            if str(extracted.get(field) or "").lower() == "clicked":
                clicked.append(f"{image_name}:{field}=clicked")
    return clicked


def _validate_replay_report(project_root: Path, *, max_images: Optional[int]) -> int:
    _print_header("[RUN] Validate image_replay_report.json")
    report_path = _report_json_path(project_root)

    try:
        report = _load_report(report_path)
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1

    summary = _normalize_report_summary(report)
    clicked_statuses = _find_clicked_runtime_statuses(report)

    for key in SUMMARY_NUMERIC_KEYS:
        print(f"[REPORT] {key}={summary.get(key)}")

    failures: List[str] = []
    if summary["errors_total"] != 0:
        failures.append(f"errors_total must be 0, got {summary['errors_total']}")
    if summary["clear_json_saved_total"] <= 0:
        failures.append("clear_json_saved_total must be > 0")
    if summary["clear_json_pending_total"] <= 0:
        failures.append("clear_json_pending_total must be > 0")
    if summary["decision_json_total"] <= 0:
        failures.append("decision_json_total must be > 0")
    if summary["decision_json_total"] != summary["clear_json_saved_total"]:
        failures.append(
            "decision_json_total must equal clear_json_saved_total, "
            f"got decision={summary['decision_json_total']}, clear={summary['clear_json_saved_total']}"
        )
    if summary["action_decision_json_total"] <= 0:
        failures.append("action_decision_json_total must be > 0")
    if summary["action_decision_json_total"] != summary["decision_json_total"]:
        failures.append(
            "action_decision_json_total must equal decision_json_total, "
            f"got action={summary['action_decision_json_total']}, decision={summary['decision_json_total']}"
        )
    if summary["action_runtime_plan_json_total"] <= 0:
        failures.append("action_runtime_plan_json_total must be > 0")
    if summary["action_runtime_plan_json_total"] != summary["action_decision_json_total"]:
        failures.append(
            "action_runtime_plan_json_total must equal action_decision_json_total, "
            f"got plan={summary['action_runtime_plan_json_total']}, action={summary['action_decision_json_total']}"
        )
    if summary["recovery_present_total"] <= 0:
        failures.append("recovery_present_total must be > 0")
    if summary["runtime_audit_present_total"] <= 0:
        failures.append("runtime_audit_present_total must be > 0")
    if summary["runtime_real_click_enabled_total"] != 0:
        failures.append(
            f"runtime_real_click_enabled_total must be 0, got {summary['runtime_real_click_enabled_total']}"
        )
    if clicked_statuses:
        failures.append(f"runtime clicked statuses are forbidden in replay: {clicked_statuses}")

    if max_images is None and summary["clear_json_skipped_total"] <= 0:
        failures.append("full replay should include skipped service/inactive frames")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        return 1

    print(f"[OK] replay report validated: {report_path}")
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run PokerVision V1.2 full regression checks.")
    parser.add_argument(
        "--max-images",
        type=int,
        default=None,
        help="Pass --max-images to test_image_replay_cycle_v12.py for smoke runs.",
    )
    parser.add_argument("--skip-compile", action="store_true", help="Skip py_compile phase.")
    parser.add_argument("--skip-unit", action="store_true", help="Skip unit tests.")
    parser.add_argument("--skip-replay", action="store_true", help="Skip image replay audit.")
    parser.add_argument("--skip-live-config", action="store_true", help="Skip live no-click config guard validation.")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    project_root = _project_root()
    python_exe = sys.executable

    if not args.skip_compile:
        rc = _compile_key_files(project_root, python_exe)
        if rc != 0:
            return rc

    if not args.skip_live_config:
        rc = _validate_live_no_click_config(project_root)
        if rc != 0:
            return rc

    if not args.skip_unit:
        unit_tests = [
            ("test_clear_json_recovery_unit.py", "Clear_JSON recovery unit tests"),
            ("test_table_action_transaction_gate_unit.py", "V2.0 early per-table transaction lifecycle gate unit tests"),
            ("test_table_lifecycle_duplicate_block_unit.py", "V2.2 duplicate lifecycle block unit tests"),
            ("test_duplicate_active_runtime_harness_unit.py", "V2.3 duplicate Active runtime lifecycle harness unit tests"),
            ("test_six_slot_lifecycle_audit_unit.py", "V2.4 six-slot lifecycle audit unit tests"),
            ("test_action_button_slot_roi_guard_unit.py", "V2.5 Action_Button_Detector slot ROI guard/audit unit tests"),
            ("test_action_button_runtime_roi_integration_unit.py", "V2.6 runtime action-button slot ROI audit integration unit tests"),
            ("test_action_button_roi_audit_exposure_unit.py", "V2.7 live Dark_JSON Action_Button ROI audit exposure unit tests"),
            ("test_controlled_detected_button_click_runner_unit.py", "V2.9 controlled detected-button test-click runner unit tests"),
            ("test_controlled_live_click_gate_integration_unit.py", "V4.7 configurable controlled live-click target gate unit tests"),
        ("test_v50_six_table_controlled_click_gate_unit.py", "V5.0 six-table controlled click gate synthetic tests"),
        ("test_v52_multi_click_limit_unit.py", "V5.2 controlled multi-click limit=2 synthetic tests"),
        ("test_v54_multi_target_table_set_unit.py", "V5.4 multi-target controlled click gate synthetic tests"),
        ("test_v57_six_click_limit_unit.py", "V5.7 six-click controlled gate synthetic tests"),
        ("test_v60_trigger_ui_service_runtime_contract_unit.py", "V6.0 Trigger_UI service runtime contract tests"),
        ("test_v66_real_service_dry_run_replay_contract.py", "V6.6 real service dry-run replay contract"),
        ("test_controlled_service_dry_run_smoke_runner_unit.py", "V6.8 controlled service dry-run smoke runner unit tests"),
        ("test_v69_service_real_click_guard_unit.py", "V6.9 service real-click guard config tests"),
        ("test_v70_service_first_stop_policy_unit.py", "V7.0 service-first stop-policy unit tests"),
        ("test_v71_multi_table_ordered_service_first_contract_unit.py", "V7.1 multi-table ordered service-first contract tests"),
        ("test_v72_multi_table_service_dry_run_unit.py", "V7.2 multi-table service dry-run contract tests"),
        ("test_v73_active_branch_multi_table_dry_run_unit.py", "V7.3 active branch multi-table dry-run contract tests"),
        ("test_v74_controlled_real_click_readiness_4_6_tables_unit.py", "V7.4 controlled real-click readiness 4-6 table tests"),
        ("test_v75_controlled_live_click_preset_4_6_tables_unit.py", "V7.5 controlled live-click preset 4-6 table tests"),
        ("test_v76_controlled_action_button_executor_4_6_tables_unit.py", "V7.6 controlled action-button executor 4-6 table tests"),
        ("test_v77_final_live_mode_launch_contract_unit.py", "V7.7 final live-mode launch contract tests"),
            ("test_v33_final_clear_real_clicked_publication_unit.py", "V3.3 final Clear_JSON real-click publication unit tests"),
            ("test_v40_duplicate_active_hard_stop_unit.py", "V4.0 duplicate Active hard-stop before Pending/Decision unit tests"),
            ("test_v41_failed_active_finalization_release_unit.py", "V4.1 failed Active finalization release unit tests"),
            ("test_decision_json_builder_unit.py", "V0.5 Decision_JSON builder unit tests"),
            ("test_action_decision_stub_unit.py", "V0.6 Action_Decision_JSON stub unit tests"),
            ("test_action_runtime_plan_builder_unit.py", "V0.7 Action_Runtime_Plan_JSON unit tests"),
            ("test_live_hand_continuity_unit.py", "V0.8 live hand continuity unit tests"),
            ("test_click_execution_guard_unit.py", "V0.9 click execution guard unit tests"),
            ("test_real_click_readiness_unit.py", "V1.0 real-click readiness unit tests"),
            ("test_action_button_runtime_policy_unit.py", "V1.1 Action Button Runtime Policy unit tests"),
            ("test_controlled_real_click_scope_unit.py", "V1.1 Controlled Real-Click Scope unit tests"),
            ("test_controlled_real_click_preset_unit.py", "V1.4 controlled real-click preset unit tests"),
            ("test_controlled_live_click_smoke_runner_unit.py", "V1.5 controlled live-click smoke runner unit tests"),
            ("test_controlled_test_click_runner_unit.py", "V1.6 controlled test-environment click runner unit tests"),
            ("test_controlled_test_click_result_audit_unit.py", "V1.7 controlled test-click result audit unit tests"),
        ]
        for filename, title in unit_tests:
            rc = _run_command([python_exe, str(project_root / filename)], cwd=project_root, title=title)
            if rc != 0:
                return rc

    if not args.skip_replay:
        replay_cmd = [python_exe, str(project_root / "test_image_replay_cycle_v12.py")]
        if args.max_images is not None:
            replay_cmd.extend(["--max-images", str(args.max_images)])

        rc = _run_command(
            replay_cmd,
            cwd=project_root,
            title="Image replay Dark/Clear/Decision/ActionDecision/ActionRuntimePlan/Recovery/Runtime audit",
        )
        if rc != 0:
            return rc

        rc = _validate_replay_report(project_root, max_images=args.max_images)
        if rc != 0:
            return rc

    _print_header("[RESULT] OK: PokerVision V1.1 full regression passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



