# Input/Output Contract — Product Gap

## Purpose

So sánh market requirement với portfolio VSF và xác định capability gap. Đây là stage duy nhất được đọc `products.json`.

## Allowed inputs

- `product_mapping.json` đã validate PASS và manual inspection `REVIEWED_ACCEPTED`.
- `references/products.json` ở chế độ chỉ đọc.
- `signals.json`, approved O/T bundle và Gate 2 decision chỉ để validate lineage.

## Output artifact

- `workspace/artifacts/product_gap.json`
- Validate bằng `../schemas/output.schema.json`.

## Semantic invariants

- Giữ nguyên `product_mapping_id`, `signal_id`, `market_product_category` và `required_capabilities`.
- Chỉ claim capability có trong record của `products.json`; không suy diễn từ tên sản phẩm.
- Chỉ record có `allowed_gap_baseline=true` được dùng làm confirmed current VSF baseline nếu chưa có human validation bổ sung.
- `portfolio_evidence_refs` ghi `product_code` và các `catalog_fields` hỗ trợ claim để QC kiểm provenance mà không đọc catalog.
- `FULL_MATCH`: matched product khác null, có current capabilities/evidence, không có missing capability.
- `PARTIAL_MATCH`: matched product khác null, có cả current và missing capabilities, có evidence.
- `NO_MATCH`: `matched_vsf_product = null`, current capabilities rỗng.
- `UNKNOWN`: không tạo capability claim chắc chắn; current capabilities rỗng và `validation_needed` không rỗng.
- Không ghép khác category nếu `comparison_rationale` không giải thích.
- Ghi một trong `EXACT_CATEGORY`, `ADJACENT_CATEGORY`, `NO_CATEGORY_MATCH`, `UNCERTAIN_CATEGORY` trong `comparison_rationale` vì frozen schema không có field riêng.
- Không tạo Action hoặc Build/Buy/Partner trong Product Gap.
- Mỗi capability và gap phải được mô tả dễ hiểu, đầy đủ chức năng và ranh giới hỗ trợ; không dùng nhãn công nghệ chung chung thay cho mô tả tính năng.

## Next stage

`11-action-recommendation`

Status: Contract v1 frozen; Skill 10 runtime logic implemented without schema changes.
