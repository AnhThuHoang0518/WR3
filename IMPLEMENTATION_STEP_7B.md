# Implementation Step 7B — Skill 10 Product Gap

## Phạm vi

Bước này triển khai và chạy riêng `10-product-gap` trên run `20260809-122107-synthetic`. Pipeline nhận Product Mapping đã được Thu review, đọc catalog VSF ở chế độ read-only, tạo Product Gap, validate schema/lineage/evidence, tạo manual inspection và dừng trước Action Recommendation.

Skill 11 Action Recommendation, Skill 12 Product Action HITL và Skill 13 Quality Control chưa được triển khai hoặc chạy trong bước này.

## Input

- `workspace/runs/20260809-122107-synthetic/artifacts/product_mapping.json`
- `.agents/skills/10-product-gap/references/products.json`
- Signals, approved O/T bundle và Gate 2 decision chỉ để kiểm tra lineage.
- `reviews/product-mapping-review.md` phải có `REVIEWED_ACCEPTED`, reviewer và reviewed timestamp.

Product Mapping và catalog được bảo vệ bằng SHA-256; Product Gap không sửa các nguồn này.

## Category matching

Mỗi assessment ghi một token trong `comparison_rationale` vì frozen schema không có field category riêng:

- `EXACT_CATEGORY`: cùng loại sản phẩm/giải pháp.
- `ADJACENT_CATEGORY`: category gần nhưng scope khác; phải nêu ranh giới.
- `NO_CATEGORY_MATCH`: catalog không có category phù hợp.
- `UNCERTAIN_CATEGORY`: catalog chưa đủ để kết luận.

Keyword normalization chỉ tìm candidate; kết luận phải đọc `product_type`, domain, capability, portfolio role, baseline flag và known unknowns.

## Capability comparison

Capability matrix dùng `CONFIRMED_PRESENT`, `CONFIRMED_ABSENT`, `PARTIALLY_SUPPORTED`, `NOT_DOCUMENTED` và `NOT_APPLICABLE`. Final artifact quy về frozen `FULL_MATCH`, `PARTIAL_MATCH`, `NO_MATCH` hoặc `UNKNOWN`.

`NOT_DOCUMENTED` không được tự động chuyển thành `CONFIRMED_ABSENT`. `UNKNOWN` dùng khi có candidate hoặc khả năng liên quan nhưng catalog chưa đủ để kết luận. `NO_MATCH` dùng khi không có product category phù hợp và không tạo current capability claim.

## Portfolio evidence

Mọi current VSF capability phải trùng nội dung catalog và có `portfolio_evidence_refs` dẫn tới đúng `product_code` cùng `catalog_fields`. Chỉ record có `allowed_gap_baseline=true` được dùng làm confirmed current baseline nếu chưa có validation bổ sung. Ecosystem, enabling, legacy và historical records không được tự động kế thừa sang Core VSF.

## Cách chạy

```powershell
python run_skill_10_product_gap.py --run-dir workspace/runs/20260809-122107-synthetic
```

Driver kiểm tra Gate 2, Product Mapping stage/validation/dependency audit/manual review, frozen catalog hash, tạo context/matrix/artifact, chạy validation, cập nhật runtime manifest, xác minh protected hashes và dừng.

## Output

- Context: `workspace/runs/20260809-122107-synthetic/intermediate/product_gap_context.json`
- Capability matrix: `workspace/runs/20260809-122107-synthetic/intermediate/product_gap_capability_matrix.json`
- Semantic draft: `workspace/runs/20260809-122107-synthetic/intermediate/product_gap_draft.json`
- Final artifact: `workspace/runs/20260809-122107-synthetic/artifacts/product_gap.json`
- Validation: `workspace/runs/20260809-122107-synthetic/validation/product-gap-validation-report.json`
- Lineage: `workspace/runs/20260809-122107-synthetic/validation/product-gap-lineage-validation-report.json`
- Portfolio evidence: `workspace/runs/20260809-122107-synthetic/validation/product-gap-portfolio-evidence-report.json`
- Coverage: `workspace/runs/20260809-122107-synthetic/validation/product-gap-coverage-report.json`
- Manual review: `workspace/runs/20260809-122107-synthetic/reviews/product-gap-review.md`

## Manual inspection

`product-gap-review.md` có `status: READY_FOR_REVIEW` và `formal_hitl_gate: false`. Reviewer kiểm tra category, catalog evidence, missing-vs-not-documented, `NO_MATCH`/`UNKNOWN`, mức tự tin của `FULL_MATCH`, bảo toàn Product Mapping và việc không có Action. Script không tự đánh dấu kết quả review.

## Chưa triển khai

Không tạo `actions.json`, không tạo Gate 3 review/decision và không tạo Quality Control output. Bước này xác nhận chưa chạy Action Recommendation.

