#!/usr/bin/env python3
"""Run raw-to-final cross-stage lineage and canonical bundle consistency checks."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_news_lineage import validate_news_lineage  # noqa: E402
from validate_stage_lineage import (  # noqa: E402
    parse_gate1_corrected_types, validate_action_lineage, validate_approved_news_bundle,
    validate_approved_ot_bundle, validate_gate3_lineage, validate_ot_lineage,
    validate_product_gap_lineage, validate_product_mapping_lineage, validate_signal_lineage,
)

from qc_common import finding, load_json, resolve_index_path, result, write_json


def _affected(report: dict[str, Any]) -> list[str]:
    values: set[str] = set()
    for error in report.get("errors", []):
        if not isinstance(error, dict):
            continue
        for key, value in error.items():
            if key.endswith("_id") and isinstance(value, str):
                values.add(value)
            elif key.endswith("_ids") and isinstance(value, list):
                values.update(str(item) for item in value)
    return sorted(values)


def _report_finding(name: str, report: dict[str, Any], success: str) -> dict[str, Any]:
    passed = report.get("status") == "PASS"
    return finding(
        name, "PASS" if passed else "ERROR", "INFO" if passed else "CRITICAL",
        success if passed else f"{name} failed with {len(report.get('errors', []))} lineage issue(s).",
        _affected(report), "Return to the owning stage, repair source lineage, repeat downstream reviews, and rerun QC." if not passed else None,
    )


def run_checks(data: dict[str, Any]) -> dict[str, Any]:
    """Validate every parent/child and bundle copy from raw News through Gate 3."""
    findings: list[dict[str, Any]] = []
    news_report = validate_news_lineage(
        data["news_lineage"], data["news_lineage_schema"], data["news_with_paths"], data["raw_news"]
    )
    findings.append(_report_finding("Raw News to canonical News lineage", news_report, "Every selected raw News record maps to a valid canonical News ID with correct type and path."))
    news_artifacts = [payload for _, payload in data["news_with_paths"].values()]
    approved_news_report = validate_approved_news_bundle(
        data["approved_news"], data["gate_1_decision"], news_artifacts, data.get("corrected_types", {})
    )
    findings.append(_report_finding("Gate 1 approved News canonical bundle", approved_news_report, "Approved News contains exactly Gate 1 KEEP records with canonical content."))
    signal_report = validate_signal_lineage(
        data["signals"], data["approved_news"], set(data["gate_1_decision"].get("excluded_news_ids", []))
    )
    findings.append(_report_finding("Signal evidence lineage", signal_report, "Every Signal uses only Gate 1-kept News with matching evidence types."))
    ot_report = validate_ot_lineage(data["opportunity_threat"], data["signals"])
    findings.append(_report_finding("Opportunity/Threat Signal lineage", ot_report, "Every O/T has a valid parent Signal and unique ID."))
    approved_ot_report = validate_approved_ot_bundle(
        data["approved_ot"], data["gate_2_decision"], data["opportunity_threat"],
        data["signals"], data.get("gate_2_validation"),
    )
    findings.append(_report_finding("Gate 2 approved O/T canonical bundle", approved_ot_report, "Approved O/T bundle exactly matches Gate 2-approved canonical O/T records."))
    mapping_report = validate_product_mapping_lineage(
        data["product_mapping"], data["signals"], data["approved_ot"], data["gate_2_decision"]
    )
    findings.append(_report_finding("Product Mapping approved lineage", mapping_report, "Every Product Mapping uses valid Signals and only Gate 2-approved O/T."))
    gap_report = validate_product_gap_lineage(
        data["product_gap"], data["product_mapping"], data["signals"],
        data["approved_ot"], data["gate_2_decision"],
    )
    findings.append(_report_finding("Product Gap Mapping lineage", gap_report, "Every Product Gap preserves its Product Mapping Signal, category and required capabilities."))
    action_report = validate_action_lineage(
        data["actions"], data["signals"], data["approved_ot"], data["product_mapping"],
        data["product_gap"], data["gate_2_decision"],
    )
    findings.append(_report_finding("Action full approved lineage", action_report, "Every Action traces to a valid Signal, approved O/T, Product Mapping and Product Gap."))
    gate3_report = validate_gate3_lineage(data["gate_3_decision"], data["actions"])
    findings.append(_report_finding("Action to Gate 3 decision lineage", gate3_report, "Every Action is reviewed exactly once in Gate 3 with no unknown IDs."))
    evidence_counts = Counter(
        news_id for signal in data["signals"].get("items", []) for news_id in signal.get("evidence_news_ids", [])
    )
    kept = set(data["gate_1_decision"].get("kept_news_ids", []))
    balanced = bool(kept) and set(evidence_counts) == kept and set(evidence_counts.values()) == {1}
    if balanced:
        findings.append(finding(
            "Signal evidence distribution", "WARNING", "LOW",
            "Every Gate 1-kept News item is used exactly once across Signals; lineage is valid but the distribution is mechanically balanced.",
            sorted(kept), "Review whether evidence grouping reflects real semantic relationships rather than a coverage pattern.",
        ))
    else:
        findings.append(finding("Signal evidence distribution", "PASS", "INFO", "Signal evidence distribution is not a forced one-use-per-kept-item pattern."))
    mappings = data["product_mapping"].get("items", [])
    approved_ot_ids = set(data["gate_2_decision"].get("approved_ot_ids", []))
    one_to_one = len(mappings) == len(approved_ot_ids) and all(len(item.get("related_ot_ids", [])) == 1 for item in mappings)
    if one_to_one:
        findings.append(finding(
            "Product Mapping relationship pattern", "WARNING", "LOW",
            "Each approved O/T maps to exactly one Product Mapping; valid lineage may still reflect a mechanical one-to-one pattern.",
            sorted(item.get("product_mapping_id") for item in mappings), "Manually assess whether related requirements should be grouped or one O/T should support multiple market categories.",
        ))
    else:
        findings.append(finding("Product Mapping relationship pattern", "PASS", "INFO", "Product Mapping relationships are not uniformly one-to-one."))
    counts = {
        "raw": len(data["raw_news"].get("records", [])),
        "news": sum(len(payload.get("items", [])) for payload in news_artifacts),
        "signals": len(data["signals"].get("items", [])),
        "ot": len(data["opportunity_threat"].get("items", [])),
        "mappings": len(mappings), "gaps": len(data["product_gap"].get("items", [])),
        "actions": len(data["actions"].get("items", [])),
        "approved_actions": len(data["gate_3_decision"].get("approved_action_ids", [])),
    }
    full_pass = all(item["status"] != "ERROR" for item in findings)
    findings.append(finding(
        "Cross-stage lineage summary", "PASS" if full_pass else "ERROR", "INFO" if full_pass else "CRITICAL",
        "Full lineage validated: " + ", ".join(f"{key}={value}" for key, value in counts.items()) + ".",
        [], "Resolve the preceding lineage ERROR findings from the earliest affected stage." if not full_pass else None,
    ))
    return result("CROSS_STAGE_LINEAGE", findings)


def load_inputs(index: dict[str, Any], root: Path) -> dict[str, Any]:
    artifacts = index["artifact_paths"]
    decisions = index["decision_paths"]
    validations = index["validation_paths"]
    schemas = index["schema_paths"]
    get = lambda name: load_json(resolve_index_path(root, artifacts[name]))
    news_with_paths = {
        key: (resolve_index_path(root, artifacts[name]), get(name))
        for key, name in [("MARKET", "market_news"), ("COMPETITOR", "competitor_news"), ("TECHNOLOGY", "technology_news"), ("POLICY", "policy_news")]
    }
    gate1_review = resolve_index_path(root, index["review_paths"]["gate_1_review"])
    return {
        "raw_news": get("raw_news"), "news_lineage": get("news_lineage"),
        "news_lineage_schema": load_json(resolve_index_path(root, schemas["news_lineage_schema"])),
        "news_with_paths": news_with_paths, "approved_news": get("approved_news_bundle"),
        "signals": get("signals"), "opportunity_threat": get("opportunity_threat"),
        "approved_ot": get("approved_opportunity_threat_bundle"), "product_mapping": get("product_mapping"),
        "product_gap": get("product_gap"), "actions": get("actions"),
        "gate_1_decision": load_json(resolve_index_path(root, decisions["gate_1_decision"])),
        "gate_2_decision": load_json(resolve_index_path(root, decisions["gate_2_decision"])),
        "gate_3_decision": load_json(resolve_index_path(root, decisions["gate_3_decision"])),
        "gate_2_validation": load_json(resolve_index_path(root, validations["gate-2-validation-report"])),
        "corrected_types": parse_gate1_corrected_types(gate1_review),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = (args.project_root or Path(__file__).resolve().parents[4]).resolve()
        output = run_checks(load_inputs(load_json(args.index), root))
        write_json(args.output, output)
        print(json.dumps({"status": "PASS", "finding_count": output["finding_count"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
