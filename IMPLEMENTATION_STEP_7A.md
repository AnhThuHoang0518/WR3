# Implementation Step 7A — Skill 09 Product Mapping

## Phạm vi

Bước 7A triển khai runtime đầy đủ cho `09-product-mapping`: chuẩn bị approved O/T bundle và context, nhận semantic draft do Codex viết theo SKILL.md, build/validate Product Mapping, lập coverage/dependency report và tạo file kiểm tra thủ công.

Không triển khai hoặc chạy Product Gap, Action Recommendation, Product Action HITL hay Quality Control. Manual inspection không phải HITL gate mới và không có decision JSON.

## Input

- `artifacts/signals.json`
- `artifacts/approved_opportunity_threat_bundle.json`
- `reviews/02-opportunity-threat-decision.json` với Gate 2 `APPROVED`

Run hiện tại chỉ sử dụng `OT-001`, `OT-004`, `OT-006` và `OT-007`. Các O/T bị REJECT không được đưa vào bundle, context hoặc Product Mapping.

## Product Mapping và Product Gap

Product Mapping nhìn outside-in: thị trường cần loại sản phẩm/giải pháp và capability nào để giải quyết market problem đã được Signal và approved O/T hỗ trợ.

Product Gap là stage sau mới đối chiếu requirement đó với portfolio VSF. Skill 09 không đọc `products.json`, không sử dụng VSF option list, không kết luận portfolio fit/gap và không đề xuất action.

## Semantic draft

Codex đọc `SKILL.md`, `product_mapping_context.json`, Signal và approved O/T rồi viết trực tiếp:

`workspace/runs/20260809-122107-synthetic/intermediate/product_mapping_draft.json`

Draft phải chứa semantic mapping outside-in và rationale cho approved O/T/Signal chưa map. Không dùng keyword mapper, không hard-code kết quả vào Python và không bịa external market example.

## Cách chạy

Từ `C:\WR3`:

```powershell
python run_skill_09_product_mapping.py --run-dir workspace/runs/20260809-122107-synthetic
```

Driver xác nhận Gate 2 APPROVED, validate/canonicalize approved bundle, tạo context, yêu cầu semantic draft tồn tại, build artifact, chạy schema/lineage/dependency/coverage validation, tạo manual review, cập nhật manifest và dừng.

## Build và validate riêng

```powershell
python .agents/skills/09-product-mapping/scripts/build_artifact.py --context workspace/runs/20260809-122107-synthetic/intermediate/product_mapping_context.json --draft workspace/runs/20260809-122107-synthetic/intermediate/product_mapping_draft.json --schema .agents/skills/09-product-mapping/schemas/output.schema.json --output workspace/runs/20260809-122107-synthetic/artifacts/product_mapping.json

python .agents/skills/09-product-mapping/scripts/validate_artifact.py --artifact workspace/runs/20260809-122107-synthetic/artifacts/product_mapping.json --schema .agents/skills/09-product-mapping/schemas/output.schema.json --signals workspace/runs/20260809-122107-synthetic/artifacts/signals.json --approved-ot-bundle workspace/runs/20260809-122107-synthetic/artifacts/approved_opportunity_threat_bundle.json --decision workspace/runs/20260809-122107-synthetic/reviews/02-opportunity-threat-decision.json --report workspace/runs/20260809-122107-synthetic/validation/product-mapping-validation-report.json
```

Validator phân biệt `ERROR` về schema/lineage/boundary với `WARNING` về chất lượng semantic cần người dùng kiểm tra.

## Output

- Final artifact: `workspace/runs/20260809-122107-synthetic/artifacts/product_mapping.json`
- Coverage: `workspace/runs/20260809-122107-synthetic/validation/product-mapping-coverage-report.json`
- Dependency audit: `workspace/runs/20260809-122107-synthetic/validation/product-mapping-dependency-audit.json`
- Validation: `workspace/runs/20260809-122107-synthetic/validation/product-mapping-validation-report.json`
- Manual inspection: `workspace/runs/20260809-122107-synthetic/reviews/product-mapping-review.md`

## Kiểm tra thủ công

Đọc từng mapping trong `product-mapping-review.md` và kiểm tra category có trung lập, market problem/capability có cụ thể, lineage có chỉ dùng approved O/T, có mapping trùng hoặc bị tạo chỉ để đạt coverage, có VSF leakage hay suy diễn quá evidence hay không.

File này giữ `formal_hitl_gate: false` và `status: READY_FOR_REVIEW`; kết quả kiểm tra không điều khiển pipeline Contract V1.

## Điểm dừng

Sau khi Skill 09 hoàn tất, runtime manifest đặt Product Mapping `COMPLETED`, Skill 10–13 `NOT_IN_SCOPE`, `pipeline_can_continue: true` và dừng trước Product Gap. Chưa chạy Product Gap hoặc Action.
