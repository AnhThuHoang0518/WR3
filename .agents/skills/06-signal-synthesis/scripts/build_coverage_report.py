#!/usr/bin/env python3
"""Build deterministic coverage from Gate 1 KEEP News to synthesized Signals."""

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


def build_coverage(bundle: dict[str, Any], signals: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
    approved_items = bundle.get("approved_news", [])
    kept = [item["news_id"] for item in approved_items]
    item_by_id = {item["news_id"]: item for item in approved_items}
    excluded = set(decision.get("excluded_news_ids", []))
    links: dict[str, list[str]] = {news_id: [] for news_id in kept}
    errors: list[str] = []
    for signal in signals.get("items", []):
        for news_id in signal.get("evidence_news_ids", []):
            if news_id in excluded:
                errors.append(f"Excluded News used as evidence: {news_id}")
            if news_id not in links:
                errors.append(f"Unknown or non-KEEP News used as evidence: {news_id}")
            else:
                links[news_id].append(signal["signal_id"])
    used = [news_id for news_id in kept if links[news_id]]
    unused = [news_id for news_id in kept if not links[news_id]]
    link_items = []
    for news_id in kept:
        item = item_by_id[news_id]
        status = item.get("content_status", "UNAVAILABLE")
        if links[news_id]:
            rationale = "Bản tin hỗ trợ các Signal về cùng cơ chế thay đổi được liệt kê."
        elif status in {"METADATA_ONLY", "UNAVAILABLE"}:
            rationale = (
                f"Không sử dụng: content_status={status}, chưa đủ nội dung nguồn để xác lập cơ chế thay đổi."
            )
        else:
            rationale = "Không sử dụng: chưa hình thành cơ chế thay đổi riêng biệt, có bằng chứng và không trùng lặp."
        link_items.append({
            "news_id": news_id,
            "signal_ids": links[news_id],
            "usage_status": "USED" if links[news_id] else "UNUSED",
            "rationale": rationale,
        })
    return {
        "run_id": bundle["run_id"],
        "kept_news_ids": kept,
        "used_evidence_news_ids": used,
        "unused_kept_news_ids": unused,
        "signal_count": len(signals.get("items", [])),
        "news_to_signal_links": link_items,
        "validation_status": "PASS" if not errors else "FAIL",
        "findings": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved-news", required=True, type=Path)
    parser.add_argument("--signals", required=True, type=Path)
    parser.add_argument("--decision", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = build_coverage(load_json(args.approved_news), load_json(args.signals), load_json(args.decision))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": report["validation_status"], "output": str(args.output)}, ensure_ascii=False))
        return 0 if report["validation_status"] == "PASS" else 1
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
