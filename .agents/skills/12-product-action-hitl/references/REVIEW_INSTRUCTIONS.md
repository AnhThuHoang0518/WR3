# Hướng dẫn review — Product Action HITL

1. Review mọi `action_id`.
2. Item chưa review để `review_decision: null`; sau review chọn đúng một: APPROVE, REVISE, REJECT, DEFER.
3. Kiểm lineage tới signal, O/T, mapping và gap; đánh giá evidence, strategic fit, feasibility, urgency, resources và next step. Không yêu cầu owner hoặc timeline.
4. APPROVE là final action; DEFER chỉ vào backlog và không phải immediate action.
5. Bốn tập ID phải đôi một không chồng lặp; hợp của chúng bằng `reviewed_action_ids`.
6. Chưa review hết: PENDING. Có REVISE: CHANGES_REQUIRED. Hoàn tất không revision: APPROVED.
7. Không coi action AI đề xuất là quyết định cuối trước human approval.
8. Không auto-approve hoặc bypass gate.

Pipeline phải dừng khi trạng thái khác `APPROVED`.
