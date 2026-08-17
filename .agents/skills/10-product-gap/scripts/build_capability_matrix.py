#!/usr/bin/env python3
"""Build a neutral candidate and capability scaffold for Product Gap semantic analysis."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

SUPPORT_STATUSES = {
    "CONFIRMED_PRESENT", "CONFIRMED_ABSENT", "PARTIALLY_SUPPORTED",
    "NOT_DOCUMENTED", "NOT_APPLICABLE",
}
STOPWORDS = {
    "and", "or", "the", "a", "an", "for", "of", "to", "with", "across", "as", "under",
    "platform", "solution", "system", "smart", "city", "management", "service", "services",
}


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def normalize(value: str) -> str:
    """Normalize text for discovery only, never as a final semantic decision."""
    folded = unicodedata.normalize("NFKD", value.casefold())
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def tokens(value: str) -> set[str]:
    """Return meaningful discovery tokens."""
    return {token for token in normalize(value).split() if len(token) >= 4 and token not in STOPWORDS}


def _catalog_text(product: dict[str, Any]) -> str:
    parts: list[str] = [str(product.get("product_type", ""))]
    parts.extend(str(value) for value in product.get("smart_city_domains", []))
    parts.extend(str(value) for value in product.get("capabilities", []))
    return " ".join(parts)


def _candidate_products(mapping: dict[str, Any], products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    query = " ".join([
        str(mapping.get("market_product_category", "")),
        *[str(value) for value in mapping.get("required_capabilities", [])],
    ])
    query_tokens = tokens(query)
    ranked: list[tuple[int, str, dict[str, Any]]] = []
    for product in products:
        if product.get("portfolio_role") == "HISTORICAL_REFERENCE" or not product.get("active_for_news_mapping", False):
            continue
        overlap = sorted(query_tokens & tokens(_catalog_text(product)))
        if overlap:
            ranked.append((len(overlap), str(product.get("product_code", "")), {
                "product_code": product.get("product_code"),
                "product_name": product.get("product_name"),
                "portfolio_role": product.get("portfolio_role"),
                "allowed_gap_baseline": product.get("allowed_gap_baseline"),
                "discovery_overlap_terms": overlap,
                "candidate_note": "Keyword overlap is discovery evidence only; inspect category and catalog descriptions before any conclusion.",
            }))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:3]]


def build_matrix(context: dict[str, Any]) -> dict[str, Any]:
    """Create non-conclusive comparisons without hard-coding current mappings."""
    mappings = context.get("product_mappings")
    products = context.get("portfolio_products")
    if not isinstance(mappings, list) or not isinstance(products, list):
        raise ValueError("Context product_mappings and portfolio_products must be arrays")
    catalog_capabilities: dict[str, tuple[str, str]] = {}
    for product in products:
        for capability in product.get("capabilities", []):
            catalog_capabilities[normalize(str(capability))] = (str(product.get("product_code")), str(capability))
    items: list[dict[str, Any]] = []
    for mapping in mappings:
        comparisons: list[dict[str, Any]] = []
        for required in mapping.get("required_capabilities", []):
            exact = catalog_capabilities.get(normalize(str(required)))
            if exact:
                product_code, catalog_capability = exact
                comparisons.append({
                    "required_capability": required,
                    "matched_catalog_capability": catalog_capability,
                    "support_status": "CONFIRMED_PRESENT",
                    "portfolio_evidence_refs": [{"product_code": product_code, "catalog_fields": ["capabilities"]}],
                    "comparison_note": "Exact normalized catalog capability match; semantic category review is still required.",
                })
            else:
                comparisons.append({
                    "required_capability": required,
                    "matched_catalog_capability": None,
                    "support_status": "NOT_DOCUMENTED",
                    "portfolio_evidence_refs": [],
                    "comparison_note": "No exact catalog capability match. Do not interpret this as confirmed absence.",
                })
        if any(item["support_status"] not in SUPPORT_STATUSES for item in comparisons):
            raise ValueError("Invalid intermediate support status")
        candidates = _candidate_products(mapping, products)
        items.append({
            "product_mapping_id": mapping.get("product_mapping_id"),
            "signal_id": mapping.get("signal_id"),
            "market_product_category": mapping.get("market_product_category"),
            "required_capabilities": mapping.get("required_capabilities", []),
            "candidate_vsf_products": candidates,
            "category_match_rationale": (
                "UNCERTAIN_CATEGORY: candidates are discovery suggestions only; Codex must inspect product_type, "
                "smart_city_domains, capabilities, portfolio_role and allowed_gap_baseline."
            ),
            "capability_comparisons": comparisons,
            "unresolved_questions": [
                "Does any candidate have the same or only an adjacent category?",
                "Which required capabilities are explicitly supported by catalog evidence?",
                "Do known_unknowns or portfolio-role rules require human validation?",
            ],
        })
    return {"run_id": context.get("run_id"), "synthetic": context.get("synthetic"), "items": items}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite existing capability matrix: {args.output}")
        matrix = build_matrix(load_json(args.context))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(matrix, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "mapping_count": len(matrix["items"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

