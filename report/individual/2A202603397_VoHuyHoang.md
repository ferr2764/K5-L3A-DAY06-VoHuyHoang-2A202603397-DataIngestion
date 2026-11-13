# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- Chủ đề: nền tảng hệ thống thông tin và chiến lược quản lý dữ liệu. Tài liệu *Foundations of Information Systems*, senior contributing author Dr. Mahesh S. Raisinghani, OpenStax/Rice University, 2025. File tại `starter/data/Foundations_of_Information_Systems.pdf`; nguồn chính thức: https://openstax.org/details/books/foundations-information-systems. Giấy phép nội dung CC BY-NC-SA 4.0 được đối chiếu trang PDF 4; giữ attribution “Access for free at openstax.org.”, chỉ dùng phi thương mại, chia sẻ bản phái sinh cùng loại giấy phép; hình/nhãn hiệu có thể có điều kiện riêng.
- Phạm vi trang PDF vật lý 30–72, tương ứng trang in 20–62: 43 trang được chọn, **34 trang nội dung** được tính. Loại trang PDF 43–51 gồm key terms, summary, câu hỏi, trang gần trống và trang mở chương. [Manifest](../../data/manifest.json) ghi từng trang, số ký tự, lý do loại, SHA-256 và cách lấy lại PDF; không tính lặp trang để đủ số lượng.
- Dùng pypdf 6.21.4 để đọc text, chuẩn hóa Unicode NFC và khoảng trắng, giữ xuống dòng phục vụ chunking. Không dùng OCR; 34 trang được tính đều trích xuất được text. Log vẫn ghi trang rỗng của toàn PDF do loader đọc toàn file rồi chọn trang. Header/footer, caption, ngắt dòng/từ và đoạn nối trang chưa được loại hết nên có thể làm nhiễu embedding. Không suy diễn mất text thành nội dung giả.
- Embedding: OpenRouter, `openai/text-embedding-3-small`, 1.536 chiều, cùng cách gọi cho document/query; SDK openai 3.50.0, python-dotenv 1.2.4. Không có mã revision nội bộ của model do provider công bố trong output hiện tại. Query được embed một lần rồi dùng cùng vector cho A/B/C. Vector store: PostgreSQL 16.16, pgvector 0.8.7, psycopg 3.3.8, lưu bền vững trong Docker volume `pg_data`, bảng `day6_chunks`; exact cosine search, score = 1 − cosine distance.
- Lệnh chạy từ `starter/`: `python -m src.run --prepare-only`, `python -m src.run --split dev`, sau khi cố định cấu hình chạy `python -m src.run --split test`. Hướng dẫn setup/chạy chi tiết ở cuối báo cáo này. **Tổng chi phí OpenRouter: $0.0018 USD**, do Võ Huy Hoàng cung cấp ngày 13/11/2026. Đây là tổng chi phí bài làm, chưa phân bổ theo strategy/split và không phải $0.0018 cho mỗi dòng kết quả. Pipeline chưa lưu token usage chính xác. Test đã gọi lại embedding.
- Metadata bắt buộc: `document_id`, `source`, `page` (trang PDF vật lý từ 1). Trường lọc chính `section` là chuỗi lấy từ heading sách; thêm `language=en`, `year=2025`, offsets, phương pháp chunk và attribution. Section giúp lọc phạm vi và phân biệt nội dung; trang 36, 40, 61, 68 được tách tại heading chuyển mục. Hạn chế: ánh xạ section hiện đặc thù corpus, cần cập nhật nếu đổi snapshot; có source/page đúng không đồng nghĩa evidence đủ hoặc liên quan.

## Cấu hình và benchmark
- A: cửa sổ 500 ký tự, overlap 50. B: nhóm đoạn/câu cuối dòng, tối đa 1.000 ký tự, đoạn quá dài cắt tại khoảng trắng, không overlap. C: dùng đúng chunk và vector của B, chỉ thêm filter section do câu hỏi cung cấp; câu không filter chạy giống B. A/B đều tách ranh giới section trước khi chunk. A có 270 chunk; B/C mỗi cấu hình 162 chunk. B là heuristic theo cấu trúc text PDF, chưa phải parser ngữ nghĩa hoàn chỉnh.
- Bộ câu hỏi: 20 câu chính (15 dev / 5 test), 4 câu filter và 2 câu dự phòng; chi tiết bên dưới.
- Quy tắc chọn đã lưu trong run config dev trước khi chạy test: ưu tiên Evidence Hit@3 dev, rồi Hit@1 dev, rồi tài nguyên. B/C hòa trên hai chỉ số dev; C dùng lại embedding B nên không lấy thời gian ingest C làm bằng chứng C rẻ hơn khi xây độc lập. Giữ nguyên cả ba cấu hình khi chạy test, không tinh chỉnh theo test. Kiểm tra sau chạy xác nhận JSON chunk A/B/C giống từng byte và SHA-256 benchmark/model giống giữa dev/test: [frozen_inputs_check.json](../../artifacts/audit/frozen_inputs_check.json).

