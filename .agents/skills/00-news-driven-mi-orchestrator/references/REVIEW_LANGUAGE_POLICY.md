# Chính sách ngôn ngữ cho nội dung review

## Phạm vi bắt buộc

Áp dụng cho mọi nội dung diễn giải do các stage 01–11 tạo ra và mọi nội dung từ các stage này được đưa cho con người review, kiểm tra hoặc ra quyết định.

## Quy tắc

1. Viết bằng tiếng Việt toàn bộ nội dung hướng tới reviewer, gồm `title`, `summary`, `key_facts`, `relevance_rationale`, fact diễn giải, nhận định, giả định, khoảng trống bằng chứng, capability mô tả, validation cần thực hiện, đề xuất và next step.
2. Khi nguồn không phải tiếng Việt, dịch đầy đủ các trường reviewer-facing sang tiếng Việt mà không thêm fact hoặc làm thay đổi mức độ chắc chắn của nguồn.
3. Giữ nguyên ID, tên field/schema, enum, status token, URL, tên riêng, tên pháp lý, tên thương hiệu và thuật ngữ kỹ thuật khó dịch. Phần giải thích bao quanh các giá trị này vẫn phải bằng tiếng Việt.
4. Giữ tiêu đề, ngôn ngữ và trích đoạn gốc trong raw crawl evidence hoặc provenance; không hiển thị chúng thay cho bản dịch trong trường reviewer-facing. URL nguồn vẫn giữ nguyên.
5. Không dùng tiếng Anh, tiếng Trung hoặc ngôn ngữ khác làm nội dung mặc định/fallback cho reviewer. Nếu chưa dịch đủ `title`, `summary`, `key_facts` và `relevance_rationale`, đặt trạng thái dịch là `PENDING` và dừng trước Gate 1.
6. Các trường do reviewer điền như reason, note, rationale và reviewer summary phải được hướng dẫn viết bằng tiếng Việt; token quyết định vẫn giữ nguyên theo schema.

Policy này chỉ quy định ngôn ngữ trình bày. Nó không thay đổi schema, enum, lineage, thứ tự stage, quyền quyết định của con người hoặc điều kiện dừng tại HITL.
