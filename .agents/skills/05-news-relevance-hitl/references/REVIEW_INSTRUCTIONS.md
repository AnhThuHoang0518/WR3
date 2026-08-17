# Hướng dẫn review — News Relevance HITL

1. Đọc Markdown review; đây là artifact review chính.
2. Review mọi `news_id` trong bốn source artifacts.
3. Item chưa review để `relevance_decision: null`; sau review chọn đúng một: `KEEP`, `EXCLUDE`, `NEEDS_REVISION`.
4. Kiểm tra title, nguồn, URL, thời gian, geography, language, summary, key facts, entities, relevance rationale, evidence quality và content status.
5. Có thể sửa `news_type`; dùng `corrected_news_type: null` nếu không sửa.
6. Có thể đánh dấu trùng; dùng `duplicate_of_news_id: null` nếu không trùng.
7. Ghi lý do loại rõ ràng. Quảng cáo dự án, sản phẩm hoặc bất động sản không bị loại tự động; chỉ EXCLUDE khi không có giá trị intelligence hoặc vi phạm tiêu chí khác.
   Với Competitor News, công ty không có trong `competitors.json` vẫn có thể `KEEP`; đánh giá evidence và intelligence value, không dùng catalog match làm điều kiện bắt buộc.
8. Ba tập quyết định phải đôi một không chồng lặp và hợp của chúng phải bằng `reviewed_news_ids`.
9. Chưa review hết: PENDING. Có NEEDS_REVISION: CHANGES_REQUIRED. Hoàn tất không revision: APPROVED.
10. Không dùng decision manifest thay thế Markdown; không auto-approve hoặc bypass gate.

Pipeline phải dừng khi trạng thái khác `APPROVED`.
