"""Read-only fixtures and module loader for Step 9 Quality Control tests."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "workspace" / "runs" / "20260809-122107-synthetic"
SKILL13 = ROOT / ".agents" / "skills" / "13-mi-quality-control"
SCRIPTS = SKILL13 / "scripts"
sys.path.insert(0, str(SCRIPTS))


def module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


COLLECT = module("step9_collect", SCRIPTS / "collect_inputs.py")
INTEGRITY = module("step9_integrity", SCRIPTS / "build_integrity_manifest.py")
SCHEMA_CHECKS = module("step9_schema_checks", SCRIPTS / "run_schema_checks.py")
HITL = module("step9_hitl", SCRIPTS / "run_hitl_checks.py")
LINEAGE = module("step9_lineage", SCRIPTS / "run_lineage_checks.py")
DEPENDENCIES = module("step9_dependencies", SCRIPTS / "run_dependency_checks.py")
PORTFOLIO = module("step9_portfolio", SCRIPTS / "run_portfolio_evidence_checks.py")
ACTION_CHECKS = module("step9_actions", SCRIPTS / "run_action_checks.py")
BUILD_REPORT = module("step9_build_report", SCRIPTS / "build_quality_control_report.py")
VALIDATE_REPORT = module("step9_validate_report", SCRIPTS / "validate_quality_control_report.py")
SUMMARY = module("step9_summary", SCRIPTS / "generate_quality_control_summary.py")
DRIVER = module("step9_driver", ROOT / "run_skill_13_quality_control.py")

INDEX = COLLECT.collect(ROOT, RUN)
QC_SCHEMA = load(SKILL13 / "schemas" / "output.schema.json")


def pre_qc_manifest():
    manifest = load(RUN / "manifest.json")
    manifest["current_stage"] = "PRODUCT_ACTION_HITL"
    manifest["pipeline_status"] = "COMPLETED"
    manifest["pipeline_can_continue"] = True
    manifest["blocking_gate"] = None
    manifest["blocking_reasons"] = []
    manifest["stage_statuses"]["MI_QUALITY_CONTROL"] = "NOT_IN_SCOPE"
    manifest.get("artifacts", {}).pop("quality_control_report", None)
    manifest.get("artifacts", {}).pop("quality_control_summary", None)
    manifest.get("validation_reports", {}).pop("final_artifact_integrity", None)
    manifest.get("validation_reports", {}).pop("quality_control_validation", None)
    return manifest


def group(status: str, name: str = "Synthetic test finding"):
    return {
        "group": "TEST",
        "finding_count": 1,
        "findings": [{
            "check_name": name,
            "status": status,
            "severity": "INFO" if status == "PASS" else ("LOW" if status == "WARNING" else "CRITICAL"),
            "affected_ids": [],
            "message": f"{status} fixture",
            "remediation": None if status == "PASS" else "Review the fixture.",
        }],
    }


def build_report(groups):
    manifest = pre_qc_manifest()
    integrity = {"integrity_status": "PASS", "file_count": len(INDEX["file_index"]), "failed_logical_names": []}
    return BUILD_REPORT.build_report(
        manifest["run_id"], True, groups, integrity, manifest, manifest["contract_version"]
    )


def hitl_data():
    return copy.deepcopy(HITL.load_inputs(INDEX, ROOT))


def lineage_data():
    return copy.deepcopy(LINEAGE.load_inputs(INDEX, ROOT))

