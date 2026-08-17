"""Tests that Skill 09 remains outside-in and independent of downstream runtime."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from pm_helpers import AUDIT, MAPPING, ROOT, RUN, SKILL


class ProductMappingDependencyTests(unittest.TestCase):
    def test_dependency_audit_passes(self) -> None:
        result = AUDIT.audit(SKILL)
        self.assertEqual(result["audit_status"], "PASS")
        self.assertEqual(result["forbidden_runtime_references"], [])

    def test_dependency_audit_detects_downstream_field_in_runtime(self) -> None:
        skill_dir = ROOT / "tests" / "fixtures" / "product-mapping-forbidden"
        result = AUDIT.audit(skill_dir)
        self.assertEqual(result["audit_status"], "FAIL")
        self.assertIn("proposed_action", {item["marker"] for item in result["forbidden_runtime_references"]})

    def test_runtime_scripts_do_not_open_product_catalog_or_import_skill10(self) -> None:
        guarded = {"validate_artifact.py", "audit_forbidden_dependencies.py"}
        for path in (SKILL / "scripts").glob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            if path.name not in guarded:
                self.assertNotIn("products.json", text)
            self.assertNotIn("10-product-gap", text)
            self.assertNotIn("from product_gap", text)
            self.assertNotIn("import product_gap", text)

    def test_market_categories_are_not_vsf_product_names(self) -> None:
        catalog = json.loads((ROOT / ".agents" / "skills" / "10-product-gap" / "references" / "products.json").read_text(encoding="utf-8"))
        product_names = {item["product_name"].casefold() for item in catalog["products"]}
        categories = {item["market_product_category"].casefold() for item in MAPPING["items"]}
        self.assertTrue(categories.isdisjoint(product_names))

    def test_quality_control_artifact_does_not_exist_before_skill_13(self) -> None:
        forbidden = [
            RUN / "artifacts" / "quality_control_report.json",
        ]
        self.assertTrue(all(not path.exists() for path in forbidden))

    def test_protected_gate_contract_and_catalog_hashes_match_baseline(self) -> None:
        expected = {
            ROOT / "PIPELINE_VERSION.md": "8E4A0A59845507E8483F6EF96A7CC1F16DECC576761D907731C4C5D4AB2A7FEA",
            ROOT / ".agents/skills/00-news-driven-mi-orchestrator/references/PIPELINE_CONTRACT.md": "A954BEE344E126E969E4E4976A533DA84484C8D0C06EC088B9CD29145AC1EFA1",
            ROOT / ".agents/skills/02-competitor-news/references/competitors.json": "9391D4328DB5EB8C7A82ACE46A1C9D912267733AB433433D45D0A747E7868A31",
            ROOT / ".agents/skills/10-product-gap/references/products.json": "0AD8E4B0CAFE5CB6DBC9444FAD3CEABCE0D57B9F2BDF533D8F85C66DEE65F4E0",
            RUN / "reviews/01-news-relevance-decision.json": "22A042889307460660A46D65E381A837B09E4BCB001E8ECC0CD43E6A0D567293",
            RUN / "reviews/02-opportunity-threat-decision.json": "104DE79B3F1CE171FD877093A93B0AEA152B57C7AA6F93BE613B1174D80FC3F8",
        }
        for path, digest in expected.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest().upper(), digest)


if __name__ == "__main__":
    unittest.main()
