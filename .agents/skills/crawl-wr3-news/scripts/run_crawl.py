#!/usr/bin/env python3
"""Preflight and run the canonical WR3 live News crawl through Gate 1."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
STAGE_SCRIPTS = {
    "market": ROOT / ".agents" / "skills" / "01-market-news" / "scripts" / "crawl_sources.py",
    "competitor": ROOT / ".agents" / "skills" / "02-competitor-news" / "scripts" / "crawl_sources.py",
    "technology": ROOT / ".agents" / "skills" / "03-technology-news" / "scripts" / "crawl_sources.py",
    "policy": ROOT / ".agents" / "skills" / "04-policy-news" / "scripts" / "crawl_sources.py",
}
REQUIRED_FILES = [ROOT / "AGENTS.md", ROOT / "news_crawl_runtime.py", ROOT / "run_live_news.py", *STAGE_SCRIPTS.values()]
FOCUS_QUERY_IDS = {
    "market": (
        "market-experience-stadium",
        "market-experience-attractions",
        "market-experience-digital-twin",
        "market-experience-safety-ai",
        "market-experience-citizen-vn",
        "market-experience-parking-vn",
        "market-experience-venues-vn",
        "market-experience-places",
        "market-experience-places-vn",
    ),
    "competitor": (
        "competitor-open-experience-venues",
        "competitor-open-experience-digital-twin",
        "competitor-open-experience-safety-ai",
        "competitor-open-experience-places",
        "competitor-open-experience-citizen-vn",
    ),
    "technology": (
        "technology-experience-stadium",
        "technology-experience-attractions",
        "technology-experience-digital-twin",
        "technology-experience-safety-ai",
        "technology-experience-citizen-vn",
        "technology-experience-parking-vn",
        "technology-experience-venues-vn",
        "technology-experience-places",
        "technology-experience-places-vn",
    ),
    "policy": (
        "policy-experience-venues",
        "policy-experience-digital-twin-ai",
        "policy-experience-citizen-vn",
        "policy-experience-parking-vn",
        "policy-experience-venues-vn",
        "policy-experience-places",
        "policy-experience-places-vn",
    ),
}
SMART_CITY_BASELINE_QUERY_IDS = {
    "market": (
        "market-vn-procurement",
        "market-global-adoption",
        "market-cn-procurement",
        "market-sg-procurement",
    ),
    "competitor": (
        "competitor-open-vn",
        "competitor-open-cn",
        "competitor-open-sg",
    ),
    "technology": (
        "technology-ai-iot",
        "technology-platform",
        "technology-vn",
        "technology-cn-capabilities",
        "technology-sg-capabilities",
    ),
    "policy": (
        "policy-vn-smart-city",
        "policy-global",
        "policy-cn-smart-city",
        "policy-sg-smart-nation",
    ),
}
JOURNEY_EVIDENCE_TERMS = (
    "journey", "experience", "accessibility", "queue", "operator",
    "walkthrough", "video", "case study", "deployment", "outcome",
)
VIETNAM_PLACE_EXPERIENCE_TERMS = (
    "màn hình led", "chói mắt", "mất tập trung", "người đi đường",
    "an toàn giao thông", "phản ánh", "xử lý",
)
CITIZEN_EXPERIENCE_TERMS = (
    "trải nghiệm người dân", "dịch vụ đô thị", "bãi đỗ xe thông minh",
    "khu vui chơi", "sân vận động", "khách tham quan",
)
REQUIRED_BLOCKED_SOURCES = ("电玩巴士", "tgbus.com")


def preflight() -> dict[str, Any]:
    missing = [str(path) for path in REQUIRED_FILES if not path.is_file()]
    texts = {
        name: path.read_text(encoding="utf-8")
        for name, path in STAGE_SCRIPTS.items()
        if path.is_file()
    }
    geography = {
        name: {
            "china": "China" in text and ("中国" in text or "智慧城市" in text),
            "singapore": "Singapore" in text,
        }
        for name, text in texts.items()
    }
    product_adjacent = {
        name: "product-adjacent" in texts.get(name, "")
        for name in ("market", "technology")
    }
    product_experience = {
        name: {
            "required_query_ids": list(query_ids),
            "missing_query_ids": [
                query_id for query_id in query_ids if query_id not in texts.get(name, "")
            ],
        }
        for name, query_ids in FOCUS_QUERY_IDS.items()
    }
    smart_city_baseline = {
        name: {
            "required_query_ids": list(query_ids),
            "missing_query_ids": [
                query_id for query_id in query_ids if query_id not in texts.get(name, "")
            ],
        }
        for name, query_ids in SMART_CITY_BASELINE_QUERY_IDS.items()
    }
    journey_evidence_terms = {
        term: any(term in text.casefold() for text in texts.values())
        for term in JOURNEY_EVIDENCE_TERMS
    }
    vietnam_place_experience_terms = {
        term: any(term in text.casefold() for text in texts.values())
        for term in VIETNAM_PLACE_EXPERIENCE_TERMS
    }
    citizen_experience_terms = {
        term: any(term in text.casefold() for text in texts.values())
        for term in CITIZEN_EXPERIENCE_TERMS
    }
    runtime_text = (
        (ROOT / "news_crawl_runtime.py").read_text(encoding="utf-8")
        if (ROOT / "news_crawl_runtime.py").is_file()
        else ""
    )
    runner_text = Path(__file__).read_text(encoding="utf-8")
    web_search_provider = {
        "runtime_provider_url": 'provider == "web"' in runtime_text,
        "runtime_parser": "parse_web_search" in runtime_text,
        "runtime_source_fetch": "WEB_SEARCH_FETCH" in runtime_text,
        "default_enabled": 'default="bing,google,web"' in runner_text,
    }
    competitor_text = texts.get("competitor", "")
    blocked_source_enforcement = {
        source: source in runtime_text for source in REQUIRED_BLOCKED_SOURCES
    }
    competitor_open_discovery = all(
        query_id in competitor_text
        for query_id in (
            "competitor-open-vn",
            "competitor-open-cn",
            "competitor-open-sg",
        )
    )
    forbidden_name = "products" + ".json"
    forbidden_references = [
        str(path)
        for path in [ROOT / "run_live_news.py", ROOT / "news_crawl_runtime.py", *STAGE_SCRIPTS.values()]
        if path.is_file() and forbidden_name in path.read_text(encoding="utf-8")
    ]
    errors: list[str] = []
    if missing:
        errors.append("missing required runtime files")
    for name in STAGE_SCRIPTS:
        if not geography.get(name, {}).get("china"):
            errors.append(f"{name} has no dedicated China query")
        if not geography.get(name, {}).get("singapore"):
            errors.append(f"{name} has no dedicated Singapore query")
    if not all(product_adjacent.values()):
        errors.append("market/technology product-adjacent query expansion is incomplete")
    if any(item["missing_query_ids"] for item in smart_city_baseline.values()):
        errors.append("broad Smart City baseline query coverage is incomplete")
    if any(item["missing_query_ids"] for item in product_experience.values()):
        errors.append("product-experience focus-lane query coverage is incomplete")
    if not all(journey_evidence_terms.values()):
        errors.append("journey or evidence-depth query vocabulary is incomplete")
    if not all(vietnam_place_experience_terms.values()):
        errors.append("Vietnamese public-space user-experience query vocabulary is incomplete")
    if not all(citizen_experience_terms.values()):
        errors.append("citizen, parking, attraction, or stadium experience query vocabulary is incomplete")
    if not all(web_search_provider.values()):
        errors.append("parallel Web Search and source-fetch discovery is incomplete or not enabled by default")
    if not competitor_open_discovery:
        errors.append("competitor open discovery is incomplete or still catalog-only")
    if not all(blocked_source_enforcement.values()):
        errors.append("blocked-source enforcement is incomplete")
    if forbidden_references:
        errors.append("an upstream crawl runtime references the VSF product catalog")
    return {
        "status": "PASS" if not errors else "FAIL",
        "workspace": str(ROOT),
        "missing_files": missing,
        "geography_coverage": geography,
        "product_adjacent_query_coverage": product_adjacent,
        "smart_city_baseline_query_coverage": smart_city_baseline,
        "product_experience_query_coverage": product_experience,
        "journey_evidence_term_coverage": journey_evidence_terms,
        "vietnam_place_experience_term_coverage": vietnam_place_experience_terms,
        "citizen_experience_term_coverage": citizen_experience_terms,
        "web_search_provider": web_search_provider,
        "competitor_open_discovery": competitor_open_discovery,
        "blocked_source_enforcement": blocked_source_enforcement,
        "forbidden_catalog_references": forbidden_references,
        "errors": errors,
        "phase_boundary": "NEWS_RELEVANCE_HITL",
    }


def build_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(ROOT / "run_live_news.py"),
        "--days", str(args.days),
        "--timezone", args.timezone,
        "--providers", args.providers,
        "--timeout", str(args.timeout),
        "--max-items-per-stage", str(args.max_items_per_stage),
        "--content-workers", str(args.content_workers),
        "--min-usable-content-ratio", str(args.min_usable_content_ratio),
    ]
    if args.run_id:
        command.extend(["--run-id", args.run_id])
    if args.end_date:
        command.extend(["--end-date", args.end_date])
    if args.max_competitors is not None:
        command.extend(["--max-competitors", str(args.max_competitors)])
    if args.no_content:
        command.append("--no-content")
    return command


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--run-id")
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--timezone", default="Asia/Bangkok")
    parser.add_argument("--end-date")
    parser.add_argument("--providers", default="bing,google,web")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-items-per-stage", type=int, default=50)
    parser.add_argument("--max-competitors", type=int)
    parser.add_argument("--content-workers", type=int, default=4)
    parser.add_argument("--min-usable-content-ratio", type=float, default=0.5)
    parser.add_argument("--no-content", action="store_true")
    args = parser.parse_args()

    report = preflight()
    if args.check_only or report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "PASS" else 1

    completed = subprocess.run(
        build_command(args),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
