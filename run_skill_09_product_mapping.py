#!/usr/bin/env python3
"""Run Skill 09 Product Mapping for one Gate 2-approved partial run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _hashes(paths: list[Path]) -> dict[str, str]:
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest().upper() for path in paths}


def _run(command: list[str], log_lines: list[str]) -> dict[str, Any]:
    log_lines.append("RUN " + " ".join(command))
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True, encoding="utf-8", capture_output=True, check=False)
    if completed.stdout.strip():
        log_lines.append("STDOUT " + completed.stdout.strip())
    if completed.stderr.strip():
        log_lines.append("STDERR " + completed.stderr.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Command returned non-JSON output: {' '.join(command)}") from exc


def _build_approved_bundle(
    opportunity_threat: dict[str, Any], decision: dict[str, Any], decision_path: Path
) -> dict[str, Any]:
    """Copy approved O/T canonically in decision order."""
    by_id = {item.get("ot_id"): item for item in opportunity_threat.get("items", [])}
    approved_ids = decision.get("approved_ot_ids", [])
    unknown = sorted(set(approved_ids) - set(by_id))
    if unknown:
        raise ValueError(f"Gate 2 approved unknown O/T IDs: {unknown}")
    return {
        "artifact_type": "approved_opportunity_threat_bundle",
        "run_id": decision["run_id"],
        "synthetic": decision["synthetic"],
        "source_decision_path": _relative(decision_path),
        "approval_status": decision["overall_status"],
        "approved_ot_count": len(approved_ids),
        "rejected_ot_count": len(decision.get("rejected_ot_ids", [])),
        "approved_opportunity_threat": [by_id[ot_id] for ot_id in approved_ids],
    }


def run_skill_09(run_dir: Path) -> dict[str, Any]:
    """Build and validate Product Mapping, then stop before Product Gap."""
    run_dir = run_dir.resolve() if run_dir.is_absolute() else (PROJECT_ROOT / run_dir).resolve()
    runs_root = (PROJECT_ROOT / "workspace" / "runs").resolve()
    if not run_dir.is_relative_to(runs_root) or not run_dir.is_dir():
        raise ValueError(f"run-dir must be an existing child of {runs_root}")
    artifacts = run_dir / "artifacts"
    intermediate = run_dir / "intermediate"
    reviews = run_dir / "reviews"
    validation = run_dir / "validation"
    manifest_path = run_dir / "manifest.json"
    manifest = _load(manifest_path)
    run_id = manifest.get("run_id")
    if run_id != run_dir.name:
        raise ValueError("run-dir name and manifest run_id must match")

    skills = PROJECT_ROOT / ".agents" / "skills"
    skill08 = skills / "08-opportunity-threat-hitl"
    skill09 = skills / "09-product-mapping"
    shared = skills / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
    python = sys.executable
    signals_path = artifacts / "signals.json"
    ot_path = artifacts / "opportunity_threat.json"
    gate2_review = reviews / "02-opportunity-threat-review.md"
    gate2_decision = reviews / "02-opportunity-threat-decision.json"
    gate2_report = validation / "gate-2-validation-report.json"
    gate1_review = reviews / "01-news-relevance-review.md"
    gate1_decision = reviews / "01-news-relevance-decision.json"
    gate1_report = validation / "gate-1-validation-report.json"
    protected = [
        signals_path, ot_path, gate2_review, gate2_decision, gate2_report,
        gate1_review, gate1_decision, gate1_report,
        PROJECT_ROOT / "PIPELINE_VERSION.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "DEPENDENCY_MATRIX.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "HITL_GATE_POLICY.md",
        skills / "00-news-driven-mi-orchestrator" / "schemas" / "pipeline_manifest.schema.json",
        skills / "02-competitor-news" / "references" / "competitors.json",
        skills / "10-product-gap" / "references" / "products.json",
        skill09 / "schemas" / "output.schema.json",
    ]
    protected_before = _hashes(protected)

    bundle_path = artifacts / "approved_opportunity_threat_bundle.json"
    context_path = intermediate / "product_mapping_context.json"
    draft_path = intermediate / "product_mapping_draft.json"
    mapping_path = artifacts / "product_mapping.json"
    manual_review = reviews / "product-mapping-review.md"
    approved_report = validation / "approved-opportunity-threat-validation-report.json"
    mapping_report = validation / "product-mapping-validation-report.json"
    coverage_report = validation / "product-mapping-coverage-report.json"
    dependency_report = validation / "product-mapping-dependency-audit.json"
    final_targets = [mapping_path, manual_review, mapping_report, coverage_report, dependency_report]
    existing = [str(path) for path in final_targets if path.exists()]
    if existing:
        raise ValueError(f"Refusing to overwrite Skill 09 final outputs: {existing}")
    if not draft_path.is_file():
        raise ValueError(f"Semantic draft must be authored before the driver runs: {draft_path}")

    log_path = PROJECT_ROOT / "workspace" / "logs" / f"{run_id}.log"
    log_lines = [f"SKILL_09_START {_utc_now()}", f"RUN_ID {run_id}", "SCOPE Product Mapping only"]
    try:
        gate2_validation = _run([
            python, str(skill08 / "scripts" / "validate_decision.py"),
            "--decision", str(gate2_decision),
            "--schema", str(skill08 / "schemas" / "review-decision.schema.json"),
            "--opportunity-threat", str(ot_path),
        ], log_lines)
        decision = _load(gate2_decision)
        if gate2_validation.get("gate_status") != "APPROVED" or gate2_validation.get("pipeline_can_continue") is not True:
            raise RuntimeError("Gate 2 is not a valid human APPROVED decision")
        if decision.get("revision_ot_ids") or not decision.get("approved_ot_ids"):
            raise RuntimeError("Gate 2 must contain approved O/T and no revisions")

        canonical_bundle = _build_approved_bundle(_load(ot_path), decision, gate2_decision)
        if bundle_path.exists():
            if _load(bundle_path) != canonical_bundle:
                raise RuntimeError("Existing approved O/T bundle is not the canonical Gate 2 selection")
        else:
            _write(bundle_path, canonical_bundle)
        approved_validation = _run([
            python, str(shared / "validate_stage_lineage.py"), "--mode", "approved-ot",
            "--approved-ot-bundle", str(bundle_path), "--decision", str(gate2_decision),
            "--opportunity-threat", str(ot_path), "--signals", str(signals_path),
            "--gate-report", str(gate2_report), "--report", str(approved_report),
        ], log_lines)
        _run([
            python, str(skill09 / "scripts" / "prepare_context.py"),
            "--signals", str(signals_path), "--approved-ot-bundle", str(bundle_path),
            "--decision", str(gate2_decision), "--output", str(context_path), "--overwrite",
        ], log_lines)
        _run([
            python, str(skill09 / "scripts" / "build_artifact.py"),
            "--context", str(context_path), "--draft", str(draft_path),
            "--schema", str(skill09 / "schemas" / "output.schema.json"), "--output", str(mapping_path),
        ], log_lines)
        mapping_validation = _run([
            python, str(skill09 / "scripts" / "validate_artifact.py"),
            "--artifact", str(mapping_path), "--schema", str(skill09 / "schemas" / "output.schema.json"),
            "--signals", str(signals_path), "--approved-ot-bundle", str(bundle_path),
            "--decision", str(gate2_decision), "--report", str(mapping_report),
        ], log_lines)
        lineage_validation = _run([
            python, str(shared / "validate_stage_lineage.py"), "--mode", "product-mapping",
            "--product-mapping", str(mapping_path), "--signals", str(signals_path),
            "--approved-ot-bundle", str(bundle_path), "--decision", str(gate2_decision),
        ], log_lines)
        dependency_audit = _run([
            python, str(skill09 / "scripts" / "audit_forbidden_dependencies.py"),
            "--skill-dir", str(skill09), "--output", str(dependency_report),
        ], log_lines)
        coverage = _run([
            python, str(skill09 / "scripts" / "build_coverage_report.py"),
            "--context", str(context_path), "--product-mapping", str(mapping_path),
            "--draft", str(draft_path), "--output", str(coverage_report),
        ], log_lines)
        _run([
            python, str(skill09 / "scripts" / "generate_manual_review.py"),
            "--context", str(context_path), "--product-mapping", str(mapping_path),
            "--output", str(manual_review),
        ], log_lines)

        manifest.update({
            "completed_at": _utc_now(), "run_mode": "PARTIAL", "current_stage": "PRODUCT_MAPPING",
            "pipeline_status": "COMPLETED", "pipeline_can_continue": True,
            "blocking_gate": None, "blocking_reasons": [],
        })
        manifest["stage_statuses"].update({
            "PRODUCT_MAPPING": "COMPLETED", "PRODUCT_GAP": "NOT_IN_SCOPE",
            "ACTION_RECOMMENDATION": "NOT_IN_SCOPE", "PRODUCT_ACTION_HITL": "NOT_IN_SCOPE",
            "MI_QUALITY_CONTROL": "NOT_IN_SCOPE",
        })
        manifest["artifacts"].update({
            "approved_opportunity_threat_bundle": _relative(bundle_path),
            "product_mapping": _relative(mapping_path),
        })
        manifest["reviews"]["product_mapping_manual_review"] = _relative(manual_review)
        manifest["validation_reports"].update({
            "approved_ot_validation": _relative(approved_report),
            "product_mapping_validation": _relative(mapping_report),
            "product_mapping_coverage": _relative(coverage_report),
            "product_mapping_dependency_audit": _relative(dependency_report),
        })
        _write(manifest_path, manifest)
        runtime_validation = _run([
            python, str(shared / "validate_json_schema.py"),
            "--schema", str(skills / "00-news-driven-mi-orchestrator" / "schemas" / "runtime-run-manifest.schema.json"),
            "--instance", str(manifest_path),
        ], log_lines)
        _write(validation / "runtime-manifest-validation-report.json", runtime_validation)

        if protected_before != _hashes(protected):
            raise RuntimeError("Protected Gate/Contract/catalog integrity changed")
        mapping = _load(mapping_path)
        coverage_data = _load(coverage_report)
        log_lines.extend([
            f"APPROVED_OT_VALIDATION {approved_validation['status']}",
            f"PRODUCT_MAPPING_VALIDATION {mapping_validation['status']}",
            f"PRODUCT_MAPPING_LINEAGE {lineage_validation['status']}",
            f"DEPENDENCY_AUDIT {dependency_audit['status']}",
            f"PRODUCT_MAPPING_COVERAGE {coverage['status']}",
            "PROTECTED_INTEGRITY PASS", "SCOPE_STOP Product Gap not executed",
            f"SKILL_09_END {_utc_now()}",
        ])
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "") + "\n".join(log_lines) + "\n", encoding="utf-8")
        return {
            "status": "PASS", "run_id": run_id,
            "approved_ot_ids": decision["approved_ot_ids"],
            "rejected_ot_ids": decision["rejected_ot_ids"],
            "product_mapping_count": len(mapping["items"]),
            "product_mappings": [
                {key: item[key] for key in ["product_mapping_id", "signal_id", "related_ot_ids", "market_product_category"]}
                for item in mapping["items"]
            ],
            "unmapped_approved_ot_ids": coverage_data["unmapped_approved_ot_ids"],
            "unmapped_signal_ids": coverage_data["unmapped_signal_ids"],
            "semantic_warning_count": mapping_validation["warning_count"],
            "schema_validation": mapping_validation["schema_status"],
            "lineage_validation": mapping_validation["lineage_status"],
            "dependency_audit": dependency_audit["status"],
            "pipeline_can_continue": True,
            "next_stage_executed": False,
            "protected_integrity": "PASS",
        }
    except Exception:
        log_lines.append(f"SKILL_09_FAILED {_utc_now()}")
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "") + "\n".join(log_lines) + "\n", encoding="utf-8")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run_skill_09(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
