#!/usr/bin/env python3
"""Crawl known and emerging Smart City competitor News candidates."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SHARED = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SHARED))
from news_crawl_runtime import QuerySpec, crawl_queries, write_json  # noqa: E402


# Open competitor discovery is intentionally independent of competitors.json. The
# catalog remains useful for tracking known entities, but it is not a company
# whitelist. Geographic coverage remains the configured WR3 crawl scope.
OPEN_DISCOVERY_QUERIES = (
    QuerySpec(
        "competitor-open-vn",
        '("đô thị thông minh" OR "smart city") (doanh nghiệp OR "nhà cung cấp" OR công ty) '
        '("ra mắt" OR hợp tác OR "trúng thầu" OR triển khai)',
        "Việt Nam",
    ),
    QuerySpec(
        "competitor-open-cn",
        '("智慧城市" OR "城市大脑" OR "数字城市") (企业 OR 厂商 OR 公司) '
        '(发布 OR 合作 OR 中标 OR 部署 OR 项目)',
        "China",
    ),
    QuerySpec(
        "competitor-open-sg",
        '("Smart Nation" OR "smart city") Singapore (company OR vendor OR provider) '
        '(launch OR partnership OR contract OR deployment OR tender)',
        "Singapore",
    ),
    QuerySpec(
        "competitor-open-experience-venues",
        '(stadium OR arena OR "theme park" OR "amusement park" OR attraction) (vendor OR provider OR platform OR company) '
        '("fan journey" OR "guest experience" OR ticketing OR wayfinding OR queue OR accessibility) '
        '(launch OR partnership OR contract OR deployment OR "case study")',
        "Global",
    ),
    QuerySpec(
        "competitor-open-experience-digital-twin",
        '("digital twin" OR "3D city model") (city OR venue OR stadium OR attraction) '
        '(vendor OR provider OR platform OR company) (launch OR partnership OR contract OR deployment OR "case study")',
        "Global",
    ),
    QuerySpec(
        "competitor-open-experience-safety-ai",
        '("smart city" OR "urban operations" OR stadium OR "theme park") (AI OR "video analytics" OR "computer vision") '
        '(safety OR security OR crowd OR "incident response") (vendor OR provider OR company) '
        '(launch OR partnership OR contract OR deployment)',
        "Global",
    ),
    QuerySpec(
        "competitor-open-experience-places",
        '("digital signage" OR "LED display" OR "smart parking" OR "theme park") (street OR pedestrian OR visitor OR driver OR resident OR "public space") '
        '(vendor OR provider OR platform OR company) (accessibility OR glare OR wayfinding OR "parking guidance" OR "user experience") '
        '(launch OR partnership OR contract OR deployment OR "case study")',
        "Global",
    ),
    QuerySpec(
        "competitor-open-experience-citizen-vn",
        '("đô thị thông minh" OR "bãi đỗ xe thông minh" OR "khu vui chơi" OR "sân vận động") ("người dân" OR "người lái xe" OR "khách tham quan" OR khán giả) (nhà cung cấp OR doanh nghiệp OR nền tảng OR giải pháp) (ra mắt OR hợp tác OR hợp đồng OR triển khai OR "nghiên cứu tình huống")',
        "Việt Nam",
    ),
)


def load_queries(catalog_path: Path, max_competitors: int | None) -> list[QuerySpec]:
    payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    active = [item for item in payload.get("competitors", []) if item.get("active", True)]
    if max_competitors is not None:
        active = active[:max_competitors]
    queries: list[QuerySpec] = list(OPEN_DISCOVERY_QUERIES)
    for item in active:
        name = str(item.get("name", "")).strip()
        competitor_id = str(item.get("competitor_id", "unknown")).strip()
        if not name:
            continue
        base_query = (
            f'"{name}" ("smart city" OR "đô thị thông minh" OR "giao thông thông minh" '
            'OR IoT OR AIoT OR "digital twin" OR "video analytics") '
            '(dự án OR hợp tác OR hợp đồng OR triển khai OR đầu tư OR "ra mắt")'
        )
        queries.append(QuerySpec(
            f"competitor-{competitor_id.lower()}",
            base_query,
            "Việt Nam" if competitor_id < "SC-027" else "Global",
            (name,),
        ))
        queries.append(QuerySpec(
            f"competitor-{competitor_id.lower()}-cn",
            f'"{name}" (China OR 中国) ("smart city" OR 智慧城市 OR deployment OR partnership OR contract)',
            "China",
            (name,),
        ))
        queries.append(QuerySpec(
            f"competitor-{competitor_id.lower()}-sg",
            f'"{name}" Singapore ("smart city" OR "Smart Nation" OR deployment OR partnership OR contract)',
            "Singapore",
            (name,),
        ))
    return queries


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--competitors", type=Path,
        default=Path(__file__).resolve().parents[1] / "references" / "competitors.json",
    )
    parser.add_argument("--max-competitors", type=int)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--timezone", default="Asia/Bangkok")
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--providers", default="bing,google,web")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--content-workers", type=int, default=4)
    parser.add_argument("--no-content", action="store_true", help="Discover RSS metadata without fetching source pages")
    args = parser.parse_args()
    try:
        payload = crawl_queries(
            news_type="COMPETITOR",
            queries=load_queries(args.competitors, args.max_competitors),
            days=args.days, timezone_name=args.timezone, end_date=args.end_date,
            providers=[value.strip() for value in args.providers.split(",") if value.strip()],
            timeout=args.timeout, max_items=args.max_items,
            fetch_content=not args.no_content,
            content_workers=args.content_workers,
        )
        write_json(args.output, payload)
        print(json.dumps({"status": "PASS", "output": str(args.output), "records": len(payload["records"]), "audit": payload["crawl_audit"]}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
