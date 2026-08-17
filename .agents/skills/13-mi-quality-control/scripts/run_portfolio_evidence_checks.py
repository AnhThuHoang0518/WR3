#!/usr/bin/env python3
"""Validate Product Mapping separation and Product Gap portfolio-evidence provenance."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

from qc_common import finding, load_json, parse_frontmatter, resolve_index_path, result, write_json

FORBIDDEN_MAPPING_FIELDS = {
    "matched_vsf_product", "current_vsf_capabilities", "capability_status", "missing_capabilities",
    "gap_type", "recommended_response", "proposed_action",
}


def _load_evidence_module(project_root: Path):
    path = project_root / ".agents" / "skills" / "10-product-gap" / "scripts" / "validate_portfolio_evidence.py"
    spec = importlib.util.spec_from_file_location("qc_product_gap_evidence", path)
    if not spec or not spec.loader:
        raise ValueError("Cannot load Product Gap portfolio evidence validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_checks(
    product_mapping: dict[str, Any], product_gap: dict[str, Any], products: dict[str, Any],
    mapping_review: dict[str, Any], gap_review: dict[str, Any], mapping_coverage: dict[str, Any],
    gap_coverage: dict[str, Any], evidence_validator: Any,
) -> dict[str, Any]:
    """Check outside-in Mapping and exact catalog-backed Product Gap claims."""
    findings: list[dict[str, Any]] = []
    product_names = {str(item.get("product_name", "")).casefold() for item in products.get("products", [])}
    mapping_violations: list[str] = []
    for item in product_mapping.get("items", []):
        mapping_id = str(item.get("product_mapping_id"))
        if FORBIDDEN_MAPPING_FIELDS & set(item):
            mapping_violations.append(mapping_id)
        if str(item.get("market_product_category", "")).casefold() in product_names:
            mapping_violations.append(mapping_id)
        if not item.get("required_capabilities"):
            mapping_violations.append(mapping_id)
    mapping_ok = not mapping_violations
    findings.append(finding(
        "Product Mapping outside-in boundary", "PASS" if mapping_ok else "ERROR", "INFO" if mapping_ok else "CRITICAL",
        "Product Mapping contains neutral market categories, non-empty requirements and no portfolio/gap/action fields."
        if mapping_ok else "Product Mapping contains a VSF product name, forbidden downstream field, or empty capability requirement.",
        mapping_violations, "Return to Product Mapping and repeat its manual review; do not fix the artifact in QC." if not mapping_ok else None,
    ))
    mapping_review_ok = mapping_review.get("status") == "REVIEWED_ACCEPTED" and bool(mapping_review.get("reviewer") and mapping_review.get("reviewed_at"))
    gap_review_ok = gap_review.get("status") == "REVIEWED_ACCEPTED" and bool(gap_review.get("reviewer") and gap_review.get("reviewed_at"))
    findings.append(finding(
        "Product Mapping manual inspection", "PASS" if mapping_review_ok else "ERROR", "INFO" if mapping_review_ok else "HIGH",
        "Product Mapping manual inspection is REVIEWED_ACCEPTED." if mapping_review_ok else "Product Mapping manual inspection is incomplete.",
        [], "Obtain manual inspection without changing the mapping in QC." if not mapping_review_ok else None,
    ))
    findings.append(finding(
        "Product Gap manual inspection", "PASS" if gap_review_ok else "ERROR", "INFO" if gap_review_ok else "HIGH",
        "Product Gap manual inspection is REVIEWED_ACCEPTED." if gap_review_ok else "Product Gap manual inspection is incomplete.",
        [], "Obtain manual inspection without changing the gap in QC." if not gap_review_ok else None,
    ))
    mapping_ids = {item.get("product_mapping_id") for item in product_mapping.get("items", [])}
    coverage_mapping_ids = set(mapping_coverage.get("product_mapping_ids", []))
    gap_coverage_ids = set(gap_coverage.get("product_mapping_ids", []))
    coverage_ok = (
        mapping_coverage.get("validation_status") == "PASS"
        and gap_coverage.get("validation_status") == "PASS"
        and mapping_ids == coverage_mapping_ids == gap_coverage_ids
    )
    findings.append(finding(
        "Product Mapping and Gap coverage consistency", "PASS" if coverage_ok else "ERROR", "INFO" if coverage_ok else "HIGH",
        "Mapping and Gap coverage reports match canonical Product Mapping IDs." if coverage_ok else "Product coverage reports differ from canonical artifacts.",
        sorted(mapping_ids ^ (coverage_mapping_ids | gap_coverage_ids)), "Regenerate coverage from unchanged canonical artifacts in the owning stage." if not coverage_ok else None,
    ))
    evidence = evidence_validator.validate_portfolio_evidence(products, product_gap)
    evidence_ok = evidence.get("status") == "PASS"
    findings.append(finding(
        "Product Gap portfolio evidence", "PASS" if evidence_ok else "ERROR", "INFO" if evidence_ok else "CRITICAL",
        f"All Product Gap portfolio claims resolve to the read-only catalog; resolved refs={evidence.get('resolved_reference_count', 0)}."
        if evidence_ok else f"Portfolio evidence validation found {evidence.get('error_count', 0)} ERROR(s).",
        sorted(str(item.get("gap_id")) for item in evidence.get("errors", []) if item.get("gap_id")),
        "Return to Product Gap, correct catalog-backed evidence, repeat manual inspection and downstream review." if not evidence_ok else None,
    ))
    warning_remediation = {
        "ADJACENT_CATEGORY_MATCH": "Confirm category fit with additional portfolio or market evidence before real deployment.",
        "CATALOG_INFORMATION_INSUFFICIENT": "Obtain deeper product documentation and retain UNKNOWN until evidence is reviewed.",
        "CATALOG_EVIDENCE_REQUIRES_HUMAN_VALIDATION": "Obtain the catalog-required human validation before operational use.",
    }
    for item in evidence.get("warnings", []):
        code = str(item.get("code"))
        gap_id = str(item.get("gap_id")) if item.get("gap_id") else None
        findings.append(finding(
            f"Portfolio evidence warning: {code}", "WARNING", "MEDIUM",
            f"Product Gap evidence validator reported {code}" + (f" for {gap_id}." if gap_id else "."),
            [gap_id] if gap_id else [], warning_remediation.get(code, "Review the cited catalog evidence before real operational use."),
        ))
    return result("PRODUCT_MAPPING_AND_PORTFOLIO_EVIDENCE", findings)


def load_inputs(index: dict[str, Any], root: Path) -> dict[str, Any]:
    artifacts = index["artifact_paths"]
    reviews = index["review_paths"]
    validations = index["validation_paths"]
    catalogs = index["catalog_paths"]
    return {
        "product_mapping": load_json(resolve_index_path(root, artifacts["product_mapping"])),
        "product_gap": load_json(resolve_index_path(root, artifacts["product_gap"])),
        "products": load_json(resolve_index_path(root, catalogs["products_catalog"])),
        "mapping_review": parse_frontmatter(resolve_index_path(root, reviews["product_mapping_review"])),
        "gap_review": parse_frontmatter(resolve_index_path(root, reviews["product_gap_review"])),
        "mapping_coverage": load_json(resolve_index_path(root, validations["product-mapping-coverage-report"])),
        "gap_coverage": load_json(resolve_index_path(root, validations["product-gap-coverage-report"])),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = (args.project_root or Path(__file__).resolve().parents[4]).resolve()
        values = load_inputs(load_json(args.index), root)
        output = run_checks(**values, evidence_validator=_load_evidence_module(root))
        write_json(args.output, output)
        print(json.dumps({"status": "PASS", "finding_count": output["finding_count"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

