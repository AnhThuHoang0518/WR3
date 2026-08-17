#!/usr/bin/env python3
"""Run Skill 10 Product Gap for one reviewed Product Mapping partial run."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
EXPECTED_PRODUCTS_SHA256 = "A05130B89606B9864FCE5303CD3974269C9FF1C2F09D4FF42D576C6AA5380B03"


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


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _hashes(paths: list[Path]) -> dict[str, str]:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise ValueError(f"Protected files are missing: {missing}")
    return {str(path): _digest(path) for path in paths}


def _parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing YAML frontmatter: {path}")
    values: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if line.startswith((" ", "\t", "-")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"\'')
    return values


def _run(command: list[str], log_lines: list[str]) -> dict[str, Any]:
    log_lines.append("RUN " + " ".join(command))
    completed = subprocess.run(
        command, cwd=PROJECT_ROOT, text=True, encoding="utf-8", capture_output=True, check=False
    )
    if completed.stdout.strip():
        log_lines.append("STDOUT " + completed.stdout.strip())
    if completed.stderr.strip():
        log_lines.append("STDERR " + completed.stderr.strip())
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(command)}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Command returned non-JSON output: {' '.join(command)}") from exc
    if not isinstance(result, dict):
        raise RuntimeError(f"Command returned non-object JSON: {' '.join(command)}")
    return result


def run_skill_10(run_dir: Path) -> dict[str, Any]:
    """Build and validate Product Gap, update the partial manifest and stop before Action."""
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
    skill10 = skills / "10-product-gap"
    shared = skills / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
    python = sys.executable

    signals_path = artifacts / "signals.json"
    ot_path = artifacts / "opportunity_threat.json"
    bundle_path = artifacts / "approved_opportunity_threat_bundle.json"
    mapping_path = artifacts / "product_mapping.json"
    mapping_review = reviews / "product-mapping-review.md"
    gate2_decision = reviews / "02-opportunity-threat-decision.json"
    products_path = skill10 / "references" / "products.json"
    mapping_validation_report = validation / "product-mapping-validation-report.json"
    mapping_dependency_report = validation / "product-mapping-dependency-audit.json"

    protected = [
        signals_path,
        ot_path,
        bundle_path,
        mapping_path,
        mapping_review,
        reviews / "01-news-relevance-review.md",
        reviews / "01-news-relevance-decision.json",
        validation / "gate-1-validation-report.json",
        reviews / "02-opportunity-threat-review.md",
        gate2_decision,
        validation / "gate-2-validation-report.json",
        PROJECT_ROOT / "PIPELINE_VERSION.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "DEPENDENCY_MATRIX.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "HITL_GATE_POLICY.md",
        skills / "02-competitor-news" / "references" / "competitors.json",
        products_path,
    ]
    protected_before = _hashes(protected)
    if protected_before[str(products_path)] != EXPECTED_PRODUCTS_SHA256:
        raise RuntimeError("products.json hash does not match the frozen Product Gap catalog")

    context_path = intermediate / "product_gap_context.json"
    matrix_path = intermediate / "product_gap_capability_matrix.json"
    draft_path = intermediate / "product_gap_draft.json"
    gap_path = artifacts / "product_gap.json"
    gap_report = validation / "product-gap-validation-report.json"
    lineage_report = validation / "product-gap-lineage-validation-report.json"
    evidence_report = validation / "product-gap-portfolio-evidence-report.json"
    coverage_report = validation / "product-gap-coverage-report.json"
    manual_review = reviews / "product-gap-review.md"
    final_targets = [gap_path, gap_report, lineage_report, evidence_report, coverage_report, manual_review]
    existing = [str(path) for path in final_targets if path.exists()]
    if existing:
        raise ValueError(f"Refusing to overwrite Skill 10 final outputs: {existing}")
    if not draft_path.is_file():
        raise ValueError(f"Semantic draft must be authored before the driver runs: {draft_path}")
    forbidden_downstream = [
        artifacts / "actions.json",
        reviews / "03-product-action-review.md",
        reviews / "03-product-action-decision.json",
        artifacts / "quality_control_report.json",
    ]
    present_downstream = [str(path) for path in forbidden_downstream if path.exists()]
    if present_downstream:
        raise ValueError(f"Downstream output already exists; Skill 10 scope cannot proceed: {present_downstream}")

    log_path = PROJECT_ROOT / "workspace" / "logs" / f"{run_id}.log"
    log_lines = [f"SKILL_10_START {_utc_now()}", f"RUN_ID {run_id}", "SCOPE Product Gap only"]
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
        if manifest.get("stage_statuses", {}).get("PRODUCT_MAPPING") != "COMPLETED":
            raise RuntimeError("Product Mapping stage must be COMPLETED")
        review = _parse_frontmatter(mapping_review)
        if review.get("status") != "REVIEWED_ACCEPTED" or not review.get("reviewer") or not review.get("reviewed_at"):
            raise RuntimeError("Product Mapping manual inspection must be REVIEWED_ACCEPTED with reviewer and reviewed_at")
        existing_mapping_validation = _load(mapping_validation_report)
        if existing_mapping_validation.get("status") != "PASS":
            raise RuntimeError("Existing Product Mapping validation report is not PASS")
        dependency = _load(mapping_dependency_report)
        if dependency.get("audit_status") != "PASS" or dependency.get("forbidden_runtime_references"):
            raise RuntimeError("Product Mapping dependency audit is not PASS")
        mapping_validation = _run([
            python, str(skill09 / "scripts" / "validate_artifact.py"),
            "--artifact", str(mapping_path),
            "--schema", str(skill09 / "schemas" / "output.schema.json"),
            "--signals", str(signals_path),
            "--approved-ot-bundle", str(bundle_path),
            "--decision", str(gate2_decision),
        ], log_lines)
        if mapping_validation.get("status") != "PASS":
            raise RuntimeError("Product Mapping revalidation failed")

        _run([
            python, str(skill10 / "scripts" / "prepare_context.py"),
            "--product-mapping", str(mapping_path),
            "--products", str(products_path),
            "--signals", str(signals_path),
            "--approved-ot-bundle", str(bundle_path),
            "--product-mapping-review", str(mapping_review),
            "--output", str(context_path), "--overwrite",
        ], log_lines)
        _run([
            python, str(skill10 / "scripts" / "build_capability_matrix.py"),
            "--context", str(context_path), "--output", str(matrix_path), "--overwrite",
        ], log_lines)
        _run([
            python, str(skill10 / "scripts" / "build_artifact.py"),
            "--product-mapping", str(mapping_path), "--draft", str(draft_path),
            "--schema", str(skill10 / "schemas" / "output.schema.json"), "--output", str(gap_path),
        ], log_lines)
        gap_validation = _run([
            python, str(skill10 / "scripts" / "validate_artifact.py"),
            "--artifact", str(gap_path), "--schema", str(skill10 / "schemas" / "output.schema.json"),
            "--product-mapping", str(mapping_path), "--products", str(products_path),
            "--signals", str(signals_path), "--approved-ot-bundle", str(bundle_path),
            "--decision", str(gate2_decision), "--report", str(gap_report),
        ], log_lines)
        lineage_validation = _run([
            python, str(shared / "validate_stage_lineage.py"), "--mode", "product-gap",
            "--product-gap", str(gap_path), "--product-mapping", str(mapping_path),
            "--signals", str(signals_path), "--approved-ot-bundle", str(bundle_path),
            "--decision", str(gate2_decision), "--report", str(lineage_report),
        ], log_lines)
        evidence_validation = _run([
            python, str(skill10 / "scripts" / "validate_portfolio_evidence.py"),
            "--products", str(products_path), "--product-gap", str(gap_path),
            "--report", str(evidence_report),
        ], log_lines)
        coverage = _run([
            python, str(skill10 / "scripts" / "build_coverage_report.py"),
            "--product-mapping", str(mapping_path), "--product-gap", str(gap_path),
            "--draft", str(draft_path), "--output", str(coverage_report),
        ], log_lines)
        _run([
            python, str(skill10 / "scripts" / "generate_manual_review.py"),
            "--product-mapping", str(mapping_path), "--product-gap", str(gap_path),
            "--output", str(manual_review),
        ], log_lines)

        manifest.update({
            "completed_at": _utc_now(), "run_mode": "PARTIAL", "current_stage": "PRODUCT_GAP",
            "pipeline_status": "COMPLETED", "pipeline_can_continue": True,
            "blocking_gate": None, "blocking_reasons": [],
        })
        manifest["stage_statuses"].update({
            "PRODUCT_MAPPING": "COMPLETED", "PRODUCT_GAP": "COMPLETED",
            "ACTION_RECOMMENDATION": "NOT_IN_SCOPE", "PRODUCT_ACTION_HITL": "NOT_IN_SCOPE",
            "MI_QUALITY_CONTROL": "NOT_IN_SCOPE",
        })
        manifest["artifacts"]["product_gap"] = _relative(gap_path)
        manifest["reviews"]["product_gap_manual_review"] = _relative(manual_review)
        manifest["validation_reports"].update({
            "product_gap_validation": _relative(gap_report),
            "product_gap_lineage_validation": _relative(lineage_report),
            "product_gap_portfolio_evidence": _relative(evidence_report),
            "product_gap_coverage": _relative(coverage_report),
        })
        _write(manifest_path, manifest)
        runtime_validation = _run([
            python, str(shared / "validate_json_schema.py"),
            "--schema", str(skills / "00-news-driven-mi-orchestrator" / "schemas" / "runtime-run-manifest.schema.json"),
            "--instance", str(manifest_path),
        ], log_lines)
        _write(validation / "runtime-manifest-validation-report.json", runtime_validation)

        protected_after = _hashes(protected)
        if protected_before != protected_after:
            changed = [path for path in protected_before if protected_before[path] != protected_after.get(path)]
            raise RuntimeError(f"Protected Gate/Contract/catalog integrity changed: {changed}")
        if any(path.exists() for path in forbidden_downstream):
            raise RuntimeError("Skill 10 created forbidden downstream output")

        gap = _load(gap_path)
        evidence = _load(evidence_report)
        coverage_data = _load(coverage_report)
        counts = Counter(item.get("capability_status") for item in gap.get("items", []))
        log_lines.extend([
            f"PRODUCT_MAPPING_REVALIDATION {mapping_validation['status']}",
            f"PRODUCT_GAP_VALIDATION {gap_validation['status']}",
            f"PRODUCT_GAP_LINEAGE {lineage_validation['status']}",
            f"PORTFOLIO_EVIDENCE {evidence_validation['status']}",
            f"PRODUCT_GAP_COVERAGE {coverage['status']}",
            "PROTECTED_INTEGRITY PASS", "SCOPE_STOP Action Recommendation not executed",
            f"SKILL_10_END {_utc_now()}",
        ])
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(
            existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "")
            + "\n".join(log_lines) + "\n",
            encoding="utf-8",
        )
        return {
            "status": "PASS", "run_id": run_id,
            "product_mapping_count": len(_load(mapping_path).get("items", [])),
            "product_gap_count": len(gap.get("items", [])),
            "capability_status_counts": {
                key: counts.get(key, 0) for key in ["FULL_MATCH", "PARTIAL_MATCH", "NO_MATCH", "UNKNOWN"]
            },
            "unresolved_mapping_ids": coverage_data.get("unresolved_mapping_ids", []),
            "portfolio_evidence_error_count": evidence.get("error_count", 0),
            "portfolio_evidence_warning_count": evidence.get("warning_count", 0),
            "schema_validation": gap_validation.get("schema_status"),
            "lineage_validation": lineage_validation.get("status"),
            "portfolio_evidence_validation": evidence_validation.get("status"),
            "coverage_validation": coverage.get("status"),
            "pipeline_can_continue": True,
            "next_stage_executed": False,
            "actions_created": False,
            "protected_integrity": "PASS",
            "product_mapping_sha256": protected_after[str(mapping_path)],
            "products_sha256": protected_after[str(products_path)],
        }
    except Exception:
        log_lines.append(f"SKILL_10_FAILED {_utc_now()}")
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(
            existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "")
            + "\n".join(log_lines) + "\n",
            encoding="utf-8",
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run_skill_10(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