### Bộ câu hỏi và gold evidence

Tài liệu: *Foundations of Information Systems*, `starter/data/Foundations_of_Information_Systems.pdf`. Quy ước hiện tại: **trang PDF vật lý 30–72**, đánh số từ 1, gồm 43 trang trước khi loại trang không đủ điều kiện nội dung. Trang in trong các gold dưới đây bằng trang PDF trừ 10. Nguồn chung (`gold_source_id`): `foundations-of-information-systems`.

Bộ chính có **20 câu: 15 dev / 5 test**, soạn trước khi chạy thử retrieval. Dev thuộc mục 1.2, 1.3, 2.1; test thuộc mục 2.3–2.4. Có câu trực tiếp, diễn đạt lại và tình huống có điều kiện. Bốn câu filter là **q03, q09, q17, q20**, gồm 2 câu test. Filter lấy từ phạm vi mục nêu trong câu hỏi trước truy xuất. Hai câu cuối là dự phòng, không tính vào chỉ số chính.

Câu hỏi và đáp án tiếng Việt; evidence giữ tiếng Anh nguyên văn sau chuẩn hóa Unicode NFC và gộp whitespace. Đã đối chiếu đáp án với nguồn và kiểm chứng 22/22 đoạn trích tồn tại trên đúng trang sau chuẩn hóa. Đây là kiểm chứng nguồn, chưa phải kết quả retrieval hay nhãn grounding. Codex hỗ trợ soạn và kiểm chứng; học viên đã xác nhận nội dung ngày 13/11/2026.

#### Tập dev — 15 câu

**q01**

- Câu hỏi: Agile chia dự án thành đơn vị nào và nhóm làm gì sau mỗi đơn vị?
- Đáp án kỳ vọng: Các giai đoạn/sprint; xem xét tiến độ và điều chỉnh trước sprint tiếp theo.
- Nguồn: `foundations-of-information-systems`; trang PDF **30**, trang in **20**; mục **1.2**.
- Filter: `Không áp dụng`.
- Evidence:

> Agile methodology is a framework used to guide project management, primarily by dividing projects into phases, or sprints. Typically, these sprints include planning, designing, developing, testing, deploying, and reviewing. After each sprint, the project team examines their progress and adjusts before moving to the next sprint.

**q02**

- Câu hỏi: Năm quy trình của COBIT là gì?
- Đáp án kỳ vọng: Evaluate, Direct, and Monitor (EDM); Align, Plan, and Organize (APO); Build, Acquire, and Implement (BAI); Deliver, Service, and Support (DSS); Monitor, Evaluate, and Assess (MEA).
- Nguồn: `foundations-of-information-systems`; trang PDF **30**, trang in **20**; mục **1.2**.
- Filter: `Không áp dụng`.
- Evidence:

> Control Objectives for Information and Related Technologies (COBIT) is a framework that develops and maintains an information system using five processes: Evaluate, Direct, and Monitor (EDM); Align, Plan, and Organize (APO); Build, Acquire, and Implement (BAI); Deliver, Service, and Support (DSS); and Monitor, Evaluate, and Assess (MEA) (Figure 1.6).

**q03**

- Câu hỏi: Trong mục 1.2, McKinsey 7-S phối hợp bảy yếu tố nào?
- Đáp án kỳ vọng: Staff, structure, strategy, skills, systems, style và shared values.
- Nguồn: `foundations-of-information-systems`; trang PDF **31**, trang in **21**; mục **1.2**.
- Filter: `section = "1.2"`.
- Evidence:

> The McKinsey 7-S Framework focuses on how an organization can be efficient and effective with interaction and coordination of its staff, structure, strategy, skills, systems, style, and shared values.

**q04**

- Câu hỏi: Theo SFIA, nhân viên nhận giám sát tổng quát, có thêm tự chủ, công việc có thể không thường lệ và có thể giám sát người khác thuộc cấp độ nào?
- Đáp án kỳ vọng: Level 3 — Apply.
- Nguồn: `foundations-of-information-systems`; trang PDF **32**, trang in **22**; mục **1.2**.
- Filter: `Không áp dụng`.
- Evidence:

> Level 3, Apply: At this level, employees receive more general supervision, and they have more autonomy. Their work is more complex and may not be routine. They also may be allowed to make some decisions on their own and may oversee other employees.

**q05**

- Câu hỏi: Theo SFIA, cấp nào cho phép nhận định hướng rộng và tự khởi xướng công việc được cho là cần thực hiện?
- Đáp án kỳ vọng: Level 5 — Ensure and Advise.
- Nguồn: `foundations-of-information-systems`; trang PDF **32**, trang in **22**; mục **1.2**.
- Filter: `Không áp dụng`.
- Evidence:

> Level 5, Ensure and Advise: At this level, employees receive broad direction, giving them more autonomy, including the ability to self-initiate work that they think should be performed.

**q06**

