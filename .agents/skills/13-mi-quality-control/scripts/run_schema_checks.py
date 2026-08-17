#!/usr/bin/env python3
"""Run file, frozen-schema, review-frontmatter and pipeline-completeness checks."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_json_schema import validate_instance  # noqa: E402

from qc_common import finding, load_json, parse_frontmatter, resolve_index_path, result, write_json

SCHEMA_TARGETS = {
    "market_news": "market_news_schema", "competitor_news": "competitor_news_schema",
    "technology_news": "technology_news_schema", "policy_news": "policy_news_schema",
    "signals": "signal_schema", "opportunity_threat": "ot_schema",
    "product_mapping": "product_mapping_schema", "product_gap": "product_gap_schema",
    "actions": "action_schema", "news_lineage": "news_lineage_schema",
    "runtime_manifest": "runtime_manifest_schema",
}
DECISION_SCHEMAS = {
    "gate_1_decision": "gate_1_schema", "gate_2_decision": "gate_2_schema",
    "gate_3_decision": "gate_3_schema",
}


def _path(index: dict[str, Any], root: Path, group: str, name: str) -> Path:
    return resolve_index_path(root, index[group][name])


def run_checks(index: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Return one explicit check for every main artifact and supporting validation evidence."""
    findings: list[dict[str, Any]] = []
    missing = index.get("missing_paths", [])
    findings.append(finding(
        "Required file presence", "ERROR" if missing else "PASS", "CRITICAL" if missing else "INFO",
        f"Missing {len(missing)} required QC input path(s)." if missing else "All indexed QC input paths exist.",
        missing, "Restore the missing canonical input before release." if missing else None,
    ))
    artifact_paths = index.get("artifact_paths", {})
    schema_paths = index.get("schema_paths", {})
    for artifact_name, schema_name in SCHEMA_TARGETS.items():
        try:
            artifact = load_json(_path(index, project_root, "artifact_paths", artifact_name))
            schema = load_json(resolve_index_path(project_root, schema_paths[schema_name]))
            errors = validate_instance(artifact, schema)
            findings.append(finding(
                f"Schema: {artifact_name}", "ERROR" if errors else "PASS", "HIGH" if errors else "INFO",
                f"{artifact_name} fails frozen schema with {len(errors)} issue(s)." if errors else f"{artifact_name} validates against its frozen schema.",
                [artifact_name] if errors else [], "Repair the producing stage and repeat downstream review; QC must not edit this artifact." if errors else None,
            ))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            findings.append(finding(f"Schema: {artifact_name}", "ERROR", "CRITICAL", str(exc), [artifact_name], "Restore a parseable artifact and rerun its stage validation."))
    for decision_name, schema_name in DECISION_SCHEMAS.items():
        try:
            decision = load_json(_path(index, project_root, "decision_paths", decision_name))
            schema = load_json(resolve_index_path(project_root, schema_paths[schema_name]))
            errors = validate_instance(decision, schema)
            findings.append(finding(
                f"Schema: {decision_name}", "ERROR" if errors else "PASS", "CRITICAL" if errors else "INFO",
                f"{decision_name} fails frozen schema with {len(errors)} issue(s)." if errors else f"{decision_name} validates against its frozen schema.",
                [decision_name] if errors else [], "Return to the human gate workflow and rebuild the decision manifest from the review." if errors else None,
            ))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            findings.append(finding(f"Schema: {decision_name}", "ERROR", "CRITICAL", str(exc), [decision_name], "Restore the human decision artifact without inventing approval."))
    parse_only = [
        "raw_news", "approved_news_bundle", "approved_opportunity_threat_bundle",
        "action_summary", "approved_actions", "deferred_actions",
    ]
    for name in parse_only:
        try:
            load_json(_path(index, project_root, "artifact_paths", name))
            findings.append(finding(f"JSON parse: {name}", "PASS", "INFO", f"{name} is a parseable JSON object."))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            findings.append(finding(f"JSON parse: {name}", "ERROR", "CRITICAL", str(exc), [name], "Restore the canonical JSON from its producing stage; do not patch it in QC."))
    for name, relative in index.get("review_paths", {}).items():
        try:
            meta = parse_frontmatter(resolve_index_path(project_root, relative))
            formal = name in {"gate_1_review", "gate_2_review", "gate_3_review"}
            ok = bool(meta.get("reviewer") and meta.get("reviewed_at")) if formal else meta.get("status") == "REVIEWED_ACCEPTED"
            findings.append(finding(
                f"Review metadata: {name}", "PASS" if ok else "ERROR", "INFO" if ok else "CRITICAL",
                f"{name} contains completed reviewer metadata." if ok else f"{name} lacks required completed review metadata.",
                [name] if not ok else [], "Complete the human review artifact; QC cannot supply reviewer metadata." if not ok else None,
            ))
        except (OSError, ValueError) as exc:
            findings.append(finding(f"Review metadata: {name}", "ERROR", "CRITICAL", str(exc), [name], "Restore valid YAML frontmatter and obtain human review."))
    for name, relative in index.get("validation_paths", {}).items():
        try:
            payload = load_json(resolve_index_path(project_root, relative))
            status = payload.get("status", payload.get("audit_status", payload.get("validation_status")))
            ok = status in {"PASS", "PASS_WITH_WARNINGS"}
            findings.append(finding(
                f"Validation evidence: {name}", "PASS" if ok else "ERROR", "INFO" if ok else "HIGH",
                f"{name} reports {status}." if status is not None else f"{name} has no recognized validation status.",
                [name] if not ok else [], "Rerun the owning validation workflow without editing its source artifact." if not ok else None,
            ))
        except (OSError, ValueError) as exc:
            findings.append(finding(f"Validation evidence: {name}", "ERROR", "HIGH", str(exc), [name], "Restore parseable validation evidence."))
    try:
        manifest = load_json(_path(index, project_root, "artifact_paths", "runtime_manifest"))
        expected_stages = [
            "MARKET_NEWS", "COMPETITOR_NEWS", "TECHNOLOGY_NEWS", "POLICY_NEWS",
            "NEWS_RELEVANCE_HITL", "SIGNAL_SYNTHESIS", "OPPORTUNITY_THREAT",
            "OPPORTUNITY_THREAT_HITL", "PRODUCT_MAPPING", "PRODUCT_GAP",
            "ACTION_RECOMMENDATION", "PRODUCT_ACTION_HITL",
        ]
        bad = [stage for stage in expected_stages if manifest.get("stage_statuses", {}).get(stage) != "COMPLETED"]
        qc_pre = manifest.get("stage_statuses", {}).get("MI_QUALITY_CONTROL") in {"NOT_IN_SCOPE", "NOT_STARTED", "RUNNING"}
        complete = not bad and qc_pre and manifest.get("blocking_gate") is None and "HUMAN_REVIEW_PENDING" not in manifest.get("blocking_reasons", [])
        findings.append(finding(
            "Pipeline completeness before QC", "PASS" if complete else "ERROR", "INFO" if complete else "CRITICAL",
            "Stages 01–12 are completed in order and QC was not pre-marked complete." if complete else f"Pipeline stage/runtime inconsistency detected; incomplete stages: {bad}.",
            bad, "Complete the affected stage/gate and correct operational manifest state through its owning driver." if not complete else None,
        ))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        findings.append(finding("Pipeline completeness before QC", "ERROR", "CRITICAL", str(exc), ["runtime_manifest"], "Restore a valid runtime manifest."))
    return result("FILE_AND_SCHEMA_INTEGRITY", findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = (args.project_root or Path(__file__).resolve().parents[4]).resolve()
        output = run_checks(load_json(args.index), root)
        write_json(args.output, output)
        print(json.dumps({"status": "PASS", "finding_count": output["finding_count"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
