# Bước 9 — MI Quality Control

## Mục tiêu

Skill 13 kiểm tra toàn bộ synthetic pipeline sau khi Gate 3 đã được con người phê duyệt. QC chỉ đọc artifact, review, decision manifest, validation report, contract, schema và catalog đã có; QC không chạy lại stage 01–12, không sửa dữ liệu nguồn và không tạo Market Intelligence report.

Run được kiểm tra: `20260809-122107-synthetic`.

## Các nhóm kiểm tra

- File, JSON schema và tính đầy đủ của pipeline.
- Ba HITL gate, tập quyết định rời nhau và canonical approved/deferred bundles.
- Lineage xuyên suốt Raw News → News → Signal → Opportunity/Threat → Product Mapping → Product Gap → Action → Gate 3.
- Dependency boundary: `competitors.json` chỉ phục vụ Competitor News; Product Mapping không đọc `products.json`; Product Gap là stage phân tích portfolio duy nhất; QC chỉ đọc catalog để xác minh.
- Product Mapping outside-in, manual inspection và Product Gap portfolio evidence.
- Action schema, lineage, chất lượng, coverage, summary và approved portfolio.
- Hash integrity của contract, catalog, review, decision, bundle, artifact và source code.

## Ý nghĩa kết quả

- `ERROR`: sai contract, thiếu bằng chứng, sai lineage, HITL chưa hợp lệ hoặc nguồn bị thay đổi. Một ERROR làm `pipeline_eligible_for_release = false`.
- `WARNING`: dữ liệu hợp lệ nhưng cần con người đánh giá thêm trước khi dùng thực tế. WARNING không tự động làm release fail.
- `PASS`: check đáp ứng điều kiện đã định nghĩa.

`pipeline_status = COMPLETED` chỉ có nghĩa runtime QC đã chạy xong. Release eligibility là kết luận độc lập trong QC report; một run có thể hoàn thành execution nhưng vẫn không đủ điều kiện release nếu còn ERROR.

## Cách chạy

```powershell
python run_skill_13_quality_control.py --run-dir workspace/runs/20260809-122107-synthetic
```

Driver thu thập baseline hash trước khi tạo output QC, chạy từng nhóm check, build và validate report, kiểm tra lại hash, cập nhật runtime manifest, ghi summary và dừng tại Skill 13.

## Output

- Input index: `workspace/runs/20260809-122107-synthetic/intermediate/qc_input_index.json`
- QC report: `workspace/runs/20260809-122107-synthetic/validation/quality_control_report.json`
- Integrity manifest: `workspace/runs/20260809-122107-synthetic/validation/final-artifact-integrity.json`
- Summary: `workspace/runs/20260809-122107-synthetic/reports/quality-control-summary.md`
- Check reports tạm: `workspace/runs/20260809-122107-synthetic/validation/qc_checks/`
- Log: `workspace/logs/20260809-122107-synthetic.log`

Mỗi `ERROR` hoặc `WARNING` có trường `remediation`. Remediation chỉ mô tả stage sở hữu cần xử lý và review nào phải lặp lại; Skill 13 không tự sửa artifact, không auto-approve và không thay thế quyết định của reviewer.

## Giới hạn

Đây là synthetic run dùng để kiểm chứng runtime contract. Chưa chạy Market Intelligence thật, chưa gọi internet và driver không tự bắt đầu real-data pipeline sau QC.