- Câu hỏi: Trong Zachman, câu hỏi nào tìm hiểu địa điểm hoạt động và câu hỏi nào tìm hiểu lịch vận hành?
- Đáp án kỳ vọng: Where? cho địa điểm; When? cho lịch và thời điểm thực hiện quy trình.
- Nguồn: `foundations-of-information-systems`; trang PDF **33**, trang in **23**; mục **1.2**.
- Filter: `Không áp dụng`.
- Evidence:

> Where? seeks to learn where the organization operates. • Who? seeks to learn who the organizational members are, as well as gather details about the organization’s units and hierarchy. • When? seeks to learn the organization’s schedule of operations, including when processes are performed.

**q07**

- Câu hỏi: IS2020 hướng dẫn nhóm cơ sở nào và nhằm chuẩn bị điều gì cho sinh viên?
- Đáp án kỳ vọng: Cơ sở giáo dục đại học; giúp chương trình IS bậc đại học chuẩn bị sinh viên theo nghề IS.
- Nguồn: `foundations-of-information-systems`; trang PDF **34**, trang in **24**; mục **1.2**.
- Filter: `Không áp dụng`.
- Evidence:

> IS2020 is a competency model that provides guidance and standards to higher education institutions to ensure that undergraduate IS programs effectively prepare students for careers in IS.

**q08**

- Câu hỏi: Competency là khả năng áp dụng những yếu tố nào để thực hiện công việc?
- Đáp án kỳ vọng: Kỹ năng cụ thể, kinh nghiệm và đặc điểm cá nhân để làm việc hiệu quả và có hiệu suất tốt.
- Nguồn: `foundations-of-information-systems`; trang PDF **36**, trang in **26**; mục **1.3**.
- Filter: `Không áp dụng`.
- Evidence:

> A competency is the ability to apply specific skills, experience, and personal characteristics to do a job in an effective and efficient manner.

**q09**

- Câu hỏi: Trong mục 2.1, DAMA-DMBOK và MIKE2.0 khác nhau về trọng tâm như thế nào?
- Đáp án kỳ vọng: DAMA-DMBOK tập trung khía cạnh kỹ thuật của quản lý dữ liệu; MIKE2.0 tập trung khía cạnh kinh doanh của quản lý thông tin.
- Nguồn: `foundations-of-information-systems`; trang PDF **55**, trang in **45**; mục **2.1**.
- Filter: `section = "2.1"`.
- Evidence:

> DAMA-DMBOK focuses on the technical aspects of data management, while MIKE2.0 focuses on the business aspects of information management.

**q10**

- Câu hỏi: Chiều nào trong bốn V phản ánh độ chính xác và đáng tin cậy của dữ liệu?
- Đáp án kỳ vọng: Veracity, xét chất lượng và tính nhất quán.
- Nguồn: `foundations-of-information-systems`; trang PDF **56**, trang in **46**; mục **2.1**.
- Filter: `Không áp dụng`.
- Evidence:

> Veracity: The veracity dimension refers to the reliability, accuracy, and trustworthiness of the data, considering factors like data quality and consistency.

**q11**

- Câu hỏi: Nếu dữ liệu được sinh và thu thập nhanh đến mức cần xử lý thời gian thực, đó là chiều nào của big data?
- Đáp án kỳ vọng: Velocity.
- Nguồn: `foundations-of-information-systems`; trang PDF **56**, trang in **46**; mục **2.1**.
- Filter: `Không áp dụng`.
- Evidence:

> Velocity: The rapid pace at which data are generated and collected, thereby necessitating real-time processing, is characterized by velocity.

**q12**

- Câu hỏi: Ba ưu tiên khi quản lý operational data để hỗ trợ quy trình kinh doanh trọng yếu là gì?
- Đáp án kỳ vọng: Tính toàn vẹn, tính sẵn sàng và hiệu năng.
- Nguồn: `foundations-of-information-systems`; trang PDF **56**, trang in **46**; mục **2.1**.
- Filter: `Không áp dụng`.
- Evidence:

> When managing operational data, the focus is on ensuring data integrity, availability, and performance to support critical business processes.

**q13**

- Câu hỏi: Nếu hai phòng ban dùng Date of Birth và Birth Date cho cùng ngày sinh, định nghĩa dữ liệu cần bảo đảm điều gì?
- Đáp án kỳ vọng: Dù tên gọi khác nhau, định nghĩa của cùng dữ liệu phải nhất quán trong hệ thống để phân tích và báo cáo chính xác.
- Nguồn: `foundations-of-information-systems`; trang PDF **57**, trang in **47**; mục **2.1**.
- Filter: `Không áp dụng`.
- Evidence:

> Addressing varied definitions: Dealing with diverse definitions across different data sources requires establishing a clear and standardized data definition, which is the instruction for how to organize information. These definitions tell a computer system what kind of data to expect (text, numbers, dates) and how the data should be formatted mapped to ensure consistency. For example, when the underlying data point is the same (the person’s date of birth), the specific term used (“Date of Birth” versus “Birth Date”) might differ based on the department using the data. However, the definition of the data point (the actual date) needs to be consistent throughout the system to ensure accurate analysis and reporting.

