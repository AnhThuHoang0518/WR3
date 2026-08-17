#!/usr/bin/env python3
"""Crawl live Technology News candidates for the WR3 seven-day input window."""

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
    QuerySpec("technology-ai-iot", '"smart city" (AI OR IoT OR sensor OR "edge computing")', "Global"),
    QuerySpec("technology-platform", '"smart city platform" (integration OR interoperability OR "digital twin")', "Global"),
    QuerySpec("technology-vn", '("đô thị thông minh" OR "thành phố thông minh") (AI OR IoT OR nền tảng OR cảm biến)', "Việt Nam"),
    QuerySpec("technology-cn-capabilities", '("智慧城市" OR "城市大脑") (人工智能 OR 物联网 OR 数字孪生 OR 计算机视觉 OR 智能交通)', "China"),
    QuerySpec("technology-cn-english", '("smart city" OR "city brain") China (AIoT OR "digital twin" OR "video analytics" OR "intelligent transport")', "China"),
    QuerySpec("technology-sg-capabilities", '("Smart Nation" OR "smart city") Singapore ("digital twin" OR IoT OR "video analytics" OR "intelligent transport" OR "environmental monitoring")', "Singapore"),
    QuerySpec(
        "technology-product-adjacent",
        '("smart city" OR municipal) ("traffic management" OR "public safety" OR "smart lighting" OR "urban operations platform" OR "air quality monitoring") (launch OR pilot OR deployment OR integration)',
        "Global",
    ),
    QuerySpec(
        "technology-experience-stadium",
        '(stadium OR arena OR "smart venue") ("mobile ticketing" OR "digital identity" OR "frictionless entry" OR wayfinding OR accessibility OR "queue management" OR "crowd analytics" OR cashless) (pilot OR deployment OR integration OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "technology-experience-attractions",
        '("theme park" OR "amusement park" OR resort OR attraction) ("guest app" OR wearable OR "digital pass" OR "virtual queue" OR wayfinding OR personalization OR accessibility OR "crowd forecasting") (pilot OR deployment OR integration OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "technology-experience-digital-twin",
        '("digital twin" OR "3D city model" OR "BIM GIS") (city OR venue OR stadium OR attraction) (simulation OR "real-time" OR interoperability OR dashboard OR visualization) (operator OR planner OR visitor OR citizen) (pilot OR deployment OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "technology-experience-safety-ai",
        '("smart city" OR "urban operations" OR stadium OR "theme park") (AI OR "video analytics" OR "computer vision") ("anomaly detection" OR safety OR security OR crowd OR "incident response") ("human in the loop" OR operator OR control room) (pilot OR deployment OR accuracy OR outcome)',
        "Global",
    ),
    QuerySpec(
        "technology-experience-citizen-vn",
        '("đô thị thông minh" OR "Smart City") ("người dân" OR cư dân OR "trải nghiệm người dân") (ứng dụng OR nền tảng OR IoT OR AI OR dữ liệu) ("dịch vụ đô thị" OR phản ánh OR giao thông OR tiện ích) (thử nghiệm OR triển khai OR sử dụng OR kết quả)',
        "Việt Nam",
    ),
    QuerySpec(
        "technology-experience-parking-vn",
        '("bãi đỗ xe thông minh" OR "smart parking") ("người lái xe" OR "người dân" OR khách hàng) (cảm biến OR ứng dụng OR chỉ dẫn OR đặt chỗ OR thanh toán OR nhận diện) (thử nghiệm OR triển khai OR sử dụng OR kết quả)',
        "Việt Nam",
    ),
    QuerySpec(
        "technology-experience-venues-vn",
        '("khu vui chơi" OR "công viên chủ đề" OR "sân vận động" OR nhà thi đấu) ("khách tham quan" OR khán giả OR người hâm mộ) (vé điện tử OR vào cổng OR xếp hàng OR chỉ dẫn OR thanh toán OR an toàn OR cá nhân hóa) (thử nghiệm OR triển khai OR tích hợp OR kết quả)',
        "Việt Nam",
    ),
    QuerySpec(
        "technology-experience-places",
        '("public space" OR street OR plaza OR "theme park" OR "amusement park" OR "smart parking") ("digital signage" OR "LED display" OR wayfinding OR "parking guidance" OR accessibility OR glare OR "visual impact" OR "visual overload" OR distraction) (pedestrian OR visitor OR driver OR resident OR operator) (pilot OR deployment OR mitigation OR remediation OR "brightness limit" OR "case study" OR outcome)',
        "Global",
    ),
    QuerySpec(
        "technology-experience-places-vn",
        '("màn hình LED" OR "biển quảng cáo điện tử" OR "màn hình công cộng" OR "biển chỉ dẫn số") ("người đi đường" OR "người đi bộ" OR "người lái xe" OR "cư dân") ("chói mắt" OR "mất tập trung" OR "an toàn giao thông" OR "khả năng tiếp cận") (công nghệ OR triển khai OR đo lường OR giảm sáng OR khắc phục OR xử lý)',
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
            news_type="TECHNOLOGY", queries=QUERIES, days=args.days,
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
