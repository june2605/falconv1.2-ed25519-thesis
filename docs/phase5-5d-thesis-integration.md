# Phase 5.5D - Tích hợp bằng chứng đa nền tảng vào luận văn

Chương 4 dùng Phase 5.5C làm thí nghiệm chính để so sánh PDF Ed25519, PDF Falcon-512 và PDF lai. Chương 5 phân biệt lý do phối hợp thuật toán, chính sách xác minh, kết quả kiểm thử và giới hạn của bằng chứng. Phép đo Windows cục bộ của Phase 5.2 và số liệu gốc FALCON/eSign tiếp tục được dẫn theo nguồn riêng. [Chương 4](thesis-chapter-experiments-vi.md) · [Chương 5](thesis-chapter-discussion-vi.md)

## Kiểm tra nguồn và số đếm

- Workspace bắt đầu sạch trên `thesis/ui-demo` ở `9772bf8e6695b91c9bf2298d98861e817c3363f8`, trùng ref từ remote. Commit này chứa báo cáo đã công bố của Phase 5.5C. Nguồn đo được ghim ở `613a46d06930ffd9224afa557fa90992e3a56a2a`. Checkout nguồn đo giữ ở đúng SHA này. Giao thức `hybridsign-5.5a-v1` và hồ sơ `p55a-cp3119-x64-v1` được xác nhận lại theo metadata từng phiên. [Báo cáo Phase 5.5C tại commit công bố](https://github.com/june2605/falconv1.2-ed25519-thesis/blob/9772bf8e6695b91c9bf2298d98861e817c3363f8/docs/phase5-5c-cross-platform-main.md)
- Đã kiểm khớp 179 mục trong danh mục Phase 5.5C và 96 mục trong danh mục pilot/C8. Kiểm tra bao gồm ZIP gốc, metadata, log, lịch, CSV, đối chứng và inventory phiên. Đã tái tạo `verified-main.json` và chạy lại lệnh tổng hợp trên đúng chín thư mục phiên từ checkout nguồn đo. Hai tệp tái tạo khớp byte với bản đã chấp nhận. [Bằng chứng chiến dịch](phase5-5c-cross-platform-main.md#lưu-trữ-và-tái-tính)
- Main có **9 phiên đầy đủ**, **3 phiên mỗi môi trường** và **30 khối đo ghép cặp mỗi phiên**. Kết quả có 4 050 lượt đo, 7 560 dòng thời gian hợp lệ, 2 430 PDF đầu ra ở phần đo và 0 lượt lỗi, dở dang hoặc bị loại. Phần khởi động riêng có 405 lượt, 756 dòng thời gian và 243 PDF. Mỗi khối đo chứa đủ ba phương pháp trên cùng kích thước và thao tác. [Số đếm từ lịch và CSV](thesis-chapter-experiments-vi.md#42-thiết-kế-thực-nghiệm)
- Job `136184651470` của `CI-LINUX-s2` nhận HTTP 503 lúc tải ZIP C8, ở bước `Validate accepted pilot and C8 evidence` của attempt 1. Log xác nhận job dừng trước bước đo. Attempt 2 chỉ chạy lại slot này, với job `137068722227`. Tám bản ghi kế thừa trong API có cùng thời gian thực thi, runner và trạng thái từng bước như attempt 1. Chúng được quy về tám phiên gốc khi đếm. [Lần chạy và log](phase5-5c-cross-platform-main.md#phiên-thực-thi-và-kiểm-tra-bằng-chứng)
- Kiểm tra trước và sau xử lý đều đọc từ thư mục gốc `%LOCALAPPDATA%\HybridSignResearch\phase5-5c\campaign-81d76271`. Bằng chứng tiền nhiệm nằm tại `%LOCALAPPDATA%\HybridSignResearch\phase5-5b\campaign-60fd4c10`. Bản tái tính và dữ liệu tạo hình của Phase 5.5D lưu riêng dưới `%LOCALAPPDATA%\HybridSignResearch\phase5-5d\integration-4c251d4b`. Các tệp bằng chứng bắt buộc cho đối chiếu Phase 5.5C và C8 đều có mặt.

| Tệp kiểm chứng | SHA-256 đã đối chiếu |
| --- | --- |
| `campaign-checksums.sha256` của Phase 5.5C | `ab0bcc2118f5d1261bd9da7321b838154c00c0de1efde97933b5c50366e53829` |
| `verified-main.json` | `dcdcf77226389248f29a8f5e4964ba7bb2cef13a40737b3dde058b7cda8139e2` |
| `summary-main.json` | `7ff23a8412216fb1306a0f8a058b3fe06039b78b807d64159c1c33811e5f7868` |
| `campaign-checksums.sha256` của Phase 5.5B | `3060b78734e264ccb3b0be9d5395a530afd2d0cd240d0660156c3fdf8cc8fd52` |

## Bản đồ bằng chứng và vị trí trong luận văn

| Câu hỏi hoặc luận điểm | Bằng chứng cụ thể | Vị trí tích hợp |
| --- | --- | --- |
| Vì sao dùng hai thuật toán và xác minh thế nào | RFC 8032, đặc tả Falcon v1.2, FIPS 202 và RFC 9955. Nội dung thông điệp đối chiếu với `sign._sign_captured()`, các hàm ghép ByteRange và SHAKE256 trong `utils.py` và `verify._verify_document()`. Quy tắc cặp và phạm vi của nó được kiểm toán Phase 5.1A | Chương 1 và 3 trong [đoạn Word](thesis-word-integration-vi.md). [Bàn luận động cơ](thesis-chapter-discussion-vi.md#51-động-cơ-mật-mã-và-chính-sách-xác-minh) |
| Môi trường, tệp và phép đo | `verified-main.json` liên kết job, attempt, phiên và thư mục. `session.json`, `schedule.json`, `outcome.json` giữ cấu hình, lịch và số đếm. `research/benchmarks/p55/protocol.py` và `pdf.py` xác định đầu vào, thời điểm đo và kiểm tra khóa | [Chương 4 mục 4.2-4.6](thesis-chapter-experiments-vi.md#42-thiết-kế-thực-nghiệm) |
| Độ trễ và biến thiên giữa phiên | Các dòng `measured` của chín `raw.csv`, theo `environment`, `session`, `workload`, `method`, `operation` và `elapsed_ns`. `summary-main.json` tách `sessions` và `aggregates`. Hình biến thiên 10 MiB lấy trung vị từng slot từ `sessions` của báo cáo 5.5C | [Kết quả và phụ lục PDF](thesis-chapter-experiments-vi.md#47-kết-quả-trên-ba-môi-trường) |
| Hiệu và tỷ số Hybrid so với từng bộ so sánh | Cùng job thực thi, phiên, khối, PDF và thao tác trong CSV. Dữ liệu ghép cặp nằm trong `aggregates[].paired` của bản tổng hợp. Các hàm `paired_values()` và `paired_stats()` quy định phép tính | [Chương 4 mục 4.8](thesis-chapter-experiments-vi.md#48-so-sánh-ghép-cặp) · [Bảng ghép cặp](tables/phase5-5d-pdf-vi.md#so-sánh-ghép-cặp) |
| Dung lượng chữ ký và mức tăng của tệp | Các cột `*_native_bytes`, `*_capacity_bytes`, `*_padding_ascii_bytes`, `*_metadata_bytes`, `*_container_bytes` và `growth_bytes`. `pdf.sizes()` đọc chiều dài vùng chứa. `utils.prepare_bytes_with_placeholder()` và `embed_signature_into_pdf()` xác định dung lượng và biểu diễn | [Tăng trưởng kích thước](thesis-chapter-experiments-vi.md#49-tăng-trưởng-kích-thước-tệp) · [Chi phí lưu trữ](thesis-chapter-discussion-vi.md#53-chi-phí-lưu-trữ) |
| Kiểm thử chức năng và C8 | Main có `controls.jsonl` và `smoke.json` với C0-C7. C8 thuộc run `44702431300`, attempt 1. `validation-complete.json` của Phase 5.5B liên kết chín ô VALID với từng job xác minh và bundle có manifest | [Chương 4 mục 4.10 và ma trận](thesis-chapter-experiments-vi.md#410-tính-đúng-và-khả-năng-xác-minh-giữa-các-môi-trường) · [Báo cáo C8](phase5-5b-cloud-pilot.md#c8-giữa-các-môi-trường) |
| Ranh giới tin cậy và khả năng sử dụng | Kiểm toán khoảng lưu chữ ký Falcon, mô hình kho khóa cục bộ, nghiệm thu desktop Windows và đặc tả CMS/PAdES. Xác minh toán học quan sát được với đúng khóa công khai của tệp thử | [Kiểm toán 5.1A](phase5-1a-signature-integrity-audit.md#impact-assessment) · [Giới hạn](thesis-chapter-discussion-vi.md#54-giới-hạn-của-bằng-chứng-mật-mã-và-sử-dụng-thực-tế) |
| Phân rã công đoạn và kết quả kế thừa | Bảng và hình Phase 5.2 từ nguồn đo Windows cục bộ. Số liệu trước đó giữ đúng ranh giới đo FALCON/eSign. Phase 5.5C bổ sung đối chứng PDF đồng thời cho câu hỏi chi phí trong truy vết Phase 5.1 | [Phần hỗ trợ của Chương 4](thesis-chapter-experiments-vi.md#411-thực-nghiệm-hỗ-trợ-trên-windows-cục-bộ---phase-52) · [Phân tích Phase 5.2B](phase5-2b-statistical-analysis.md) · [Truy vết ban đầu](phase5-1-thesis-traceability.md#research-questions) |

## Bảng, hình và diễn giải

Phụ lục gồm 6 bảng thống kê gộp theo môi trường và thao tác, 2 bảng trung vị từng phiên, 2 bảng tương phản ghép cặp và 1 bảng kích thước. Hai thao tác PDF có đơn vị ms. Chương 4 trích thêm một bảng mức thuật toán bằng µs và các trung vị 10 MiB để đọc cùng biểu đồ. [Phụ lục bảng PDF](tables/phase5-5d-pdf-vi.md)

| Hình | Trường dữ liệu trực tiếp từ Phase 5.5C | SHA-256 của PNG |
| --- | --- | --- |
| [Hình 4.1. Ký và xuất](figures/phase5-5d/pdf-ky-va-xuat.png) | `aggregates[].statistics`, lớp PDF, `sign_and_publish`, trung vị và Q1-Q3 | `47c8da67a26304e2236754b70350f80437c97daf718597b78c4611d750f68d4d` |
| [Hình 4.2. Xác minh PDF](figures/phase5-5d/pdf-xac-minh.png) | `aggregates[].statistics`, lớp PDF, `verify_published_file`, trung vị và Q1-Q3 | `c840172a4875d2526c12004bf7f96995f77bb5a168050a4f8ec7e7e53b80a5db` |
| [Hình 4.3. Hiệu ghép cặp khi ký](figures/phase5-5d/chenh-lech-ky-va-xuat.png) | `aggregates[].paired[].hybrid_minus_baseline_ms`, `sign_and_publish`, trung vị và Q1-Q3 của từng đối chiếu | `33522cf66ba12584f819f01239b42410bcae663b95c65ef5a7ce00885042b2d3` |
| [Hình 4.4. Hiệu ghép cặp khi xác minh](figures/phase5-5d/chenh-lech-xac-minh.png) | `aggregates[].paired[].hybrid_minus_baseline_ms`, `verify_published_file`, trung vị và Q1-Q3 của từng đối chiếu | `aadb445168a6a8ab8dd7a20122e8499333ff33be615bf9c9d3a77dc1549bc19b` |
| [Hình 4.5. Tăng trưởng tệp](figures/phase5-5d/tang-truong-pdf.png) | `sessions[].output_sizes`, sức chứa nhân hai cho ô Contents, tổng phần khung và mức tăng của PDF | `a89c84a8111fc6e20746cda392e6c766db82abb329734d7ba0a746135ac931ff` |

Mỗi nhóm độ trễ có n = 90. Mỗi ô kích thước trong các hình dùng thang tuyến tính riêng để đọc chênh lệch giữa phương pháp và môi trường ở cùng cỡ PDF. Dấu thể hiện trung vị, còn hai đầu đoạn là Q1 và Q3. P95 và số liệu đầy đủ có trong phụ lục. Hai biểu đồ trung vị 10 MiB theo phiên từ Phase 5.5C được dùng lại để minh họa biến thiên. [Ký theo phiên](figures/phase5-5c/phase5-5c-10mib-sign.png) · [Xác minh theo phiên](figures/phase5-5c/phase5-5c-10mib-verify.png)

- Hybrid có trung vị thời gian cao hơn cả hai bộ so sánh ở 18 tổ hợp môi trường, cỡ PDF và thao tác. Ví dụ, với 10 MiB trên Windows, hiệu ghép cặp ký và xuất là 90,438 ms so với Ed25519 và 129,408 ms so với Falcon-512. Tỷ số được tính trên từng cặp, lần lượt có trung vị 1,559 và 2,049. [Bảng ghép cặp](tables/phase5-5d-pdf-vi.md#so-sánh-ghép-cặp)
- Độ trễ Ed25519 trên macOS Intel ở 10 MiB cao trong cả ba phiên, lặp lại hiện tượng đã ghi ở pilot. CPU, image, kernel và hệ tệp thuộc cấu hình quan sát. Phân tích nguyên nhân cần phép đo công đoạn có kiểm soát. [Thực nghiệm và điều kiện](thesis-chapter-experiments-vi.md#47-kết-quả-trên-ba-môi-trường)
- Chi phí tăng của tệp ký lai là 4 626 byte. Chênh lệch so với tệp đơn lớp lần lượt là thêm 4 232 byte và 394 byte. Khi đọc khuôn tạo placeholder từ nguồn đo, kích thước từng phần theo thứ tự là dấu mở, ByteRange, SigLength, cú pháp Contents, ô hex và dấu đóng. Ed25519 có 23, 59, 22, 13, 256, 21 byte. Falcon có 22, 59, 22, 13, 4 096, 20 byte. Tổng 394 và 4 232 byte khớp từng dòng PDF đã đo. Giá trị này phản ánh mã hóa và sức chứa của định dạng thử nghiệm. [Khuôn tạo vùng chứa](../utils.py#L223) · [Giải thích lưu trữ](thesis-chapter-discussion-vi.md#53-chi-phí-lưu-trữ)
- Chín ô C8 phản ánh xác minh tệp thử và khóa công khai trong cùng lõi trên ba môi trường. Bằng chứng main đo chi phí và kiểm tra C0-C7. Tính duy nhất của biểu diễn Falcon, chứng minh an toàn của tổ hợp, danh tính và thời gian ký, chuẩn trao đổi và tương thích GUI hoặc trình đọc PDF vẫn cần bằng chứng riêng. [Phạm vi an toàn và khả năng sử dụng](thesis-chapter-discussion-vi.md#54-giới-hạn-của-bằng-chứng-mật-mã-và-sử-dụng-thực-tế)

## Tái tạo và xác nhận

Chạy từ gốc kho mã bằng Windows PowerShell. Tạo thư mục đầu ra mới bên ngoài bằng chứng Phase 5.5C. Lệnh `summarize` ở báo cáo 5.5C tái tạo bản tổng hợp từ đúng chín CSV trước bước dẫn xuất dưới đây. Script tạo bảng kiểm hai SHA-256 nguồn và ánh xạ đúng ba phiên mỗi môi trường. [Tái tính bằng công cụ đo đã chốt](phase5-5c-cross-platform-main.md#lưu-trữ-và-tái-tính)

```powershell
$campaign = Join-Path $env:LOCALAPPDATA 'HybridSignResearch\phase5-5c\campaign-81d76271'
$parent = Join-Path $env:LOCALAPPDATA 'HybridSignResearch\phase5-5d'
New-Item -ItemType Directory -Force -Path $parent | Out-Null
$out = Join-Path $parent ('repro-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $out | Out-Null
$tables = Join-Path $out 'tables'
$figures = Join-Path $out 'figures'
New-Item -ItemType Directory -Path $figures | Out-Null

.\.venv\Scripts\python.exe -B research/orchestration/phase55d_tables.py --campaign $campaign --output $tables
if ($LASTEXITCODE -ne 0) { throw 'Table generation failed.' }
.\research\orchestration\phase55d_charts.ps1 -DataPath (Join-Path $tables 'figure-data.json') -OutputDirectory $figures
```

- Phép tính độc lập từ 7 560 dòng xác nhận 336 chuỗi thời gian và 144 nhóm ghép cặp của bản tổng hợp đầy đủ, gồm Q1, Q3, IQR, trung bình, SD mẫu và P95 Type 7. Kiểm tra riêng phần công bố xác nhận từng ô trong 54 nhóm PDF gộp, 162 trung vị từng phiên và 36 nhóm ghép cặp theo thao tác và phương pháp đối chiếu. Đã đối chiếu đủ 2 430 dòng kích thước PDF, 93 bản ghi đầu vào biểu đồ và các số liệu trích trong bản thảo. Cả năm PNG 1 920 × 920 pixel và tệp bảng tái tạo khớp SHA-256 trên cùng máy dựng. Đã soát 5 tài liệu Markdown, kiểm tra đường dẫn nội bộ, tiêu đề, cấu trúc bảng và dấu gạch ASCII. Kiểm tra thử khi thiếu bằng chứng trả NOT PERFORMED trước khi tạo đầu ra.
- Đã xác nhận SHA-256 của 37 tệp nguồn và nghiên cứu từ baseline, hai bộ chữ ký mẫu đóng băng, PDF mẫu công khai, 15 tệp benchmark gốc, 138 tệp trong payload portable và ba hiện vật phát hành. Đối chiếu Git xác nhận tập mã đo `research/benchmarks/p55` và workflow cũ vẫn khớp commit nguồn cố định. [Baseline kiểm băm](phase5-5a-baseline.json)
- Danh mục IEEE dùng RFC, đặc tả chính thức của tác giả, chuẩn của NIST và ETSI, và bài báo gốc Hyndman-Fan. Các mục này hỗ trợ đúng thuật ngữ, phạm vi mật mã và công thức phân vị đã dùng. Mẫu trình bày luận văn, báo cáo thực tập và tài liệu chấm điểm dùng cho biên tập. [Tài liệu tham khảo](thesis-word-integration-vi.md#tài-liệu-tham-khảo-dùng-cho-các-đoạn-cập-nhật)

## Đưa vào bản Word hiện hành

**Đối chiếu bố cục trong Word - NOT PERFORMED.** Bản Word mới nhất chưa có trong kho mã đã kiểm tra. Các đoạn thay thế được lưu riêng và định vị theo chương, để áp dụng vào bản Word của người viết. [Đoạn chèn cho Word](thesis-word-integration-vi.md)

1. Ghép tóm tắt, mục tiêu và câu hỏi nghiên cứu vào bản Word. Giữ bố cục năm chương và các mục lý thuyết đã duyệt ở Chương 2. Đối chiếu tên phiên bản đặc tả với tên binding ở Chương 3.
2. Đặt kết quả chính Phase 5.5C tại Chương 4. Chèn hình PNG và bảng so sánh theo thao tác, rồi đặt bảng thống kê đầy đủ ở phụ lục. Đặt nội dung Phase 5.2 trong phần hỗ trợ hoặc phụ lục riêng, kèm nguồn và ranh giới đo của nó.
3. Ghép bàn luận về chi phí, phạm vi C8 và các giới hạn vào Chương 5. Áp dụng kiểu tiêu đề, bảng, hình và căn lề theo mẫu Đại học Thăng Long của bản Word. Đánh số lại hình, bảng và trích dẫn IEEE theo thứ tự xuất hiện, rồi cập nhật mục lục và kiểm tra các trang sau dàn.

## Danh mục tệp thay đổi

| Tệp | Nội dung |
| --- | --- |
| `docs/thesis-chapter-experiments-vi.md` | Tích hợp Phase 5.5C vào Chương 4 và giữ bảng, hình và dữ liệu bổ trợ của Phase 5.2 |
| `docs/thesis-chapter-discussion-vi.md` | Chương 5 về động cơ, hiệu năng, dung lượng, tin cậy và giới hạn |
| `docs/thesis-word-integration-vi.md` | Đoạn thay thế cho tóm tắt, Chương 1, 3, 5 và danh mục nguồn IEEE |
| `docs/tables/phase5-5d-pdf-vi.md` | Toàn bộ bảng PDF và tương phản ghép cặp |
| `docs/phase5-5d-thesis-integration.md` | Truy vết, kết quả kiểm tra, giới hạn và hướng dẫn đưa vào Word |
| `docs/figures/phase5-5d/pdf-ky-va-xuat.png` | So sánh ký và xuất |
| `docs/figures/phase5-5d/pdf-xac-minh.png` | So sánh xác minh |
| `docs/figures/phase5-5d/chenh-lech-ky-va-xuat.png` | Hiệu ghép cặp khi ký và xuất |
| `docs/figures/phase5-5d/chenh-lech-xac-minh.png` | Hiệu ghép cặp khi xác minh |
| `docs/figures/phase5-5d/tang-truong-pdf.png` | Phân rã mức tăng theo ô Contents và phần khung |
| `research/orchestration/phase55d_tables.py` | Tạo bảng và dữ liệu hình từ bản tổng hợp đã xác nhận |
| `research/orchestration/phase55d_charts.ps1` | Dựng năm biểu đồ bằng thư viện biểu đồ .NET |
