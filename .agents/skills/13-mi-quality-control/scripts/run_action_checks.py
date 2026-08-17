#!/usr/bin/env python3
"""Validate Action schema/quality, coverage, summary and final approved copies."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from qc_common import finding, load_json, resolve_index_path, result, write_json


def _module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if not spec or not spec.loader:
        raise ValueError(f"Cannot load module: {path}")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def run_checks(data: dict[str, Any], validator: Any, summary_builder: Any) -> dict[str, Any]:
    """Check canonical actions without adding, changing or approving any Action."""
    findings: list[dict[str, Any]] = []
    report = validator.validate_artifact(
        data["actions"], data["action_schema"], data["signals"], data["approved_ot"],
        data["product_mapping"], data["product_gap"], data["gate_2_decision"],
    )
    valid = report.get("status") == "PASS"
    affected = sorted({
        str(item.get("action_id")) for item in report.get("errors", []) if item.get("action_id")
    })
    findings.append(finding(
        "Action schema, lineage and semantic quality", "PASS" if valid else "ERROR", "INFO" if valid else "CRITICAL",
        f"All {len(data['actions'].get('items', []))} Actions pass frozen schema, approved lineage and semantic validation."
        if valid else f"Action validation found {report.get('error_count', 0)} ERROR(s).",
        affected, "Return affected Actions to Action Recommendation and repeat Gate 3 review." if not valid else None,
    ))
    for warning in report.get("warnings", []):
        findings.append(finding(
            f"Action quality warning: {warning.get('code')}", "WARNING", "MEDIUM",
            f"Action validator reported {warning.get('code')}.",
            [str(warning["action_id"])] if warning.get("action_id") else [],
            "Review the affected Action's specificity, evidence and decision level before real use.",
        ))
    expected_summary = summary_builder.build_summary(data["actions"])
    summary_ok = expected_summary == data["action_summary"]
    findings.append(finding(
        "Action summary consistency", "PASS" if summary_ok else "ERROR", "INFO" if summary_ok else "HIGH",
        "action_summary.json exactly matches deterministic aggregation of actions.json."
        if summary_ok else "action_summary.json differs from actions.json.",
        [], "Regenerate the machine summary from unchanged actions.json; do not edit Action semantics." if not summary_ok else None,
    ))
    action_ids = [item.get("action_id") for item in data["actions"].get("items", [])]
    coverage_ok = (
        data["action_coverage"].get("validation_status") in {"PASS", "PASS_WITH_WARNINGS"}
        and set(data["action_coverage"].get("action_ids", [])) == set(action_ids)
        and not data["action_coverage"].get("duplicate_candidate_groups")
    )
    findings.append(finding(
        "Action coverage consistency", "PASS" if coverage_ok else "ERROR", "INFO" if coverage_ok else "HIGH",
        "Action coverage links and duplicate groups match actions.json." if coverage_ok else "Action coverage is stale or inconsistent.",
        [], "Regenerate coverage from unchanged Action inputs." if not coverage_ok else None,
    ))
    gaps = [tuple(sorted(item.get("gap_ids", []))) for item in data["actions"].get("items", [])]
    all_gap_ids = {item.get("gap_id") for item in data["product_gap"].get("items", [])}
    one_per_gap = len(gaps) == len(all_gap_ids) and all(len(group) == 1 for group in gaps) and {group[0] for group in gaps} == all_gap_ids
    if one_per_gap:
        findings.append(finding(
            "Action-to-Gap pattern", "WARNING", "LOW",
            "Each Product Gap produces exactly one Action; valid coverage may still reflect a mechanical one-to-one pattern.",
            sorted(str(item) for item in action_ids), "Review whether related gaps should share an Action or whether a gap needs multiple phased Actions.",
        ))
    else:
        findings.append(finding("Action-to-Gap pattern", "PASS", "INFO", "Action-to-Gap relationships are not uniformly one-to-one."))
    response_counts = Counter(item.get("recommended_response") for item in data["actions"].get("items", []))
    priority_counts = Counter(item.get("priority") for item in data["actions"].get("items", []))
    diversity = len(response_counts) > 1 and len(priority_counts) > 1
    findings.append(finding(
        "Action decision diversity", "PASS" if diversity else "WARNING", "INFO" if diversity else "LOW",
        "Actions use multiple response and priority levels." if diversity else "All Actions use the same response or priority.",
        action_ids if not diversity else [], "Reassess evidence-based response and priority levels." if not diversity else None,
    ))
    approved_ids = data["gate_3_decision"].get("approved_action_ids", [])
    approved_items = data["approved_actions"].get("items", [])
    canonical = {item.get("action_id"): item for item in data["actions"].get("items", [])}
    approved_ok = (
        [item.get("action_id") for item in approved_items] == approved_ids
        and all(canonical.get(item.get("action_id")) == item for item in approved_items)
    )
    findings.append(finding(
        "Approved Action canonical preservation", "PASS" if approved_ok else "ERROR", "INFO" if approved_ok else "CRITICAL",
        "Approved Action bundle preserves every approved Action byte-for-structure from actions.json."
        if approved_ok else "Approved Action bundle is missing, reordered or content-modified.",
        sorted(set(approved_ids) ^ {item.get("action_id") for item in approved_items}),
        "Rebuild the approved bundle from the validated Gate 3 decision." if not approved_ok else None,
    ))
    return result("ACTION_LINEAGE_AND_QUALITY", findings)


def load_inputs(index: dict[str, Any], root: Path) -> dict[str, Any]:
    artifacts = index["artifact_paths"]
    decisions = index["decision_paths"]
    validations = index["validation_paths"]
    schemas = index["schema_paths"]
    get = lambda name: load_json(resolve_index_path(root, artifacts[name]))
    return {
        "actions": get("actions"), "action_summary": get("action_summary"),
        "approved_actions": get("approved_actions"), "signals": get("signals"),
        "approved_ot": get("approved_opportunity_threat_bundle"),
        "product_mapping": get("product_mapping"), "product_gap": get("product_gap"),
        "gate_2_decision": load_json(resolve_index_path(root, decisions["gate_2_decision"])),
        "gate_3_decision": load_json(resolve_index_path(root, decisions["gate_3_decision"])),
        "action_schema": load_json(resolve_index_path(root, schemas["action_schema"])),
        "action_coverage": load_json(resolve_index_path(root, validations["action-coverage-report"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = (args.project_root or Path(__file__).resolve().parents[4]).resolve()
        skill11 = root / ".agents" / "skills" / "11-action-recommendation" / "scripts"
        output = run_checks(
            load_inputs(load_json(args.index), root),
            _module("qc_action_validator", skill11 / "validate_artifact.py"),
            _module("qc_action_summary", skill11 / "generate_action_summary.py"),
        )
        write_json(args.output, output)
        print(json.dumps({"status": "PASS", "finding_count": output["finding_count"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
