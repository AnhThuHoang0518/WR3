"""Offline tests for WR3 live RSS discovery and live News artifact support."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import unittest
import urllib.parse
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARED_PATH = ROOT / "news_crawl_runtime.py"
SPEC = importlib.util.spec_from_file_location("wr3_live_news_crawl", SHARED_PATH)
assert SPEC and SPEC.loader
LIVE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LIVE
SPEC.loader.exec_module(LIVE)
RUN_SPEC = importlib.util.spec_from_file_location("wr3_run_live_news", ROOT / "run_live_news.py")
assert RUN_SPEC and RUN_SPEC.loader
RUN_LIVE = importlib.util.module_from_spec(RUN_SPEC)
sys.modules[RUN_SPEC.name] = RUN_LIVE
RUN_SPEC.loader.exec_module(RUN_LIVE)
COMPETITOR_SPEC = importlib.util.spec_from_file_location(
    "wr3_competitor_crawl",
    ROOT / ".agents" / "skills" / "02-competitor-news" / "scripts" / "crawl_sources.py",
)
assert COMPETITOR_SPEC and COMPETITOR_SPEC.loader
COMPETITOR = importlib.util.module_from_spec(COMPETITOR_SPEC)
sys.modules[COMPETITOR_SPEC.name] = COMPETITOR
COMPETITOR_SPEC.loader.exec_module(COMPETITOR)
CRAWL_SKILL_SPEC = importlib.util.spec_from_file_location(
    "wr3_crawl_skill",
    ROOT / ".agents" / "skills" / "crawl-wr3-news" / "scripts" / "run_crawl.py",
)
assert CRAWL_SKILL_SPEC and CRAWL_SKILL_SPEC.loader
CRAWL_SKILL = importlib.util.module_from_spec(CRAWL_SKILL_SPEC)
sys.modules[CRAWL_SKILL_SPEC.name] = CRAWL_SKILL
CRAWL_SKILL_SPEC.loader.exec_module(CRAWL_SKILL)


RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item><title>Vietnam pilots a smart traffic platform</title>
    <link>https://example.com/news/smart-traffic?utm_source=rss</link>
    <pubDate>Sat, 08 Aug 2026 03:00:00 GMT</pubDate>
    <description>A municipal pilot was announced.</description>
    <source>Example News</source></item>
  <item><title>Old smart city article</title>
    <link>https://example.com/news/old</link>
    <pubDate>Sat, 01 Aug 2026 03:00:00 GMT</pubDate>
    <description>Outside the window.</description></item>
</channel></rss>"""

ARTICLE = """<!doctype html><html><head>
  <title>Vietnam pilots a smart traffic platform</title>
  <meta charset="utf-8">
  <meta property="og:description" content="Thành phố công bố phạm vi thử nghiệm nền tảng giao thông thông minh.">
</head><body><article>
  <p>Vietnam pilots a smart traffic platform. Thành phố công bố thử nghiệm nền tảng giao thông thông minh tại ba quận trong tháng 8 năm 2026, tập trung vào giám sát lưu lượng theo thời gian thực.</p>
  <p>Giai đoạn thử nghiệm kết nối dữ liệu từ camera giao thông và cảm biến hiện trường vào một giao diện điều hành chung cho đơn vị vận hành.</p>
  <p>Cơ quan triển khai cho biết chương trình hiện ở quy mô thí điểm; bài viết chưa công bố ngân sách hoặc kế hoạch mua sắm chính thức.</p>
  <p>Kết quả thử nghiệm sẽ được đánh giá trước khi thành phố xem xét mở rộng phạm vi sang các khu vực khác và bổ sung thêm nguồn dữ liệu vận hành.</p>
  <p>Đơn vị vận hành sẽ theo dõi độ trễ dữ liệu, tỷ lệ phát hiện sự cố và khả năng phối hợp giữa các bộ phận trong suốt thời gian thử nghiệm.</p>
</article></body></html>""".encode("utf-8")

