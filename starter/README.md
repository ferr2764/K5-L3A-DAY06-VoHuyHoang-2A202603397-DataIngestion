# Pipeline — PostgreSQL + pgvector và OpenRouter

Pipeline đã triển khai đọc PDF, chuẩn hóa, chia chunk A/B/C, embedding OpenRouter, lưu pgvector và benchmark dev/test.

Hướng dẫn setup, tạo `.env`, khởi động database, chạy kiểm tra, chạy dev/test và đọc output nằm trong [báo cáo cá nhân — Hướng dẫn setup và chạy lại](../report/individual/2A202603397_VoHuyHoang.md#hướng-dẫn-setup-và-chạy-lại).

- Code: `src/`; kiểm tra database: `scripts/check_setup.py`; kiểm tra offline: `tests/test_pipeline.py`.
- Corpus: `data/Foundations_of_Information_Systems.pdf`; manifest: `../data/manifest.json`.
- Benchmark: `../benchmark/questions.json`; kết quả: `results/`; audit đã xác nhận: `../artifacts/audit/`.
- Tổng chi phí OpenRouter của bài hiện tại: **$0.0018**, do học viên cung cấp; chạy lại API phát sinh phí mới.

Không commit `.env` hoặc API key. Dùng cùng model, corpus và benchmark cho ba cấu hình; không tinh chỉnh dựa trên tập test đã xem.
