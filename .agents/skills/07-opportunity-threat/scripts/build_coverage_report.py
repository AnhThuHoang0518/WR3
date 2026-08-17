#!/usr/bin/env python3
"""Build Signal-to-Opportunity/Threat coverage with explicit uncovered rationale."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc


def build_coverage(signals: dict[str, Any], opportunity_threat: dict[str, Any]) -> dict[str, Any]:
    signal_ids = [item["signal_id"] for item in signals.get("items", [])]
    links = {signal_id: {"OPPORTUNITY": [], "THREAT": []} for signal_id in signal_ids}
    errors: list[str] = []
    for item in opportunity_threat.get("items", []):
        if item.get("signal_id") not in links:
            errors.append(f"Orphan O/T {item.get('ot_id')} -> {item.get('signal_id')}")
            continue
        if item.get("type") in links[item["signal_id"]]:
            links[item["signal_id"]][item["type"]].append(item["ot_id"])
    with_ot = [signal_id for signal_id in signal_ids if any(links[signal_id].values())]
    without_ot = [signal_id for signal_id in signal_ids if not any(links[signal_id].values())]
    link_items = [{
        "signal_id": signal_id,
        "opportunity_ids": links[signal_id]["OPPORTUNITY"],
        "threat_ids": links[signal_id]["THREAT"],
        "coverage_status": "COVERED" if any(links[signal_id].values()) else "NO_OT",
        "rationale": (
            "Signal cha hỗ trợ các cơ chế tác động cụ thể đối với VSF/Vingroup được liệt kê."
            if any(links[signal_id].values())
            else "Chưa suy ra được cơ chế Opportunity hoặc Threat đủ cụ thể đối với VSF/Vingroup từ Signal này."
        ),
    } for signal_id in signal_ids]
    items = opportunity_threat.get("items", [])
    return {
        "run_id": signals["run_id"],
        "signal_ids": signal_ids,
        "signal_ids_with_ot": with_ot,
        "signal_ids_without_ot": without_ot,
        "opportunity_count": sum(item.get("type") == "OPPORTUNITY" for item in items),
        "threat_count": sum(item.get("type") == "THREAT" for item in items),
        "signal_to_ot_links": link_items,
        "validation_status": "PASS" if not errors else "FAIL",
        "findings": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--opportunity-threat", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_coverage(load_json(args.signals), load_json(args.opportunity_threat))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["validation_status"], "output": str(args.output)}, ensure_ascii=False))
        return 0 if report["validation_status"] == "PASS" else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