UNRELATED_PAGE = """<!doctype html><html><head>
  <title>Example publisher</title><meta charset="utf-8">
</head><body><article>
  <p>Quân đội công bố một chương trình huấn luyện mới với nhiều phương tiện và đơn vị tham gia trong tháng này.</p>
  <p>Các hoạt động quốc phòng được tổ chức tại nhiều khu vực và không liên quan đến giao thông đô thị.</p>
  <p>Thông tin chi tiết về lịch huấn luyện sẽ được cơ quan chức năng cập nhật trong thông báo tiếp theo.</p>
</article></body></html>""".encode("utf-8")

BING_FALLBACK_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
  <title>Vietnam pilots a smart traffic platform</title>
  <link>https://www.bing.com/news/apiclick?id=matched</link>
  <pubDate>Sat, 08 Aug 2026 03:00:00 GMT</pubDate>
  <description>Matching Bing result.</description>
</item></channel></rss>"""

BLOCKED_SOURCE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <item><title>Blocked smart city claim</title>
    <link>https://www.tgbus.com/news/blocked</link>
    <pubDate>Sat, 08 Aug 2026 03:00:00 GMT</pubDate>
    <description>Untrusted claim.</description><source>电玩巴士</source></item>
  <item><title>Vietnam pilots a smart traffic platform</title>
    <link>https://example.com/news/smart-traffic</link>
    <pubDate>Sat, 08 Aug 2026 03:00:00 GMT</pubDate>
    <description>A municipal pilot was announced.</description><source>Example News</source></item>
</channel></rss>""".encode("utf-8")

WEB_SEARCH_HTML = """<!doctype html><html><body><ol>
  <li class="b_algo"><h2><a href="https://example.com/news/smart-traffic">Vietnam pilots a smart traffic platform</a></h2>
    <p>A city service deployment affecting resident journeys.</p></li>
</ol></body></html>""".encode("utf-8")

BING_REDIRECT_SEARCH_HTML = """<!doctype html><html><body><ol>
  <li class="b_algo"><h2><a href="https://www.bing.com/ck/a?u=a1aHR0cHM6Ly9leGFtcGxlLmNvbS9uZXdzL3NtYXJ0LXRyYWZmaWM&amp;ntb=1">Vietnam pilots a smart traffic platform</a></h2>
    <p>A city service deployment affecting resident journeys.</p></li>
</ol></body></html>""".encode("utf-8")

WEB_ARTICLE = """<!doctype html><html><head>
  <meta property="article:published_time" content="2026-08-08T03:00:00Z">
  <meta property="og:title" content="Vietnam pilots a smart traffic platform">
  <meta property="og:site_name" content="Example News">
  <meta property="og:description" content="A city service deployment affecting resident journeys.">
</head><body><article><p>Vietnam pilots a smart traffic platform for residents.</p></article></body></html>""".encode("utf-8")


