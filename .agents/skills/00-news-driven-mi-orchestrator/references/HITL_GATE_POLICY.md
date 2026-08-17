# HITL Gate Policy

## Vai trò con người

Reviewer đọc/chỉnh Markdown, quyết định từng item, ghi danh tính và thời gian, rồi đặt overall status. AI và orchestrator không thay thế reviewer, không tạo approval và không sửa review thay reviewer.

## Phân biệt hai lớp quyết định

Item-level decision phân loại từng ID. `overall_status` điều khiển toàn gate. Một item KEEP/APPROVE không đồng nghĩa gate APPROVED.

## Overall status chung

- `PENDING`: chưa review hết mọi source ID hoặc chưa có quyết định hoàn chỉnh.
- `CHANGES_REQUIRED`: có ít nhất một NEEDS_REVISION/REVISE; quay lại stage trước và review lại.
- `APPROVED`: review hoàn tất, không còn revision, reviewer cho phép pipeline tiếp tục.
- `REJECTED`: reviewer dừng batch hoặc toàn batch không nên sử dụng.

## Decision-set invariants

- Gate 1: reviewed = kept ∪ excluded ∪ revision.
- Gate 2: reviewed = approved ∪ rejected ∪ revision.
- Gate 3: reviewed = approved ∪ rejected ∪ revision ∪ deferred.
- Các tập quyết định trong cùng gate phải đôi một không chồng lặp.
- Mọi ID phải tồn tại trong source artifact cùng `run_id`.
- Decision JSON điều khiển pipeline; Markdown là review artifact chính. Hai artifact không nhất quán thì dừng.

## Revision routing

- Gate 1 quay lại đúng News skill.
- Gate 2 quay lại Opportunity / Threat.
- Gate 3 quay lại Action Recommendation.
- Downstream artifact bị ảnh hưởng phải tạo lại và ID mới phải review lại.

## Cấm

Cấm auto-approval, bypass HITL, tiếp tục khi status khác APPROVED, hoặc dùng item approval thay overall approval.

Status: Contract v1 frozen.