**q14**

- Câu hỏi: Master data management tạo và duy trì điều gì cho dữ liệu quan trọng của tổ chức?
- Đáp án kỳ vọng: Một nguồn sự thật duy nhất, chính xác; kho tập trung loại bỏ bất nhất và hỗ trợ trao đổi thông tin giữa các hệ thống.
- Nguồn: `foundations-of-information-systems`; trang PDF **57**, trang in **47**; mục **2.1**.
- Filter: `Không áp dụng`.
- Evidence:

> Master data management (MDM) ensures the creation and maintenance of a single, accurate source of truth for crucial data points within an organization. This centralized data repository eliminates inconsistencies and fosters seamless information exchange across different systems and applications.

**q15**

- Câu hỏi: Strategic planning khác management control về mục tiêu như thế nào?
- Đáp án kỳ vọng: Strategic planning xác định sứ mệnh, tầm nhìn, mục tiêu và chiến lược, thường do quản lý cấp cao; management control bảo đảm vận hành hằng ngày hiệu quả và tuân thủ kế hoạch chiến lược.
- Nguồn: `foundations-of-information-systems`; trang PDF **58**, trang in **48**; mục **2.1**.
- Filter: `Không áp dụng`.
- Evidence:

> An organization’s strategic planning is its process of defining the organization’s mission, vision, goals, and objectives, and developing strategies to achieve them, often with the support of information systems, typically done by senior-level managers. In contrast, management control ensures efficient day-to-day operations and adherence to those strategic plans.

#### Tập test — 5 câu

**q16**

- Câu hỏi: Dịch vụ miễn phí phiên bản cơ bản và cho nâng cấp trả phí để thêm tính năng thuộc mô hình nào?
- Đáp án kỳ vọng: Freemium.
- Nguồn: `foundations-of-information-systems`; trang PDF **68**, trang in **58**; mục **2.3**.
- Filter: `Không áp dụng`.
- Evidence:

> The freemium model provides a free basic service, with the option to upgrade to a premium version for enhanced features or benefits, such as with the services offered by LinkedIn, DropBox, and MailChimp.

**q17**

- Câu hỏi: Trong mục 2.3, affiliate model kiếm tiền thế nào và IT cần theo dõi điều gì để ghi nhận doanh số đúng?
- Đáp án kỳ vọng: Hoa hồng qua quảng bá và bán sản phẩm/dịch vụ của công ty khác; theo dõi và báo cáo phải quy doanh số chính xác cho affiliate giới thiệu.
- Nguồn: `foundations-of-information-systems`; trang PDF **69**, trang in **59**; mục **2.3**.
- Filter: `section = "2.3"`.
- Evidence:

> In an affiliate model, one company earns commissions by promoting and selling other companies’ products or services through websites or social media channels. They help drive traffic and sales, receiving a percentage of the revenue from the companies they promote. Amazon Associates, ClickBank, and Commission Junction use this model. These organizations should work with IT to build effective tracking and reporting systems to accurately attribute sales to affiliates by implementing affiliate tracking software, optimizing landing pages for conversion, and ensuring a seamless user journey from the affiliate’s site to the merchant’s platform.

**q18**

- Câu hỏi: Trong case Cohealo, sản phẩm nào giúp phòng khám tìm và huy động thiết bị y tế đang nhàn rỗi trên mạng lưới?
- Đáp án kỳ vọng: Cohealo + Clinical.
- Nguồn: `foundations-of-information-systems`; trang PDF **70**, trang in **60**; mục **2.3**.
- Filter: `Không áp dụng`.
- Evidence:

> Cohealo + Clinical: This network-based application empowers clinics to locate and enlist any idle medical equipment across the network to support procedures wherever and whenever needed.

**q19**

- Câu hỏi: Khi người lao động có điểm uy tín cao và nhiều kinh nghiệm nhận thêm việc trên gig platform, nhóm điểm thấp và ít kinh nghiệm chịu hệ quả gì?
- Đáp án kỳ vọng: Cơ hội bị phân phối không đều, gây bất lợi cho nhóm điểm thấp và ít kinh nghiệm; hiệu ứng người giàu càng giàu.
- Nguồn: `foundations-of-information-systems`; trang PDF **71**, trang in **61**; mục **2.3**.
- Filter: `Không áp dụng`.
- Evidence:

> Unequal distribution of opportunities: Research has shed light on a concerning phenomenon observed in gig work platforms—the “rich get richer” effect. Workers with higher reputation scores and greater experience tend to receive more work, as clients prefer to engage with those perceived as more reliable. Consequently, this phenomenon results in an unequal distribution of opportunities, disadvantaging workers with lower scores and less experience.

**q20**

