#!/usr/bin/env python3
"""Shared read-only helpers for MI Quality Control runtime scripts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object."""
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Write deterministic UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256(path: Path) -> str:
    """Return uppercase SHA-256 for one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def project_relative(path: Path, project_root: Path) -> str:
    """Return a normalized project-relative path."""
    return path.resolve().relative_to(project_root.resolve()).as_posix()


def resolve_index_path(project_root: Path, value: str) -> Path:
    """Resolve one project-relative index path without permitting escape."""
    resolved = (project_root / value).resolve()
    if not resolved.is_relative_to(project_root.resolve()):
        raise ValueError(f"Indexed path escapes project root: {value}")
    return resolved


def parse_frontmatter(path: Path) -> dict[str, Any]:
    """Parse the simple scalar/list YAML frontmatter used by review artifacts."""
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"Missing YAML frontmatter: {path}")
    result: dict[str, Any] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return result
        if line.startswith((" ", "\t", "-")) or ":" not in line:
            continue
        key, raw = line.split(":", 1)
        value = raw.strip().strip("'\"")
        if value.lower() in {"null", "~", ""}:
            result[key.strip()] = None
        elif value.lower() in {"true", "false"}:
            result[key.strip()] = value.lower() == "true"
        elif value.startswith("[") and value.endswith("]"):
            result[key.strip()] = [item.strip().strip("'\"") for item in value[1:-1].split(",") if item.strip()]
        else:
            result[key.strip()] = value
    raise ValueError(f"Unclosed YAML frontmatter: {path}")


def finding(
    check_name: str, status: str, severity: str, message: str,
    affected_ids: list[str] | None = None, remediation: str | None = None,
) -> dict[str, Any]:
    """Create one schema-ready finding without assigning the final deterministic ID."""
    return {
        "check_name": check_name,
        "status": status,
        "severity": severity,
        "affected_ids": sorted(set(affected_ids or [])),
        "message": message,
        "remediation": remediation,
    }


def result(group: str, findings: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap a check group for deterministic report assembly."""
    return {"group": group, "finding_count": len(findings), "findings": findings}

