#!/usr/bin/env python3
"""Run WR3 News stages 01-04 from synthetic or live raw input and stop at Gate 1."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from news_crawl_runtime import review_translation_gate

PROJECT_ROOT = Path(__file__).resolve().parent
RUN_ID_PATTERN = re.compile(r"^[0-9]{8}-[0-9]{6}-(synthetic|live)$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _resolve_input(value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (PROJECT_ROOT / value).resolve()


def _run(command: list[str], log_lines: list[str]) -> dict[str, Any]:
    """Run one Python stage without shell access and return its JSON output."""
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


def _relative(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def run_vertical_slice(input_path: Path, run_id: str) -> dict[str, Any]:
    """Build, validate and stop the run at a non-approved Gate 1."""
    match = RUN_ID_PATTERN.fullmatch(run_id)
    if not match:
        raise ValueError("run_id must match YYYYMMDD-HHMMSS-(synthetic|live)")
    input_path = _resolve_input(input_path)
    if not input_path.is_file():
        raise ValueError(f"Input file not found: {input_path}")
    try:
        raw_payload = json.loads(input_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid raw input JSON: {exc}") from exc
    if not isinstance(raw_payload.get("synthetic"), bool):
        raise ValueError("Raw input root must contain boolean synthetic")
    synthetic = raw_payload["synthetic"]
    if not synthetic:
        translation_gate = review_translation_gate(raw_payload.get("records", []))
        if translation_gate["status"] != "PASS":
            raise ValueError(
                "Vietnamese review translation gate failed: "
                f"{len(translation_gate['pending_records'])} record(s) pending"
            )

    run_root = PROJECT_ROOT / "workspace" / "runs" / run_id
    if run_root.exists():
        raise ValueError(f"Run already exists; refusing overwrite: {run_root}")
    artifacts_dir = run_root / "artifacts"
    reviews_dir = run_root / "reviews"
    validation_dir = run_root / "validation"
    log_path = PROJECT_ROOT / "workspace" / "logs" / f"{run_id}.log"
    for directory in [artifacts_dir, reviews_dir, validation_dir, log_path.parent]:
        directory.mkdir(parents=True, exist_ok=True)

    python = sys.executable
    skills_root = PROJECT_ROOT / ".agents" / "skills"
    contract_schema_path = skills_root / "00-news-driven-mi-orchestrator" / "schemas" / "pipeline_manifest.schema.json"
    runtime_schema_path = skills_root / "00-news-driven-mi-orchestrator" / "schemas" / "runtime-run-manifest.schema.json"
    started_at = _utc_now()
    log_lines = [
        f"START {started_at}",
        f"RUN_ID {run_id}",
        "SCOPE stages 01-05 only; Gate 1 remains human-controlled",
        f"Contract schema: {_relative(contract_schema_path)}",
        f"Runtime schema: {_relative(runtime_schema_path)}",
    ]
    stage_specs = [
        ("01-market-news", "market_news.json", "market", "MARKET"),
        ("02-competitor-news", "competitor_news.json", "competitor", "COMPETITOR"),
        ("03-technology-news", "technology_news.json", "technology", "TECHNOLOGY"),
        ("04-policy-news", "policy_news.json", "policy", "POLICY"),
    ]
    artifact_paths: dict[str, Path] = {}
    validation_results: dict[str, Any] = {}
    lineage: list[dict[str, Any]] = []
    try:
        expected_mode = "synthetic" if synthetic else "live"
        if match.group(1) != expected_mode:
            raise RuntimeError(f"Run ID suffix must be -{expected_mode} for this input")
        raw_positions: dict[str, int] = {}
        for position, record in enumerate(raw_payload.get("records", [])):
            raw_news_id = str(record.get("raw_news_id"))
            if raw_news_id in raw_positions:
                raise RuntimeError(f"Duplicate raw_news_id in input: {raw_news_id}")
            raw_positions[raw_news_id] = position

        for folder, filename, key, news_type in stage_specs:
            skill_dir = skills_root / folder
            output = artifacts_dir / filename
            build_command = [
                python, str(skill_dir / "scripts" / "build_artifact.py"),
                "--input", str(input_path), "--output", str(output), "--run-id", run_id,
            ]
            if folder == "02-competitor-news":
                build_command.extend(["--competitors", str(skill_dir / "references" / "competitors.json")])
            build_result = _run(build_command, log_lines)
            for mapping in build_result.get("lineage", []):
                raw_news_id = str(mapping["raw_news_id"])
                if raw_news_id not in raw_positions:
                    raise RuntimeError(f"Builder returned unknown raw_news_id: {raw_news_id}")
                lineage.append({
                    "raw_news_id": raw_news_id,
                    "news_id": mapping["news_id"],
                    "news_type": news_type,
                    "artifact_path": _relative(output),
                    "input_position": raw_positions[raw_news_id],
                })
            artifact_paths[key] = output
            validation_results[key] = _run([
                python, str(skill_dir / "scripts" / "validate_artifact.py"),
                "--artifact", str(output), "--schema", str(skill_dir / "schemas" / "output.schema.json"),
            ], log_lines)

        artifacts = [json.loads(path.read_text(encoding="utf-8")) for path in artifact_paths.values()]
        all_ids = [item["news_id"] for artifact in artifacts for item in artifact["items"]]
        global_duplicates = sorted({value for value in all_ids if all_ids.count(value) > 1})
        if global_duplicates:
            raise RuntimeError(f"Global duplicate news IDs: {global_duplicates}")

        lineage_path = validation_dir / "news-lineage.json"
        lineage_payload = {
            "run_id": run_id,
            "synthetic": synthetic,
            "mapping_count": len(lineage),
            "mappings": lineage,
        }
        lineage_path.write_text(json.dumps(lineage_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        lineage_report_path = validation_dir / "news-lineage-validation-report.json"
        lineage_report = _run([
            python,
            str(skills_root / "00-news-driven-mi-orchestrator" / "scripts" / "validators" / "validate_news_lineage.py"),
            "--lineage", str(lineage_path),
            "--schema", str(skills_root / "00-news-driven-mi-orchestrator" / "schemas" / "news-lineage.schema.json"),
            "--market", str(artifact_paths["market"]),
            "--competitor", str(artifact_paths["competitor"]),
            "--technology", str(artifact_paths["technology"]),
            "--policy", str(artifact_paths["policy"]),
            "--input", str(input_path),
            "--report", str(lineage_report_path),
        ], log_lines)
        news_report = {
            "status": "PASS",
            "run_id": run_id,
            "artifact_validation": validation_results,
            "global_news_id_unique": True,
            "total_items": len(all_ids),
            "counts": {key: result["item_count"] for key, result in validation_results.items()},
        }
        news_report_path = validation_dir / "news-validation-report.json"
        news_report_path.write_text(json.dumps(news_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        review_path = reviews_dir / "01-news-relevance-review.md"
        hitl_dir = skills_root / "05-news-relevance-hitl"
        _run([
            python, str(hitl_dir / "scripts" / "generate_review.py"),
            "--market", str(artifact_paths["market"]),
            "--competitor", str(artifact_paths["competitor"]),
            "--technology", str(artifact_paths["technology"]),
            "--policy", str(artifact_paths["policy"]),
            "--template", str(hitl_dir / "references" / "REVIEW_TEMPLATE.md"),
            "--run-id", run_id, "--output", str(review_path),
        ], log_lines)

        decision_path = reviews_dir / "01-news-relevance-decision.json"
        _run([
            python, str(hitl_dir / "scripts" / "build_decision_manifest.py"),
            "--review", str(review_path), "--output", str(decision_path),
        ], log_lines)
        gate_report_path = validation_dir / "gate-1-validation-report.json"
        gate_report = _run([
            python, str(hitl_dir / "scripts" / "validate_decision.py"),
            "--decision", str(decision_path),
            "--schema", str(hitl_dir / "schemas" / "review-decision.schema.json"),
            "--market", str(artifact_paths["market"]),
            "--competitor", str(artifact_paths["competitor"]),
            "--technology", str(artifact_paths["technology"]),
            "--policy", str(artifact_paths["policy"]),
            "--report", str(gate_report_path),
        ], log_lines)
        if gate_report["pipeline_can_continue"]:
            raise RuntimeError("Initial review must not permit pipeline continuation")

        completed_at = _utc_now()
        runtime_manifest_report_path = validation_dir / "runtime-manifest-validation-report.json"
        manifest = {
            "runtime_manifest_version": "1.0.0-runtime",
            "contract_version": "1.0.0-contract",
            "run_id": run_id,
            "synthetic": synthetic,
            "started_at": started_at,
            "completed_at": completed_at,
            "run_mode": "PARTIAL",
            "current_stage": "NEWS_RELEVANCE_HITL",
            "pipeline_status": "BLOCKED",
            "pipeline_can_continue": False,
            "blocking_gate": "NEWS_RELEVANCE_HITL",
            "blocking_reasons": ["HUMAN_REVIEW_PENDING"],
            "stage_statuses": {
                "MARKET_NEWS": "COMPLETED",
                "COMPETITOR_NEWS": "COMPLETED",
                "TECHNOLOGY_NEWS": "COMPLETED",
                "POLICY_NEWS": "COMPLETED",
                "NEWS_RELEVANCE_HITL": "BLOCKED",
                "SIGNAL_SYNTHESIS": "NOT_IN_SCOPE",
                "OPPORTUNITY_THREAT": "NOT_IN_SCOPE",
                "OPPORTUNITY_THREAT_HITL": "NOT_IN_SCOPE",
                "PRODUCT_MAPPING": "NOT_IN_SCOPE",
                "PRODUCT_GAP": "NOT_IN_SCOPE",
                "ACTION_RECOMMENDATION": "NOT_IN_SCOPE",
                "PRODUCT_ACTION_HITL": "NOT_IN_SCOPE",
                "MI_QUALITY_CONTROL": "NOT_IN_SCOPE"
            },
            "artifacts": {
                **{f"{key}_news": _relative(path) for key, path in artifact_paths.items()},
                "raw_news_input": _relative(input_path),
                "news_lineage": _relative(lineage_path),
            },
            "reviews": {
                "news_relevance_review": _relative(review_path),
                "news_relevance_decision": _relative(decision_path),
            },
            "validation_reports": {
                "news_validation": _relative(news_report_path),
                "news_lineage_validation": _relative(lineage_report_path),
                "gate_1_validation": _relative(gate_report_path),
                "runtime_manifest_validation": _relative(runtime_manifest_report_path),
            },
            "log_path": _relative(log_path),
        }
        manifest_path = run_root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        runtime_manifest_validation = _run([
            python,
            str(skills_root / "00-news-driven-mi-orchestrator" / "scripts" / "validators" / "validate_json_schema.py"),
            "--schema", str(runtime_schema_path),
            "--instance", str(manifest_path),
        ], log_lines)
        runtime_manifest_report_path.write_text(
            json.dumps(runtime_manifest_validation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        log_lines.extend([
            f"RUNTIME_MANIFEST_VALIDATION {runtime_manifest_validation['status']}",
            f"NEWS_LINEAGE_VALIDATION {lineage_report['status']}",
            f"GATE_STATUS {gate_report['gate_status']}",
            "PIPELINE_CAN_CONTINUE false",
            f"END {completed_at}",
        ])
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        return {
            "status": "PASS",
            "run_id": run_id,
            "run_root": str(run_root),
            "counts": news_report["counts"],
            "overall_status": gate_report["gate_status"],
            "semantic_validation": gate_report["semantic_status"],
            "runtime_manifest_validation": runtime_manifest_validation["status"],
            "news_lineage_validation": lineage_report["status"],
            "pipeline_can_continue": False,
            "blocking_reasons": gate_report["blocking_reasons"],
            "synthetic": synthetic,
        }
    except Exception:
        log_lines.append(f"FAILED {_utc_now()}")
        log_path.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    if args.run_id:
        run_id = args.run_id
    else:
        try:
            payload = json.loads(_resolve_input(args.input).read_text(encoding="utf-8"))
            suffix = "synthetic" if payload.get("synthetic") is True else "live"
        except (OSError, json.JSONDecodeError):
            suffix = "live"
        run_id = datetime.now().strftime(f"%Y%m%d-%H%M%S-{suffix}")
    try:
        result = run_vertical_slice(args.input, run_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