- Câu hỏi: Trong mục 2.4, ba thành phần thiết yếu của business process là gì và có vai trò nào?
- Đáp án kỳ vọng: Inputs: vật liệu, dịch vụ, thông tin được biến đổi; resources: con người và nguồn lực thực hiện hoạt động; outputs: sản phẩm/dịch vụ cuối cùng sẵn sàng giao cho người nhận.
- Nguồn: `foundations-of-information-systems`; trang PDF **72**, trang in **62**; mục **2.4**.
- Filter: `section = "2.4"`.
- Evidence:

> This process relies on three essential components: • Inputs: These encompass the materials, services, and information that flow through the process and undergo transformations as a consequence of the activities within the process. • Resources: People and other resources form the backbone of process activities, performing various tasks to facilitate the progression of the process. • Outputs: Outputs are the ultimate result of the process, ending in the creation of a specific product or service that is ready to be delivered to the intended recipient.

#### Câu dự phòng — không tính vào bộ chính

**q21**

- Câu hỏi: Marketplace model đóng vai trò gì giữa người mua và người bán?
- Đáp án kỳ vọng: Tập hợp hai bên trên một nền tảng; doanh nghiệp làm trung gian hỗ trợ giao dịch.
- Nguồn: `foundations-of-information-systems`; trang PDF **69**, trang in **59**; mục **2.3**.
- Filter: `Không áp dụng`.
- Evidence:

> Amazon, eBay, and Airbnb demonstrate the marketplace model, which brings buyers and sellers together on a single platform, with the enterprise acting as an intermediary that facilitates transactions between parties.

**q22**

- Câu hỏi: Vì sao thuật toán độc quyền làm người dùng khó hiểu điểm uy tín và cơ hội việc làm?
- Đáp án kỳ vọng: Bí mật thương mại ngăn kiểm tra bên ngoài, khiến người dùng không biết yếu tố ảnh hưởng điểm và tác động của thay đổi thuật toán.
- Nguồn: `foundations-of-information-systems`; trang PDF **71**, trang in **61**; mục **2.3**.
- Filter: `Không áp dụng`.
- Evidence:

> Proprietary algorithms protected by trade secrecy laws prevent external scrutiny, leaving users in the dark about the factors influencing their reputation scores or how changes to algorithms may impact their job opportunities.

#### Quy tắc chấm và nguy cơ rò rỉ

Giữ nguyên câu hỏi, split và nhãn gold cho A/B/C. Query chỉ chứa câu hỏi, không chứa đáp án hoặc gold source/page. A/B không dùng filter; C chỉ dùng filter được cung cấp. Metadata section lấy từ heading thật. Trang PDF 36 và 68 có chuyển tiếp giữa hai mục, cần tách ranh giới nội dung thay vì gán cả trang theo gold.

Tách theo chủ đề giảm trùng câu nhưng dev/test vẫn cùng sách và thuật ngữ; summary/key terms có thể lặp ý. Test nhỏ, tập trung 4 câu ở mục 2.3 và 1 câu ở mục 2.4 nên chưa đại diện toàn corpus. Không dùng test để tinh chỉnh. Chỉ bổ sung dự phòng trước lần chạy test đầu tiên, ghi phiên bản; không thay câu sau khi xem kết quả. Nếu đã dùng test để sửa bài, phải công bố và tạo tập độc lập mới khi có thể.

Chấp nhận trang khác nếu người chấm xác nhận có bằng chứng tương đương đủ hỗ trợ đáp án và điều kiện. Ghi nguồn/trang/quote và lý do vào audit, áp dụng cùng nhãn cho mọi chiến lược. Gold trên là evidence đã xác minh, chưa khẳng định liệt kê hết mọi cách diễn đạt tương đương trong corpus. Hit@1/Hit@3 yêu cầu một chunk đúng nguồn/trang hợp lệ và đủ bằng chứng; trường hợp phải ghép nhiều chunk ghi riêng. Mọi câu chính đều có đáp án trong nguồn.

## Hướng dẫn setup và chạy lại

Yêu cầu: Python 3.11–3.14, Docker Desktop đang chạy và mạng để tải dependencies/image, gọi OpenRouter. Các lệnh dưới dùng Windows PowerShell. Bắt đầu tại thư mục gốc project.

### 1. Tạo môi trường Python

