#!/usr/bin/env python3
"""Run Action Recommendation and stop at the PENDING Product Action HITL Gate 3."""

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
        raise ValueError(f"Expected JSON object: {path}")
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


def _frontmatter(path: Path) -> dict[str, str | None]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing YAML frontmatter: {path}")
    values: dict[str, str | None] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return values
        if line.startswith((" ", "\t", "-")) or ":" not in line:
            continue
        key, value = line.split(":", 1)
        cleaned = value.strip().strip("'\"")
        values[key.strip()] = None if cleaned.lower() in {"", "null", "~"} else cleaned
    raise ValueError(f"Unclosed YAML frontmatter: {path}")


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


def run_vertical_slice_04(run_dir: Path) -> dict[str, Any]:
    """Build Action proposals, create a PENDING Gate 3 review, and block for a human."""
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
    skill11 = skills / "11-action-recommendation"
    skill12 = skills / "12-product-action-hitl"
    shared = skills / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
    python = sys.executable

    signals = artifacts / "signals.json"
    ot = artifacts / "opportunity_threat.json"
    approved_ot = artifacts / "approved_opportunity_threat_bundle.json"
    mapping = artifacts / "product_mapping.json"
    gap = artifacts / "product_gap.json"
    mapping_review = reviews / "product-mapping-review.md"
    gap_review = reviews / "product-gap-review.md"
    gate2_decision = reviews / "02-opportunity-threat-decision.json"
    products = skill10 / "references" / "products.json"
    protected = [
        signals, ot, approved_ot, mapping, gap, mapping_review, gap_review,
        reviews / "01-news-relevance-review.md", reviews / "01-news-relevance-decision.json",
        validation / "gate-1-validation-report.json", reviews / "02-opportunity-threat-review.md",
        gate2_decision, validation / "gate-2-validation-report.json", PROJECT_ROOT / "PIPELINE_VERSION.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "DEPENDENCY_MATRIX.md",
        skills / "00-news-driven-mi-orchestrator" / "references" / "HITL_GATE_POLICY.md",
        skills / "02-competitor-news" / "references" / "competitors.json", products,
    ]
    protected_before = _hashes(protected)

    context = intermediate / "action_context.json"
    matrix = intermediate / "action_matrix.json"
    draft = intermediate / "actions_draft.json"
    actions = artifacts / "actions.json"
    summary = artifacts / "action_summary.json"
    action_report = validation / "action-validation-report.json"
    lineage_report = validation / "action-lineage-report.json"
    coverage_report = validation / "action-coverage-report.json"
    gate3_review = reviews / "03-product-action-review.md"
    gate3_decision = reviews / "03-product-action-decision.json"
    gate3_report = validation / "gate-3-validation-report.json"
    forbidden = [
        artifacts / "approved-actions.json", artifacts / "deferred-actions.json",
        artifacts / "quality_control_report.json",
    ]
    if any(path.exists() for path in forbidden):
        raise ValueError("Final Action or Quality Control output already exists before Gate 3 approval")
    if not draft.is_file():
        raise ValueError(f"Semantic Action draft must be authored before the driver runs: {draft}")
    rendered_draft = draft.read_text(encoding="utf-8").casefold()
    if any(marker in rendered_draft for marker in ['"reviewer"', '"overall_status"', '"review_decision"']):
        raise ValueError("Semantic Action draft contains a human-decision field")

    log_path = PROJECT_ROOT / "workspace" / "logs" / f"{run_id}.log"
    log_lines = [f"VERTICAL_SLICE_4_START {_utc_now()}", f"RUN_ID {run_id}", "SCOPE Skills 11-12 through PENDING Gate 3"]
    try:
        gate2 = _run([
            python, str(skill08 / "scripts" / "validate_decision.py"), "--decision", str(gate2_decision),
            "--schema", str(skill08 / "schemas" / "review-decision.schema.json"), "--opportunity-threat", str(ot),
        ], log_lines)
        if gate2.get("gate_status") != "APPROVED" or gate2.get("pipeline_can_continue") is not True:
            raise RuntimeError("Gate 2 is not a valid human APPROVED decision")
        stages = manifest.get("stage_statuses", {})
        if stages.get("PRODUCT_MAPPING") != "COMPLETED" or stages.get("PRODUCT_GAP") != "COMPLETED":
            raise RuntimeError("Product Mapping and Product Gap must be COMPLETED")
        gap_meta = _frontmatter(gap_review)
        if gap_meta.get("status") != "REVIEWED_ACCEPTED" or not gap_meta.get("reviewer") or not gap_meta.get("reviewed_at"):
            raise RuntimeError("Product Gap review must be REVIEWED_ACCEPTED with reviewer and reviewed_at")

        mapping_validation = _run([
            python, str(skill09 / "scripts" / "validate_artifact.py"), "--artifact", str(mapping),
            "--schema", str(skill09 / "schemas" / "output.schema.json"), "--signals", str(signals),
            "--approved-ot-bundle", str(approved_ot), "--decision", str(gate2_decision),
        ], log_lines)
        gap_validation = _run([
            python, str(skill10 / "scripts" / "validate_artifact.py"), "--artifact", str(gap),
            "--schema", str(skill10 / "schemas" / "output.schema.json"), "--product-mapping", str(mapping),
            "--products", str(products), "--signals", str(signals), "--approved-ot-bundle", str(approved_ot),
            "--decision", str(gate2_decision),
        ], log_lines)
        gap_lineage = _run([
            python, str(shared / "validate_stage_lineage.py"), "--mode", "product-gap", "--product-gap", str(gap),
            "--product-mapping", str(mapping), "--signals", str(signals), "--approved-ot-bundle", str(approved_ot),
            "--decision", str(gate2_decision),
        ], log_lines)
        gap_evidence = _run([
            python, str(skill10 / "scripts" / "validate_portfolio_evidence.py"), "--products", str(products),
            "--product-gap", str(gap),
        ], log_lines)
        if any(result.get("status") != "PASS" for result in [mapping_validation, gap_validation, gap_lineage, gap_evidence]):
            raise RuntimeError("Upstream Product Mapping or Product Gap revalidation failed")

        _run([
            python, str(skill11 / "scripts" / "prepare_context.py"), "--signals", str(signals),
            "--approved-ot-bundle", str(approved_ot), "--product-mapping", str(mapping), "--product-gap", str(gap),
            "--product-gap-review", str(gap_review), "--decision", str(gate2_decision),
            "--output", str(context), "--overwrite",
        ], log_lines)
        _run([
            python, str(skill11 / "scripts" / "build_action_matrix.py"), "--context", str(context),
            "--output", str(matrix), "--overwrite",
        ], log_lines)
        _run([
            python, str(skill11 / "scripts" / "build_artifact.py"), "--context", str(context), "--draft", str(draft),
            "--schema", str(skill11 / "schemas" / "output.schema.json"), "--output", str(actions), "--overwrite",
        ], log_lines)
        action_validation = _run([
            python, str(skill11 / "scripts" / "validate_artifact.py"), "--artifact", str(actions),
            "--schema", str(skill11 / "schemas" / "output.schema.json"), "--signals", str(signals),
            "--approved-ot-bundle", str(approved_ot), "--product-mapping", str(mapping), "--product-gap", str(gap),
            "--decision", str(gate2_decision), "--report", str(action_report),
        ], log_lines)
        action_lineage = _run([
            python, str(shared / "validate_stage_lineage.py"), "--mode", "action", "--actions", str(actions),
            "--signals", str(signals), "--approved-ot-bundle", str(approved_ot), "--product-mapping", str(mapping),
            "--product-gap", str(gap), "--decision", str(gate2_decision), "--report", str(lineage_report),
        ], log_lines)
        coverage = _run([
            python, str(skill11 / "scripts" / "build_coverage_report.py"), "--context", str(context),
            "--actions", str(actions), "--draft", str(draft), "--output", str(coverage_report),
        ], log_lines)
        _run([
            python, str(skill11 / "scripts" / "generate_action_summary.py"), "--actions", str(actions),
            "--output", str(summary), "--overwrite",
        ], log_lines)
        if action_validation.get("status") != "PASS" or action_lineage.get("status") != "PASS" or coverage.get("status") == "FAIL":
            raise RuntimeError("Action validation, lineage, or coverage failed")

        if not gate3_review.exists():
            _run([
                python, str(skill12 / "scripts" / "generate_review.py"), "--signals", str(signals),
                "--approved-ot-bundle", str(approved_ot), "--product-mapping", str(mapping), "--product-gap", str(gap),
                "--actions", str(actions), "--output", str(gate3_review),
            ], log_lines)
        review_meta = _frontmatter(gate3_review)
        if review_meta.get("overall_status") != "PENDING" or review_meta.get("reviewer") is not None or review_meta.get("reviewed_at") is not None:
            raise RuntimeError("Initial Gate 3 review must remain PENDING with no reviewer metadata")
        if not gate3_decision.exists():
            _run([
                python, str(skill12 / "scripts" / "build_decision_manifest.py"), "--review", str(gate3_review),
                "--output", str(gate3_decision),
            ], log_lines)
        decision = _load(gate3_decision)
        action_ids = {item.get("action_id") for item in _load(actions).get("items", [])}
        if decision.get("overall_status") != "PENDING" or any(decision.get(field) for field in [
            "reviewed_action_ids", "approved_action_ids", "rejected_action_ids", "revision_action_ids", "deferred_action_ids"
        ]) or decision.get("reviewer") is not None or decision.get("reviewed_at") is not None:
            raise RuntimeError("Initial Gate 3 decision manifest is not a clean PENDING decision")
        gate3 = _run([
            python, str(skill12 / "scripts" / "validate_decision.py"), "--decision", str(gate3_decision),
            "--schema", str(skill12 / "schemas" / "review-decision.schema.json"), "--actions", str(actions),
            "--report", str(gate3_report),
        ], log_lines)
        if gate3.get("status") != "PASS" or gate3.get("gate_status") != "PENDING" or gate3.get("pipeline_can_continue") is not False:
            raise RuntimeError("Gate 3 PENDING validation did not block continuation correctly")
        if set(gate3.get("set_validation", {}).get("unreviewed_ids", [])) != action_ids:
            raise RuntimeError("Gate 3 set validation did not identify all Action IDs as unreviewed")

        manifest.update({
            "completed_at": _utc_now(), "run_mode": "PARTIAL", "current_stage": "PRODUCT_ACTION_HITL",
            "pipeline_status": "BLOCKED", "pipeline_can_continue": False,
            "blocking_gate": "PRODUCT_ACTION_HITL", "blocking_reasons": ["HUMAN_REVIEW_PENDING"],
        })
        manifest["stage_statuses"].update({
            "ACTION_RECOMMENDATION": "COMPLETED", "PRODUCT_ACTION_HITL": "BLOCKED",
            "MI_QUALITY_CONTROL": "NOT_IN_SCOPE",
        })
        manifest["artifacts"].update({"actions": _relative(actions), "action_summary": _relative(summary)})
        manifest["reviews"].update({
            "product_action_review": _relative(gate3_review), "product_action_decision": _relative(gate3_decision),
        })
        manifest["validation_reports"].update({
            "action_validation": _relative(action_report), "action_lineage": _relative(lineage_report),
            "action_coverage": _relative(coverage_report), "gate_3_validation": _relative(gate3_report),
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
            changed = [path for path, digest in protected_before.items() if protected_after.get(path) != digest]
            raise RuntimeError(f"Protected upstream, contract, review, or catalog files changed: {changed}")
        if any(path.exists() for path in forbidden):
            raise RuntimeError("A final Action or Quality Control output was created while Gate 3 is PENDING")

        action_data = _load(actions)
        summary_data = _load(summary)
        report_data = _load(action_report)
        log_lines.extend([
            f"ACTION_COUNT {len(action_data.get('items', []))}", f"ACTION_VALIDATION {action_validation['status']}",
            f"ACTION_LINEAGE {action_lineage['status']}", f"GATE_3 {gate3['gate_status']}",
            "PIPELINE_CAN_CONTINUE false", "PROTECTED_INTEGRITY PASS", "SCOPE_STOP Skill 13 not executed",
            f"VERTICAL_SLICE_4_END {_utc_now()}",
        ])
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(
            existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "")
            + "\n".join(log_lines) + "\n", encoding="utf-8",
        )
        return {
            "status": "PASS", "run_id": run_id, "action_count": len(action_data.get("items", [])),
            "response_counts": summary_data.get("response_counts", {}),
            "priority_counts": summary_data.get("priority_counts", {}),
            "build_buy_partner_counts": summary_data.get("build_buy_partner_counts", {}),
            "pilot_or_productize_counts": summary_data.get("pilot_or_productize_counts", {}),
            "approved_ot_ids_without_action": _load(coverage_report).get("ot_ids_without_action", []),
            "gap_ids_without_action": _load(coverage_report).get("gap_ids_without_action", []),
            "semantic_warning_count": report_data.get("warning_count", 0),
            "schema_validation": action_validation.get("schema_status"),
            "lineage_validation": action_lineage.get("status"), "gate_3_validation": gate3.get("status"),
            "overall_status": gate3.get("gate_status"), "pipeline_can_continue": False,
            "blocking_reasons": gate3.get("blocking_reasons", []), "protected_integrity": "PASS",
            "product_mapping_sha256_before": protected_before[str(mapping)],
            "product_mapping_sha256_after": protected_after[str(mapping)],
            "product_gap_sha256_before": protected_before[str(gap)],
            "product_gap_sha256_after": protected_after[str(gap)],
            "gate_1_decision_sha256_before": protected_before[str(reviews / "01-news-relevance-decision.json")],
            "gate_1_decision_sha256_after": protected_after[str(reviews / "01-news-relevance-decision.json")],
            "gate_2_decision_sha256_before": protected_before[str(gate2_decision)],
            "gate_2_decision_sha256_after": protected_after[str(gate2_decision)],
            "contract_sha256_before": protected_before[str(skills / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md")],
            "contract_sha256_after": protected_after[str(skills / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md")],
            "catalog_sha256_before": protected_before[str(products)],
            "catalog_sha256_after": protected_after[str(products)],
            "auto_approved": False, "skill_13_executed": False, "final_action_bundles_created": False,
        }
    except Exception:
        log_lines.append(f"VERTICAL_SLICE_4_FAILED {_utc_now()}")
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(
            existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "")
            + "\n".join(log_lines) + "\n", encoding="utf-8",
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run_vertical_slice_04(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
