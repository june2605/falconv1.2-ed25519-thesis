# Phase 5.5B - Pilot cloud ba hệ điều hành và xác minh C8

## Công bố và phạm vi chạy

- Commit nghiên cứu `613a46d06930ffd9224afa557fa90992e3a56a2a` trên `thesis/ui-demo` chứa đúng 14 tệp đã rà soát. Không có mã ứng dụng, dữ liệu chiến dịch, khóa bí mật hoặc bản phát hành trong thay đổi. Các đường dẫn thư mục cá nhân được thay bằng đường dẫn tương đối trong báo cáo Phase 5.5A.
- Đăng ký trên worktree riêng từ `origin/main` tại `c4c968bb91fc2bdb55af9e184d07a02cfbc4d471`. Commit đăng ký `70bef3125b87f4e7af09df031a128bb4fffde609` thêm đúng một tệp YAML. PR #1 được kiểm tra chỉ có tệp đó và hợp nhất thành `00e8efb55ef58c7a24c0b3c6789667258c94924b`. Blob workflow khớp giữa hai nhánh. [Pull request đăng ký](https://github.com/june2605/falconv1.2-ed25519-thesis/pull/1)
- Workflow ID `424773343` chỉ nhận `workflow_dispatch`. Hai mode `pilot` và `compat` có đúng ba job mỗi mode, chạy tuần tự với `max-parallel: 1` và giữ bằng chứng từ các job riêng lẻ. Bước kiểm tra nằm trong từng job. Mỗi job xác nhận branch tip đã duyệt và checkout bằng đúng SHA, rồi ghi riêng SHA của workflow và của mã nghiên cứu. C8 dùng đúng run và attempt sản xuất bundle và ghi ô thiếu là NOT RUN. Chế độ main chưa đăng ký trong workflow này. [Workflow đã đăng ký](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/workflows/phase5-5a-research.yml)
- Kho được xác nhận public ngay trước cả hai lượt dispatch. Dùng runner GitHub chuẩn x64 `windows-2022`, `ubuntu-24.04` và `macos-15-intel`. Phần compute của runner chuẩn public theo chính sách GitHub hiện hành là miễn phí. Không thay đổi cấu hình thanh toán. [Runner hỗ trợ](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) · [Chính sách tính phí](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

Bằng chứng Phase 5.5A tại chỗ được kiểm băm lại đầy đủ. CSV có 3 khối khởi động, 6 khối đo, 45 lượt khởi động, 90 lượt đo, 168 dòng thời gian đo và 81 PDF đầu ra, trong đó 27 khởi động và 54 đo. Không có dòng lỗi hoặc bị loại. Với 14 tệp được băm trong metadata nguồn cục bộ, 8 tệp khớp byte với blob đã công bố, 5 tệp chỉ khác chuẩn hóa CRLF/LF và `ci.py` thay đổi điều phối. Thao tác đo, lịch, bộ tạo đầu vào và profile giữ nguyên. Không lặp lại pilot cục bộ. 36 lượt pytest nghiên cứu và actionlint đã đạt trước công bố. Con số 32 lượt riêng của Phase 5.5A nằm trong 564 lượt trọng điểm của chính phase đó. [Báo cáo địa phương](phase5-5a-research-comparison-readiness.md)

## Pilot cloud

Run `44701642390`, attempt 1, kết luận `success`, dispatch từ `main` với `mode=pilot` và `source_commit=613a46d06930ffd9224afa557fa90992e3a56a2a`. Mỗi job ghi một phiên Python mới. Đã đọc log từng job, đối chiếu checkout sạch và băm mã thực thi với blob Git của SHA đã duyệt. Giao thức `hybridsign-5.5a-v1` có SHA-256 tệp `protocol.py` là `625aee7677dd8178f8cb1d6b52578f284a9354e1c29deff10f904f0df357112b`. SHA-256 tập nguồn là `d2c84e532ebba4b062d25e8f078238d7736b51fc545e3a27aa0b7311d8f4de91`. [Run pilot](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44701642390)

| Job | PID | Thời gian 20/11/2026 (giờ Bangkok) | Tổng job (s) | Setup (s) | Cài wheel (s) | Test và smoke (s) | Đo và đối chứng (s) |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| [CI-WIN](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44701642390/job/136171227790) | `7144` | 15:19:47-15:21:20 | 93 | 18,42 | 5,49 | 33,36 | 23,85 |
| [CI-LINUX](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44701642390/job/136171228135) | `2559` | 15:21:22-15:22:30 | 68 | 21,69 | 4,44 | 8,24 | 17,24 |
| [CI-MAC](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44701642390/job/136171228186) | `3076` | 15:22:33-15:24:45 | 132 | 18,02 | 7,81 | 13,77 | 76,97 |

Ba job đo chạy tuần tự với tổng thời gian job 293 s. Tổng job lấy từ Jobs API và gồm cả thời gian upload. Windows đạt 568 pytest. Linux và macOS mỗi môi trường đạt 566 và có 2 skip từ hai tham số của kiểm thử chia sẻ handle riêng cho Windows. Cả ba job ghi 19/19 smoke. Từ CSV tải về, mỗi môi trường có 45 lượt và 84 dòng thời gian khởi động, 90 lượt và 168 dòng đo. Tổng cộng **135 lượt khởi động, 270 lượt đo và 504 dòng đo**, gồm 162 PDF đầu ra trong phần đo và 81 PDF trong phần khởi động. Không có lượt lỗi, dở dang hoặc bị loại. Đối chiếu đủ 306 bản ghi kiểm soát mỗi phiên và kết quả C0-C7. Các phép từ chối cấu trúc giữ trạng thái NOT EVALUATED ở hai lớp. [Giao thức và đối chứng](phase5-5a-research-protocol.md)

### Môi trường và thư viện

Các nhãn và thông số dưới đây là thông tin thấy từ runner. `physical_host_id` và `physical_parent_id` đều `unknown`. Mỗi môi trường ghi run/job/attempt, PID và ID phiên logic riêng. RAM khả dụng và dung lượng đĩa lấy ở tiền kiểm.

| Môi trường | Nhãn / image version | OS / build hoặc kernel | CPU quan sát | Lõi khai báo / logic | RAM tổng / còn (GiB) | Hệ tệp / đĩa còn (GiB) |
| --- | --- | --- | --- | ---: | ---: | --- |
| CI-WIN | `windows-2022` / `20261116.370.1` | Windows Server 2022 Datacenter, 10.0.20348.5870 | AMD EPYC 7763 64-Core Processor | 2 / 4 | 15,99 / 13,53 | NTFS / 146,86 |
| CI-LINUX | `ubuntu-24.04` / `20261111.127.1` | Ubuntu 24.04.5 LTS, 7.0.0-1014-aws | Intel Xeon 6975P-C | 2 / 4 | 15,33 / 14,24 | ext4 / 87,44 |
| CI-MAC | `macos-15-intel` / `20260824.0482.1` | macOS 15.7.9, 24G830 | Intel Core i7-8700B CPU @ 3.20GHz | 4 / 4 | 14,00 / 9,62 | apfs / 107,61 |

Cả ba dùng CPython 3.11.9 x64, PyNaCl 1.6.2, pqcrypto 0.3.4 và cffi 2.0.0. Hồ sơ wheel `p55a-cp3119-x64-v1` có SHA-256 `f3389d41a7efaa590e3619f46eb9a4529ededb6a45f10ed7e51ba6d26cebbbbb`. Đối chiếu băm wheel và mô-đun nạp cho cả Falcon, PyNaCl và cffi. Bảng dưới liệt kê Falcon, dùng các bản PQClean clean theo truy nguyên được ghi trong profile. Mỗi job giữ đầy đủ các băm còn lại trong `session.json`. [Hồ sơ phụ thuộc](../research/benchmarks/p55/wheels.json)

| Môi trường | Wheel Falcon | SHA-256 wheel | SHA-256 mô-đun thực nạp |
| --- | --- | --- | --- |
| CI-WIN | `pqcrypto-0.3.4-cp311-cp311-win_amd64.whl` | `36ec272e32d24cd137fd937bf218d0c86f4b0d5d17ed26828708e1a71b667380` | `ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237` |
| CI-LINUX | `pqcrypto-0.3.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | `7b48f4048f22b4dcacb012dd46b21df01f7962ef01a0c3032166cca3b9dab508` | `50977ae2d63515605559fc8aae03c4967e401e69946c8bdb1f62dc88122e2010` |
| CI-MAC | `pqcrypto-0.3.4-cp311-cp311-macosx_10_9_x86_64.whl` | `0274de7296be38ff9e1f5474953240eb876f45cd560ef5c51140144638b261ae` | `e9310f05b87440bf4052fbeddcfddeaa953f6962c0e34beeea19dc3b7755ffeb` |

### Độ trễ PDF đã tái tính

Bảng dùng **trung vị (IQR)**, đơn vị ms, từ CSV tải về, chỉ gồm khối đo. Thời gian ký và xuất gồm xác minh ứng viên và công bố. Cột xác minh đo lời gọi độc lập sau xuất. Mỗi điều kiện có sáu quan sát.

| Môi trường | PDF | Phương pháp | n | Ký và xuất (ms) | Xác minh (ms) | Tăng trưởng (byte) |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| CI-WIN | 742 byte | Ed25519 | 6 | 3,407 (0,275) | 0,242 (0,005) | 394 |
| CI-WIN | 742 byte | Falcon-512 | 6 | 13,562 (0,282) | 0,225 (0,001) | 4232 |
| CI-WIN | 742 byte | Hybrid | 6 | 14,462 (0,233) | 0,358 (0,003) | 4626 |
| CI-WIN | 1 MiB | Ed25519 | 6 | 20,227 (0,143) | 5,443 (0,025) | 394 |
| CI-WIN | 1 MiB | Falcon-512 | 6 | 24,903 (0,167) | 4,308 (0,018) | 4232 |
| CI-WIN | 1 MiB | Hybrid | 6 | 39,826 (0,821) | 8,607 (0,067) | 4626 |
| CI-WIN | 10 MiB | Ed25519 | 6 | 164,718 (1,528) | 50,785 (0,644) | 394 |
| CI-WIN | 10 MiB | Falcon-512 | 6 | 124,836 (0,956) | 40,676 (0,137) | 4232 |
| CI-WIN | 10 MiB | Hybrid | 6 | 256,794 (1,210) | 80,344 (0,468) | 4626 |
| CI-LINUX | 742 byte | Ed25519 | 6 | 1,000 (0,194) | 0,077 (0,001) | 394 |
| CI-LINUX | 742 byte | Falcon-512 | 6 | 7,845 (0,322) | 0,089 (0,006) | 4232 |
| CI-LINUX | 742 byte | Hybrid | 6 | 7,959 (0,062) | 0,144 (0,008) | 4626 |
| CI-LINUX | 1 MiB | Ed25519 | 6 | 11,169 (0,615) | 3,165 (0,033) | 394 |
| CI-LINUX | 1 MiB | Falcon-512 | 6 | 15,602 (0,868) | 2,999 (0,005) | 4232 |
| CI-LINUX | 1 MiB | Hybrid | 6 | 24,140 (2,972) | 5,418 (0,052) | 4626 |
| CI-LINUX | 10 MiB | Ed25519 | 6 | 153,601 (12,762) | 50,709 (5,862) | 394 |
| CI-LINUX | 10 MiB | Falcon-512 | 6 | 125,108 (7,928) | 39,763 (4,426) | 4232 |
| CI-LINUX | 10 MiB | Hybrid | 6 | 224,116 (11,363) | 81,331 (3,668) | 4626 |
| CI-MAC | 742 byte | Ed25519 | 6 | 4,518 (0,575) | 0,390 (0,050) | 394 |
| CI-MAC | 742 byte | Falcon-512 | 6 | 15,158 (2,231) | 0,300 (0,066) | 4232 |
| CI-MAC | 742 byte | Hybrid | 6 | 17,566 (2,073) | 0,665 (0,173) | 4626 |
| CI-MAC | 1 MiB | Ed25519 | 6 | 98,740 (9,262) | 27,314 (4,105) | 394 |
| CI-MAC | 1 MiB | Falcon-512 | 6 | 30,833 (3,441) | 5,458 (1,477) | 4232 |
| CI-MAC | 1 MiB | Hybrid | 6 | 113,401 (17,399) | 33,240 (5,550) | 4626 |
| CI-MAC | 10 MiB | Ed25519 | 6 | 951,158 (142,635) | 319,601 (85,382) | 394 |
| CI-MAC | 10 MiB | Falcon-512 | 6 | 173,632 (8,834) | 60,776 (8,002) | 4232 |
| CI-MAC | 10 MiB | Hybrid | 6 | 1072,141 (132,026) | 356,324 (188,643) | 4626 |

Chữ ký Ed25519 rời dài 64 byte. Độ dài rời Falcon-512 trong PDF đo được lần lượt là CI-WIN 651-659 byte, CI-LINUX 651-662 byte, CI-MAC 650-659 byte. Mức tăng của tệp gồm phần đệm, hex và metadata của cấu hình vùng chứa mặc định. Nó được xác nhận từ số đo kích thước độc lập với thời gian.

### Tương phản ghép cặp

Ghép đúng job, tiến trình, khối, kích thước và thao tác. Mỗi ô chênh lệch là trung vị (IQR) của `Hybrid - đơn lớp`, đơn vị ms. Tỷ số là trung vị của các tỷ số từng cặp có mẫu số dương. Không dùng tỷ số hai trung vị.

| Môi trường | PDF | Thao tác | Chênh với Ed25519 (ms) | Tỷ số với Ed25519 | Chênh với Falcon-512 (ms) | Tỷ số với Falcon-512 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| CI-WIN | 742 byte | Ký và xuất | 11,047 (0,567) | 4,336 | 0,897 (0,391) | 1,066 |
| CI-WIN | 742 byte | Xác minh | 0,115 (0,004) | 1,475 | 0,133 (0,005) | 1,590 |
| CI-WIN | 1 MiB | Ký và xuất | 19,813 (0,757) | 1,983 | 14,721 (0,614) | 1,590 |
| CI-WIN | 1 MiB | Xác minh | 3,176 (0,060) | 1,585 | 4,306 (0,060) | 2,001 |
| CI-WIN | 10 MiB | Ký và xuất | 92,076 (0,670) | 1,560 | 132,233 (2,239) | 2,057 |
| CI-WIN | 10 MiB | Xác minh | 29,581 (0,902) | 1,580 | 39,593 (0,692) | 1,972 |
| CI-LINUX | 742 byte | Ký và xuất | 6,936 (0,130) | 7,908 | 0,125 (0,160) | 1,016 |
| CI-LINUX | 742 byte | Xác minh | 0,065 (0,007) | 1,843 | 0,056 (0,001) | 1,621 |
| CI-LINUX | 1 MiB | Ký và xuất | 13,204 (3,130) | 2,231 | 8,112 (3,243) | 1,532 |
| CI-LINUX | 1 MiB | Xác minh | 2,294 (0,085) | 1,729 | 2,421 (0,049) | 1,808 |
| CI-LINUX | 10 MiB | Ký và xuất | 64,902 (10,090) | 1,427 | 100,151 (12,981) | 1,808 |
| CI-LINUX | 10 MiB | Xác minh | 28,391 (5,255) | 1,569 | 39,680 (0,937) | 2,005 |
| CI-MAC | 742 byte | Ký và xuất | 13,193 (2,006) | 4,119 | 2,428 (0,804) | 1,161 |
| CI-MAC | 742 byte | Xác minh | 0,288 (0,180) | 1,725 | 0,336 (0,199) | 2,027 |
| CI-MAC | 1 MiB | Ký và xuất | 15,440 (7,555) | 1,161 | 84,484 (7,966) | 3,779 |
| CI-MAC | 1 MiB | Xác minh | 4,124 (5,401) | 1,167 | 28,009 (6,685) | 6,323 |
| CI-MAC | 10 MiB | Ký và xuất | 149,824 (239,472) | 1,157 | 904,324 (121,310) | 6,106 |
| CI-MAC | 10 MiB | Xác minh | 84,727 (140,454) | 1,276 | 300,741 (180,217) | 6,516 |

Các chênh lệch giữa ba môi trường quan sát đi cùng khác biệt CPU, image, hệ tệp, nền ảo hóa và mô-đun native. Pilot cung cấp thống kê mô tả. Chưa suy ra tác động riêng của hệ điều hành, P95, độ trễ ứng dụng desktop hoặc kết quả chiến dịch main.

## C8 giữa các môi trường

Run `44702431300`, attempt 1, kết luận `success`. Input dùng `mode=compat`, cùng `source_commit`, `pilot_run=44701642390`, `pilot_attempt=1` và `accepted_protocol=hybridsign-5.5a-v1`. Mỗi job tải đúng ba artifact công khai của pilot đã chốt, đối chiếu manifest và băm trước khi dùng bộ xác minh Hybrid sản xuất. Đã tải các báo cáo xác minh và đối chiếu băm manifest mà verifier ghi với từng bundle đã tải từ producer. [Run C8](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44702431300)

| Môi trường xác minh | Bundle từ Windows | Bundle từ Linux | Bundle từ macOS Intel |
| --- | --- | --- | --- |
| [CI-WIN](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44702431300/job/136173787841) | VALID | VALID | VALID |
| [CI-LINUX](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44702431300/job/136173788147) | VALID | VALID | VALID |
| [CI-MAC](https://github.com/june2605/falconv1.2-ed25519-thesis/actions/runs/44702431300/job/136173788030) | VALID | VALID | VALID |

Chín ô đạt gồm sáu lượt khác hệ điều hành và ba lượt cùng hệ điều hành ở job xác minh khác job tạo. Không có ô NOT RUN. Mỗi bundle có một PDF 5 368 byte từ mẫu công khai, hai khóa công khai và một manifest. Bảng dưới định danh đúng manifest đã xác minh.

| Bên tạo | SHA-256 manifest C8 |
| --- | --- |
| CI-WIN | `21218cb1d1a8c80e531833ca80856dbf61ec48b8aecf34c016b3f13f3a1d879e` |
| CI-LINUX | `2aaf209fec9ebf3502b766b8b73450d0b5e9cace6c2be110d66d6582f07a1aae` |
| CI-MAC | `ef2b762f72f1a50ac6d9150168ac8567c406ed7a2114caa7f9d296a79b5e264b` |

Ba job C8 đã được kiểm tra riêng theo log. Windows đạt 568 pytest. Linux và macOS mỗi môi trường đạt 566 với 2 skip Windows đã nêu. Cả ba có 19/19 smoke. C8 có tổng thời gian job 177 s và không tạo dòng đo pilot. Hai run dùng đúng sáu job. Không có lần repair, rerun hoặc job main.

## Bằng chứng lưu bền vững

Thư mục `%LOCALAPPDATA%\HybridSignResearch\phase5-5b\campaign-60fd4c10` nằm ngoài Git và Temp. Bản lưu giữ receipt dispatch, metadata run/job, log từng job, ZIP gốc, dữ liệu giải nén, inventory và bản thống kê dẫn xuất `summary-pilot.json`. Đã đối chiếu SHA-256 ZIP của GitHub, inventory bản tải, mã nguồn, profile, lịch chạy và hash đầu vào. Pilot có 61 mục trong inventory bản tải. C8 có 22 mục. Tất cả 9 ZIP tải về khớp digest do GitHub báo. Danh mục toàn chiến dịch có 96 mục và SHA-256 `3060b78734e264ccb3b0be9d5395a530afd2d0cd240d0660156c3fdf8cc8fd52`. SHA-256 bản thống kê tái tính là `67193878f9920656d0a0e80c5f7f4ffa5060172231aebf72a1bbd4af5d708bac`, khớp khi tái tạo lần hai. Tệp `validation-complete.json` liên kết từng ô C8 với job và băm bundle.

| Môi trường | SHA-256 raw.csv | SHA-256 schedule.json | SHA-256 inventory phiên |
| --- | --- | --- | --- |
| CI-WIN | `4ef20c19b93c8f3306c6ee275a4898972aba097821d4ad12a39e97f6f6e57c34` | `c2fe6bb914ab96a6133f37c52a259352c8dbc82dd66bd2d02d77aa18c4249dd7` | `26a0985ac8f702e2b0f840102e90ace6488567f6a2949559fbb686f72993db52` |
| CI-LINUX | `536f577245dc5619e491196fc9aa09081ca879500b996923301a49854c99b4fb` | `69578c16d543f7b12d81d39d44fce4ba449cfa7283cee2703031354be7cfbd13` | `269d2667dbb8e25213d8e7a1ea6d5e6e6362f10168593be0a1c0b471a5176b49` |
| CI-MAC | `4481d14d1e5a87d69c6b93d230a63067ba950787213f6e8a658f0bcbad31e7b8` | `933257cea1fe09eed46f9b491153c8836f14290f286cdc1c487332fbb28b463f` | `9d20ae48e59395a6f5a685ab5b9e53f8b17a5f2d98b1ca1d36c55e7b6536a511` |

Tái tính từ ba thư mục `session` trong bản lưu pilot bằng `python -B -m research.benchmarks.p55 summarize --campaign <CI-WIN/session> <CI-LINUX/session> <CI-MAC/session>` trong venv nghiên cứu. Lệnh nhận thư mục phiên thực tế có tên gắn nguồn, run và attempt. Kết quả giữ Q1, Q3, IQR, trung bình, SD mẫu, cực trị và tách phiên. Hai lịch sử Phase 5.2A/5.2B và dữ liệu Phase 5.5A được giữ riêng.

## Khuyến nghị

Pilot và C8 đạt điều kiện kỹ thuật để đề xuất phê duyệt chiến dịch main riêng trên ba nhãn đã thử. Trước khi chạy main, cần chốt nguồn, profile và kế hoạch ba phiên mỗi môi trường, kiểm tra thay đổi image và duyệt workflow main riêng. Workflow đang đăng ký chỉ cho phép pilot và C8. Main chưa được khởi chạy.

Sau thực thi đã xác nhận 37 tệp nguồn và nghiên cứu cũ, fixture đông cứng, mẫu công khai, 15 tệp dữ liệu kế thừa, 138 tệp portable và 3 hiện vật phát hành đều khớp baseline. Báo cáo này là tệp bổ sung duy nhất sau commit mã nghiên cứu. Không thay đổi kết luận luận văn. Giới hạn đối với mã hóa Falcon, xác định danh tính và thời điểm ký vẫn áp dụng. Windows Server CI chỉ cung cấp bằng chứng cho lõi và hệ tệp đã chạy. Checklist GUI Windows và hỗ trợ GUI Linux/macOS nằm ngoài chiến dịch.
