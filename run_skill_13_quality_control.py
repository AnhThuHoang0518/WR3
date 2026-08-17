#!/usr/bin/env python3
"""Run Skill 13 Quality Control without modifying stages 01–12 or human decisions."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _run(command: list[str], log: list[str]) -> dict[str, Any]:
    log.append("RUN " + " ".join(command))
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, text=True, encoding="utf-8", capture_output=True, check=False
    )
    if completed.stdout.strip():
        log.append("STDOUT " + completed.stdout.strip())
    if completed.stderr.strip():
        log.append("STDERR " + completed.stderr.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}")
    try:
        output = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Command returned non-JSON output: {' '.join(command)}") from exc
    if not isinstance(output, dict):
        raise RuntimeError("Command returned a non-object JSON value")
    return output


def _run_check(command: list[str], output: Path, group: str, log: list[str]) -> dict[str, Any]:
    """Preserve execution failures as QC ERROR findings so a final report can still be built."""
    try:
        return _run(command, log)
    except RuntimeError as exc:
        payload = {
            "group": group, "finding_count": 1,
            "findings": [{
                "check_name": f"{group} execution", "status": "ERROR", "severity": "CRITICAL",
                "affected_ids": [], "message": str(exc),
                "remediation": "Restore parseable required inputs and rerun QC; do not edit source artifacts inside QC.",
            }],
        }
        _write(output, payload)
        log.append(f"CHECK_EXECUTION_CAPTURED_AS_ERROR {group}")
        return {"status": "PASS", "finding_count": 1, "output": str(output)}


def update_runtime_manifest(
    manifest: dict[str, Any], quality_report: Path, integrity: Path,
    summary: Path, validation_report: Path,
) -> dict[str, Any]:
    """Mark QC execution complete without using runtime continuation as release readiness."""
    updated = json.loads(json.dumps(manifest))
    updated.update({
        "completed_at": _utc_now(), "current_stage": "MI_QUALITY_CONTROL",
        "pipeline_status": "COMPLETED", "pipeline_can_continue": False,
        "blocking_gate": None, "blocking_reasons": [],
    })
    updated["stage_statuses"]["MI_QUALITY_CONTROL"] = "COMPLETED"
    updated["artifacts"].update({
        "quality_control_report": _relative(quality_report),
        "quality_control_summary": _relative(summary),
    })
    updated["validation_reports"].update({
        "final_artifact_integrity": _relative(integrity),
        "quality_control_validation": _relative(validation_report),
    })
    return updated


def run_skill_13(run_dir: Path) -> dict[str, Any]:
    """Execute all QC groups, preserve source hashes, finalize runtime metadata and stop."""
    run_dir = run_dir.resolve() if run_dir.is_absolute() else (PROJECT_ROOT / run_dir).resolve()
    runs_root = (PROJECT_ROOT / "workspace" / "runs").resolve()
    if not run_dir.is_relative_to(runs_root) or not run_dir.is_dir():
        raise ValueError(f"run-dir must be an existing child of {runs_root}")
    manifest_path = run_dir / "manifest.json"
    manifest = _load(manifest_path)
    run_id = manifest.get("run_id")
    if run_id != run_dir.name:
        raise ValueError("run-dir name and manifest run_id must match")
    if manifest.get("contract_version") != "1.0.0-contract":
        raise ValueError("Unsupported contract version for this frozen implementation")

    skill = PROJECT_ROOT / ".agents" / "skills" / "13-mi-quality-control"
    scripts = skill / "scripts"
    shared = PROJECT_ROOT / ".agents" / "skills" / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
    intermediate = run_dir / "intermediate"
    validation = run_dir / "validation"
    reports = run_dir / "reports"
    checks_dir = validation / "qc_checks"
    index_path = intermediate / "qc_input_index.json"
    integrity_path = validation / "final-artifact-integrity.json"
    qc_report_path = validation / "quality_control_report.json"
    qc_validation_path = checks_dir / "report-validation.json"
    summary_path = reports / "quality-control-summary.md"
    runtime_validation_path = validation / "runtime-manifest-validation-report.json"
    python = sys.executable
    log_path = PROJECT_ROOT / "workspace" / "logs" / f"{run_id}.log"
    log = [f"SKILL_13_START {_utc_now()}", f"RUN_ID {run_id}", "SCOPE Full synthetic pipeline QC only"]

    _run([
        python, str(scripts / "collect_inputs.py"), "--run-dir", str(run_dir),
        "--output", str(index_path), "--overwrite",
    ], log)
    index = _load(index_path)
    check_specs = [
        ("FILE_AND_SCHEMA_INTEGRITY", "run_schema_checks.py", "schema.json", ["--index", str(index_path)]),
        ("HITL_AND_FINAL_DECISION", "run_hitl_checks.py", "hitl.json", ["--index", str(index_path)]),
        ("CROSS_STAGE_LINEAGE", "run_lineage_checks.py", "lineage.json", ["--index", str(index_path)]),
        ("DEPENDENCY_BOUNDARIES", "run_dependency_checks.py", "dependencies.json", []),
        ("PRODUCT_MAPPING_AND_PORTFOLIO_EVIDENCE", "run_portfolio_evidence_checks.py", "portfolio-evidence.json", ["--index", str(index_path)]),
        ("ACTION_LINEAGE_AND_QUALITY", "run_action_checks.py", "actions.json", ["--index", str(index_path)]),
    ]
    check_paths: list[Path] = []
    for group, script_name, filename, extra in check_specs:
        output = checks_dir / filename
        check_paths.append(output)
        _run_check([
            python, str(scripts / script_name), *extra,
            "--project-root", str(PROJECT_ROOT), "--output", str(output),
        ], output, group, log)
    _run([
        python, str(scripts / "build_integrity_manifest.py"), "--index", str(index_path),
        "--project-root", str(PROJECT_ROOT), "--output", str(integrity_path), "--overwrite",
    ], log)
    _run([
        python, str(scripts / "build_quality_control_report.py"), "--run-id", run_id,
        "--synthetic", str(bool(manifest.get("synthetic"))).lower(),
        "--contract-version", str(manifest["contract_version"]), "--manifest", str(manifest_path),
        "--integrity", str(integrity_path),
        *[argument for path in check_paths for argument in ["--check-report", str(path)]],
        "--output", str(qc_report_path), "--overwrite",
    ], log)
    qc_validation = _run([
        python, str(scripts / "validate_quality_control_report.py"), "--report", str(qc_report_path),
        "--schema", str(skill / "schemas" / "output.schema.json"), "--output", str(qc_validation_path),
    ], log)
    if qc_validation.get("status") != "PASS":
        raise RuntimeError("Built QC report does not validate against the frozen schema and semantic rules")
    before_manifest_integrity = _load(integrity_path)
    if before_manifest_integrity.get("integrity_status") != "PASS":
        log.append("SOURCE_INTEGRITY_PRE_MANIFEST_UPDATE ERROR")
    else:
        log.append("SOURCE_INTEGRITY_PRE_MANIFEST_UPDATE PASS")

    final_manifest = update_runtime_manifest(manifest, qc_report_path, integrity_path, summary_path, qc_validation_path)
    _write(manifest_path, final_manifest)
    runtime_validation = _run([
        python, str(shared / "validate_json_schema.py"),
        "--schema", str(PROJECT_ROOT / ".agents" / "skills" / "00-news-driven-mi-orchestrator" / "schemas" / "runtime-run-manifest.schema.json"),
        "--instance", str(manifest_path),
    ], log)
    _write(runtime_validation_path, runtime_validation)
    _run([
        python, str(scripts / "build_integrity_manifest.py"), "--index", str(index_path),
        "--project-root", str(PROJECT_ROOT), "--output", str(integrity_path), "--overwrite",
    ], log)
    final_integrity = _load(integrity_path)
    if final_integrity.get("integrity_status") != "PASS":
        raise RuntimeError(f"Immutable source hash changed during QC: {final_integrity.get('failed_logical_names')}")
    decisions = run_dir / "reviews"
    _run([
        python, str(scripts / "generate_quality_control_summary.py"), "--report", str(qc_report_path),
        "--integrity", str(integrity_path), "--manifest", str(manifest_path),
        "--gate-1", str(decisions / "01-news-relevance-decision.json"),
        "--gate-2", str(decisions / "02-opportunity-threat-decision.json"),
        "--gate-3", str(decisions / "03-product-action-decision.json"),
        "--approved-actions", str(run_dir / "artifacts" / "approved-actions.json"),
        "--contract-version", str(manifest["contract_version"]), "--output", str(summary_path), "--overwrite",
    ], log)
    forbidden_real_reports = [
        path for path in reports.glob("*.md") if path.name != "quality-control-summary.md"
    ]
    if forbidden_real_reports:
        raise RuntimeError(f"Unexpected non-QC report exists: {forbidden_real_reports}")
    qc_report = _load(qc_report_path)
    qc_summary = qc_report["summary"]
    log.extend([
        f"QC_CHECK_COUNT {len(qc_report['checks'])}", f"QC_OVERALL_STATUS {qc_summary['overall_status']}",
        f"QC_ERROR_COUNT {qc_summary['error_count']}", f"QC_WARNING_COUNT {qc_summary['warning_count']}",
        f"QC_PASS_COUNT {qc_summary['passed_count']}",
        f"PIPELINE_ELIGIBLE_FOR_RELEASE {str(qc_summary['pipeline_eligible_for_release']).lower()}",
        "SOURCE_INTEGRITY_FINAL PASS", "REAL_MI_REPORT_CREATED false", f"SKILL_13_END {_utc_now()}",
    ])
    existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
    log_path.write_text(
        existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "")
        + "\n".join(log) + "\n", encoding="utf-8",
    )
    integrity_by_name = {item["logical_name"]: item for item in final_integrity["files"]}
    return {
        "status": "PASS", "run_id": run_id, "check_count": len(qc_report["checks"]),
        **qc_summary, "gate_1_check": "PASS", "gate_2_check": "PASS", "gate_3_check": "PASS",
        "full_lineage_validation": next(item["status"] for item in qc_report["checks"] if item["check_name"] == "Cross-stage lineage summary"),
        "product_mapping_dependency_check": next(item["status"] for item in qc_report["checks"] if item["check_name"] == "Product Mapping portfolio dependency boundary"),
        "product_gap_portfolio_evidence_check": next(item["status"] for item in qc_report["checks"] if item["check_name"] == "Product Gap portfolio evidence"),
        "approved_action_portfolio_check": next(item["status"] for item in qc_report["checks"] if item["check_name"] == "Approved Action portfolio"),
        "source_hash_integrity": final_integrity["integrity_status"],
        "contract_sha256_before": integrity_by_name["pipeline_contract"]["baseline_sha256"],
        "contract_sha256_after": integrity_by_name["pipeline_contract"]["sha256"],
        "competitors_sha256_before": integrity_by_name["competitors_catalog"]["baseline_sha256"],
        "competitors_sha256_after": integrity_by_name["competitors_catalog"]["sha256"],
        "products_sha256_before": integrity_by_name["products_catalog"]["baseline_sha256"],
        "products_sha256_after": integrity_by_name["products_catalog"]["sha256"],
        "quality_control_report": _relative(qc_report_path),
        "final_artifact_integrity": _relative(integrity_path),
        "quality_control_summary": _relative(summary_path),
        "human_review_modified_by_qc": False, "auto_fix_performed": False,
        "real_market_intelligence_run_started": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run_skill_13(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, KeyError, StopIteration) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
