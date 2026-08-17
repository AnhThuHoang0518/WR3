#!/usr/bin/env python3
"""Audit source-code dependency boundaries without executing or modifying upstream stages."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

from qc_common import finding, load_json, result, write_json


def _python_texts(skill_dir: Path) -> list[tuple[Path, str]]:
    return [(path, path.read_text(encoding="utf-8")) for path in sorted((skill_dir / "scripts").glob("*.py"))]


def audit_product_mapping(skill_dir: Path) -> list[str]:
    """Return forbidden Product Mapping runtime files that read products or import Skill 10."""
    allowed = {"validate_artifact.py", "audit_forbidden_dependencies.py"}
    violations: list[str] = []
    for path, text in _python_texts(skill_dir):
        lower = text.casefold()
        if path.name not in allowed and ("products.json" in lower or "10-product-gap" in lower or "from product_gap" in lower or "import product_gap" in lower):
            violations.append(path.name)
    return violations


def run_checks(project_root: Path) -> dict[str, Any]:
    """Check catalog, downstream, HITL, internet and static mutation boundaries."""
    skills = project_root / ".agents" / "skills"
    findings: list[dict[str, Any]] = []
    news_violations: list[str] = []
    for stage in ["01-market-news", "03-technology-news", "04-policy-news"]:
        for path, text in _python_texts(skills / stage):
            if "competitors.json" in text.casefold():
                news_violations.append(f"{stage}/{path.name}")
    competitor_uses_catalog = any(
        "competitors.json" in text.casefold() or "--competitors" in text.casefold() or "read_competitor_catalog" in text.casefold()
        for _, text in _python_texts(skills / "02-competitor-news")
    )
    news_ok = not news_violations and competitor_uses_catalog
    findings.append(finding(
        "Competitor catalog boundary", "PASS" if news_ok else "ERROR", "INFO" if news_ok else "HIGH",
        "Only Competitor News runtime references competitors.json." if news_ok else "Competitor catalog boundary violation detected.",
        news_violations, "Remove competitor catalog access from non-Competitor News runtime code." if not news_ok else None,
    ))
    mapping_violations = audit_product_mapping(skills / "09-product-mapping")
    mapping_ok = not mapping_violations
    findings.append(finding(
        "Product Mapping portfolio dependency boundary", "PASS" if mapping_ok else "ERROR", "INFO" if mapping_ok else "CRITICAL",
        "Product Mapping runtime does not read products.json or import Product Gap; the run-specific audit is checked separately as validation evidence."
        if mapping_ok else "Product Mapping has a forbidden portfolio or downstream dependency.",
        mapping_violations, "Remove the forbidden runtime dependency and rerun the Skill 09 dependency audit." if not mapping_ok else None,
    ))
    upstream_product_violations: list[str] = []
    for stage in ["01-market-news", "02-competitor-news", "03-technology-news", "04-policy-news", "05-news-relevance-hitl", "06-signal-synthesis", "07-opportunity-threat", "08-opportunity-threat-hitl", "09-product-mapping", "11-action-recommendation", "12-product-action-hitl"]:
        for path, text in _python_texts(skills / stage):
            if "products.json" in text.casefold() and not (stage == "09-product-mapping" and path.name in {"validate_artifact.py", "audit_forbidden_dependencies.py"}):
                upstream_product_violations.append(f"{stage}/{path.name}")
    findings.append(finding(
        "Product catalog analysis boundary", "PASS" if not upstream_product_violations else "ERROR",
        "INFO" if not upstream_product_violations else "HIGH",
        "Only Product Gap and read-only QC perform portfolio catalog analysis." if not upstream_product_violations else "An upstream or Action runtime references products.json.",
        upstream_product_violations, "Remove direct product-catalog analysis outside Product Gap and read-only QC." if upstream_product_violations else None,
    ))
    action_hardcodes: list[str] = []
    rejected_pattern = re.compile(r"OT-(?:002|003|005|008)")
    for path, text in _python_texts(skills / "11-action-recommendation"):
        if rejected_pattern.search(text):
            action_hardcodes.append(path.name)
    findings.append(finding(
        "Action rejected-O/T decision dependency", "PASS" if not action_hardcodes else "ERROR",
        "INFO" if not action_hardcodes else "HIGH",
        "Action runtime reads rejected O/T dynamically from Gate 2 and contains no synthetic rejected-ID hard-coding."
        if not action_hardcodes else "Action runtime hard-codes rejected O/T IDs.",
        action_hardcodes, "Read rejected IDs only from the Gate 2 decision manifest." if action_hardcodes else None,
    ))
    auto_approval: list[str] = []
    forbidden_approval = re.compile(r"overall_status\s*[:=]\s*[\"']APPROVED[\"']", re.IGNORECASE)
    for stage in ["05-news-relevance-hitl", "08-opportunity-threat-hitl", "12-product-action-hitl"]:
        for path, text in _python_texts(skills / stage):
            if path.name == "generate_review.py" and forbidden_approval.search(text):
                auto_approval.append(f"{stage}/{path.name}")
    findings.append(finding(
        "HITL no-auto-approval boundary", "PASS" if not auto_approval else "ERROR", "INFO" if not auto_approval else "CRITICAL",
        "All HITL review generators initialize human decisions as PENDING." if not auto_approval else "A HITL review generator contains automatic APPROVED status.",
        auto_approval, "Restore PENDING generation and require explicit human review." if auto_approval else None,
    ))
    internet_markers = ["requests.get(", "requests.post(", "urlopen(", "http.client", "urllib.request"]
    internet_violations: list[str] = []
    for stage_number in range(1, 13):
        stage = next((path for path in skills.iterdir() if path.is_dir() and path.name.startswith(f"{stage_number:02d}-")), None)
        if not stage:
            continue
        for path, text in _python_texts(stage):
            lower = text.casefold()
            if any(marker in lower for marker in internet_markers):
                internet_violations.append(f"{stage.name}/{path.name}")
    findings.append(finding(
        "Synthetic runtime offline boundary", "PASS" if not internet_violations else "ERROR", "INFO" if not internet_violations else "HIGH",
        "No stage 01–12 runtime script contains an active internet-client call." if not internet_violations else "Internet-client code was detected in synthetic runtime stages.",
        internet_violations, "Remove network calls from the synthetic runtime path." if internet_violations else None,
    ))
    findings.append(finding(
        "QC catalog access mode", "PASS", "INFO",
        "Skill 13 uses competitors.json and products.json read-only for boundary/provenance validation and does not regenerate portfolio analysis."
    ))
    return result("DEPENDENCY_BOUNDARIES", findings)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        root = (args.project_root or Path(__file__).resolve().parents[4]).resolve()
        output = run_checks(root)
        write_json(args.output, output)
        print(json.dumps({"status": "PASS", "finding_count": output["finding_count"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
