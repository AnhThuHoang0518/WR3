# Hướng dẫn review — Opportunity / Threat HITL

1. Review mọi `ot_id`.
2. Item chưa review để `review_decision: null`; sau review chọn đúng một: `APPROVE`, `REVISE`, `REJECT`.
3. Kiểm alignment với signal, type, statement, stakeholder, impact mechanism, importance, evidence sufficiency và overlap.
4. Có thể đề xuất sửa type/statement.
5. Nếu cần merge/split, chọn REVISE, ghi `structure_change`, `superseded_ot_ids`, `replacement_ot_ids`; không đổi âm thầm ID cũ.
6. Ba tập approved/rejected/revision phải đôi một không chồng lặp; hợp của chúng bằng `reviewed_ot_ids`.
7. Chưa review hết: PENDING. Có REVISE: CHANGES_REQUIRED. Hoàn tất không revision: APPROVED.
8. Item APPROVE không thay thế overall status APPROVED.
9. Không auto-approve hoặc bypass gate.

Pipeline phải dừng khi trạng thái khác `APPROVED`.
