# WR3 News-driven Market Intelligence

WR3 là pipeline Market Intelligence dựa trên News. Pipeline thu thập và chuẩn hóa tin tức, tổng hợp thành Signal, phân loại Opportunity / Threat, xác định nhóm giải pháp trung lập, đối chiếu Product Gap, đề xuất Action và kiểm soát chất lượng.

## Trạng thái hiện tại

- Contract: `1.0.0-contract`
- Trạng thái contract: `FROZEN_FOR_IMPLEMENTATION`
- Ba cổng HITL bắt buộc:
  1. News Relevance HITL
  2. Opportunity / Threat HITL
  3. Product Action HITL
- Pipeline không tự động phê duyệt quyết định của con người.
- Pipeline phải dừng khi một cổng HITL bắt buộc chưa có trạng thái `APPROVED`.

## Luồng xử lý

```text
Market News
+ Competitor News
+ Technology News
+ Policy News
        ↓
News Relevance HITL
        ↓
Signal Synthesis
        ↓
Opportunity / Threat
        ↓
Opportunity / Threat HITL
        ↓
Product Mapping
        ↓
Product Gap
        ↓
Action Recommendation
        ↓
Product Action HITL
        ↓
Quality Control
```

## Yêu cầu môi trường

- Windows PowerShell
- Python 3
- Chạy lệnh từ thư mục gốc `C:\WR3`
- Kết nối mạng khi crawl nguồn Google/Bing RSS

Kiểm tra phiên bản Python:

```powershell
cd C:\WR3
python --version
```

## Cách dùng nhanh

### 1. Kiểm tra preflight trước khi crawl

```powershell
python C:\WR3\.agents\skills\crawl-wr3-news\scripts\run_crawl.py --check-only
```

Chỉ bắt đầu crawl khi kết quả preflight có `status: PASS`.

### 2. Crawl News trực tiếp và dừng tại Gate 1

Lệnh khuyến nghị:

```powershell
python C:\WR3\run_live_news.py `
  --days 7 `
  --timezone Asia/Bangkok `
  --providers bing,google
```

Có thể truyền thêm:

```powershell
--run-id 20260817-090000-live
--end-date 2026-08-17
--max-items-per-stage 50
--max-competitors 30
--content-workers 4
--min-usable-content-ratio 0.5
```

`run_live_news.py` chạy đủ bốn nhóm News: Market, Competitor, Technology và Policy. Script tạo một run mới, không ghi đè run hoặc thư mục input đã tồn tại.

Chỉ dùng `--no-content` cho kiểm tra metadata hoặc chẩn đoán có giới hạn:

```powershell
python C:\WR3\run_live_news.py --days 7 --timezone Asia/Bangkok --providers bing,google --no-content
```

### 3. Kiểm tra kết quả và chuẩn bị Gate 1

Sau khi chạy, kiểm tra các thư mục:

```text
C:\WR3\workspace\inputs\news\live\<run-id>\
C:\WR3\workspace\runs\<run-id>\artifacts\
C:\WR3\workspace\runs\<run-id>\reviews\
C:\WR3\workspace\runs\<run-id>\validation\
```

Reviewer xử lý gói News Relevance trong `reviews`. Không sửa quyết định thay reviewer và không tự chuyển trạng thái từ `PENDING` sang `APPROVED`.

### 4. Tiếp tục sau khi Gate 1 được phê duyệt

Khi quyết định Gate 1 đã là `APPROVED`, chạy:

```powershell
python C:\WR3\run_vertical_slice_02.py `
  --run-dir C:\WR3\workspace\runs\<run-id>
```

Lệnh này tiếp tục qua Signal, Opportunity / Threat và tạo gói review cho Gate 2. Chỉ các News có trạng thái `KEEP` được dùng để tổng hợp Signal.

### 5. Chạy Product Mapping và Product Gap sau Gate 2

Sau khi Gate 2 có trạng thái `APPROVED`, chạy Product Mapping:

```powershell
python C:\WR3\run_skill_09_product_mapping.py --run-dir C:\WR3\workspace\runs\<run-id>
```

Sau khi Product Mapping hoàn tất và được kiểm tra theo gói review của stage, chạy Product Gap:

```powershell
python C:\WR3\run_skill_10_product_gap.py --run-dir C:\WR3\workspace\runs\<run-id>
```

Trước khi chuyển sang Action Recommendation, Product Gap phải có review status `REVIEWED_ACCEPTED` cùng thông tin reviewer và thời điểm review.

Product Mapping phải trung lập, không đọc `products.json`. Chỉ Product Gap được phép đọc và đối chiếu:

```text
C:\WR3\.agents\skills\10-product-gap\references\products.json
```

### 6. Chạy Action Recommendation và xử lý Gate 3

Khi Gate 2 đã `APPROVED`, Product Mapping đã `COMPLETED` và Product Gap đã `REVIEWED_ACCEPTED`, chạy:

```powershell
python C:\WR3\run_vertical_slice_04.py `
  --run-dir C:\WR3\workspace\runs\<run-id>
```

Driver tạo Action Recommendation và dừng ở trạng thái `PENDING` tại Product Action HITL Gate 3.

`run_vertical_slice_04.py` tạo gói Product Action HITL. Reviewer quyết định trạng thái từng Action. Chỉ Action có trạng thái `APPROVE` là hành động cuối cùng; `DEFER` chỉ là backlog.

Sau khi Gate 3 đã được xử lý, chạy Quality Control:

```powershell
python C:\WR3\run_skill_13_quality_control.py `
  --run-dir C:\WR3\workspace\runs\<run-id>
```

Quality Control chỉ kiểm tra và báo cáo; không sửa các stage trước đó hoặc thay đổi quyết định của con người.

## Chạy với dữ liệu có sẵn hoặc dữ liệu kiểm thử

Để chạy các stage News 01–04 từ một bộ raw input:

```powershell
python C:\WR3\run_vertical_slice_01.py `
  --input C:\WR3\workspace\inputs\news\synthetic_raw_news.json `
  --run-id <run-id>
```

Không dùng dữ liệu synthetic để kết luận về thị trường thực tế. Hãy ghi rõ run là synthetic trong báo cáo và kiểm tra metadata của run trước khi sử dụng đầu ra.

## Nguyên tắc bắt buộc

- Không bỏ qua stage hoặc HITL gate.
- Không tự động phê duyệt News, Opportunity / Threat hoặc Action.
- Chỉ News có trạng thái `KEEP` được đưa vào Signal Synthesis.
- Chỉ Opportunity / Threat có trạng thái `APPROVE` được đưa vào Product Mapping hoặc Action Recommendation.
- Chỉ Action có trạng thái `APPROVE` là hành động cuối cùng.
- `DEFER` là backlog, không phải hành động cần triển khai ngay.
- `competitors.json` chỉ phục vụ Competitor News.
- `products.json` chỉ được đọc tại Product Gap.
- Không sửa các catalog tham chiếu nếu người dùng chưa yêu cầu rõ ràng.
- Bảo toàn ID lineage:

```text
news_id → signal_id → ot_id → product_mapping_id → gap_id → action_id
```

## Cấu trúc thư mục chính

```text
C:\WR3\
├── .agents\skills\       # Skill, schema, template và script của từng stage
├── workspace\inputs\     # Dữ liệu đầu vào
├── workspace\runs\       # Artifact, review và validation theo từng run
├── tests\                 # Bộ kiểm thử
├── run_live_news.py       # Crawl live News, dừng tại Gate 1
├── run_vertical_slice_01.py
├── run_vertical_slice_02.py
├── run_vertical_slice_04.py
├── run_skill_09_product_mapping.py
├── run_skill_10_product_gap.py
└── run_skill_13_quality_control.py
```

## Xem trợ giúp lệnh

Mọi runner chính đều hỗ trợ `--help`:

```powershell
python C:\WR3\run_live_news.py --help
python C:\WR3\run_vertical_slice_01.py --help
python C:\WR3\run_vertical_slice_02.py --help
python C:\WR3\run_vertical_slice_04.py --help
python C:\WR3\run_skill_13_quality_control.py --help
```

## Chạy kiểm thử

```powershell
python -m pytest C:\WR3\tests
```

## Tài liệu liên quan

- [AGENTS.md](AGENTS.md): quy tắc vận hành bắt buộc của WR3
- [PIPELINE_VERSION.md](PIPELINE_VERSION.md): phiên bản contract và các invariant
- [crawl-wr3-news/SKILL.md](.agents/skills/crawl-wr3-news/SKILL.md): quy trình crawl News
- [00-news-driven-mi-orchestrator/SKILL.md](.agents/skills/00-news-driven-mi-orchestrator/SKILL.md): điều phối pipeline
- [News Relevance HITL](.agents/skills/05-news-relevance-hitl/SKILL.md)
- [Opportunity / Threat HITL](.agents/skills/08-opportunity-threat-hitl/SKILL.md)
- [Product Action HITL](.agents/skills/12-product-action-hitl/SKILL.md)
