#!/usr/bin/env python3
"""Crawl live Market News candidates for the WR3 seven-day input window."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

SHARED = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(SHARED))
from news_crawl_runtime import QuerySpec, crawl_queries, write_json  # noqa: E402


QUERIES = [
    QuerySpec("market-vn-procurement", '"đô thị thông minh" (đầu tư OR mua sắm OR triển khai OR dự án)', "Việt Nam"),
    QuerySpec("market-vn-operations", '("smart city" OR "đô thị thông minh") (vận hành OR giao thông OR tiện ích OR khu công nghiệp)', "Việt Nam"),
    QuerySpec("market-global-adoption", '"smart city" (procurement OR investment OR deployment OR adoption)', "Global"),
    QuerySpec("market-cn-procurement", '("智慧城市" OR "城市大脑") (项目 OR 采购 OR 部署 OR 招标)', "China"),
    QuerySpec("market-cn-deployment", '("smart city" OR "urban digital twin") China (procurement OR deployment OR pilot OR contract)', "China"),
    QuerySpec("market-sg-procurement", '("Smart Nation" OR "smart city") Singapore (tender OR procurement OR deployment OR pilot)', "Singapore"),
    QuerySpec(
        "market-product-adjacent-deployment",
        '("smart city" OR municipal) ("intelligent transport" OR "video analytics" OR "urban digital twin" OR "IoT platform" OR "environmental monitoring") (deployment OR procurement OR contract)',
        "Global",
    ),
    QuerySpec(
        "market-experience-stadium",
        '(stadium OR arena OR "smart venue") ("fan journey" OR "guest experience" OR accessibility OR wayfinding OR queue) (walkthrough OR video OR "case study" OR deployment OR adoption OR outcome)',
        "Global",
    ),
    QuerySpec(
        "market-experience-attractions",
        '("theme park" OR "amusement park" OR resort OR attraction) ("guest journey" OR "visitor experience" OR accessibility OR queue OR itinerary) (walkthrough OR video OR "case study" OR deployment OR adoption OR outcome)',
        "Global",
    ),
    QuerySpec(
        "market-experience-digital-twin",
        '("digital twin" OR "3D city model") (city OR venue OR stadium OR attraction) (operator OR planner OR visitor OR citizen) (deployment OR adoption OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "market-experience-safety-ai",
        '("smart city" OR "urban operations" OR stadium OR "theme park") (AI OR "video analytics" OR "computer vision") (safety OR security OR "incident response" OR crowd) (deployment OR adoption OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "market-experience-citizen-vn",
        '("đô thị thông minh" OR "Smart City") ("người dân" OR cư dân OR "trải nghiệm người dân") ("dịch vụ đô thị" OR ứng dụng OR phản ánh OR thủ tục OR giao thông) (triển khai OR sử dụng OR "phản hồi người dùng" OR hiệu quả OR bất tiện)',
        "Việt Nam",
    ),
    QuerySpec(
        "market-experience-parking-vn",
        '("bãi đỗ xe thông minh" OR "smart parking") ("người dân" OR "người lái xe" OR khách hàng) (tìm chỗ OR đặt chỗ OR chỉ dẫn OR thanh toán OR ra vào OR an toàn) (triển khai OR sử dụng OR chờ đợi OR phản hồi OR hiệu quả)',
        "Việt Nam",
    ),
    QuerySpec(
        "market-experience-venues-vn",
        '("khu vui chơi" OR "công viên chủ đề" OR "sân vận động" OR nhà thi đấu) ("khách tham quan" OR khán giả OR người hâm mộ) (đặt vé OR vào cổng OR xếp hàng OR chỉ dẫn OR thanh toán OR an toàn OR "trải nghiệm") (triển khai OR sử dụng OR phản hồi OR "nghiên cứu tình huống")',
        "Việt Nam",
    ),
    QuerySpec(
        "market-experience-places",
        '("public space" OR street OR plaza OR "theme park" OR "amusement park" OR "smart parking") (pedestrian OR visitor OR driver OR resident OR "user experience" OR accessibility) (wayfinding OR "digital signage" OR "LED display" OR glare OR "visual impact" OR "visual overload" OR distraction OR queue OR parking) (deployment OR adoption OR complaint OR mitigation OR "brightness limit" OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "market-experience-places-vn",
        '("màn hình LED" OR "biển quảng cáo điện tử" OR "màn hình công cộng" OR "biển chỉ dẫn số") ("người đi đường" OR "người đi bộ" OR "người lái xe" OR "cư dân") ("chói mắt" OR "tấn công thị giác" OR "mất tập trung" OR "quá tải thị giác" OR "an toàn giao thông") ("phản ánh" OR "khiếu nại" OR "xử lý" OR "khắc phục" OR "giới hạn độ sáng")',
        "Việt Nam",
    ),
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--timezone", default="Asia/Bangkok")
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--providers", default="bing,google,web")
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--max-items", type=int, default=50)
    parser.add_argument("--content-workers", type=int, default=4)
    parser.add_argument("--no-content", action="store_true", help="Discover RSS metadata without fetching source pages")
    args = parser.parse_args()
    try:
        payload = crawl_queries(
            news_type="MARKET", queries=QUERIES, days=args.days,
            timezone_name=args.timezone, end_date=args.end_date,
            providers=[value.strip() for value in args.providers.split(",") if value.strip()],
            timeout=args.timeout, max_items=args.max_items,
            fetch_content=not args.no_content,
            content_workers=args.content_workers,
        )
        write_json(args.output, payload)
        print(json.dumps({"status": "PASS", "output": str(args.output), "records": len(payload["records"]), "audit": payload["crawl_audit"]}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
