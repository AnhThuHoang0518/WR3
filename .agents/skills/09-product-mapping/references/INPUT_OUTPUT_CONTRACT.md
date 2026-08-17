# Input/Output Contract — Product Mapping

## Purpose

Trả lời: “Signal và O/T này cho thấy thị trường cần loại sản phẩm, giải pháp, module, platform, service hoặc technology nào?”

## Allowed inputs

- `workspace/artifacts/signals.json`
- `workspace/artifacts/opportunity_threat.json`, chỉ các ID trong `approved_ot_ids`
- `workspace/reviews/02-opportunity-threat-decision.json` với `overall_status = APPROVED`

## Forbidden inputs

- Existing VSF portfolio catalogs hoặc option lists.
- O/T REVISE, REJECT hoặc chưa review.
- Bất kỳ field hoặc score nào dùng để đối chiếu trực tiếp với portfolio VSF.

## Output artifact

- `workspace/artifacts/product_mapping.json`
- Validate bằng `../schemas/output.schema.json`.

## Semantic invariants

- Mỗi mapping giữ `signal_id` và một hoặc nhiều `related_ot_ids` đã APPROVE.
- Output là outside-in market requirement, không bị giới hạn bởi portfolio VSF.
- `external_market_examples` là optional. Chỉ ghi khi có nguồn; không được bịa và không coi ví dụ thị trường là sản phẩm VSF.
- Example contract phải ghi `synthetic: true`.
- Nội dung Mapping không bị giới hạn độ dài hay số lượng capability; tiêu chí chính là dễ hiểu, đầy đủ và mỗi capability mô tả được sản phẩm thực sự làm gì.

## Next stage

`10-product-gap`

Status: Contract v1 frozen; detailed logic pending.
