#!/usr/bin/env python3
"""Validate all three human gates and the final approved/deferred Action portfolios."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

VALIDATORS = Path(__file__).resolve().parents[2] / "00-news-driven-mi-orchestrator" / "scripts" / "validators"
sys.path.insert(0, str(VALIDATORS))
from validate_hitl_sets import validate_hitl_sets  # noqa: E402

from qc_common import finding, load_json, parse_frontmatter, resolve_index_path, result, write_json


def check_gate(
    name: str, decision: dict[str, Any], source_ids: set[str], reviewed_field: str,
    decision_fields: list[str], approved_field: str, revision_field: str,
) -> dict[str, Any]:
    """Create one finding for approval status and union/disjoint/source-ID semantics."""
    report = validate_hitl_sets(decision, reviewed_field, decision_fields, source_ids, approved_field)
    approved = decision.get("overall_status") == "APPROVED"
    reviewer = bool(decision.get("reviewer") and decision.get("reviewed_at"))
    no_revision = not decision.get(revision_field, [])
    passed = report.get("status") == "PASS" and approved and reviewer and no_revision
    error_codes = [item.get("code") for item in report.get("errors", [])]
    return finding(
        f"{name} human approval and decision sets", "PASS" if passed else "ERROR",
        "INFO" if passed else "CRITICAL",
        f"{name} is human-APPROVED; all {len(source_ids)} source IDs are reviewed once with disjoint decision sets."
        if passed else f"{name} is not a complete valid approval; set/status errors: {error_codes}.",
        sorted(source_ids - set(decision.get(reviewed_field, []))),
        "Return to the human gate, review every source ID exactly once, remove overlaps/revisions, and rebuild the manifest." if not passed else None,
    )


def run_checks(data: dict[str, Any]) -> dict[str, Any]:
    """Validate Gate 1/2/3 and exact canonical final Action portfolios."""
    findings: list[dict[str, Any]] = []
    news_ids = {
        item.get("news_id") for artifact in data["news_artifacts"]
        for item in artifact.get("items", []) if isinstance(item, dict)
    }
    ot_ids = {item.get("ot_id") for item in data["opportunity_threat"].get("items", []) if isinstance(item, dict)}
    action_by_id = {item.get("action_id"): item for item in data["actions"].get("items", []) if isinstance(item, dict)}
    action_ids = set(action_by_id)
    findings.append(check_gate(
        "Gate 1", data["gate_1_decision"], news_ids, "reviewed_news_ids",
        ["kept_news_ids", "excluded_news_ids", "revision_news_ids"], "kept_news_ids", "revision_news_ids",
    ))
    findings.append(check_gate(
        "Gate 2", data["gate_2_decision"], ot_ids, "reviewed_ot_ids",
        ["approved_ot_ids", "rejected_ot_ids", "revision_ot_ids"], "approved_ot_ids", "revision_ot_ids",
    ))
    findings.append(check_gate(
        "Gate 3", data["gate_3_decision"], action_ids, "reviewed_action_ids",
        ["approved_action_ids", "rejected_action_ids", "revision_action_ids", "deferred_action_ids"],
        "approved_action_ids", "revision_action_ids",
    ))
    decision = data["gate_3_decision"]
    approved_ids = decision.get("approved_action_ids", [])
    approved_items = data["approved_actions"].get("items", [])
    approved_bundle_ids = [item.get("action_id") for item in approved_items if isinstance(item, dict)]
    exact_approved = (
        set(approved_bundle_ids) == set(approved_ids)
        and len(approved_bundle_ids) == len(set(approved_bundle_ids))
        and all(action_by_id.get(item.get("action_id")) == item for item in approved_items if isinstance(item, dict))
        and data["approved_actions"].get("gate_status") == "APPROVED"
    )
    findings.append(finding(
        "Approved Action portfolio", "PASS" if exact_approved else "ERROR", "INFO" if exact_approved else "CRITICAL",
        f"Approved portfolio contains exact canonical copies of {len(approved_ids)} Gate 3-approved Actions."
        if exact_approved else "Approved Action portfolio differs from Gate 3 or canonical actions.json.",
        sorted(set(approved_ids) ^ set(approved_bundle_ids)),
        "Rebuild the approved bundle from a semantically valid human APPROVED Gate 3 decision; do not edit Action records." if not exact_approved else None,
    ))
    deferred_ids = decision.get("deferred_action_ids", [])
    deferred_items = data["deferred_actions"].get("items", [])
    deferred_bundle_ids = [item.get("action_id") for item in deferred_items if isinstance(item, dict)]
    exact_deferred = set(deferred_bundle_ids) == set(deferred_ids) and len(deferred_bundle_ids) == len(set(deferred_bundle_ids))
    findings.append(finding(
        "Deferred Action backlog", "PASS" if exact_deferred else "ERROR", "INFO" if exact_deferred else "HIGH",
        f"Deferred backlog correctly contains {len(deferred_ids)} Action(s), including a valid empty backlog."
        if exact_deferred else "Deferred Action backlog does not match the Gate 3 decision.",
        sorted(set(deferred_ids) ^ set(deferred_bundle_ids)),
        "Rebuild the deferred bundle from the validated Gate 3 decision." if not exact_deferred else None,
    ))
    review_meta = data.get("review_meta", {})
    consistent = all(
        review_meta.get(key, {}).get("reviewer") == data[f"gate_{number}_decision"].get("reviewer")
        and review_meta.get(key, {}).get("reviewed_at") == data[f"gate_{number}_decision"].get("reviewed_at")
        for key, number in [("gate_1_review", 1), ("gate_2_review", 2), ("gate_3_review", 3)]
    )
    findings.append(finding(
        "Review and decision metadata consistency", "PASS" if consistent else "ERROR", "INFO" if consistent else "HIGH",
        "All formal review Markdown artifacts agree with their decision manifests on reviewer and reviewed_at."
        if consistent else "At least one formal review disagrees with its decision manifest.",
        [], "Reconcile the human-authored review and rebuild its decision manifest without inventing metadata." if not consistent else None,
    ))
    return result("HITL_AND_FINAL_DECISION", findings)


def load_inputs(index: dict[str, Any], root: Path) -> dict[str, Any]:
    """Load the minimum read-only data required by Gate checks."""
    artifacts = index["artifact_paths"]
    decisions = index["decision_paths"]
    reviews = index["review_paths"]
    load_artifact = lambda name: load_json(resolve_index_path(root, artifacts[name]))
    return {
        "news_artifacts": [load_artifact(name) for name in ["market_news", "competitor_news", "technology_news", "policy_news"]],
        "opportunity_threat": load_artifact("opportunity_threat"), "actions": load_artifact("actions"),
        "approved_actions": load_artifact("approved_actions"), "deferred_actions": load_artifact("deferred_actions"),
        "gate_1_decision": load_json(resolve_index_path(root, decisions["gate_1_decision"])),
        "gate_2_decision": load_json(resolve_index_path(root, decisions["gate_2_decision"])),
        "gate_3_decision": load_json(resolve_index_path(root, decisions["gate_3_decision"])),
        "review_meta": {name: parse_frontmatter(resolve_index_path(root, path)) for name, path in reviews.items() if name.startswith("gate_")},
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
