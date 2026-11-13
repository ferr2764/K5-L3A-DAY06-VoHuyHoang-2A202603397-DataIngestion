# Benchmark — Foundations of Information Systems

| File | Nội dung |
|---|---|
| `questions.json` | 20 câu chính: q01–q15 dev, q16–q20 test; đáp án, gold source/page, evidence và filter |
| `reserve_questions.json` | q21–q22 dự phòng, không tính vào chỉ số chính |
| `evidence_validation.json` | Kết quả kiểm chứng evidence trên PDF, SHA-256 của PDF và báo cáo |
| `export_from_report.py` | Xuất lại JSON từ báo cáo và tái kiểm chứng evidence |

## Nguồn và quy ước

Corpus: `starter/data/Foundations_of_Information_Systems.pdf`, trang PDF vật lý 30–72, đánh số từ 1. `gold_page` dùng số trang PDF; `printed_page` dùng số in trong sách. `gold_source_id` là `foundations-of-information-systems`, khớp [manifest](../data/manifest.json). Câu hỏi và đáp án tiếng Việt, evidence tiếng Anh. Chuẩn hóa để đối chiếu: Unicode NFC và gộp whitespace, giữ nguyên dấu câu và chữ hoa/thường.

## Split và filter

Dev thuộc các mục 1.2, 1.3, 2.1; test thuộc 2.3–2.4. Có bốn câu filter: q03, q09 (dev), q17, q20 (test). Giá trị `section` lấy từ heading sách, được nêu trong câu hỏi trước truy xuất. A/B không dùng filter; C chỉ dùng `filter` khác null. Trường `section` mô tả gold trong bản ghi không tự động trở thành filter. Chỉ truyền `question` và filter đã cung cấp vào truy xuất; không truyền đáp án, evidence hoặc gold source/page.

Trang PDF 36 và 68 chứa chuyển tiếp giữa hai mục; ingestion cần giữ đúng ranh giới section thay vì gán toàn trang theo gold.

## Giữ cố định và chấm

Giữ cùng câu hỏi, split, gold và định nghĩa hit cho A/B/C. Không tinh chỉnh theo test, không đổi câu sau khi xem kết quả. Chỉ thêm câu dự phòng trước lần chạy test đầu tiên và phải ghi nhận phiên bản. Chưa chạy retrieval trong bước xuất dữ liệu này.

Tách theo chủ đề vẫn có nguy cơ rò rỉ do cùng sách và thuật ngữ, nội dung lặp ở summary/key terms. Test nhỏ và tập trung 4 câu ở mục 2.3, 1 câu ở mục 2.4; không suy rộng kết quả ngoài corpus.

`alternative_gold` liệt kê trang khác có cùng evidence nguyên văn trong phạm vi đã chọn nếu có. Danh sách này không bao quát mọi cách diễn đạt tương đương. Nếu người chấm xác nhận evidence tương đương khác đủ hỗ trợ đáp án và điều kiện, ghi nguồn/trang/quote cùng lý do trong audit và áp dụng thống nhất cho A/B/C. Không loại hit hợp lệ chỉ vì khác trang gold chính.

Hit@1 và Evidence Hit@3 yêu cầu một chunk đúng nguồn/trang hợp lệ và chứa đủ evidence, hoặc bằng chứng tương đương đã xác nhận. Nếu phải ghép nhiều chunk mới đủ, ghi riêng. Kiểm tra literal evidence không thay nhãn coherence hoặc grounding thủ công.

## Tái xuất và kiểm chứng

Chạy từ thư mục gốc với Python đã cài `pypdf`:

```powershell
python benchmark/export_from_report.py
```

Lệnh ghi lại ba file JSON từ báo cáo hiện tại, kiểm tra 22 evidence trên PDF; không gọi API hoặc vector search. Sau khi chốt benchmark, chỉ tái xuất khi có chủ ý cập nhật phiên bản, không thay đổi nhãn dựa trên điểm test.
