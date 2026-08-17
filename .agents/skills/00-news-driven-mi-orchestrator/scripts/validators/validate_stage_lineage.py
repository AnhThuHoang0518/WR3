#!/usr/bin/env python3
"""Validate lineage from approved News through Action and Gate 3 artifacts."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from validate_hitl_sets import validate_hitl_sets
from validate_json_schema import load_json


def parse_gate1_corrected_types(review_path: Path | None) -> dict[str, str]:
    """Return explicit KEEP-row news_type corrections from Gate 1 Markdown."""
    if review_path is None:
        return {}
    lines = review_path.read_text(encoding="utf-8").splitlines()
    header_index = next((i for i, line in enumerate(lines) if line.startswith("| news_id |")), None)
    if header_index is None:
        raise ValueError("Gate 1 review table header not found")
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    corrections: dict[str, str] = {}
    for line in lines[header_index + 2:]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(headers):
            raise ValueError("Gate 1 review row has invalid column count")
        row = dict(zip(headers, cells))
        corrected = row.get("corrected_news_type", "").upper()
        if row.get("relevance_decision", "").upper() == "KEEP" and corrected not in {"", "NULL", "PENDING"}:
            corrections[row["news_id"]] = corrected
    return corrections


def _result(errors: list[dict[str, Any]], **counts: Any) -> dict[str, Any]:
    return {"status": "PASS" if not errors else "FAIL", **counts, "errors": errors}


def _canonical_news(artifacts: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    news: dict[str, dict[str, Any]] = {}
    errors: list[dict[str, Any]] = []
    for artifact in artifacts:
        for item in artifact.get("items", []):
            news_id = item.get("news_id")
            if news_id in news:
                errors.append({"code": "DUPLICATE_CANONICAL_NEWS_ID", "news_id": news_id})
            news[news_id] = item
    return news, errors


def validate_approved_news_bundle(
    bundle: dict[str, Any],
    decision: dict[str, Any],
    artifacts: list[dict[str, Any]],
    corrected_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Validate exact Gate 1 KEEP selection and canonical content preservation."""
    corrected_types = corrected_types or {}
    canonical, errors = _canonical_news(artifacts)
    kept = decision.get("kept_news_ids", [])
    excluded = set(decision.get("excluded_news_ids", []))
    bundle_items = bundle.get("approved_news", []) if isinstance(bundle.get("approved_news"), list) else []
    ids = [item.get("news_id") for item in bundle_items if isinstance(item, dict)]
    duplicates = sorted(news_id for news_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_APPROVED_NEWS_ID", "news_ids": duplicates})
    if decision.get("overall_status") != "APPROVED":
        errors.append({"code": "GATE_1_NOT_APPROVED"})
    if bundle.get("run_id") != decision.get("run_id"):
        errors.append({"code": "RUN_ID_MISMATCH"})
    if bundle.get("approval_status") != "APPROVED":
        errors.append({"code": "INVALID_APPROVAL_STATUS"})
    if bundle.get("kept_news_count") != len(kept) or bundle.get("excluded_news_count") != len(excluded):
        errors.append({"code": "DECISION_COUNT_MISMATCH"})
    if set(ids) != set(kept):
        errors.append({
            "code": "KEEP_SET_MISMATCH",
            "missing_kept_ids": sorted(set(kept) - set(ids)),
            "unexpected_ids": sorted(set(ids) - set(kept)),
        })
    excluded_present = sorted(set(ids) & excluded)
    if excluded_present:
        errors.append({"code": "EXCLUDED_NEWS_PRESENT", "news_ids": excluded_present})
    unknown = sorted(set(ids) - set(canonical))
    if unknown:
        errors.append({"code": "UNKNOWN_NEWS_ID", "news_ids": unknown})
    for item in bundle_items:
        if not isinstance(item, dict) or item.get("news_id") not in canonical:
            continue
        expected = copy.deepcopy(canonical[item["news_id"]])
        if item["news_id"] in corrected_types:
            expected["news_type"] = corrected_types[item["news_id"]]
        if item != expected:
            errors.append({"code": "CANONICAL_CONTENT_MISMATCH", "news_id": item["news_id"]})
    return _result(errors, expected_kept_count=len(kept), actual_bundle_count=len(ids))


def validate_signal_lineage(
    signals: dict[str, Any], bundle: dict[str, Any], excluded_news_ids: set[str] | None = None
) -> dict[str, Any]:
    """Validate Signal IDs and evidence links against Gate 1 KEEP News only."""
    errors: list[dict[str, Any]] = []
    excluded_news_ids = excluded_news_ids or set()
    approved = {item["news_id"]: item for item in bundle.get("approved_news", [])}
    signal_items = signals.get("items", []) if isinstance(signals.get("items"), list) else []
    signal_ids = [item.get("signal_id") for item in signal_items if isinstance(item, dict)]
    duplicates = sorted(signal_id for signal_id, count in Counter(signal_ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_SIGNAL_ID", "signal_ids": duplicates})
    if signals.get("run_id") != bundle.get("run_id"):
        errors.append({"code": "RUN_ID_MISMATCH"})
    for signal in signal_items:
        evidence_ids = signal.get("evidence_news_ids", [])
        if not evidence_ids:
            errors.append({"code": "SIGNAL_WITHOUT_EVIDENCE", "signal_id": signal.get("signal_id")})
            continue
        unknown = sorted(set(evidence_ids) - set(approved))
        if unknown:
            errors.append({"code": "EVIDENCE_NOT_KEPT", "signal_id": signal.get("signal_id"), "news_ids": unknown})
        excluded = sorted(set(evidence_ids) & excluded_news_ids)
        if excluded:
            errors.append({"code": "EXCLUDED_EVIDENCE", "signal_id": signal.get("signal_id"), "news_ids": excluded})
        expected_types = {approved[news_id]["news_type"] for news_id in evidence_ids if news_id in approved}
        actual_types = set(signal.get("evidence_types", []))
        if expected_types != actual_types:
            errors.append({
                "code": "EVIDENCE_TYPES_MISMATCH",
                "signal_id": signal.get("signal_id"),
                "expected": sorted(expected_types),
                "actual": sorted(actual_types),
            })
    return _result(errors, signal_count=len(signal_items), approved_news_count=len(approved))


def validate_ot_lineage(opportunity_threat: dict[str, Any], signals: dict[str, Any]) -> dict[str, Any]:
    """Validate O/T IDs and parent Signal links."""
    errors: list[dict[str, Any]] = []
    signal_ids = {item.get("signal_id") for item in signals.get("items", [])}
    ot_items = opportunity_threat.get("items", []) if isinstance(opportunity_threat.get("items"), list) else []
    ot_ids = [item.get("ot_id") for item in ot_items if isinstance(item, dict)]
    duplicates = sorted(ot_id for ot_id, count in Counter(ot_ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_OT_ID", "ot_ids": duplicates})
    if opportunity_threat.get("run_id") != signals.get("run_id"):
        errors.append({"code": "RUN_ID_MISMATCH"})
    for item in ot_items:
        if item.get("signal_id") not in signal_ids:
            errors.append({"code": "ORPHAN_OT", "ot_id": item.get("ot_id"), "signal_id": item.get("signal_id")})
    return _result(errors, ot_count=len(ot_items), signal_count=len(signal_ids))


def validate_gate2_lineage(decision: dict[str, Any], opportunity_threat: dict[str, Any]) -> dict[str, Any]:
    """Validate Gate 2 decision sets against available O/T IDs."""
    all_ids = {item.get("ot_id") for item in opportunity_threat.get("items", [])}
    return validate_hitl_sets(
        decision,
        "reviewed_ot_ids",
        ["approved_ot_ids", "rejected_ot_ids", "revision_ot_ids"],
        all_ids,
        "approved_ot_ids",
    )


def validate_approved_ot_bundle(
    bundle: dict[str, Any],
    decision: dict[str, Any],
    opportunity_threat: dict[str, Any],
    signals: dict[str, Any],
    gate_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate exact Gate 2 APPROVE selection and canonical O/T content."""
    errors: list[dict[str, Any]] = []
    canonical = {item.get("ot_id"): item for item in opportunity_threat.get("items", [])}
    signal_ids = {item.get("signal_id") for item in signals.get("items", [])}
    approved = decision.get("approved_ot_ids", [])
    rejected = set(decision.get("rejected_ot_ids", []))
    revisions = set(decision.get("revision_ot_ids", []))
    items = bundle.get("approved_opportunity_threat", [])
    ids = [item.get("ot_id") for item in items if isinstance(item, dict)]
    duplicates = sorted(ot_id for ot_id, count in Counter(ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_APPROVED_OT_ID", "ot_ids": duplicates})
    if decision.get("overall_status") != "APPROVED":
        errors.append({"code": "GATE_2_NOT_APPROVED"})
    if gate_report is not None and gate_report.get("pipeline_can_continue") is not True:
        errors.append({"code": "GATE_2_CANNOT_CONTINUE"})
    if bundle.get("approval_status") != "APPROVED":
        errors.append({"code": "INVALID_APPROVAL_STATUS"})
    if len(revisions) > 0:
        errors.append({"code": "REVISION_OT_PRESENT_IN_DECISION", "ot_ids": sorted(revisions)})
    if not (
        bundle.get("run_id") == decision.get("run_id") == opportunity_threat.get("run_id") == signals.get("run_id")
    ):
        errors.append({"code": "RUN_ID_MISMATCH"})
    if bundle.get("synthetic") is not opportunity_threat.get("synthetic"):
        errors.append({"code": "SYNTHETIC_MISMATCH"})
    if bundle.get("approved_ot_count") != len(approved) or bundle.get("rejected_ot_count") != len(rejected):
        errors.append({"code": "DECISION_COUNT_MISMATCH"})
    if set(ids) != set(approved):
        errors.append({
            "code": "APPROVED_OT_SET_MISMATCH",
            "missing_approved_ot_ids": sorted(set(approved) - set(ids)),
            "unexpected_ot_ids": sorted(set(ids) - set(approved)),
        })
    leaked = sorted(set(ids) & (rejected | revisions))
    if leaked:
        errors.append({"code": "NON_APPROVED_OT_PRESENT", "ot_ids": leaked})
    unknown = sorted(set(ids) - set(canonical))
    if unknown:
        errors.append({"code": "UNKNOWN_OT_ID", "ot_ids": unknown})
    for item in items:
        if not isinstance(item, dict):
            errors.append({"code": "INVALID_APPROVED_OT_ITEM"})
            continue
        ot_id = item.get("ot_id")
        if ot_id in canonical and item != canonical[ot_id]:
            errors.append({"code": "CANONICAL_OT_CONTENT_MISMATCH", "ot_id": ot_id})
        if item.get("signal_id") not in signal_ids:
            errors.append({"code": "ORPHAN_APPROVED_OT", "ot_id": ot_id, "signal_id": item.get("signal_id")})
    return _result(errors, expected_approved_count=len(approved), actual_bundle_count=len(ids))


def validate_product_mapping_lineage(
    product_mapping: dict[str, Any],
    signals: dict[str, Any],
    approved_ot_bundle: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Validate Product Mapping IDs and links against approved Signal/O/T inputs."""
    errors: list[dict[str, Any]] = []
    signal_ids = {item.get("signal_id") for item in signals.get("items", [])}
    approved_items = {
        item.get("ot_id"): item for item in approved_ot_bundle.get("approved_opportunity_threat", [])
    }
    rejected_ids = set(decision.get("rejected_ot_ids", [])) | set(decision.get("revision_ot_ids", []))
    mappings = product_mapping.get("items", []) if isinstance(product_mapping.get("items"), list) else []
    mapping_ids = [item.get("product_mapping_id") for item in mappings if isinstance(item, dict)]
    duplicates = sorted(mapping_id for mapping_id, count in Counter(mapping_ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_PRODUCT_MAPPING_ID", "product_mapping_ids": duplicates})
    if not (
        product_mapping.get("run_id") == signals.get("run_id") == approved_ot_bundle.get("run_id") == decision.get("run_id")
    ):
        errors.append({"code": "RUN_ID_MISMATCH"})
    seen_links: set[tuple[str, tuple[str, ...]]] = set()
    for mapping in mappings:
        mapping_id = mapping.get("product_mapping_id")
        signal_id = mapping.get("signal_id")
        related = mapping.get("related_ot_ids", [])
        if signal_id not in signal_ids:
            errors.append({"code": "UNKNOWN_SIGNAL_ID", "product_mapping_id": mapping_id, "signal_id": signal_id})
        if not related:
            errors.append({"code": "MAPPING_WITHOUT_APPROVED_OT", "product_mapping_id": mapping_id})
        unknown = sorted(set(related) - set(approved_items))
        if unknown:
            errors.append({"code": "UNKNOWN_OR_UNAPPROVED_OT_ID", "product_mapping_id": mapping_id, "ot_ids": unknown})
        rejected = sorted(set(related) & rejected_ids)
        if rejected:
            errors.append({"code": "REJECTED_OT_LEAKAGE", "product_mapping_id": mapping_id, "ot_ids": rejected})
        for ot_id in related:
            parent = approved_items.get(ot_id, {}).get("signal_id")
            if parent and parent != signal_id and "cross-signal linkage:" not in str(mapping.get("fit_rationale", "")).lower():
                errors.append({
                    "code": "OT_SIGNAL_MISMATCH_WITHOUT_RATIONALE",
                    "product_mapping_id": mapping_id,
                    "ot_id": ot_id,
                    "mapping_signal_id": signal_id,
                    "ot_signal_id": parent,
                })
        pair = (str(signal_id), tuple(sorted(str(ot_id) for ot_id in related)))
        if pair in seen_links:
            errors.append({"code": "DUPLICATE_MAPPING_LINK_SET", "product_mapping_id": mapping_id})
        seen_links.add(pair)
    return _result(
        errors,
        product_mapping_count=len(mappings),
        approved_ot_count=len(approved_items),
        signal_count=len(signal_ids),
    )


def validate_product_gap_lineage(
    product_gap: dict[str, Any],
    product_mapping: dict[str, Any],
    signals: dict[str, Any],
    approved_ot_bundle: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    """Validate Product Gap preservation and its full approved upstream chain."""
    mapping_result = validate_product_mapping_lineage(
        product_mapping, signals, approved_ot_bundle, decision
    )
    errors: list[dict[str, Any]] = [dict(item) for item in mapping_result["errors"]]
    mappings = {
        item.get("product_mapping_id"): item
        for item in product_mapping.get("items", [])
        if isinstance(item, dict)
    }
    gaps = product_gap.get("items", []) if isinstance(product_gap.get("items"), list) else []
    gap_ids = [item.get("gap_id") for item in gaps if isinstance(item, dict)]
    duplicates = sorted(gap_id for gap_id, count in Counter(gap_ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_GAP_ID", "gap_ids": duplicates})
    if not (
        product_gap.get("run_id") == product_mapping.get("run_id")
        == signals.get("run_id") == approved_ot_bundle.get("run_id") == decision.get("run_id")
    ):
        errors.append({"code": "RUN_ID_MISMATCH"})
    for gap in gaps:
        if not isinstance(gap, dict):
            errors.append({"code": "INVALID_PRODUCT_GAP_ITEM"})
            continue
        gap_id = gap.get("gap_id")
        mapping_id = gap.get("product_mapping_id")
        parent = mappings.get(mapping_id)
        if parent is None:
            errors.append({
                "code": "UNKNOWN_PRODUCT_MAPPING_ID",
                "gap_id": gap_id,
                "product_mapping_id": mapping_id,
            })
            continue
        if gap.get("signal_id") != parent.get("signal_id"):
            errors.append({
                "code": "GAP_SIGNAL_ID_MISMATCH", "gap_id": gap_id,
                "expected_signal_id": parent.get("signal_id"), "actual_signal_id": gap.get("signal_id"),
            })
        if gap.get("market_product_category") != parent.get("market_product_category"):
            errors.append({
                "code": "GAP_CATEGORY_MISMATCH", "gap_id": gap_id,
                "product_mapping_id": mapping_id,
            })
        if gap.get("required_capabilities") != parent.get("required_capabilities"):
            errors.append({
                "code": "GAP_REQUIRED_CAPABILITIES_MISMATCH", "gap_id": gap_id,
                "product_mapping_id": mapping_id,
            })
        if gap.get("current_vsf_capabilities") and not gap.get("portfolio_evidence_refs"):
            errors.append({"code": "CLAIM_MISSING_PORTFOLIO_EVIDENCE", "gap_id": gap_id})
        if gap.get("capability_status") in {"FULL_MATCH", "PARTIAL_MATCH"} and not gap.get("portfolio_evidence_refs"):
            errors.append({"code": "STATUS_MISSING_PORTFOLIO_EVIDENCE", "gap_id": gap_id})
    return _result(
        errors,
        product_gap_count=len(gaps),
        product_mapping_count=len(mappings),
        approved_ot_count=mapping_result.get("approved_ot_count", 0),
        signal_count=mapping_result.get("signal_count", 0),
    )


def validate_action_lineage(
    actions: dict[str, Any], signals: dict[str, Any], approved_ot_bundle: dict[str, Any],
    product_mapping: dict[str, Any], product_gap: dict[str, Any], decision: dict[str, Any],
) -> dict[str, Any]:
    """Validate every Action through approved Signal/O-T, Mapping and Gap parents."""
    gap_result = validate_product_gap_lineage(
        product_gap, product_mapping, signals, approved_ot_bundle, decision
    )
    errors: list[dict[str, Any]] = [dict(item) for item in gap_result["errors"]]
    signal_ids = {item.get("signal_id") for item in signals.get("items", [])}
    approved_ids = {
        item.get("ot_id") for item in approved_ot_bundle.get("approved_opportunity_threat", [])
    }
    rejected_ids = set(decision.get("rejected_ot_ids", [])) | set(decision.get("revision_ot_ids", []))
    mappings = {
        item.get("product_mapping_id"): item for item in product_mapping.get("items", [])
        if isinstance(item, dict)
    }
    gaps = {
        item.get("gap_id"): item for item in product_gap.get("items", []) if isinstance(item, dict)
    }
    items = actions.get("items", []) if isinstance(actions.get("items"), list) else []
    action_ids = [item.get("action_id") for item in items if isinstance(item, dict)]
    duplicates = sorted(action_id for action_id, count in Counter(action_ids).items() if count > 1)
    if duplicates:
        errors.append({"code": "DUPLICATE_ACTION_ID", "action_ids": duplicates})
    if not (
        actions.get("run_id") == signals.get("run_id") == approved_ot_bundle.get("run_id")
        == product_mapping.get("run_id") == product_gap.get("run_id") == decision.get("run_id")
    ):
        errors.append({"code": "RUN_ID_MISMATCH"})
    for action in items:
        if not isinstance(action, dict):
            errors.append({"code": "INVALID_ACTION_ITEM"})
            continue
        action_id = action.get("action_id")
        signal_id = action.get("source_signal_id")
        mapping_id = action.get("product_mapping_id")
        related = action.get("related_ot_ids", [])
        gap_ids = action.get("gap_ids", [])
        mapping = mappings.get(mapping_id)
        if signal_id not in signal_ids:
            errors.append({"code": "UNKNOWN_ACTION_SIGNAL_ID", "action_id": action_id, "signal_id": signal_id})
        if mapping is None:
            errors.append({"code": "UNKNOWN_ACTION_PRODUCT_MAPPING_ID", "action_id": action_id, "product_mapping_id": mapping_id})
        elif signal_id != mapping.get("signal_id"):
            errors.append({"code": "ACTION_SIGNAL_MAPPING_MISMATCH", "action_id": action_id})
        if not related:
            errors.append({"code": "ACTION_WITHOUT_APPROVED_OT", "action_id": action_id})
        unknown_ot = sorted(set(related) - approved_ids)
        if unknown_ot:
            errors.append({"code": "ACTION_UNKNOWN_OR_UNAPPROVED_OT", "action_id": action_id, "ot_ids": unknown_ot})
        leaked = sorted(set(related) & rejected_ids)
        if leaked:
            errors.append({"code": "ACTION_REJECTED_OT_LEAKAGE", "action_id": action_id, "ot_ids": leaked})
        if mapping is not None:
            unlinked_ot = sorted(set(related) - set(mapping.get("related_ot_ids", [])))
            if unlinked_ot and "cross-mapping rationale:" not in str(action.get("rationale", "")).lower():
                errors.append({"code": "ACTION_OT_MAPPING_MISMATCH", "action_id": action_id, "ot_ids": unlinked_ot})
        if not gap_ids:
            errors.append({"code": "ACTION_WITHOUT_GAP", "action_id": action_id})
        for gap_id in gap_ids:
            gap = gaps.get(gap_id)
            if gap is None:
                errors.append({"code": "UNKNOWN_ACTION_GAP_ID", "action_id": action_id, "gap_id": gap_id})
                continue
            if gap.get("product_mapping_id") != mapping_id and "cross-mapping rationale:" not in str(action.get("rationale", "")).lower():
                errors.append({
                    "code": "ACTION_GAP_MAPPING_MISMATCH", "action_id": action_id,
                    "gap_id": gap_id, "gap_product_mapping_id": gap.get("product_mapping_id"),
                })
            if gap.get("signal_id") != signal_id:
                errors.append({"code": "ACTION_GAP_SIGNAL_MISMATCH", "action_id": action_id, "gap_id": gap_id})
    return _result(
        errors, action_count=len(items), signal_count=len(signal_ids),
        approved_ot_count=len(approved_ids), product_mapping_count=len(mappings), gap_count=len(gaps),
    )


def validate_gate3_lineage(decision: dict[str, Any], actions: dict[str, Any]) -> dict[str, Any]:
    """Validate Gate 3 action ID sets against the canonical Action artifact."""
    action_ids = {item.get("action_id") for item in actions.get("items", []) if isinstance(item, dict)}
    result = validate_hitl_sets(
        decision,
        "reviewed_action_ids",
        ["approved_action_ids", "rejected_action_ids", "revision_action_ids", "deferred_action_ids"],
        action_ids,
        "approved_action_ids",
    )
    errors = list(result.get("errors", []))
    if decision.get("run_id") != actions.get("run_id"):
        errors.append({"code": "RUN_ID_MISMATCH"})
    if decision.get("synthetic") is not actions.get("synthetic"):
        errors.append({"code": "SYNTHETIC_MISMATCH"})
    return _result(
        errors,
        reviewed_count=result.get("reviewed_count", 0),
        source_count=result.get("source_count", len(action_ids)),
        unreviewed_ids=result.get("unreviewed_ids", []),
    )


def _write_result(result: dict[str, Any], report: Path | None) -> int:
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if report:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        required=True,
        choices=["approved-news", "signal", "ot", "gate2", "approved-ot", "product-mapping", "product-gap", "action", "gate3"],
    )
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--decision", type=Path)
    parser.add_argument("--review", type=Path)
    parser.add_argument("--market", type=Path)
    parser.add_argument("--competitor", type=Path)
    parser.add_argument("--technology", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--signals", type=Path)
    parser.add_argument("--opportunity-threat", type=Path)
    parser.add_argument("--approved-ot-bundle", type=Path)
    parser.add_argument("--gate-report", type=Path)
    parser.add_argument("--product-mapping", type=Path)
    parser.add_argument("--product-gap", type=Path)
    parser.add_argument("--actions", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "approved-news":
            result = validate_approved_news_bundle(
                load_json(args.bundle), load_json(args.decision),
                [load_json(path) for path in [args.market, args.competitor, args.technology, args.policy]],
                parse_gate1_corrected_types(args.review),
            )
        elif args.mode == "signal":
            decision = load_json(args.decision) if args.decision else {}
            result = validate_signal_lineage(
                load_json(args.signals), load_json(args.bundle), set(decision.get("excluded_news_ids", []))
            )
        elif args.mode == "ot":
            result = validate_ot_lineage(load_json(args.opportunity_threat), load_json(args.signals))
        elif args.mode == "gate2":
            result = validate_gate2_lineage(load_json(args.decision), load_json(args.opportunity_threat))
        elif args.mode == "approved-ot":
            result = validate_approved_ot_bundle(
                load_json(args.approved_ot_bundle),
                load_json(args.decision),
                load_json(args.opportunity_threat),
                load_json(args.signals),
                load_json(args.gate_report) if args.gate_report else None,
            )
        elif args.mode == "product-mapping":
            result = validate_product_mapping_lineage(
                load_json(args.product_mapping),
                load_json(args.signals),
                load_json(args.approved_ot_bundle),
                load_json(args.decision),
            )
        elif args.mode == "product-gap":
            result = validate_product_gap_lineage(
                load_json(args.product_gap),
                load_json(args.product_mapping),
                load_json(args.signals),
                load_json(args.approved_ot_bundle),
                load_json(args.decision),
            )
        elif args.mode == "action":
            result = validate_action_lineage(
                load_json(args.actions), load_json(args.signals),
                load_json(args.approved_ot_bundle), load_json(args.product_mapping),
                load_json(args.product_gap), load_json(args.decision),
            )
        else:
            result = validate_gate3_lineage(load_json(args.decision), load_json(args.actions))
    except (OSError, ValueError, TypeError) as exc:
        result = {"status": "FAIL", "errors": [{"code": "INPUT_ERROR", "message": str(exc)}]}
    return _write_result(result, args.report)


if __name__ == "__main__":
    sys.exit(main())
