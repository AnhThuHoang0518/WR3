#!/usr/bin/env python3
"""Audit Skill 09 for forbidden runtime dependencies and allowed guardrail mentions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PRODUCT_CATALOG_NAME = "products" + ".json"
NEXT_SKILL_PATH = "10-product" + "-gap"
RUNTIME_EXTENSIONS = {".py"}
SCANNED_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml"}
GUARDRAIL_FILES = {"validate_artifact.py", "audit_forbidden_dependencies.py"}
FORBIDDEN_DOWNSTREAM_FIELDS = {
    "matched_vsf_product", "current_vsf_capabilities", "missing_vsf_capabilities",
    "capability_status", "gap_type", "gap_severity", "recommended_response",
    "proposed_action", "build_buy_partner", "pilot_or_productize",
}


def audit(skill_dir: Path) -> dict[str, Any]:
    """Classify actual runtime dependency leaks separately from policy guardrails."""
    files = sorted(
        path for path in skill_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in SCANNED_EXTENSIONS and "__pycache__" not in path.parts
    )
    forbidden: list[dict[str, Any]] = []
    documentation: list[dict[str, Any]] = []
    guardrails: list[dict[str, Any]] = []
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(skill_dir).as_posix()
        lower = text.lower()
        markers = [marker for marker in [PRODUCT_CATALOG_NAME, NEXT_SKILL_PATH, "vsf product catalog"] if marker in lower]
        if path.suffix.lower() not in RUNTIME_EXTENSIONS:
            for marker in markers:
                documentation.append({"file": relative, "marker": marker})
            continue
        if path.name in GUARDRAIL_FILES:
            for marker in markers:
                guardrails.append({"file": relative, "marker": marker, "purpose": "validation guardrail"})
            continue
        for marker in markers:
            forbidden.append({"file": relative, "marker": marker, "reason": "forbidden runtime dependency reference"})
        for field in sorted(FORBIDDEN_DOWNSTREAM_FIELDS):
            if field in lower:
                forbidden.append({"file": relative, "marker": field, "reason": "forbidden downstream output field"})
        if "product_gap" in lower or "action_recommendation" in lower:
            forbidden.append({"file": relative, "marker": "downstream module", "reason": "Skill 09 runtime may not import downstream stages"})
        if "--product-catalog" in lower or "--portfolio" in lower:
            forbidden.append({"file": relative, "marker": "forbidden CLI input", "reason": "portfolio input is not allowed"})
    return {
        "files_scanned": [path.relative_to(skill_dir).as_posix() for path in files],
        "forbidden_runtime_references": forbidden,
        "documentation_only_references": documentation,
        "allowed_guardrail_references": guardrails,
        "audit_status": "PASS" if not forbidden else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.skill_dir.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": result["audit_status"], "output": str(args.output), "files_scanned": len(result["files_scanned"]), "forbidden_runtime_references": len(result["forbidden_runtime_references"])}, ensure_ascii=False))
        return 0 if result["audit_status"] == "PASS" else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