class LiveNewsCrawlTests(unittest.TestCase):
    def test_web_experience_filter_rejects_search_noise(self) -> None:
        self.assertFalse(LIVE._web_experience_candidate_relevant(
            "market-experience-citizen-vn",
            "Tỷ giá USD hôm nay tại các ngân hàng",
        ))
        self.assertTrue(LIVE._web_experience_candidate_relevant(
            "market-experience-parking-vn",
            "Người lái xe phản hồi về thanh toán tại bãi đỗ xe thông minh",
        ))

    def test_web_search_unwraps_bing_result_redirect(self) -> None:
        self.assertEqual(
            LIVE.parse_web_search(BING_REDIRECT_SEARCH_HTML)[0]["link"],
            "https://example.com/news/smart-traffic",
        )

    def test_blocked_disinformation_source_is_excluded_and_audited(self) -> None:
        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("market-test", "smart city", "Global")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: BLOCKED_SOURCE_RSS,
        )
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(payload["records"][0]["source_name"], "Example News")
        self.assertEqual(payload["crawl_audit"]["blocked_source_count"], 1)
        self.assertEqual(payload["crawl_audit"]["blocked_source_names"], ["电玩巴士"])
        self.assertEqual(payload["crawl_audit"]["blocked_source_hosts"], ["tgbus.com"])

    def test_crawl_skill_requires_smart_city_baseline_and_experience_overlay(self) -> None:
        report = CRAWL_SKILL.preflight()
        self.assertEqual(report["status"], "PASS", report["errors"])
        self.assertTrue(all(
            not item["missing_query_ids"]
            for item in report["smart_city_baseline_query_coverage"].values()
        ))
        self.assertTrue(all(
            not item["missing_query_ids"]
            for item in report["product_experience_query_coverage"].values()
        ))
        self.assertTrue(all(report["journey_evidence_term_coverage"].values()))
        self.assertTrue(all(report["vietnam_place_experience_term_coverage"].values()))
        self.assertTrue(all(report["citizen_experience_term_coverage"].values()))
        self.assertTrue(all(report["web_search_provider"].values()))
        self.assertTrue(all(report["blocked_source_enforcement"].values()))
        self.assertEqual(report["forbidden_catalog_references"], [])

    def test_competitor_open_discovery_remains_when_catalog_queries_are_disabled(self) -> None:
        catalog = (
            ROOT / ".agents" / "skills" / "02-competitor-news" /
            "references" / "competitors.json"
        )
        queries = COMPETITOR.load_queries(catalog, max_competitors=0)
        open_queries = {query.query_id: query for query in queries}
        self.assertEqual(
            set(open_queries),
            {
                "competitor-open-vn",
                "competitor-open-cn",
                "competitor-open-sg",
                "competitor-open-experience-venues",
                "competitor-open-experience-digital-twin",
                "competitor-open-experience-safety-ai",
                "competitor-open-experience-places",
                "competitor-open-experience-citizen-vn",
            },
        )
        self.assertEqual(
            {query.geography for query in open_queries.values()},
            {"Việt Nam", "China", "Singapore", "Global"},
        )
        self.assertTrue(all(not query.entities for query in open_queries.values()))

    def test_product_experience_open_queries_cover_venue_twin_and_safety_lanes(self) -> None:
        catalog = (
            ROOT / ".agents" / "skills" / "02-competitor-news" /
            "references" / "competitors.json"
        )
        queries = COMPETITOR.load_queries(catalog, max_competitors=0)
        text_by_id = {query.query_id: query.query.casefold() for query in queries}
        self.assertIn("stadium", text_by_id["competitor-open-experience-venues"])
        self.assertIn("theme park", text_by_id["competitor-open-experience-venues"])
        self.assertIn("digital twin", text_by_id["competitor-open-experience-digital-twin"])
        self.assertIn("incident response", text_by_id["competitor-open-experience-safety-ai"])
        self.assertIn("người dân", text_by_id["competitor-open-experience-citizen-vn"])

    def test_chinese_discovery_is_labeled_for_translation_review(self) -> None:
        chinese_rss = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><item>
  <title>城市发布智慧交通平台试点</title>
  <link>https://example.cn/news/smart-traffic</link>
  <pubDate>Sat, 08 Aug 2026 03:00:00 GMT</pubDate>
  <description>项目采用物联网传感器开展城市交通监测。</description>
  <source>示例新闻</source>
