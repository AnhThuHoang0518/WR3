#!/usr/bin/env python3
"""Generate a human-readable synthetic QC summary without adding analysis or Actions."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from qc_common import load_json


def generate_summary(
    report: dict[str, Any], integrity: dict[str, Any], manifest: dict[str, Any],
    decisions: list[dict[str, Any]], approved_actions: dict[str, Any], contract_version: str,
) -> str:
    """Render required QC sections directly from canonical QC data."""
    summary = report["summary"]
    eligible = summary["pipeline_eligible_for_release"]
    errors = [item for item in report["checks"] if item["status"] == "ERROR"]
    warnings = [item for item in report["checks"] if item["status"] == "WARNING"]
    lineage = next((item for item in report["checks"] if item["check_name"] == "Cross-stage lineage summary"), None)
    lines = [
        "---", "report_type: MI_QUALITY_CONTROL_SUMMARY", f"run_id: {report['run_id']}",
        f"contract_version: {contract_version}", f"pipeline_eligible_for_release: {str(eligible).lower()}",
        "formal_hitl_gate: false", "---", "", "# Quality Control Summary", "",
        "## Release decision", "", f"- {'Eligible' if eligible else 'Not eligible'}",
        f"- Error count: {summary['error_count']}", f"- Warning count: {summary['warning_count']}",
        f"- Pass count: {summary['passed_count']}", f"- Overall status: `{summary['overall_status']}`", "",
        "## Pipeline status", "",
    ]
    for stage, status in manifest.get("stage_statuses", {}).items():
        lines.append(f"- {stage}: `{status}`")
    lines.extend(["", "## HITL status", ""])
    for number, decision in enumerate(decisions, start=1):
        lines.append(f"- Gate {number}: `{decision.get('overall_status')}` — reviewer {decision.get('reviewer')}")
    lines.extend(["", "## Critical findings", ""])
    lines.extend(
        [f"- `{item['check_id']}` {item['check_name']}: {item['message']} Remediation: {item['remediation']}" for item in errors]
        or ["- Không có ERROR."]
    )
    lines.extend(["", "## Warnings", ""])
    lines.extend(
        [f"- `{item['check_id']}` {item['check_name']}: {item['message']} Remediation: {item['remediation']}" for item in warnings]
        or ["- Không có WARNING."]
    )
    lines.extend(["", "## Lineage summary", "", f"- {lineage['message'] if lineage else 'Không có lineage summary.'}", "", "## Approved action portfolio", ""])
    for action in approved_actions.get("items", []):
        lines.append(f"- `{action.get('action_id')}` — {action.get('target_product_or_category')} — {action.get('recommended_response')}")
    lines.extend([
        "", "## Integrity", "", f"- Files checked: {integrity.get('file_count', 0)}",
        f"- Hash status: `{integrity.get('integrity_status')}`",
        "- Contract, catalog, human reviews, decisions, bundles and canonical artifacts are immutable after QC.",
        "", "## Next operational step", "",
    ])
    if eligible:
        lines.extend([
            "- Synthetic pipeline đủ điều kiện kết thúc Quality Control.",
            "- Đây không phải Market Intelligence thật và không được tự động bắt đầu real-data pipeline.",
        ])
    else:
        lines.extend([
            "- Hoàn thành remediation của mọi ERROR rồi chạy lại QC.",
            "- QC không tự sửa artifact hoặc human decision.",
        ])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--integrity", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--gate-1", required=True, type=Path)
    parser.add_argument("--gate-2", required=True, type=Path)
    parser.add_argument("--gate-3", required=True, type=Path)
    parser.add_argument("--approved-actions", required=True, type=Path)
    parser.add_argument("--contract-version", required=True)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite QC summary: {args.output}")
        text = generate_summary(
            load_json(args.report), load_json(args.integrity), load_json(args.manifest),
            [load_json(args.gate_1), load_json(args.gate_2), load_json(args.gate_3)],
            load_json(args.approved_actions), args.contract_version,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
