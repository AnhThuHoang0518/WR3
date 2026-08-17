#!/usr/bin/env python3
"""Collect a path-only QC input index and immutable hash baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from qc_common import load_json, project_relative, sha256, utc_now, write_json


def build_specs(project_root: Path, run_dir: Path) -> dict[str, dict[str, Path] | list[Path]]:
    """Return all required pipeline, contract, catalog, schema and source-code paths."""
    skills = project_root / ".agents" / "skills"
    artifacts = run_dir / "artifacts"
    reviews = run_dir / "reviews"
    validation = run_dir / "validation"
    manifest_path = run_dir / "manifest.json"
    manifest = load_json(manifest_path)
    raw_news_ref = manifest.get("artifacts", {}).get("raw_news_input")
    raw_news_path = (project_root / raw_news_ref).resolve() if raw_news_ref else project_root / "workspace" / "inputs" / "news" / "synthetic_raw_news.json"
    artifact_paths = {
        "raw_news": raw_news_path,
        "market_news": artifacts / "market_news.json", "competitor_news": artifacts / "competitor_news.json",
        "technology_news": artifacts / "technology_news.json", "policy_news": artifacts / "policy_news.json",
        "approved_news_bundle": artifacts / "approved_news_bundle.json", "signals": artifacts / "signals.json",
        "opportunity_threat": artifacts / "opportunity_threat.json",
        "approved_opportunity_threat_bundle": artifacts / "approved_opportunity_threat_bundle.json",
        "product_mapping": artifacts / "product_mapping.json", "product_gap": artifacts / "product_gap.json",
        "actions": artifacts / "actions.json", "action_summary": artifacts / "action_summary.json",
        "approved_actions": artifacts / "approved-actions.json", "deferred_actions": artifacts / "deferred-actions.json",
        "news_lineage": validation / "news-lineage.json", "runtime_manifest": manifest_path,
    }
    review_paths = {
        "gate_1_review": reviews / "01-news-relevance-review.md",
        "gate_2_review": reviews / "02-opportunity-threat-review.md",
        "product_mapping_review": reviews / "product-mapping-review.md",
        "product_gap_review": reviews / "product-gap-review.md",
        "gate_3_review": reviews / "03-product-action-review.md",
    }
    decision_paths = {
        "gate_1_decision": reviews / "01-news-relevance-decision.json",
        "gate_2_decision": reviews / "02-opportunity-threat-decision.json",
        "gate_3_decision": reviews / "03-product-action-decision.json",
    }
    validation_paths = {
        path.stem: path for path in sorted(validation.glob("*.json"))
        if path.name not in {"quality_control_report.json", "final-artifact-integrity.json", "news-lineage.json"}
        and not path.name.startswith("qc-")
    }
    schema_paths = {
        "market_news_schema": skills / "01-market-news" / "schemas" / "output.schema.json",
        "competitor_news_schema": skills / "02-competitor-news" / "schemas" / "output.schema.json",
        "technology_news_schema": skills / "03-technology-news" / "schemas" / "output.schema.json",
        "policy_news_schema": skills / "04-policy-news" / "schemas" / "output.schema.json",
        "gate_1_schema": skills / "05-news-relevance-hitl" / "schemas" / "review-decision.schema.json",
        "signal_schema": skills / "06-signal-synthesis" / "schemas" / "output.schema.json",
        "ot_schema": skills / "07-opportunity-threat" / "schemas" / "output.schema.json",
        "gate_2_schema": skills / "08-opportunity-threat-hitl" / "schemas" / "review-decision.schema.json",
        "product_mapping_schema": skills / "09-product-mapping" / "schemas" / "output.schema.json",
        "product_gap_schema": skills / "10-product-gap" / "schemas" / "output.schema.json",
        "action_schema": skills / "11-action-recommendation" / "schemas" / "output.schema.json",
        "gate_3_schema": skills / "12-product-action-hitl" / "schemas" / "review-decision.schema.json",
        "news_lineage_schema": skills / "00-news-driven-mi-orchestrator" / "schemas" / "news-lineage.schema.json",
        "pipeline_manifest_schema": skills / "00-news-driven-mi-orchestrator" / "schemas" / "pipeline_manifest.schema.json",
        "runtime_manifest_schema": skills / "00-news-driven-mi-orchestrator" / "schemas" / "runtime-run-manifest.schema.json",
        "quality_control_schema": skills / "13-mi-quality-control" / "schemas" / "output.schema.json",
    }
    catalog_paths = {
        "competitors_catalog": skills / "02-competitor-news" / "references" / "competitors.json",
        "products_catalog": skills / "10-product-gap" / "references" / "products.json",
    }
    contract_paths = {
        "pipeline_version": project_root / "PIPELINE_VERSION.md",
        "pipeline_contract": skills / "00-news-driven-mi-orchestrator" / "references" / "PIPELINE_CONTRACT.md",
        "dependency_matrix": skills / "00-news-driven-mi-orchestrator" / "references" / "DEPENDENCY_MATRIX.md",
        "hitl_gate_policy": skills / "00-news-driven-mi-orchestrator" / "references" / "HITL_GATE_POLICY.md",
    }
    source_code_paths = sorted(
        path for stage in skills.iterdir() if stage.is_dir()
        for path in (stage / "scripts").glob("*.py") if path.is_file() and "__pycache__" not in path.parts
    )
    return {
        "artifact_paths": artifact_paths, "review_paths": review_paths,
        "decision_paths": decision_paths, "validation_paths": validation_paths,
        "schema_paths": schema_paths, "catalog_paths": catalog_paths,
        "contract_paths": contract_paths, "source_code_paths": source_code_paths,
    }


def collect(project_root: Path, run_dir: Path) -> dict[str, Any]:
    """Build a path index containing no copied artifact content."""
    manifest = load_json(run_dir / "manifest.json")
    specs = build_specs(project_root, run_dir)
    path_groups: dict[str, Any] = {}
    file_index: list[dict[str, Any]] = []
    missing: list[str] = []
    role_map = {
        "artifact_paths": "canonical_artifact", "review_paths": "human_review",
        "decision_paths": "decision_manifest", "validation_paths": "validation_evidence",
        "schema_paths": "schema", "catalog_paths": "catalog", "contract_paths": "contract",
        "source_code_paths": "source_code",
    }
    for group, values in specs.items():
        if isinstance(values, dict):
            path_groups[group] = {name: project_relative(path, project_root) for name, path in values.items()}
            entries = [(name, path) for name, path in values.items()]
        else:
            path_groups[group] = [project_relative(path, project_root) for path in values]
            entries = [(f"source_code_{index:03d}", path) for index, path in enumerate(values, start=1)]
        for logical_name, path in entries:
            relative = project_relative(path, project_root)
            exists = path.is_file()
            if not exists:
                missing.append(relative)
            if logical_name == "runtime_manifest":
                role = "runtime_manifest"
            elif group == "validation_paths" and logical_name == "runtime-manifest-validation-report":
                role = "runtime_validation"
            else:
                role = role_map[group]
            file_index.append({
                "logical_name": logical_name, "path": relative, "role": role,
                "sha256": sha256(path) if exists else None,
                "file_size": path.stat().st_size if exists else None,
            })
    return {
        "run_id": manifest.get("run_id"), "contract_version": manifest.get("contract_version"),
        "synthetic": manifest.get("synthetic"), "generated_at": utc_now(),
        **path_groups, "file_index": file_index, "missing_paths": sorted(set(missing)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        project_root = Path(__file__).resolve().parents[4]
        run_dir = args.run_dir.resolve() if args.run_dir.is_absolute() else (project_root / args.run_dir).resolve()
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite QC input index: {args.output}")
        index = collect(project_root, run_dir)
        write_json(args.output, index)
        print(json.dumps({"status": "PASS", "output": str(args.output), "file_count": len(index["file_index"]), "missing_count": len(index["missing_paths"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
