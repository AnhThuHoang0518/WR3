#!/usr/bin/env python3
"""Build final source-file integrity evidence against the pre-QC baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from qc_common import load_json, resolve_index_path, sha256, utc_now, write_json


def build_integrity(index: dict[str, Any], project_root: Path) -> dict[str, Any]:
    """Compare current files with baseline while allowing the runtime manifest update."""
    files: list[dict[str, Any]] = []
    failures: list[str] = []
    for source in index.get("file_index", []):
        path = resolve_index_path(project_root, source["path"])
        exists = path.is_file()
        current = sha256(path) if exists else None
        role = source.get("role")
        mutable = role in {"runtime_manifest", "runtime_validation"}
        unchanged = exists and current == source.get("sha256")
        parse_status: str | None = None
        if exists and path.suffix.lower() == ".json":
            try:
                json.loads(path.read_text(encoding="utf-8"))
                parse_status = "PASS"
            except (OSError, json.JSONDecodeError):
                parse_status = "FAIL"
        if not exists or parse_status == "FAIL" or (not unchanged and not mutable):
            failures.append(source["logical_name"])
        files.append({
            "logical_name": source["logical_name"], "path": source["path"],
            "sha256": current, "baseline_sha256": source.get("sha256"),
            "file_size": path.stat().st_size if exists else None, "role": role,
            "mutable_after_qc": mutable, "exists": exists, "parse_status": parse_status,
            "unchanged_from_baseline": unchanged,
        })
    return {
        "run_id": index.get("run_id"), "generated_at": utc_now(),
        "contract_version": index.get("contract_version"), "file_count": len(files),
        "files": files, "integrity_status": "PASS" if not failures else "ERROR",
        "failed_logical_names": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    try:
        if args.output.exists() and not args.overwrite:
            raise ValueError(f"Refusing to overwrite integrity manifest: {args.output}")
        project_root = (args.project_root or Path(__file__).resolve().parents[4]).resolve()
        integrity = build_integrity(load_json(args.index), project_root)
        write_json(args.output, integrity)
        print(json.dumps({"status": "PASS", "integrity_status": integrity["integrity_status"], "file_count": integrity["file_count"], "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
