#!/usr/bin/env python3
"""Crawl live Policy News candidates for the WR3 seven-day input window."""

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
    QuerySpec("policy-vn-smart-city", '("đô thị thông minh" OR "thành phố thông minh") (quyết định OR nghị định OR thông tư OR tiêu chuẩn OR phê duyệt)', "Việt Nam"),
    QuerySpec("policy-vn-data", '("dữ liệu đô thị" OR "chính quyền số") (quy định OR tiêu chuẩn OR an toàn thông tin OR bảo vệ dữ liệu)', "Việt Nam"),
    QuerySpec("policy-global", '"smart city" (regulation OR standard OR policy OR "government program")', "Global"),
    QuerySpec("policy-cn-smart-city", '("智慧城市" OR "数字城市") (政策 OR 标准 OR 规划 OR 指导意见 OR 数据治理)', "China"),
    QuerySpec("policy-cn-english", 'China ("smart city" OR "digital city") (policy OR regulation OR standard OR plan)', "China"),
    QuerySpec("policy-sg-smart-nation", '("Smart Nation" OR "smart city") Singapore (policy OR regulation OR standard OR government OR procurement)', "Singapore"),
    QuerySpec(
        "policy-experience-venues",
        '(stadium OR arena OR "theme park" OR attraction) (accessibility OR biometric OR privacy OR safety OR ticketing) (policy OR regulation OR standard OR guideline)',
        "Global",
    ),
    QuerySpec(
        "policy-experience-digital-twin-ai",
        '("digital twin" OR "urban AI" OR "video analytics") (city OR municipal OR venue) (privacy OR governance OR interoperability OR accessibility OR accountability) (policy OR regulation OR standard OR guideline)',
        "Global",
    ),
    QuerySpec(
        "policy-experience-citizen-vn",
        '("đô thị thông minh" OR "Smart City") ("người dân" OR cư dân OR "trải nghiệm người dân") ("dịch vụ đô thị" OR ứng dụng OR phản ánh OR giao thông) (quy định OR tiêu chuẩn OR chương trình OR đánh giá OR xử lý)',
        "Việt Nam",
    ),
    QuerySpec(
        "policy-experience-parking-vn",
        '("bãi đỗ xe thông minh" OR "smart parking") ("người dân" OR "người lái xe") (chỉ dẫn OR thanh toán OR dữ liệu OR an toàn OR tiếp cận) (quy định OR tiêu chuẩn OR quy hoạch OR phản ánh OR xử lý)',
        "Việt Nam",
    ),
    QuerySpec(
        "policy-experience-venues-vn",
        '("khu vui chơi" OR "công viên chủ đề" OR "sân vận động" OR nhà thi đấu) ("khách tham quan" OR khán giả OR người hâm mộ) (vé OR vào cổng OR xếp hàng OR tiếp cận OR an toàn) (quy định OR tiêu chuẩn OR hướng dẫn OR phản ánh OR xử lý)',
        "Việt Nam",
    ),
    QuerySpec(
        "policy-experience-places",
        '("digital signage" OR "LED display" OR "smart parking" OR "theme park") (street OR roadside OR pedestrian OR visitor OR driver OR resident OR "public space") (glare OR "visual impact" OR "visual overload" OR distraction OR accessibility OR safety OR parking) (policy OR regulation OR standard OR guideline OR complaint OR enforcement OR "brightness limit")',
        "Global",
    ),
    QuerySpec(
        "policy-experience-places-vn",
        '("màn hình LED" OR "biển quảng cáo điện tử" OR "màn hình công cộng" OR "biển chỉ dẫn số") ("người đi đường" OR "người đi bộ" OR "người lái xe" OR "cư dân") ("chói mắt" OR "tấn công thị giác" OR "mất tập trung" OR "an toàn giao thông") (quy định OR tiêu chuẩn OR phản ánh OR khiếu nại OR xử lý OR khắc phục OR "giới hạn độ sáng")',
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
            news_type="POLICY", queries=QUERIES, days=args.days,
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