</item></channel></rss>""".encode("utf-8")
        payload = LIVE.crawl_queries(
            news_type="TECHNOLOGY",
            queries=[LIVE.QuerySpec("technology-cn", "智慧城市", "China")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: chinese_rss,
        )
        record = payload["records"][0]
        evidence = record["crawl_evidence"]
        self.assertEqual(record["language"], "zh")
        self.assertTrue(evidence["review_translation_required"])
        self.assertEqual(evidence["translation_status"], "PENDING")
        self.assertEqual(evidence["original_title"], "城市发布智慧交通平台试点")
        gate = LIVE.review_translation_gate(payload["records"])
        self.assertEqual(gate["status"], "FAIL")
        self.assertEqual(
            set(gate["pending_records"][0]["missing_fields"]),
            {"title", "summary", "key_facts", "relevance_rationale"},
        )

    def test_completed_vietnamese_translation_passes_review_gate(self) -> None:
        record = {
            "raw_news_id": "RAW-LIVE-TECHNOLOGY-TRANSLATED",
            "language": "zh",
            "title": "Thành phố công bố thí điểm nền tảng giao thông thông minh",
            "summary": "Thành phố công bố một chương trình thí điểm.",
            "key_facts": ["Chương trình đang ở giai đoạn thí điểm."],
            "relevance_rationale": "Ứng viên cần được Gate 1 đánh giá.",
            "crawl_evidence": {
                "original_title": "城市发布智慧交通平台试点",
                "original_language": "zh",
                "review_translation_required": True,
                "translation_status": "COMPLETE",
                "translated_fields": [
                    "title", "summary", "key_facts", "relevance_rationale",
                ],
            },
        }
        gate = LIVE.review_translation_gate([record])
        self.assertEqual(gate["status"], "PASS")
        self.assertEqual(gate["translated_records"], 1)

    def test_provider_urls_use_query_geography_locale(self) -> None:
        china = urllib.parse.parse_qs(urllib.parse.urlsplit(
            LIVE.provider_url("google", "智慧城市", 7, "China")
        ).query)
        singapore = urllib.parse.parse_qs(urllib.parse.urlsplit(
            LIVE.provider_url("bing", "Smart Nation", 7, "Singapore")
        ).query)
        global_query = urllib.parse.parse_qs(urllib.parse.urlsplit(
            LIVE.provider_url("google", "smart city", 7, "Global")
        ).query)
        web_query = urllib.parse.parse_qs(urllib.parse.urlsplit(
            LIVE.provider_url("web", "trải nghiệm người dân", 7, "Việt Nam")
        ).query)
        self.assertEqual(china["gl"], ["CN"])
        self.assertEqual(china["ceid"], ["CN:zh-Hans"])
        self.assertEqual(singapore["mkt"], ["en-SG"])
        self.assertEqual(global_query["hl"], ["en-US"])
        self.assertEqual(web_query["setlang"], ["vi-VN"])
        self.assertEqual(web_query["cc"], ["VN"])

    def test_web_search_runs_alongside_successful_rss_and_fetches_source_date(self) -> None:
        def discovery_fetcher(url, _timeout):
            return WEB_SEARCH_HTML if "/search?" in url else RSS

        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec(
                "market-experience-citizen-vn", "trải nghiệm người dân", "Việt Nam",
            )],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google", "web"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=discovery_fetcher,
            content_fetcher=lambda url, _timeout: LIVE.PageFetch(WEB_ARTICLE, url),
        )
        attempts = payload["crawl_audit"]["attempts"]
        self.assertEqual([attempt["provider"] for attempt in attempts], ["google", "web"])
        self.assertEqual(payload["crawl_audit"]["web_search_attempts"], 1)
        self.assertEqual(payload["crawl_audit"]["web_search_successful_attempts"], 1)
        self.assertEqual(payload["crawl_audit"]["web_search_fetched_pages"], 1)
        self.assertEqual(payload["crawl_audit"]["web_search_undated_items"], 0)
        self.assertEqual(len(payload["records"]), 1)

    def test_web_search_rejects_undated_pages(self) -> None:
        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec(
                "market-experience-citizen-vn", "trải nghiệm người dân", "Việt Nam",
            )],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["web"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: WEB_SEARCH_HTML,
            content_fetcher=lambda url, _timeout: LIVE.PageFetch(ARTICLE, url),
        )
        self.assertEqual(payload["records"], [])
        self.assertEqual(payload["crawl_audit"]["web_search_undated_items"], 1)

    def test_record_cap_does_not_skip_later_geographies(self) -> None:
        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[
                LIVE.QuerySpec("market-vn", "smart city", "Việt Nam"),
                LIVE.QuerySpec("market-cn", "smart city", "China"),
                LIVE.QuerySpec("market-sg", "smart city", "Singapore"),
            ],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=1,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: RSS,
        )
        self.assertEqual(len(payload["records"]), 1)
        self.assertEqual(
            [attempt["query_id"] for attempt in payload["crawl_audit"]["attempts"]],
            ["market-vn", "market-cn", "market-sg"],
        )

    def test_content_quality_gate_requires_configured_usable_ratio(self) -> None:
        counts = {"FULL_TEXT": 2, "PARTIAL_TEXT": 0, "METADATA_ONLY": 18, "UNAVAILABLE": 0}
        failed = RUN_LIVE._content_quality_gate(counts, fetch_content=True, minimum_ratio=0.5)
        bypassed = RUN_LIVE._content_quality_gate(counts, fetch_content=False, minimum_ratio=0.5)
        self.assertEqual(failed["status"], "FAIL")
        self.assertEqual(failed["usable_content_ratio"], 0.1)
        self.assertEqual(bypassed["status"], "PASS")

    def test_window_is_seven_calendar_days_in_bangkok(self) -> None:
        start, end = LIVE.window_bounds(
            days=7, timezone_name="Asia/Bangkok", end_date=date(2026, 8, 9)
        )
        self.assertEqual(start.isoformat(), "2026-08-02T17:00:00+00:00")
        self.assertEqual(end.isoformat(), "2026-08-09T17:00:00+00:00")

    def test_crawl_filters_window_deduplicates_and_keeps_gate_boundary(self) -> None:
        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[
                LIVE.QuerySpec("q1", "smart city", "Việt Nam"),
                LIVE.QuerySpec("q2", "đô thị thông minh", "Việt Nam"),
            ],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: RSS,
        )
        self.assertFalse(payload["synthetic"])
        self.assertEqual(len(payload["records"]), 1)
        record = payload["records"][0]
        self.assertEqual(record["expected_candidate_type"], "MARKET")
        self.assertEqual(record["content_status"], "METADATA_ONLY")
        self.assertIn("reviewer", record["summary"])
        self.assertFalse(payload["phase_boundary"]["signal_extraction_performed"])
        self.assertFalse(payload["phase_boundary"]["ot_evaluation_performed"])

    def test_market_builder_accepts_live_input(self) -> None:
        output_dir = ROOT / "workspace" / "test-tmp" / "live-news"
        output_dir.mkdir(parents=True, exist_ok=True)
        raw_path = output_dir / "raw.json"
        artifact_path = output_dir / "market_news.json"
        record = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("q1", "smart city", "Việt Nam")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: RSS,
        )["records"][0]
        raw_path.write_text(
            json.dumps({"synthetic": False, "records": [record]}, ensure_ascii=False),
            encoding="utf-8",
        )
        skill = ROOT / ".agents" / "skills" / "01-market-news"
        built = subprocess.run([
            sys.executable, str(skill / "scripts" / "build_artifact.py"),
            "--input", str(raw_path), "--output", str(artifact_path),
            "--run-id", "20260809-101010-live",
        ], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=False)
        self.assertEqual(built.returncode, 0, built.stderr)
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
        self.assertFalse(artifact["synthetic"])
        self.assertEqual(artifact["items"][0]["news_type"], "MARKET")

    def test_content_enrichment_resolves_source_and_uses_article_evidence(self) -> None:
        direct_url = "https://publisher.example/news/smart-traffic"
        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("market-vn-procurement", "smart city", "Việt Nam")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: RSS,
            fetch_content=True,
            content_fetcher=lambda _url, _timeout: LIVE.PageFetch(ARTICLE, direct_url),
        )
        record = payload["records"][0]
        reviewer_text = " ".join([
            record["summary"], *record["key_facts"], record["relevance_rationale"]
        ]).casefold()
        self.assertEqual(record["source_url"], direct_url)
        self.assertEqual(record["content_status"], "FULL_TEXT")
        self.assertEqual(record["evidence_quality"], "MEDIUM")
        self.assertIn("ba quận", record["summary"])
        self.assertNotIn("market-vn-procurement", reviewer_text)
        self.assertEqual(record["crawl_evidence"]["query_id"], "market-vn-procurement")
        self.assertEqual(record["crawl_evidence"]["resolution_status"], "RESOLVED")
        self.assertEqual(payload["crawl_audit"]["resolved_source_count"], 1)

    def test_failed_content_fetch_retains_metadata_without_inventing_content(self) -> None:
        def fail(_url, _timeout):
            raise TimeoutError("source timed out")

        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("q1", "smart city", "Việt Nam")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: RSS,
            fetch_content=True,
            content_fetcher=fail,
        )
        record = payload["records"][0]
        self.assertEqual(record["content_status"], "METADATA_ONLY")
        self.assertEqual(record["crawl_evidence"]["resolution_status"], "FAILED")
        self.assertIn("chưa được xác minh", record["summary"])
        self.assertEqual(payload["crawl_audit"]["content_fetch_failed_count"], 1)

    def test_unrelated_page_chrome_is_not_accepted_as_article_content(self) -> None:
        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("q1", "smart city", "Việt Nam")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=lambda _url, _timeout: RSS,
            fetch_content=True,
            content_fetcher=lambda _url, _timeout: LIVE.PageFetch(
                UNRELATED_PAGE, "https://publisher.example/news/smart-traffic"
            ),
        )
        record = payload["records"][0]
        self.assertEqual(record["content_status"], "METADATA_ONLY")
        self.assertEqual(
            record["crawl_evidence"]["content_rejection_reason"], "TITLE_BODY_MISMATCH"
        )
        self.assertNotIn("Quân đội", record["summary"])

    def test_google_rss_uses_title_matched_bing_resolution_fallback(self) -> None:
        google_url = "https://news.google.com/rss/articles/AU_yqL-token"
        direct_url = "https://publisher.example/news/smart-traffic"
        google_rss = RSS.replace(
            b"https://example.com/news/smart-traffic?utm_source=rss", google_url.encode("ascii")
        )

        def feed_fetcher(url, _timeout):
            return BING_FALLBACK_RSS if "bing.com" in url else google_rss

        def page_fetcher(url, _timeout):
            if "news.google.com" in url:
                return LIVE.PageFetch(b"<html><body>Google News</body></html>", google_url)
            return LIVE.PageFetch(ARTICLE, direct_url)

        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("q1", "smart city", "Việt Nam")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=feed_fetcher,
            fetch_content=True,
            content_fetcher=page_fetcher,
        )
        record = payload["records"][0]
        self.assertEqual(record["source_url"], direct_url)
        self.assertEqual(record["content_status"], "FULL_TEXT")
        self.assertEqual(record["crawl_evidence"]["title_resolution_status"], "MATCHED")
        self.assertEqual(record["crawl_evidence"]["resolution_method"], "bing_title_fallback")

    def test_title_fallback_rejects_different_publisher(self) -> None:
        google_url = "https://news.google.com/rss/articles/AU_yqL-token"
        google_rss = RSS.replace(
            b"https://example.com/news/smart-traffic?utm_source=rss", google_url.encode("ascii")
        ).replace(b"<source>Example News</source>", b"<source>Different News</source>")

        def feed_fetcher(url, _timeout):
            return BING_FALLBACK_RSS if "bing.com" in url else google_rss

        def page_fetcher(url, _timeout):
            if "news.google.com" in url:
                return LIVE.PageFetch(b"<html><body>Google News</body></html>", google_url)
            return LIVE.PageFetch(ARTICLE, "https://publisher.example/news/smart-traffic")

        payload = LIVE.crawl_queries(
            news_type="MARKET",
            queries=[LIVE.QuerySpec("q1", "smart city", "Việt Nam")],
            days=7,
            timezone_name="Asia/Bangkok",
            providers=["google"],
            timeout=1.0,
            max_items=10,
            end_date=date(2026, 8, 9),
            fetcher=feed_fetcher,
            fetch_content=True,
            content_fetcher=page_fetcher,
        )
        record = payload["records"][0]
        self.assertEqual(record["source_url"], google_url)
        self.assertEqual(record["content_status"], "METADATA_ONLY")
        self.assertEqual(
            record["crawl_evidence"]["title_resolution_status"], "PUBLISHER_MISMATCH"
        )

    def test_cross_stage_postprocess_deduplicates_and_preserves_discoveries(self) -> None:
        def record(news_type: str, query_id: str) -> dict:
            title = "City awards contract for smart traffic AI platform"
            return {
                "synthetic": False,
                "raw_news_id": f"RAW-LIVE-{news_type}-SAME",
                "title": title,
                "source_name": "Example News",
                "source_url": "https://example.com/smart-traffic",
                "published_at": "2026-08-08T03:00:00Z",
                "collected_at": "2026-08-08T04:00:00Z",
                "raw_content": "The city awards a deployment contract for a smart traffic AI platform.",
                "expected_candidate_type": news_type,
                "geography": ["Global"],
                "language": "en",
                "summary": title,
                "key_facts": [title],
                "entities": [],
                "relevance_rationale": "Gate 1 review required.",
                "evidence_quality": "LOW",
                "content_status": "METADATA_ONLY",
                "crawl_evidence": {
                    "query_id": query_id,
                    "query": "smart city",
                    "provider": "google",
                    "original_title": title,
                    "original_language": "en",
                    "original_rss_description": "",
                    "review_translation_required": True,
                    "translation_status": "PENDING",
                    "translated_fields": [],
                },
            }

        records, audit = LIVE.deduplicate_and_classify(
            {
                "market": {"records": [record("MARKET", "market-q")]},
                "technology": {"records": [record("TECHNOLOGY", "technology-q")]},
            },
            max_items_per_type=10,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(audit["duplicates_removed"], 1)
        discoveries = records[0]["crawl_evidence"]["discoveries"]
        self.assertEqual({item["candidate_type"] for item in discoveries}, {"MARKET", "TECHNOLOGY"})

    def test_postprocess_reassigns_policy_and_filters_ai_stock_noise(self) -> None:
        def record(title: str, raw_id: str) -> dict:
            return {
                "synthetic": False,
                "raw_news_id": raw_id,
                "title": title,
                "source_name": "Example News",
                "source_url": f"https://example.com/{raw_id}",
                "published_at": "2026-08-08T03:00:00Z",
                "collected_at": "2026-08-08T04:00:00Z",
                "raw_content": title,
                "expected_candidate_type": "TECHNOLOGY",
                "geography": ["Global"],
                "language": "en",
                "summary": title,
                "key_facts": [title],
                "entities": [],
                "relevance_rationale": "Gate 1 review required.",
                "evidence_quality": "LOW",
                "content_status": "METADATA_ONLY",
                "crawl_evidence": {
                    "query_id": "technology-q",
                    "query": "smart city AI",
                    "provider": "google",
                    "original_title": title,
                    "original_language": "en",
                    "original_rss_description": "",
                    "review_translation_required": True,
                    "translation_status": "PENDING",
                    "translated_fields": [],
                },
            }

        records, audit = LIVE.deduplicate_and_classify(
            {"technology": {"records": [
                record("Government issues smart city data governance regulation", "RAW-LIVE-TECHNOLOGY-POLICY"),
                record("AI stocks with strong profit growth", "RAW-LIVE-TECHNOLOGY-STOCKS"),
            ]}},
            max_items_per_type=10,
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["expected_candidate_type"], "POLICY")
        self.assertEqual(audit["scope_filtered_records"], 1)

    def test_known_competitor_query_requires_smart_city_context_and_keeps_entity(self) -> None:
        catalog = (
            ROOT / ".agents" / "skills" / "02-competitor-news" /
            "references" / "competitors.json"
        )
        queries = COMPETITOR.load_queries(catalog, max_competitors=1)
        base = next(query for query in queries if query.query_id.endswith("sc-001"))
        self.assertIn('"smart city"', base.query)
        self.assertIn("hợp đồng", base.query)
        self.assertEqual(len(base.entities), 1)


if __name__ == "__main__":
    unittest.main()
