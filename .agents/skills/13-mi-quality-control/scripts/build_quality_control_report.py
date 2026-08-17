#!/usr/bin/env python3
"""Assemble deterministic QC findings and compute release eligibility."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from qc_common import finding, load_json, result, write_json


def build_report(
    run_id: str, synthetic: bool, check_groups: list[dict[str, Any]],
    integrity: dict[str, Any], manifest: dict[str, Any], contract_version: str,
) -> dict[str, Any]:
    """Merge check groups, append integrity/runtime/release checks and assign QC IDs."""
    findings = [dict(item) for group in check_groups for item in group.get("findings", [])]
    integrity_ok = integrity.get("integrity_status") == "PASS"
    findings.append(finding(
        "Hash and source immutability", "PASS" if integrity_ok else "ERROR", "INFO" if integrity_ok else "CRITICAL",
        f"Integrity baseline covers {integrity.get('file_count', 0)} files and all immutable source hashes are unchanged."
        if integrity_ok else f"Integrity failures: {integrity.get('failed_logical_names', [])}.",
        integrity.get("failed_logical_names", []), "Restore immutable files from the reviewed baseline and repeat affected reviews." if not integrity_ok else None,
    ))
    expected_stages = [
        "MARKET_NEWS", "COMPETITOR_NEWS", "TECHNOLOGY_NEWS", "POLICY_NEWS", "NEWS_RELEVANCE_HITL",
        "SIGNAL_SYNTHESIS", "OPPORTUNITY_THREAT", "OPPORTUNITY_THREAT_HITL", "PRODUCT_MAPPING",
        "PRODUCT_GAP", "ACTION_RECOMMENDATION", "PRODUCT_ACTION_HITL",
    ]
    runtime_bad = [stage for stage in expected_stages if manifest.get("stage_statuses", {}).get(stage) != "COMPLETED"]
    runtime_ok = (
        manifest.get("run_id") == run_id and manifest.get("contract_version") == contract_version
        and manifest.get("synthetic") is synthetic and not runtime_bad
        and manifest.get("blocking_gate") is None and not manifest.get("blocking_reasons")
        and manifest.get("stage_statuses", {}).get("MI_QUALITY_CONTROL") != "COMPLETED"
    )
    findings.append(finding(
        "Runtime manifest pre-QC consistency", "PASS" if runtime_ok else "ERROR", "INFO" if runtime_ok else "HIGH",
        "Runtime manifest matches the run, all stages 01–12 are completed, no gate blocks, and QC was not pre-marked complete."
        if runtime_ok else f"Runtime manifest is inconsistent before QC; affected stages: {runtime_bad}.",
        runtime_bad, "Correct runtime state through the owning stage driver; do not use the manifest to manufacture release readiness." if not runtime_ok else None,
    ))
    root_errors = sum(item.get("status") == "ERROR" for item in findings)
    findings.append(finding(
        "Release readiness evaluation", "PASS" if root_errors == 0 else "ERROR", "INFO" if root_errors == 0 else "CRITICAL",
        "No QC ERROR exists; warnings are disclosed and the synthetic pipeline is eligible to conclude QC."
        if root_errors == 0 else f"Release is not eligible because {root_errors} preceding QC ERROR finding(s) exist.",
        [], "Complete every ERROR remediation and rerun QC without altering reviewed evidence in place." if root_errors else None,
    ))
    checks = [{"check_id": f"QC-{index:03d}", **item} for index, item in enumerate(findings, start=1)]
    error_count = sum(item["status"] == "ERROR" for item in checks)
    warning_count = sum(item["status"] == "WARNING" for item in checks)
    passed_count = sum(item["status"] == "PASS" for item in checks)
    overall = "ERROR" if error_count else ("WARNING" if warning_count else "PASS")
    return {
        "artifact_type": "quality_control_report", "run_id": run_id, "synthetic": synthetic,
        "summary": {
            "overall_status": overall, "error_count": error_count, "warning_count": warning_count,
            "passed_count": passed_count, "pipeline_eligible_for_release": error_count == 0,
        },
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--synthetic", choices=["true", "false"], required=True)
    parser.add_argument("--contract-version", required=True)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--integrity", required=True, type=Path)
    parser.add_argument("--check-report", action="append", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite QC report: {args.output}")
        report = build_report(
            args.run_id, args.synthetic == "true", [load_json(path) for path in args.check_report],
            load_json(args.integrity), load_json(args.manifest), args.contract_version,
        )
        write_json(args.output, report)
        print(json.dumps({"status": "PASS", "output": str(args.output), **report["summary"], "check_count": len(report["checks"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

