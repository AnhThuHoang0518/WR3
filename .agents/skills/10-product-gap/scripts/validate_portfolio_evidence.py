#!/usr/bin/env python3
"""Validate Product Gap portfolio products, evidence references and capability claims."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _finding(severity: str, code: str, item: dict[str, Any], **details: Any) -> dict[str, Any]:
    return {"severity": severity, "code": code, "gap_id": item.get("gap_id"), **details}


def validate_portfolio_evidence(catalog: dict[str, Any], artifact: dict[str, Any]) -> dict[str, Any]:
    """Resolve every evidence ref and require exact catalog support for current capability claims."""
    products = catalog.get("products")
    if not isinstance(products, list):
        raise ValueError("Catalog products must be an array")
    by_code = {item.get("product_code"): item for item in products if isinstance(item, dict)}
    by_name = {item.get("product_name"): item for item in products if isinstance(item, dict)}
    findings: list[dict[str, Any]] = []
    resolved_reference_count = 0
    for item in artifact.get("items", []):
        if not isinstance(item, dict):
            findings.append({"severity": "ERROR", "code": "INVALID_GAP_ITEM"})
            continue
        status = item.get("capability_status")
        refs = item.get("portfolio_evidence_refs", [])
        current = item.get("current_vsf_capabilities", [])
        matched = item.get("matched_vsf_product")
        matched_product = by_code.get(matched) or by_name.get(matched)
        if matched is not None and matched_product is None:
            findings.append(_finding("ERROR", "MATCHED_PRODUCT_NOT_FOUND", item, matched_vsf_product=matched))
        if status == "FULL_MATCH" and not refs:
            findings.append(_finding("ERROR", "FULL_MATCH_WITHOUT_EVIDENCE", item))
        resolved: dict[str, dict[str, Any]] = {}
        fields_by_code: dict[str, set[str]] = {}
        for ref in refs:
            if not isinstance(ref, dict):
                findings.append(_finding("ERROR", "INVALID_EVIDENCE_REF", item))
                continue
            code = ref.get("product_code")
            product = by_code.get(code)
            if product is None:
                findings.append(_finding("ERROR", "EVIDENCE_PRODUCT_NOT_FOUND", item, product_code=code))
                continue
            fields = ref.get("catalog_fields", [])
            invalid_fields = [field for field in fields if field not in product]
            if invalid_fields:
                findings.append(_finding(
                    "ERROR", "EVIDENCE_FIELD_NOT_FOUND", item,
                    product_code=code, catalog_fields=invalid_fields,
                ))
                continue
            empty_fields = [field for field in fields if product.get(field) in (None, "", [])]
            if empty_fields:
                findings.append(_finding(
                    "ERROR", "EVIDENCE_FIELD_EMPTY", item,
                    product_code=code, catalog_fields=empty_fields,
                ))
                continue
            resolved[code] = product
            fields_by_code.setdefault(code, set()).update(str(field) for field in fields)
            resolved_reference_count += 1
        if current and not refs:
            findings.append(_finding("ERROR", "CAPABILITY_CLAIM_WITHOUT_EVIDENCE", item))
        if current and matched_product is None:
            findings.append(_finding("ERROR", "CAPABILITY_CLAIM_WITHOUT_MATCHED_PRODUCT", item))
        if current and matched_product is not None:
            matched_code = str(matched_product.get("product_code"))
            if matched_product.get("allowed_gap_baseline") is not True:
                findings.append(_finding(
                    "ERROR", "NON_BASELINE_PRODUCT_CAPABILITY_CLAIM", item, product_code=matched_code,
                ))
            if matched_code not in resolved or "capabilities" not in fields_by_code.get(matched_code, set()):
                findings.append(_finding(
                    "ERROR", "MATCHED_PRODUCT_CAPABILITY_EVIDENCE_MISSING", item, product_code=matched_code,
                ))
            catalog_capabilities = set(matched_product.get("capabilities", []))
            unsupported = [capability for capability in current if capability not in catalog_capabilities]
            if unsupported:
                findings.append(_finding(
                    "ERROR", "CAPABILITY_NOT_SUPPORTED_BY_CATALOG", item,
                    product_code=matched_code, capabilities=unsupported,
                ))
        rationale = str(item.get("comparison_rationale", ""))
        if "ADJACENT_CATEGORY" in rationale:
            findings.append(_finding("WARNING", "ADJACENT_CATEGORY_MATCH", item))
        if status == "UNKNOWN":
            findings.append(_finding("WARNING", "CATALOG_INFORMATION_INSUFFICIENT", item))
        for code, product in resolved.items():
            if product.get("human_validation_required") is True and status in {"FULL_MATCH", "PARTIAL_MATCH"}:
                findings.append(_finding(
                    "WARNING", "CATALOG_EVIDENCE_REQUIRES_HUMAN_VALIDATION", item, product_code=code,
                ))
    errors = [item for item in findings if item["severity"] == "ERROR"]
    warnings = [item for item in findings if item["severity"] == "WARNING"]
    return {
        "status": "PASS" if not errors else "FAIL",
        "catalog_schema_version": catalog.get("schema_version"),
        "catalog_product_count": len(products),
        "product_gap_count": len(artifact.get("items", [])),
        "resolved_reference_count": resolved_reference_count,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--products", required=True, type=Path)
    parser.add_argument("--product-gap", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        result = validate_portfolio_evidence(load_json(args.products), load_json(args.product_gap))
    except (OSError, ValueError, TypeError) as exc:
        result = {
            "status": "FAIL", "error_count": 1, "warning_count": 0,
            "errors": [{"severity": "ERROR", "code": "INPUT_ERROR", "message": str(exc)}], "warnings": [],
        }
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())

