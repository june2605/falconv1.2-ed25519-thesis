# Phase 5.3 — Chỉ mục bằng chứng và hướng dẫn tái tạo

Hai chương tiếng Việt trình bày phương pháp, kết quả và bàn luận từ chiến dịch Phase 5.2B. Các chương được đánh dấu là bản thảo tạm thời. Tài liệu `phase5-1-thesis-traceability.md` cung cấp bố cục đề xuất nội bộ. Chưa tìm thấy đề cương được duyệt, mẫu luận văn, rubric, quy cách trích dẫn do trường quy định hoặc nhận xét của người hướng dẫn trong các cây dự án đã kiểm tra. Khi có các tài liệu đó, cần đối chiếu thứ tự chương, định dạng bảng, quy chuẩn tài liệu tham khảo và yêu cầu lưu dữ liệu. [Chương thực nghiệm](thesis-chapter-experiments-vi.md) · [Chương bàn luận](thesis-chapter-discussion-vi.md) · [Bố cục đề xuất](phase5-1-thesis-traceability.md#proposed-chapter-structure)

## 1. Nguồn và định danh

Kho công việc `D:\Final_Thesis_GitHub` bắt đầu với cây làm việc sạch trên `thesis/ui-demo` tại `d93b0beacc6511ad0c3bc551a789a36c312ccada`. Commit này lưu phân tích Phase 5.2B. Mọi thực nghiệm đọc trong Phase 5.3 ghi commit phần mềm **`3ebfe31abb080a0355ac512d6190910d33e98a63`**. Bộ đo chạy thực tế là `research/benchmarks/phase5_2a.py` v1.0.0 với SHA-256 `29a697ca3d4063773e3be9856a9a3e70fba7d4671e37c89613d0fc775a579410`. SHA-256 của sáu mô-đun thực thi trong metadata của cả năm phiên khớp với tệp hiện tại. Trong Phase 5.2B, các tệp nghiên cứu mới khiến metadata báo cây làm việc có thay đổi. So sánh với commit thực nghiệm cho thấy các mô-đun sản xuất liên quan và bộ đo có nội dung giống nhau. [Hồ sơ gốc Phase 5.2B](phase5-2b-experimental-results.md#source-and-preserved-pilot)

Thư mục gốc của chiến dịch là `%LOCALAPPDATA%\HybridSignResearch\phase5-2b\campaign-l54v36l5`. Danh mục SHA-256 chính có **59 mục** và SHA-256 của chính danh mục là `f96d025145a113009eb3224fa9129b1985dd1fb3b13cee983a49a424e1679da3`. Tất cả 59 mục khớp, gồm các tệp đầu vào công khai, `raw.csv`, metadata, bản tóm tắt và hình Phase 5.2B. Tám tệp trong bản phân tích tạo lại của Phase 5.2B cũng khớp bản được liệt kê. Tám hiện vật Phase 5.2A tại vị trí Temp gốc và tám bản sao bền vững đều khớp danh mục. [Chiến dịch](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5>) · [Danh mục 59 mục](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/analysis-l3zob63s/checksums.sha256>) · [Danh mục bản chạy thăm dò](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/phase5-2a-preserved/archive-checksums.json>)

| Phiên | PID Python | Mã thử nghiệm | Bắt đầu–kết thúc (UTC, 19/11/2026) | Thời gian tiến trình (s) |
| --- | ---: | --- | --- | ---: |
| `matched-01` | 23808 | `947a29d1-20d5-4bec-ac88-c4b6246078bc` | 10:25:02.818–10:25:47.316 | 44,497 |
| `matched-02` | 11940 | `557b4525-a5c4-45bd-bc65-13702c0cc449` | 10:25:52.129–10:26:35.526 | 43,396 |
| `matched-03` | 24448 | `891a1e44-20d4-496e-bb42-c5bf4d804457` | 10:26:40.431–10:27:25.460 | 45,029 |
| `optional-40-feasibility` | 18908 | `a582ff1a-6aea-438d-930c-7f7ff110e8f4` | 10:27:32.871–10:27:43.843 | 10,973 |
| `optional-40-measured` | 24084 | `15131c1f-2d5d-4b31-abde-8b23576e3e38` | 10:29:26.974–10:31:56.063 | 149,089 |

| Phiên | Dữ liệu | SHA-256 của raw.csv | SHA-256 của experiment.json |
| --- | --- | --- | --- |
| `matched-01` | [raw.csv](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/matched-01/hybridsign-phase5-2a-ujk7cemj/raw.csv>) | `2f593201c15bbec63dfa36645fdfd77af284e21614d0fe7230d4ceb98f406c15` | `81a7d5b4330808598fba2538988a0108e5a695075aa050270b674a19d77db807` |
| `matched-02` | [raw.csv](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/matched-02/hybridsign-phase5-2a-9eglstai/raw.csv>) | `a453929eb65a6bbc3651c413ca6c05de5d375b6c8cfbf6df1e79282677a35d8a` | `4eb02c9ec6d4123ef879f042375d0b70dd2022b50bec6b589843fa2e05ec3a70` |
| `matched-03` | [raw.csv](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/matched-03/hybridsign-phase5-2a-hr6dfrst/raw.csv>) | `5a660fed8ca726a54ab99d453d25d3e24cf241e84869f0666850595da52d8418` | `deb0c3e5dafb99f146455580380d493ef73299e7524a7867ad771e2878f47a35` |
| `optional-40-feasibility` | [raw.csv](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-40-feasibility/hybridsign-phase5-2a-mg3q8ba9/raw.csv>) | `a5d8ba79de58f270d21d70edda74cca519854195ec1ad424aba87e714388cad9` | `8b66c54d19c7b96da053937924fc59cd98af4c883768549a9bceb5e3014a7a3f` |
| `optional-40-measured` | [raw.csv](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-40-measured/hybridsign-phase5-2a-uyfh4kd9/raw.csv>) | `2baf2cb948f11ef1cdeec9ed1d1077865f0fa21cae699a1aaf04be596b3df3dc` | `03718a7db123bc179d2ae384f21403cfce66072a14dde75bf3833344b293bec2` |

Các tệp `experiment.json` và `summary.json` ở cùng thư mục với CSV. Thư mục cha của mỗi phiên có `session.json` và `process.log`. Metadata ghi đầu vào, giờ UTC, PID Python và PID trình khởi chạy Windows, điều kiện tài nguyên, bộ đếm thời gian, thông số thu gom rác, phần mềm, mã băm của các mô-đun, và biến thể Falcon. Hai tệp riêng ghi khảo sát khả thi và quyết định tiếp tục ở ngưỡng 600 s. Chế độ và kích thước được xác nhận bằng lịch chạy và mã băm đầu vào, gồm thông điệp 64 và 1 024 byte, mẫu 742 byte, PDF 1 MiB, 10 MiB và PDF bổ sung 40 MiB. [Metadata khảo sát](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-40-preflight.json>) · [Metadata phiên bổ sung](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/campaign-l54v36l5/optional-extension.json>) · [Bảng mã băm đầu vào](phase5-2b-experimental-results.md#conditions-and-per-process-counts)

## 2. Kiểm tra số đếm và kết quả

| Phạm vi | Khối khởi động / đo | Lượt chuẩn bị thông điệp khởi động / đo | Chữ ký thuật toán khởi động / đo | PDF đầu ra khởi động / đo | Tổng lượt khởi động / đo | Dòng CSV khởi động / đo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mỗi phiên chính | 3 / 30 | 6 / 60 | 12 / 120 | 18 / 180 | 36 / 360 | 591 / 5 910 |
| Ba phiên chính cộng lại | 9 / 90 | 18 / 180 | 36 / 360 | 54 / 540 | 108 / 1 080 | 1 773 / 17 730 |
| Khảo sát khả thi 40 MiB | 1 / 1 | 2 / 2 | 4 / 4 | 4 / 4 | 10 / 10 | 140 / 140 |
| Phiên bổ sung 40 MiB | 3 / 30 | 6 / 60 | 12 / 120 | 12 / 120 | 30 / 300 | 420 / 4 200 |
| Toàn bộ chiến dịch | 13 / 121 | 26 / 242 | 52 / 484 | 70 / 664 | 148 / 1 390 | 2 333 / 22 070 |

Lượt chuẩn bị thông điệp chỉ ghi thời gian chuẩn bị. Lượt thuật toán tạo một chữ ký rời và kiểm tra nó. Lượt PDF tạo một kết quả gồm một cặp chữ ký và ghi nhiều chỉ số. Vì vậy 734 PDF đầu ra là 734 cặp, tương ứng 1 468 chữ ký thành phần trong các PDF. Con số 536 chữ ký mức thuật toán thuộc nhóm thử riêng. Hai phiên liên quan 40 MiB chạy thêm mẫu 742 byte và các điều kiện thuật toán theo lịch bộ đo. Riêng PDF 40 MiB có 2 lượt khởi động và 2 lượt đo trong khảo sát, 6 lượt khởi động và 60 lượt đo trong phiên bổ sung, cộng cả hai chế độ. Bảng thời gian toàn lời gọi PDF 40 MiB dùng 30 quan sát `unprofiled` cho mỗi thao tác. Phân tích từng bước dùng 30 quan sát `profiled` riêng. [Định nghĩa lượt và phạm vi](thesis-chapter-experiments-vi.md#x2-thiết-kế-thực-nghiệm) · [Mã lập lịch](../research/benchmarks/phase5_2a.py#L348)

Tất cả điều kiện có đủ dòng, đúng thứ tự và trạng thái `ok`. Không có lượt lỗi hoặc bị loại. `record_trial()` chỉ ghi trạng thái này sau khi các kiểm tra của lượt hoàn tất. Vì vậy bằng chứng về tính đúng thuộc về bộ đo đã chạy. Nó cho thấy các phép xác minh dương dùng khóa phù hợp thành công, các sửa đổi thông điệp của lượt thuật toán bị từ chối, và các phép thử sửa nội dung vùng ký hoặc đổi cặp khóa ở lượt PDF bị từ chối. Các phần đo chức năng và tài liệu Phase 5.1A được dùng để đánh giá phạm vi của bằng chứng. [Ghi trạng thái thử](../research/benchmarks/phase5_2a.py#L142) · [Kiểm toán toàn vẹn](phase5-1a-signature-integrity-audit.md)

## 3. Truy vết bảng và biểu đồ

| Nội dung | Nguồn tái tạo |
| --- | --- |
| Bảng X.1–X.2, X.10 | Metadata, lịch, các cột `phase`, `mode`, `workload`, `repetition`, `order_in_block`, `observed_bytes` của CSV |
| Bảng X.3–X.5 | `primitive`, các thao tác `sign` và `verify`, đơn vị ns từ ba phiên chính |
| Bảng X.6–X.8 | `unprofiled`, các thao tác `sign_and_publish` và `verify_published_file`. Bảng X.8 dùng riêng `optional-40-measured` |
| Bảng X.9 | `profiled`, các điểm đo cấp bước và toàn lời gọi, theo nhóm kích thước và phiên |
| Bảng Y.1 | Độ dài mã hóa của các hằng số trong `utils.py` và hai dung lượng mặc định |
| Bảng Y.2 | Mười CSV và năm PDF gốc, xác minh theo `docs/phase1-baseline.json` |
| Hình X.1–X.4 | 16 nhóm, mỗi nhóm gồm trung vị, Q1, Q3 và các trung vị theo phiên phù hợp |
| Hình X.5 | 270 giá trị ký và xuất đã đo, xếp theo thứ hạng trong từng phiên và kích thước chính |

Mọi trục thời gian trên hình có đơn vị ms. Hình X.1 dùng thang logarit. Hình X.5 dùng thang tuyến tính riêng cho mỗi ô và thể hiện thứ hạng quan sát. Ba phiên chính giữ nguyên mã phiên trong chú giải để truy ngược về CSV. Hình X.3 và X.4 đánh dấu rõ kích thước bổ sung. Tệp PNG 1 800 × 1 050 pixel dùng nhãn tiếng Việt. SHA-256 dưới đây áp dụng cho các tệp được đính kèm trong chương.

| Hình | Tệp | SHA-256 |
| --- | --- | --- |
| X.1 | [primitive-sign.png](figures/phase5-3/primitive-sign.png) | `c5c69044c5d32eadff2d0834470ad183216d3b462a0ee7beac6b376c454bedb1` |
| X.2 | [primitive-verify.png](figures/phase5-3/primitive-verify.png) | `8cdefab2a47877b4f7402f3a223dc1487f028f30e79c53cf9851d6a195e1ea08` |
| X.3 | [hybrid-sign.png](figures/phase5-3/hybrid-sign.png) | `3f6662b4bb9186e76c2524f34cf0cd068a110989765037859d34071a1283499c` |
| X.4 | [hybrid-verify.png](figures/phase5-3/hybrid-verify.png) | `fc78e379a09030f9d780445c86a9accf2674bfc618bddb5f55216f7ad3ce750e` |
| X.5 | [hybrid-sign-session-variability.png](figures/phase5-3/hybrid-sign-session-variability.png) | `0fb79dacfb42d114f6766ba6ea1e1cfb79d41ff9e4485be0f22252ff5576f7cb` |

Khảo sát khả thi và bản chạy thăm dò nằm ngoài thống kê chính. Dữ liệu lịch sử được đối chiếu theo phương pháp của nghiên cứu gốc và giữ riêng. [Tài liệu lịch sử và phạm vi đo](phase5-1-experiment-gap-analysis.md) · [Phương pháp và kết quả chạy thăm dò](phase5-2a-benchmark-methodology.md) · [Báo cáo chạy thăm dò](phase5-2a-pilot-analysis.md)

## 4. Tái tạo trên Windows

Từ thư mục gốc của kho mã, dùng Python 3.11 trong `.venv` và Windows PowerShell có .NET WinForms Charting. Thay đường dẫn chiến dịch, thư mục lưu trữ lịch sử nếu cần. Lệnh đầu chỉ đọc năm phiên, kiểm tra danh mục và xuất hai tệp dẫn xuất vào thư mục mới. Lệnh sau đọc `plot-data.json` để dựng năm hình. `tables.json` chứa chín bảng sinh tự động. Cả hai lệnh dùng tạo tệp độc quyền ở đích. [Tính thống kê](../research/benchmarks/phase5_3_thesis.py) · [Dựng hình](../research/benchmarks/phase5_3_charts.ps1)

```powershell
$research = Join-Path $env:LOCALAPPDATA 'HybridSignResearch\phase5-2b'
$campaign = Join-Path $research 'campaign-l54v36l5'
$output = Join-Path $research ('phase5-3-' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
.\.venv\Scripts\python.exe -B -m research.benchmarks.phase5_3_thesis --campaign $campaign --historical-root 'D:\Final_Thesis' --output $output
if ($LASTEXITCODE -ne 0) { throw 'Phase 5.3 analysis failed' }
.\research\benchmarks\phase5_3_charts.ps1 -AnalysisDirectory $output
Get-ChildItem -File -LiteralPath $output | Get-FileHash -Algorithm SHA256
```

Hai lần tái tạo sau khi chốt mã cho ra hai tệp JSON và năm PNG giống từng byte trên máy hiện tại. Khác phiên bản .NET, phông chữ hoặc môi trường hiển thị có thể thay đổi PNG dù dữ liệu đưa vào đồ thị giữ nguyên. Kiểm tra độc lập bằng NumPy đọc riêng CSV, đối chiếu 58 dòng thống kê độ trễ, 16 tỷ số, 52 ô thống kê cấp bước và 362 giá trị đồ thị. Chín bảng sinh tự động xuất hiện nguyên trạng trong hai chương. Các giá trị trình bày được làm tròn từ đơn vị gốc. Biểu đồ được mở để kiểm tra kích thước, chữ tiếng Việt, đơn vị, dấu phiên bổ sung và cách thể hiện đuôi phân bố. [Bảng dẫn xuất](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/phase5-3-75ae8e52/tables.json>) · [Các giá trị đưa vào đồ thị](<C:/Users/Khanh Duy/AppData/Local/HybridSignResearch/phase5-2b/phase5-3-75ae8e52/plot-data.json>)

## 5. Kiểm tra hồi quy, toàn vẹn và giới hạn

Chạy lại nhóm kiểm tra trọng điểm đã dùng cho Phase 5.2B, gồm kiểm tra ký và xác minh, vùng chứa, ranh giới toàn vẹn, bộ đo thăm dò và phân tích phiên. Kết quả **220 passed trong 6,18 s**, 0 lỗi, 0 bỏ qua, 0 xfail, 0 xpass. Kiểm thử sản phẩm đầy đủ và GUI nằm ngoài lượt chạy trọng điểm này. Không chạy lại chiến dịch đo để sinh thời gian mới. [Danh sách kiểm tra trọng điểm](phase5-1a-signature-integrity-audit.md#raw-test-counts) · [Kiểm tra bộ đo](../tests/test_research_benchmark_pilot.py) · [Kiểm tra phiên](../tests/test_research_benchmark_sessions.py)

Đối chiếu 15 băm lịch sử trong `D:\Final_Thesis`, mã băm mẫu công khai, 138 tệp của bộ portable, tệp ZIP portable và bộ cài đã thẩm định đều khớp. Các thay đổi thuộc tài liệu, hình và công cụ nghiên cứu. Giữ nguyên tệp vận hành, bản phát hành desktop, định dạng chữ ký và dữ liệu nguồn. Mục đích của đối chiếu SHA-256 ở đây là phát hiện thay đổi so với bản lưu của nghiên cứu. Nó không xác nhận danh tính người ký, tính chuẩn hóa của biểu diễn Falcon, chứng nhận FIPS 206 hoặc sự phù hợp CMS/PAdES. Giới hạn về một máy, thiếu dữ liệu lịch sử, độ biến thiên đuôi và giả thuyết chưa kiểm tra được giữ trong chương bàn luận. [Giới hạn đã ghi](thesis-chapter-discussion-vi.md#y6-giới-hạn-của-bằng-chứng-mật-mã-và-sử-dụng-thực-tế) · [Danh mục bản phát hành](../frontend/qa/phase4c2a/release-manifest.json)

| Tệp tạo ở Phase 5.3 | Vai trò |
| --- | --- |
| [docs/thesis-chapter-experiments-vi.md](thesis-chapter-experiments-vi.md) | Chương thực nghiệm tạm thời, 10 bảng và 5 hình |
| [docs/thesis-chapter-discussion-vi.md](thesis-chapter-discussion-vi.md) | Chương bàn luận tạm thời, 2 bảng và giới hạn kết luận |
| [docs/phase5-3-evidence-index.md](phase5-3-evidence-index.md) | Chỉ mục bằng chứng, kiểm tra và lệnh tái tạo |
| [research/benchmarks/phase5_3_thesis.py](../research/benchmarks/phase5_3_thesis.py) | Tái tính thống kê và tạo dữ liệu đồ thị từ CSV đã lưu |
| [research/benchmarks/phase5_3_charts.ps1](../research/benchmarks/phase5_3_charts.ps1) | Dựng đồ thị tiếng Việt |
| [docs/figures/phase5-3/primitive-sign.png](figures/phase5-3/primitive-sign.png) | So sánh ký ở mức thuật toán |
| [docs/figures/phase5-3/primitive-verify.png](figures/phase5-3/primitive-verify.png) | So sánh xác minh ở mức thuật toán |
| [docs/figures/phase5-3/hybrid-sign.png](figures/phase5-3/hybrid-sign.png) | Ký và xuất PDF theo kích thước |
| [docs/figures/phase5-3/hybrid-verify.png](figures/phase5-3/hybrid-verify.png) | Xác minh độc lập PDF theo kích thước |
| [docs/figures/phase5-3/hybrid-sign-session-variability.png](figures/phase5-3/hybrid-sign-session-variability.png) | Biến thiên ký và xuất PDF theo phiên |