```powershell
cd starter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu không kích hoạt môi trường, thay `python` bằng `.\.venv\Scripts\python.exe` ở các lệnh tiếp theo. Phiên bản đã chạy: pypdf 6.21.4, openai 3.50.0, psycopg 3.3.8, python-dotenv 1.2.4; ghi trong `run_config.json` để đối chiếu.

### 2. Cấu hình OpenRouter và database

Chỉ tạo `.env` nếu chưa có, tránh ghi đè cấu hình hiện tại:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Điền nội dung sau trong `starter/.env`, dùng API key riêng; không commit file này:

```dotenv
DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
OPENROUTER_API_KEY=your_openrouter_key
EMBEDDING_MODEL=openai/text-embedding-3-small
EMBEDDING_DIMENSIONS=1536
```

Khởi động PostgreSQL + pgvector và kiểm tra:

```powershell
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py
```

Kỳ vọng `Setup OK`. Database chỉ mở local tại cổng 55433; nếu cổng bận, đổi đồng thời port Compose và DATABASE_URL. Docker volume giữ dữ liệu qua các lần dừng; không cần xóa volume để chạy lại.

### 3. Kiểm tra dữ liệu và chạy pipeline

PDF cần nằm tại `starter/data/Foundations_of_Information_Systems.pdf`. Manifest và benchmark ở `data/manifest.json`, `benchmark/questions.json` tính từ thư mục gốc; pipeline tự tìm qua đường dẫn project, không cần sao chép chúng vào starter. Cách tải PDF và SHA-256 trong manifest.

Các lệnh sau vẫn chạy trong `starter/`:

```powershell
# Chỉ chuẩn bị corpus/chunk/gold; không gọi API hoặc database
python -m src.run --prepare-only

# Kiểm tra code bằng fixture offline; không gọi API
python -m unittest discover -s tests -v

# Gọi embedding thật, ingest A/B/C và đánh giá 15 câu dev
python -m src.run --split dev

