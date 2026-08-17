#!/usr/bin/env python3
"""Validate auditable parity between source and fine-tuned WR3 Markdown."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import sys


RECORD_ID_RE = re.compile(
    r"(?:NEWS-[A-Z]+-\d+|SIGNAL-\d+|OT-\d+|PM-\d+|GAP-\d+|ACTION-\d+)"
)
URL_RE = re.compile(r"https?://[^)\s]+")
INLINE_CODE_RE = re.compile(r"`[^`]+`")
LINK_TARGET_RE = re.compile(r"\]\(([^)]+)\)")
HEADING_RE = re.compile(r"^(#+) ", re.MULTILINE)
LIST_ITEM_RE = re.compile(r"^(\s*)- ", re.MULTILINE)
SIGNAL_LINK_RE = re.compile(r"Liên hệ\s+`(SIGNAL-\d+)`")
NEWS_TITLE_RE = re.compile(r"^- \*\*(NEWS-[A-Z]+-\d+.*?)\*\*$", re.MULTILINE)
SOURCE_LINE_RE = re.compile(r"^\s*Nguồn:\s+.*$", re.MULTILINE)
METADATA_LINE_RE = re.compile(r"^- (?:Run ID|Thời gian|Crawl[^:]*):.*$", re.MULTILINE)
STATUS_RE = re.compile(
    r"(?<![A-Z_])(?:KEEP|APPROVE|REVISE|REJECT|DEFER|PENDING|VALIDATE|"
    r"PREPARE|MONITOR|ACT|HIGH|MEDIUM|LOW|CRITICAL|NO_MATCH|PARTIAL_MATCH|"
    r"OPPORTUNITY|THREAT)(?![A-Z_])"
)

NUMBER_WORD_RE = re.compile(
    r"\b(?:hai|ba|bốn|năm|sáu|bảy|tám|chín|mười)\s+"
    r"(?:sân(?:\s+vận\s+động)?|khu|địa\s+điểm|điểm|sơ\s+đồ|"
    r"service\s+blueprint|quy\s+trình|luồng|kết\s+nối|camera|lượt|"
    r"ngày|tuần|tháng|giây|chỉ\s+số|hệ\s+thống|nguồn|bộ\s+phận|"
    r"giai\s+đoạn|kiến\s+trúc|thử\s+nghiệm|chỗ)\b",
    re.IGNORECASE,
)
ACTION_ONE_RE = re.compile(
    r"\bmột\s+(?:sân(?:\s+vận\s+động)?|khu|địa\s+điểm|điểm|sơ\s+đồ|"
    r"service\s+blueprint|quy\s+trình|luồng|kết\s+nối|chỉ\s+số|"
    r"hệ\s+thống|nguồn|bộ\s+phận|giai\s+đoạn|kiến\s+trúc|"
    r"thử\s+nghiệm|chỗ)\b",
    re.IGNORECASE,
)
DIGIT_NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)?(?:[–-]\d+(?:[.,]\d+)?)?%?")
ACTION_COPY_RE = re.compile(
    r"^\s*-\s+(?:Action|Hành động đề xuất|Bước tiếp theo):", re.IGNORECASE
)


def sequence(pattern: re.Pattern[str], text: str, group: int = 0) -> list[str]:
    return [match.group(group) for match in pattern.finditer(text)]


def count_tokens(line: str, include_action_one: bool = False) -> list[str]:
    clean = URL_RE.sub("", line)
    clean = RECORD_ID_RE.sub("", clean)
    tokens = [match.group(0).lower() for match in NUMBER_WORD_RE.finditer(clean)]
    if include_action_one:
        tokens.extend(match.group(0).lower() for match in ACTION_ONE_RE.finditer(clean))
    tokens.extend(match.group(0) for match in DIGIT_NUMBER_RE.finditer(clean))
    return tokens


def compare_sequence(
    name: str,
    source_values: list[object],
    tuned_values: list[object],
    errors: list[dict[str, object]],
    checks: dict[str, object],
) -> None:
    passed = source_values == tuned_values
    checks[name] = {
        "passed": passed,
        "source_count": len(source_values),
        "fine_tuned_count": len(tuned_values),
    }
    if not passed:
        errors.append(
            {
                "check": name,
                "message": f"{name} changed or was reordered",
                "source": source_values,
                "fine_tuned": tuned_values,
            }
        )


def validate(source: str, tuned: str, allow_action_number_removal: bool) -> dict[str, object]:
    errors: list[dict[str, object]] = []
    warnings: list[dict[str, object]] = []
    checks: dict[str, object] = {}

    compare_sequence(
        "heading_structure",
        [len(value) for value in sequence(HEADING_RE, source, 1)],
        [len(value) for value in sequence(HEADING_RE, tuned, 1)],
        errors,
        checks,
    )
    compare_sequence(
        "list_structure",
        [len(value) for value in sequence(LIST_ITEM_RE, source, 1)],
        [len(value) for value in sequence(LIST_ITEM_RE, tuned, 1)],
        errors,
        checks,
    )
    compare_sequence(
        "record_ids",
        sequence(RECORD_ID_RE, source),
        sequence(RECORD_ID_RE, tuned),
        errors,
        checks,
    )
    compare_sequence(
        "url_targets",
        sequence(URL_RE, source),
        sequence(URL_RE, tuned),
        errors,
        checks,
    )
    compare_sequence(
        "markdown_link_targets",
        sequence(LINK_TARGET_RE, source, 1),
        sequence(LINK_TARGET_RE, tuned, 1),
        errors,
        checks,
    )
    compare_sequence(
        "inline_code",
        sequence(INLINE_CODE_RE, source),
        sequence(INLINE_CODE_RE, tuned),
        errors,
        checks,
    )
    compare_sequence(
        "decision_statuses",
        sequence(STATUS_RE, source),
        sequence(STATUS_RE, tuned),
        errors,
        checks,
    )
    compare_sequence(
        "signal_linkage",
        sequence(SIGNAL_LINK_RE, source, 1),
        sequence(SIGNAL_LINK_RE, tuned, 1),
        errors,
        checks,
    )
    compare_sequence(
        "news_titles",
        sequence(NEWS_TITLE_RE, source, 1),
        sequence(NEWS_TITLE_RE, tuned, 1),
        errors,
        checks,
    )
    compare_sequence(
        "source_citations",
        sequence(SOURCE_LINE_RE, source),
        sequence(SOURCE_LINE_RE, tuned),
        errors,
        checks,
    )
    compare_sequence(
        "report_metadata",
        sequence(METADATA_LINE_RE, source),
        sequence(METADATA_LINE_RE, tuned),
        errors,
        checks,
    )

    source_lines = source.splitlines()
    tuned_lines = tuned.splitlines()
    checks["line_count"] = {
        "passed": len(source_lines) == len(tuned_lines),
        "source_count": len(source_lines),
        "fine_tuned_count": len(tuned_lines),
    }
    if len(source_lines) != len(tuned_lines):
        errors.append(
            {
                "check": "line_count",
                "message": "Line count changed; preserve one source block per fine-tuned block before validating numbers",
            }
        )
    else:
        for line_number, (source_line, tuned_line) in enumerate(
            zip(source_lines, tuned_lines), start=1
        ):
            is_action_copy = ACTION_COPY_RE.match(source_line) is not None
            source_numbers = count_tokens(source_line, include_action_one=is_action_copy)
            tuned_numbers = count_tokens(tuned_line, include_action_one=is_action_copy)
            if source_numbers == tuned_numbers:
                continue

            source_counter = Counter(source_numbers)
            tuned_counter = Counter(tuned_numbers)
            added = list((tuned_counter - source_counter).elements())
            removed = list((source_counter - tuned_counter).elements())
            permitted_removal = (
                allow_action_number_removal
                and is_action_copy
                and not added
                and bool(removed)
            )
            finding = {
                "check": "numeric_parity",
                "line": line_number,
                "added": added,
                "removed": removed,
                "source": source_line,
                "fine_tuned": tuned_line,
            }
            if permitted_removal:
                finding["message"] = "Review intentional removal of an incidental Action quantity"
                warnings.append(finding)
            else:
                finding["message"] = "A number or scoped count changed outside the permitted Action rule"
                errors.append(finding)

    checks["numeric_parity"] = {
        "passed": not any(item["check"] == "numeric_parity" for item in errors),
        "warning_count": sum(item["check"] == "numeric_parity" for item in warnings),
    }

    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate source-to-fine-tuned Markdown parity for the writing-style skill."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("fine_tuned", type=Path)
    parser.add_argument(
        "--allow-action-incidental-number-removal",
        action="store_true",
        help="Allow removals of scoped counts only on Action, proposed-action, or next-step lines.",
    )
    args = parser.parse_args()

    try:
        source = args.source.read_text(encoding="utf-8")
        tuned = args.fine_tuned.read_text(encoding="utf-8")
    except OSError as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    result = validate(source, tuned, args.allow_action_incidental_number_removal)
    result["source"] = str(args.source.resolve())
    result["fine_tuned"] = str(args.fine_tuned.resolve())
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
