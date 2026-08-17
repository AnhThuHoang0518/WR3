#!/usr/bin/env python3
"""Validate a JSON instance with the JSON Schema subset used by WR3."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def load_json(path: Path) -> Any:
    """Load UTF-8 JSON and raise a readable error when it is invalid."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"File not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _is_type(value: Any, expected: str) -> bool:
    mapping = {
        "object": lambda item: isinstance(item, dict),
        "array": lambda item: isinstance(item, list),
        "string": lambda item: isinstance(item, str),
        "boolean": lambda item: isinstance(item, bool),
        "null": lambda item: item is None,
        "integer": lambda item: isinstance(item, int) and not isinstance(item, bool),
        "number": lambda item: isinstance(item, (int, float)) and not isinstance(item, bool),
    }
    return expected in mapping and mapping[expected](value)


def _valid_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return "T" in value
    except ValueError:
        return False


def _valid_uri(value: str) -> bool:
    parsed = urlparse(value)
    return bool(parsed.scheme and (parsed.netloc or parsed.path))


def validate_instance(instance: Any, schema: dict[str, Any], path: str = "$") -> list[dict[str, str]]:
    """Return deterministic validation errors for the schema features used in WR3."""
    errors: list[dict[str, str]] = []

    expected_type = schema.get("type")
    if expected_type is not None:
        candidates = expected_type if isinstance(expected_type, list) else [expected_type]
        if not any(_is_type(instance, candidate) for candidate in candidates):
            errors.append({"path": path, "message": f"expected type {expected_type!r}"})
            return errors

    if "const" in schema and instance != schema["const"]:
        errors.append({"path": path, "message": f"expected constant {schema['const']!r}"})
    if "enum" in schema and instance not in schema["enum"]:
        errors.append({"path": path, "message": f"value {instance!r} is not in enum"})

    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append({"path": path, "message": "string is shorter than minLength"})
        if "pattern" in schema and re.fullmatch(schema["pattern"], instance) is None:
            errors.append({"path": path, "message": f"does not match pattern {schema['pattern']!r}"})
        if schema.get("format") == "date-time" and not _valid_datetime(instance):
            errors.append({"path": path, "message": "invalid date-time"})
        if schema.get("format") == "uri" and not _valid_uri(instance):
            errors.append({"path": path, "message": "invalid URI"})

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append({"path": path, "message": "number is below minimum"})

    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append({"path": path, "message": "array has fewer than minItems"})
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append({"path": path, "message": "array has more than maxItems"})
        if schema.get("uniqueItems"):
            encoded = [json.dumps(item, sort_keys=True, ensure_ascii=False) for item in instance]
            if len(encoded) != len(set(encoded)):
                errors.append({"path": path, "message": "array items are not unique"})
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(instance):
                errors.extend(validate_instance(item, item_schema, f"{path}[{index}]"))

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for field in required:
            if field not in instance:
                errors.append({"path": f"{path}.{field}", "message": "required field is missing"})
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for field in instance:
                if field not in properties:
                    errors.append({"path": f"{path}.{field}", "message": "additional property is not allowed"})
        for field, child_schema in properties.items():
            if field in instance:
                errors.extend(validate_instance(instance[field], child_schema, f"{path}.{field}"))

    for branch in schema.get("allOf", []):
        errors.extend(validate_instance(instance, branch, path))

    if "if" in schema:
        condition_errors = validate_instance(instance, schema["if"], path)
        chosen = schema.get("then") if not condition_errors else schema.get("else")
        if isinstance(chosen, dict):
            errors.extend(validate_instance(instance, chosen, path))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--instance", required=True, type=Path)
    args = parser.parse_args()
    try:
        schema = load_json(args.schema)
        instance = load_json(args.instance)
        errors = validate_instance(instance, schema)
    except ValueError as exc:
        print(json.dumps({"status": "FAIL", "errors": [{"path": "$", "message": str(exc)}]}, ensure_ascii=False))
        return 2
    result = {"status": "PASS" if not errors else "FAIL", "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
