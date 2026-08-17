#!/usr/bin/env python3
"""Continue one approved run through Signal, O/T and a PENDING Gate 2."""

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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _relative(path: Path) -> str:
    return path.resolve().relative_to(PROJECT_ROOT).as_posix()


def _load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc


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


def run_vertical_slice(run_dir: Path) -> dict[str, Any]:
    """Validate Gate 1, create stages 06-08 outputs, then stop at Gate 2."""
    run_dir = run_dir.resolve() if run_dir.is_absolute() else (PROJECT_ROOT / run_dir).resolve()
    runs_root = (PROJECT_ROOT / "workspace" / "runs").resolve()
    if not run_dir.is_relative_to(runs_root) or not run_dir.is_dir():
        raise ValueError(f"run-dir must be an existing child of {runs_root}")
    artifacts_dir = run_dir / "artifacts"
    reviews_dir = run_dir / "reviews"
    validation_dir = run_dir / "validation"
    manifest_path = run_dir / "manifest.json"
    manifest = _load(manifest_path)
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or run_dir.name != run_id:
        raise ValueError("run-dir name and manifest run_id must match")
    synthetic = manifest.get("synthetic")
    if not isinstance(synthetic, bool):
        raise ValueError("manifest synthetic must be boolean")

    skills = PROJECT_ROOT / ".agents" / "skills"
    python = sys.executable
    gate1_review = reviews_dir / "01-news-relevance-review.md"
    gate1_decision = reviews_dir / "01-news-relevance-decision.json"
    gate1_report = validation_dir / "gate-1-validation-report.json"
    news_paths = {
        "market": artifacts_dir / "market_news.json",
        "competitor": artifacts_dir / "competitor_news.json",
        "technology": artifacts_dir / "technology_news.json",
        "policy": artifacts_dir / "policy_news.json",
    }
    protected_gate1 = [gate1_review, gate1_decision, gate1_report, *news_paths.values()]
    gate1_hash_before = _hashes(protected_gate1)

    approved_bundle = artifacts_dir / "approved_news_bundle.json"
    signals_path = artifacts_dir / "signals.json"
    ot_path = artifacts_dir / "opportunity_threat.json"
    gate2_review = reviews_dir / "02-opportunity-threat-review.md"
    gate2_decision = reviews_dir / "02-opportunity-threat-decision.json"
    approved_report = validation_dir / "approved-news-validation-report.json"
    signal_report = validation_dir / "signal-validation-report.json"
    signal_coverage = validation_dir / "signal-coverage-report.json"
    ot_report = validation_dir / "opportunity-threat-validation-report.json"
    ot_coverage = validation_dir / "opportunity-threat-coverage-report.json"
    gate2_report = validation_dir / "gate-2-validation-report.json"
    targets = [
        approved_bundle, signals_path, ot_path, gate2_review, gate2_decision,
        approved_report, signal_report, signal_coverage, ot_report, ot_coverage, gate2_report,
    ]
    live_resume_inputs = {approved_bundle, signals_path, approved_report} if not synthetic else set()
    existing = [str(path) for path in targets if path.exists() and path not in live_resume_inputs]
    if existing:
        raise ValueError(f"Refusing to overwrite vertical slice 2 outputs: {existing}")

    log_path = PROJECT_ROOT / "workspace" / "logs" / f"{run_id}.log"
    log_lines = [f"VERTICAL_SLICE_2_START {_utc_now()}", f"RUN_ID {run_id}", "SCOPE stages 06-08 only"]
    skill05 = skills / "05-news-relevance-hitl"
    skill06 = skills / "06-signal-synthesis"
    skill07 = skills / "07-opportunity-threat"
    skill08 = skills / "08-opportunity-threat-hitl"
    shared = skills / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
    try:
        gate1_validation = _run([
            python, str(skill05 / "scripts" / "validate_decision.py"),
            "--decision", str(gate1_decision),
            "--schema", str(skill05 / "schemas" / "review-decision.schema.json"),
            "--market", str(news_paths["market"]),
            "--competitor", str(news_paths["competitor"]),
            "--technology", str(news_paths["technology"]),
            "--policy", str(news_paths["policy"]),
        ], log_lines)
        decision = _load(gate1_decision)
        if not (
            gate1_validation.get("pipeline_can_continue") is True
            and gate1_validation.get("gate_status") == "APPROVED"
            and decision.get("overall_status") == "APPROVED"
            and decision.get("revision_news_ids") == []
        ):
            raise RuntimeError("Gate 1 is not the expected valid APPROVED decision")

        if not approved_bundle.exists():
            _run([
                python, str(skill06 / "scripts" / "build_approved_news_bundle.py"),
                "--decision", str(gate1_decision), "--review", str(gate1_review),
                "--market", str(news_paths["market"]), "--competitor", str(news_paths["competitor"]),
                "--technology", str(news_paths["technology"]), "--policy", str(news_paths["policy"]),
                "--output", str(approved_bundle),
            ], log_lines)
        approved_validation = _run([
            python, str(shared / "validate_stage_lineage.py"), "--mode", "approved-news",
            "--bundle", str(approved_bundle), "--decision", str(gate1_decision), "--review", str(gate1_review),
            "--market", str(news_paths["market"]), "--competitor", str(news_paths["competitor"]),
            "--technology", str(news_paths["technology"]), "--policy", str(news_paths["policy"]),
            "--report", str(approved_report),
        ], log_lines)
        if synthetic:
            _run([python, str(skill06 / "scripts" / "build_artifact.py"), "--approved-news", str(approved_bundle), "--output", str(signals_path)], log_lines)
        elif not signals_path.exists():
            raise RuntimeError(
                f"Live Signal Synthesis requires the current chat LLM to author {signals_path} "
                f"from {approved_bundle}; rerun after the artifact is written"
            )
        signal_validation = _run([
            python, str(skill06 / "scripts" / "validate_artifact.py"),
            "--artifact", str(signals_path), "--schema", str(skill06 / "schemas" / "output.schema.json"),
            "--approved-news", str(approved_bundle), "--decision", str(gate1_decision), "--report", str(signal_report),
        ], log_lines)
        signal_coverage_result = _run([
            python, str(skill06 / "scripts" / "build_coverage_report.py"),
            "--approved-news", str(approved_bundle), "--signals", str(signals_path),
            "--decision", str(gate1_decision), "--output", str(signal_coverage),
        ], log_lines)
        _run([
            python, str(skill07 / "scripts" / "build_artifact.py"),
            "--signals", str(signals_path), "--approved-news", str(approved_bundle), "--output", str(ot_path),
        ], log_lines)
        ot_validation = _run([
            python, str(skill07 / "scripts" / "validate_artifact.py"),
            "--artifact", str(ot_path), "--schema", str(skill07 / "schemas" / "output.schema.json"),
            "--signals", str(signals_path), "--report", str(ot_report),
        ], log_lines)
        ot_coverage_result = _run([
            python, str(skill07 / "scripts" / "build_coverage_report.py"),
            "--signals", str(signals_path), "--opportunity-threat", str(ot_path), "--output", str(ot_coverage),
        ], log_lines)
        _run([
            python, str(skill08 / "scripts" / "generate_review.py"),
            "--signals", str(signals_path), "--opportunity-threat", str(ot_path),
            "--template", str(skill08 / "references" / "REVIEW_TEMPLATE.md"),
            "--run-id", run_id, "--output", str(gate2_review),
        ], log_lines)
        _run([
            python, str(skill08 / "scripts" / "build_decision_manifest.py"),
            "--review", str(gate2_review), "--output", str(gate2_decision),
        ], log_lines)
        gate2_validation = _run([
            python, str(skill08 / "scripts" / "validate_decision.py"),
            "--decision", str(gate2_decision), "--schema", str(skill08 / "schemas" / "review-decision.schema.json"),
            "--opportunity-threat", str(ot_path), "--report", str(gate2_report),
        ], log_lines)
        if gate2_validation.get("gate_status") != "PENDING" or gate2_validation.get("pipeline_can_continue") is not False:
            raise RuntimeError("Initial Gate 2 decision must be PENDING and blocked")

        runtime_report = validation_dir / "runtime-manifest-validation-report.json"
        manifest.update({
            "completed_at": _utc_now(),
            "run_mode": "PARTIAL",
            "current_stage": "OPPORTUNITY_THREAT_HITL",
            "pipeline_status": "BLOCKED",
            "pipeline_can_continue": False,
            "blocking_gate": "OPPORTUNITY_THREAT_HITL",
            "blocking_reasons": ["HUMAN_REVIEW_PENDING"],
        })
        manifest["stage_statuses"].update({
            "MARKET_NEWS": "COMPLETED", "COMPETITOR_NEWS": "COMPLETED",
            "TECHNOLOGY_NEWS": "COMPLETED", "POLICY_NEWS": "COMPLETED",
            "NEWS_RELEVANCE_HITL": "COMPLETED", "SIGNAL_SYNTHESIS": "COMPLETED",
            "OPPORTUNITY_THREAT": "COMPLETED", "OPPORTUNITY_THREAT_HITL": "BLOCKED",
            "PRODUCT_MAPPING": "NOT_IN_SCOPE", "PRODUCT_GAP": "NOT_IN_SCOPE",
            "ACTION_RECOMMENDATION": "NOT_IN_SCOPE", "PRODUCT_ACTION_HITL": "NOT_IN_SCOPE",
            "MI_QUALITY_CONTROL": "NOT_IN_SCOPE",
        })
        manifest["artifacts"].update({
            "approved_news_bundle": _relative(approved_bundle), "signals": _relative(signals_path),
            "opportunity_threat": _relative(ot_path),
        })
        manifest["reviews"].update({
            "opportunity_threat_review": _relative(gate2_review),
            "opportunity_threat_decision": _relative(gate2_decision),
        })
        manifest["validation_reports"].update({
            "approved_news_validation": _relative(approved_report),
            "signal_validation": _relative(signal_report), "signal_coverage": _relative(signal_coverage),
            "opportunity_threat_validation": _relative(ot_report),
            "opportunity_threat_coverage": _relative(ot_coverage),
            "gate_2_validation": _relative(gate2_report),
            "runtime_manifest_validation": _relative(runtime_report),
        })
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        runtime_validation = _run([
            python, str(shared / "validate_json_schema.py"),
            "--schema", str(skills / "00-news-driven-mi-orchestrator" / "schemas" / "runtime-run-manifest.schema.json"),
            "--instance", str(manifest_path),
        ], log_lines)
        runtime_report.write_text(json.dumps(runtime_validation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        gate1_hash_after = _hashes(protected_gate1)
        if gate1_hash_before != gate1_hash_after:
            raise RuntimeError("Protected Gate 1 artifact hash changed")
        signals = _load(signals_path)
        ot = _load(ot_path)
        coverage = _load(signal_coverage)
        ot_cov = _load(ot_coverage)
        log_lines.extend([
            "GATE_1_INTEGRITY PASS", f"APPROVED_NEWS_VALIDATION {approved_validation['status']}",
            f"SIGNAL_VALIDATION {signal_validation['status']}", f"SIGNAL_COVERAGE {signal_coverage_result['status']}",
            f"OT_VALIDATION {ot_validation['status']}", f"OT_COVERAGE {ot_coverage_result['status']}",
            "GATE_2_STATUS PENDING", "PIPELINE_CAN_CONTINUE false", "SCOPE_STOP Product Mapping not executed",
            f"VERTICAL_SLICE_2_END {_utc_now()}",
        ])
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "") + "\n".join(log_lines) + "\n", encoding="utf-8")
        return {
            "status": "PASS", "run_id": run_id,
            "approved_news_count": len(_load(approved_bundle)["approved_news"]),
            "signal_count": len(signals["items"]),
            "opportunity_count": ot_cov["opportunity_count"], "threat_count": ot_cov["threat_count"],
            "unused_kept_news_ids": coverage["unused_kept_news_ids"],
            "signals_without_ot": ot_cov["signal_ids_without_ot"],
            "gate_2_status": gate2_validation["gate_status"],
            "pipeline_can_continue": False, "blocking_reasons": gate2_validation["blocking_reasons"],
            "runtime_manifest_validation": runtime_validation["status"], "gate_1_integrity": "PASS",
        }
    except Exception:
        log_lines.append(f"VERTICAL_SLICE_2_FAILED {_utc_now()}")
        existing_log = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        log_path.write_text(existing_log + ("\n" if existing_log and not existing_log.endswith("\n") else "") + "\n".join(log_lines) + "\n", encoding="utf-8")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(run_vertical_slice(args.run_dir), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