# Sau khi cố định cấu hình, đánh giá 5 câu test
python -m src.run --split test
```

Lệnh dev/test phát sinh phí OpenRouter và mỗi lần đều ingest lại corpus. Chi phí $0.0018 là số đã ghi nhận của bài làm hiện tại, không cam kết chi phí của lần chạy lại. Bộ test hiện đã được xem: không dùng kết quả này để tinh chỉnh rồi coi là đánh giá độc lập mới.

### 4. Đọc kết quả và tái tạo audit

Mỗi lần chạy tạo thư mục `starter/results/<UTC timestamp>/`. Đọc `metrics.json` (Hit@1/Hit@3), `traces.json` (top-3 đầy đủ), `ingestion.json` (thời gian và kiểm tra nạp lại), `run_config.json` (model/version), `preparation.json` và `chunks_A/B/C.json`. Nếu thất bại, xem `failure.json`/`errors.log`; không có fallback sang mock. Các thư mục dev/test đã lưu được dẫn chiếu bên dưới, không cần gọi API lại để đọc chúng.

Để tái kiểm chứng gold và tái tạo audit của **hai run đã lưu**, trở về thư mục gốc:

```powershell
cd ..
python benchmark/export_from_report.py
python artifacts/complete_report.py
python artifacts/review_retrieval.py
```

Các script này không gọi API. Script export ghi lại JSON benchmark và checksum báo cáo từ nội dung hiện tại; chỉ chạy có chủ ý vì đã chốt benchmark. Script audit dùng run ID cố định, tái xuất nhãn đã đánh giá và xác nhận; không tự chấm nội dung cho một run mới. `review_retrieval.py` tái tạo điểm test sau đối chiếu bằng chứng tương đương, giữ nguyên gold và trace gốc. Các file `*_to_label.json` trống là mẫu gốc; nhãn chính thức nằm ở `artifacts/audit/` với trạng thái confirmed.

Dừng database nhưng giữ dữ liệu (từ thư mục gốc):

```powershell
cd starter
docker compose -p day6_student_starter stop
```

## Kết quả
| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 3/15 | 6/15 | 270 | 18,646 s | Tổng bài: $0.0018; chưa phân bổ |
| B | dev | 8/15 | 12/15 | 162 | 10,874 s | Tổng bài: $0.0018; chưa phân bổ |
| C | dev | 8/15 | 12/15 | 162 | 1,026 s | Dùng lại vector B; nằm trong tổng $0.0018; chưa phân bổ |
| A | test | 1/5 | 1/5 | 270 | 15,546 s | Tổng bài: $0.0018; chưa phân bổ |
| B | test | 4/5 | 4/5 | 162 | 9,260 s | Tổng bài: $0.0018; chưa phân bổ |
| C | test | 4/5 | 4/5 | 162 | 0,864 s | Dùng lại vector B; nằm trong tổng $0.0018; chưa phân bổ |

Thời gian trên là ingest **kèm lần nạp lại kiểm chứng**, có API ở A/B, không gồm chuẩn bị corpus hay toàn bộ truy vấn. Đây là một lần đo mỗi split, có độ trễ mạng; không dùng để kết luận hiệu năng tổng quát. Tổng text chunk A là 125.855 ký tự, B/C là 114.255; chênh lệch do overlap A. Độ dài min/mean/max: A 51/466,13/500; B/C 41/705,28/1.000. Nạp lại: A 270→270, B 162→162, C 162→162; thay snapshot trong transaction loại chunk lỗi thời.

Các số retrieval là **literal evidence metrics**, không tự nâng điểm nhờ audit tương đương. Đúng nguồn/trang nhưng thiếu bất kỳ phần nào trong evidence đã ghi vẫn là miss ở bảng này. Có thể thiếu nhạy với evidence dài hoặc câu dẫn không cần thiết; không sửa gold sau khi xem test.

### Retrieval test sau audit bằng chứng tương đương

Bảng dưới áp dụng định nghĩa hit của đề bài: một chunk có đủ gold **hoặc bằng chứng tương đương đã đối chiếu**, đúng nguồn/trang và đủ điều kiện trả lời. Không gộp nhiều chunk để tính hit. Đây là chấm lại trace test đã lưu theo audit được học viên xác nhận, không phải chạy model hoặc thay đổi gold/cấu hình sau test. Dev ở bảng trên vẫn là literal, chưa trình bày như điểm đã audit tương đương.

| Strategy | Split | Hit@1 sau audit (n/N) | Evidence Hit@3 sau audit (n/N) |
|---|---|---|---|
| A | test | 2/5 | 2/5 |
| B | test | 4/5 | 5/5 |
| C | test | 4/5 | 5/5 |

Các điều chỉnh có quote, source/page, chunk ID và lý do trong [retrieval_review.json](../../artifacts/audit/retrieval_review.json). Quyết định được gắn theo cặp câu hỏi/chunk, áp dụng giống nhau cho A/B/C:

- q19, A rank 1, trang PDF 71: giữ đủ điều kiện uy tín/kinh nghiệm và hệ quả phân phối cơ hội; thiếu câu dẫn không làm thiếu đáp án. Chấp nhận hit tương đương.
- q20, B/C rank 2, trang PDF 72: một chunk có đủ inputs, resources, outputs và định nghĩa; không cần ghép câu dẫn ở rank 1. Chấp nhận hit tương đương.
- q17, A: vẫn không là hit sau audit vì hoa hồng và tracking nằm ở hai chunk; grounding top-3 có thể đủ nhưng retrieval một-chunk không đủ. q18 và q20 của A vẫn thiếu bằng chứng cần thiết.

Bảng literal gốc giữ nguyên để truy vết; báo cáo đồng thời hai phương pháp, không coi tỷ lệ 5/5 trên 5 câu là bằng chứng tổng quát.

### Chất lượng chunk, metadata và grounding

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 1,00 (10) | 15/15 | 2/2 | 0 / 2 / 3; 1,60/2 |
| B | 1,40 (10) | 15/15 | 1/2 | 0 / 0 / 5; 2,00/2 |
| C | 1,40 (10) | 15/15 | 2/2 | 0 / 0 / 5; 2,00/2 |

**Nguồn nhãn audit:** bảng trên được Codex hỗ trợ đánh giá bằng cách đọc chunk/top-3 và đối chiếu PDF theo rubric; **Võ Huy Hoàng đã xác nhận các nhãn ngày 13/11/2026** (`human_confirmation=confirmed`). Mọi nhãn có lý do và provenance trong JSON. Đây là đánh giá có hỗ trợ AI và xác nhận bởi học viên, không phải đánh giá mù độc lập: cùng trợ lý hỗ trợ benchmark/code và xem điểm retrieval trước audit nên vẫn có nguy cơ thiên lệch.

- Dev trace/metrics/config: [run dev](../../starter/results/20261113T110230648138Z/metrics.json), [trace dev](../../starter/results/20261113T110230648138Z/traces.json).
- Test trace/metrics/config: [run test](../../starter/results/20261113T114712057039Z/metrics.json), [trace test](../../starter/results/20261113T114712057039Z/traces.json).
- Coherence: vị trí ký tự nội dung đầu tiên trên cùng 10 trang PDF 30–39, đã xuất mẫu trước test; mỗi strategy dùng chunk bao phủ vị trí đó. [30 nhãn và lý do](../../artifacts/audit/coherence_review.json). Cùng vị trí không bảo đảm đại diện mọi vị trí trong trang; mẫu đầu trang thường gặp đoạn nối trang/caption.
- Grounding/metadata: đọc cùng 5 câu test × top-3 × 3 cấu hình, 15 nhãn grounding và 45 bản ghi metadata. [Nhãn chi tiết](../../artifacts/audit/test_review.json), [tổng hợp](../../artifacts/audit/summary.json). Các bản ghi đều khớp source/path, trang text và section trong PDF. Filter compliance xét cả top-3 so với phạm vi câu hỏi, kể cả A/B không thực thi filter; A đúng 2/2 là kết quả tình cờ trên mẫu này, không chứng minh A có cơ chế lọc.
- Các mẫu `*_to_label.json` của run được giữ nguyên như output gốc; nhãn đã xác nhận được lưu riêng trong `artifacts/audit/`. Tái tạo nhãn AI đã ghi nhận và phép kiểm chứng bằng `python artifacts/complete_report.py`; script không gọi API và không tự suy diễn nhãn bằng exact match.
- Lần dev đầu bị `APIConnectionError` trong môi trường hạn chế kết nối; chạy lại có kết nối đã thành công. Không fallback embedding mock. Thư mục thất bại giữ riêng, không tính vào chỉ số. Chi phí tổng do học viên cung cấp là $0.0018; không có phân rã riêng cho lần lỗi.

## Phân tích và kết luận

**Retrieval và tác động chunking:** A→B tăng dev Evidence Hit@3 từ 6/15 lên 12/15, test từ 1/5 lên 4/5. Chunk dài hơn và ranh giới đoạn/câu giúp giữ bằng chứng liền mạch; số chunk giảm 270→162. Tuy nhiên B thay cả kích thước, overlap và quy tắc ranh giới nên không thể quy toàn bộ cải thiện cho duy nhất một thành phần của chunking. B/C vẫn có chunk dài chứa nội dung không liên quan, header/footer, citation hoặc danh sách bị tách.

**Metadata:** B→C không đổi Hit@1/Hit@3 trên cả dev và test nhưng tăng tuân thủ filter test 1/2→2/2. Với q20 (trang PDF 72, mục 2.4), B rank 3 lấy trang 65 mục 2.2, còn C rank 3 nằm trong trang 72 mục 2.4. Trường section có ích dù không tăng hit trong bộ nhỏ; source/page giúp truy lại bằng chứng, chưa đủ chứng minh liên quan. C không được dùng gold source/page để lọc.

**Hai trường hợp lỗi tiêu biểu:**

1. **q18, A, trang PDF 70:** top-3 lấy đúng case Cohealo nhưng rank 1 là C-suite/Finance, rank 2 là giới thiệu nền tảng, rank 3 bắt đầu giữa đoạn Clinical nên mất tên sản phẩm và đầu mô tả. Không đủ xác định Cohealo + Clinical; grounding 1/2. B/C rank 1 giữ tên và chức năng Clinical đầy đủ, grounding 2/2. Đây là lỗi mất ngữ cảnh dù đúng trang.
2. **q20, B/C, trang PDF 72:** gold gồm câu dẫn “This process relies on three essential components:” và ba định nghĩa. Rank 1 chứa câu dẫn; rank 2 chứa đủ inputs/resources/outputs. Literal Hit@3 của câu vẫn 0 vì không có nguyên quote trong một chunk. Sau audit, rank 2 tự nó đủ đáp án và điều kiện, được chấp nhận là evidence tương đương nên Hit@3 sau audit là 1; grounding 2/2. Riêng B có rank 3 ngoài section, được C loại ra. Giữ nguyên benchmark, trace và literal metrics; lưu quyết định tương đương riêng để đối chiếu.

**Grounding:** A có 3/5 câu đủ bằng chứng theo top-3, 2 câu thiếu (q18, q20); B/C đủ cả 5 theo đánh giá AI hiện tại. q17 của A cần ghép rank 3 (hoa hồng) và rank 1 (tracking), nên grounding đủ nhưng literal hit không đạt. q19 của A có đủ điều kiện và hệ quả trong rank 1 dù thiếu phần dẫn trong quote. Vì vậy grounding không đồng nhất với Hit@3 và không phải độ chính xác câu trả lời LLM; bài không sinh câu trả lời bằng LLM.

**Coherence:** điểm AI tăng 1,00→1,40/2 nhờ B giữ thêm câu hoàn chỉnh. A thường cắt giữa từ; B vẫn bị đoạn nối trang, danh sách chưa trọn và caption/credit. C có cùng chunk B nên coherence bằng B; không tuyên bố filter cải thiện cấu trúc chunk.

**Lựa chọn:** chọn B làm cấu hình chunking nền; dùng biến thể C khi người dùng cung cấp phạm vi section đáng tin. B/C hòa trên tiêu chí retrieval dev đã định trước; không coi C thắng nhờ thời gian tái dùng embedding. Với truy vấn có phạm vi, C cung cấp ràng buộc phù hợp; với truy vấn không filter, C bằng B. Kết luận này giới hạn trong corpus, bộ câu hỏi và model đã đo.

**Giới hạn và bước tiếp theo:** test chỉ 5 câu, mỗi câu làm thay đổi tỷ lệ 20 điểm phần trăm; chưa có lặp đo hoặc khoảng tin cậy. Benchmark xuyên ngôn ngữ, gold có đoạn dài/câu dẫn, split cùng sách, ánh xạ section đặc thù và mẫu coherence đầu trang đều có thể thiên lệch. Nhãn có hỗ trợ AI đã được học viên xác nhận; vẫn không phải đánh giá mù độc lập. Tổng chi phí OpenRouter được học viên cung cấp là $0.0018; chưa có phân bổ theo run/strategy hoặc token usage chính xác, chưa có model revision cố định từ provider. Nếu mở rộng, cải thiện loại footer và nhận dạng paragraph/list, xây gold gồm evidence tối thiểu đã xác minh cùng alternative hợp lệ, thiết kế thêm câu phân biệt section, rồi tạo **tập test mới** trước khi tinh chỉnh; không tối ưu bằng test đã đọc.
