#!/usr/bin/env python3
"""Prepare immutable approved Signal/O-T context for semantic Product Mapping."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object with a clear error."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def prepare_context(
    signals: dict[str, Any], bundle: dict[str, Any], decision: dict[str, Any]
) -> dict[str, Any]:
    """Return a context containing only Gate 2-approved O/T and their Signals."""
    if decision.get("overall_status") != "APPROVED":
        raise ValueError("Gate 2 overall_status must be APPROVED")
    if decision.get("revision_ot_ids"):
        raise ValueError("Gate 2 must not contain revision_ot_ids")
    if not (decision.get("reviewer") and decision.get("reviewed_at")):
        raise ValueError("Gate 2 human reviewer metadata is required")
    run_ids = {signals.get("run_id"), bundle.get("run_id"), decision.get("run_id")}
    if len(run_ids) != 1 or None in run_ids:
        raise ValueError("Signals, approved bundle and decision must share one run_id")
    if signals.get("synthetic") is not bundle.get("synthetic") or bundle.get("synthetic") is not decision.get("synthetic"):
        raise ValueError("Synthetic flags do not match")

    approved_ids = list(decision.get("approved_ot_ids", []))
    rejected = set(decision.get("rejected_ot_ids", [])) | set(decision.get("revision_ot_ids", []))
    ot_items = bundle.get("approved_opportunity_threat", [])
    if not isinstance(ot_items, list):
        raise ValueError("approved_opportunity_threat must be an array")
    bundle_ids = [item.get("ot_id") for item in ot_items if isinstance(item, dict)]
    if len(bundle_ids) != len(set(bundle_ids)) or set(bundle_ids) != set(approved_ids):
        raise ValueError("Approved bundle must contain each approved_ot_id exactly once")
    if set(bundle_ids) & rejected:
        raise ValueError("Approved bundle contains rejected or revision O/T")

    signal_by_id = {item.get("signal_id"): item for item in signals.get("items", [])}
    unknown_signals = sorted({item.get("signal_id") for item in ot_items} - set(signal_by_id))
    if unknown_signals:
        raise ValueError(f"Approved O/T references unknown Signal IDs: {unknown_signals}")
    relevant_ids = {item.get("signal_id") for item in ot_items}
    relevant_signals = [item for item in signals.get("items", []) if item.get("signal_id") in relevant_ids]
    links = [
        {
            "signal_id": signal["signal_id"],
            "approved_ot_ids": [
                item["ot_id"] for item in ot_items if item.get("signal_id") == signal["signal_id"]
            ],
        }
        for signal in relevant_signals
    ]
    return {
        "run_id": signals["run_id"],
        "synthetic": signals["synthetic"],
        "gate_2_status": decision["overall_status"],
        "approved_ot_ids": approved_ids,
        "relevant_signals": relevant_signals,
        "approved_opportunity_threat": ot_items,
        "signal_to_approved_ot_links": links,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--approved-ot-bundle", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite existing context: {args.output}")
        context = prepare_context(load_json(args.signals), load_json(args.approved_ot_bundle), load_json(args.decision))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(context, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS", "output": str(args.output), "approved_ot_count": len(context["approved_ot_ids"]), "relevant_signal_count": len(context["relevant_signals"])}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
