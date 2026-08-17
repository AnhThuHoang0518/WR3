#!/usr/bin/env python3
"""Crawl and enrich live WR3 News inputs for a rolling window, then stop at Gate 1."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

from news_crawl_runtime import deduplicate_and_classify, review_translation_gate
from run_vertical_slice_01 import run_vertical_slice


ROOT = Path(__file__).resolve().parent
STAGES = [
    ("market", ROOT / ".agents" / "skills" / "01-market-news" / "scripts" / "crawl_sources.py"),
    ("competitor", ROOT / ".agents" / "skills" / "02-competitor-news" / "scripts" / "crawl_sources.py"),
    ("technology", ROOT / ".agents" / "skills" / "03-technology-news" / "scripts" / "crawl_sources.py"),
    ("policy", ROOT / ".agents" / "skills" / "04-policy-news" / "scripts" / "crawl_sources.py"),
]


def _run_stage(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command, cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "crawl stage failed")
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"crawl stage returned non-JSON output: {' '.join(command)}") from exc


def _content_quality_gate(
    counts: dict[str, int], *, fetch_content: bool, minimum_ratio: float,
) -> dict[str, Any]:
    if not 0.0 <= minimum_ratio <= 1.0:
        raise ValueError("minimum_ratio must be between 0 and 1")
    usable = sum(counts.get(status, 0) for status in ("FULL_TEXT", "PARTIAL_TEXT"))
    total = sum(counts.values())
    ratio = usable / total if total else 0.0
    passed = not fetch_content or (usable > 0 and ratio >= minimum_ratio)
    return {
        "status": "PASS" if passed else "FAIL",
        "usable_content_records": usable,
        "total_records": total,
        "usable_content_ratio": round(ratio, 4),
        "minimum_usable_content_ratio": minimum_ratio,
        "rule": "Khi bật content fetch, tỷ lệ FULL_TEXT/PARTIAL_TEXT phải đạt ngưỡng trước Gate 1.",
    }


def run_live(
    *,
    run_id: str,
    days: int,
    timezone_name: str,
    end_date: date | None,
    providers: str,
    timeout: float,
    max_items_per_stage: int,
    max_competitors: int | None,
    fetch_content: bool = True,
    content_workers: int = 4,
    min_usable_content_ratio: float = 0.5,
) -> dict[str, Any]:
    input_dir = ROOT / "workspace" / "inputs" / "news" / "live" / run_id
    if not 0.0 <= min_usable_content_ratio <= 1.0:
        raise ValueError("min_usable_content_ratio must be between 0 and 1")
    if input_dir.exists() and not input_dir.is_dir():
        raise ValueError(f"Live input path is not a directory: {input_dir}")
    # A live crawl can be interrupted after one or more stage crawlers have
    # atomically written their raw payloads.  Resume only from those complete
    # stage files; never overwrite them or a completed canonical run.
    input_dir.mkdir(parents=True, exist_ok=True)
    stage_payloads: dict[str, dict[str, Any]] = {}
    stage_results: dict[str, dict[str, Any]] = {}
    for stage_name, script in STAGES:
        output = input_dir / f"{stage_name}_raw_news.json"
        if output.is_file():
            try:
                stage_payloads[stage_name] = json.loads(output.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Existing stage payload is invalid JSON: {output}") from exc
            stage_results[stage_name] = {
                "status": "RESUMED",
                "output": str(output),
                "records": len(stage_payloads[stage_name].get("records", [])),
            }
            continue
        command = [
            sys.executable, str(script), "--output", str(output),
            "--days", str(days), "--timezone", timezone_name,
            "--providers", providers, "--timeout", str(timeout),
            "--max-items", str(max_items_per_stage),
            "--content-workers", str(content_workers),
        ]
        if end_date:
            command.extend(["--end-date", end_date.isoformat()])
        if not fetch_content:
            command.append("--no-content")
        if stage_name == "competitor" and max_competitors is not None:
            command.extend(["--max-competitors", str(max_competitors)])
        stage_results[stage_name] = _run_stage(command)
        stage_payloads[stage_name] = json.loads(output.read_text(encoding="utf-8"))

    successful_attempts = sum(
        payload["crawl_audit"]["successful_attempts"] for payload in stage_payloads.values()
    )
    if successful_attempts == 0:
        raise RuntimeError(
            "All live provider attempts failed; crawl evidence was retained but canonical News artifacts were not built"
        )
    records, postprocess_audit = deduplicate_and_classify(
        stage_payloads, max_items_per_type=max_items_per_stage,
    )
    raw_ids = [record["raw_news_id"] for record in records]
    if len(raw_ids) != len(set(raw_ids)):
        raise RuntimeError("Duplicate raw_news_id across live crawl stages")
    windows = {
        (payload["window_start"], payload["window_end_exclusive"], payload["timezone"])
        for payload in stage_payloads.values()
    }
    if len(windows) != 1:
        raise RuntimeError("Live crawl stages produced inconsistent date windows")
    window_start, window_end_exclusive, window_timezone = windows.pop()
    merged = {
        "dataset_name": "WR3 live News candidates for stages 01-04",
        "synthetic": False,
        "run_id": run_id,
        "timezone": window_timezone,
        "window_start": window_start,
        "window_end_exclusive": window_end_exclusive,
        "records": records,
        "crawl_audit": {
            "stage_results": stage_results,
            "stages": {name: payload["crawl_audit"] for name, payload in stage_payloads.items()},
            "total_records": len(records),
            "postprocess": postprocess_audit,
            "successful_attempts": successful_attempts,
            "failed_attempts": sum(
                payload["crawl_audit"]["failed_attempts"] for payload in stage_payloads.values()
            ),
            "content_fetch_enabled": fetch_content,
            "content_status_counts": {
                status: sum(record.get("content_status") == status for record in records)
                for status in ("FULL_TEXT", "PARTIAL_TEXT", "METADATA_ONLY", "UNAVAILABLE")
            },
            "resolved_source_count": sum(
                record.get("crawl_evidence", {}).get("resolution_status") == "RESOLVED"
                for record in records
            ),
            "content_fetch_failed_count": sum(
                record.get("crawl_evidence", {}).get("resolution_status") == "FAILED"
                for record in records
            ),
        },
        "phase_boundary": {
            "signal_extraction_performed": False,
            "ot_evaluation_performed": False,
            "human_relevance_review_required": True,
        },
    }
    raw_input = input_dir / "raw_news.json"
    quality_gate = _content_quality_gate(
        merged["crawl_audit"]["content_status_counts"],
        fetch_content=fetch_content,
        minimum_ratio=min_usable_content_ratio,
    )
    merged["crawl_audit"]["content_quality_gate"] = quality_gate
    translation_gate = review_translation_gate(records)
    merged["crawl_audit"]["review_translation_gate"] = translation_gate
    raw_input.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if quality_gate["status"] != "PASS":
        raise RuntimeError(
            "Content quality gate failed: "
            f"usable ratio {quality_gate['usable_content_ratio']:.1%} is below {min_usable_content_ratio:.1%}; "
            f"raw crawl evidence retained at {raw_input}"
        )
    if translation_gate["status"] != "PASS":
        raise RuntimeError(
            "Vietnamese review translation required before Gate 1: "
            f"{len(translation_gate['pending_records'])} record(s) pending; "
            f"raw crawl evidence retained at {raw_input}"
        )
    pipeline_result = run_vertical_slice(raw_input, run_id)
    return {
        "status": "PASS",
        "run_id": run_id,
        "window_start": window_start,
        "window_end_exclusive": window_end_exclusive,
        "timezone": window_timezone,
        "raw_input": str(raw_input),
        "crawl_counts": {
            name: postprocess_audit["counts_by_type"][name.upper()]
            for name, _ in STAGES
        },
        "postprocess": postprocess_audit,
        "failed_attempts": merged["crawl_audit"]["failed_attempts"],
        "content_quality": {
            "content_status_counts": merged["crawl_audit"]["content_status_counts"],
            "resolved_source_count": merged["crawl_audit"]["resolved_source_count"],
            "content_fetch_failed_count": merged["crawl_audit"]["content_fetch_failed_count"],
            "quality_gate": merged["crawl_audit"]["content_quality_gate"],
        },
        "review_translation": translation_gate,
        "pipeline": pipeline_result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--timezone", default="Asia/Bangkok")
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--providers", default="bing,google,web")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-items-per-stage", type=int, default=50)
    parser.add_argument("--max-competitors", type=int)
    parser.add_argument("--content-workers", type=int, default=4)
    parser.add_argument("--min-usable-content-ratio", type=float, default=0.5)
    parser.add_argument("--no-content", action="store_true", help="Discover RSS metadata without fetching source pages")
    args = parser.parse_args()
    run_id = args.run_id or datetime.now().strftime("%Y%m%d-%H%M%S-live")
    try:
        result = run_live(
            run_id=run_id, days=args.days, timezone_name=args.timezone,
            end_date=args.end_date, providers=args.providers, timeout=args.timeout,
            max_items_per_stage=args.max_items_per_stage,
            max_competitors=args.max_competitors,
            fetch_content=not args.no_content,
            content_workers=args.content_workers,
            min_usable_content_ratio=args.min_usable_content_ratio,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "run_id": run_id, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
