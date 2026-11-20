# Phase 5.5A - Bộ so sánh nghiên cứu và mức sẵn sàng chạy thử

> Tài liệu ghi trạng thái cuối Phase 5.5A. Thông tin đăng ký, phạm vi workflow và chạy cloud được cập nhật riêng trong Phase 5.5B.

| Trạng thái | Kết quả |
| --- | --- |
| IMPLEMENTED | Hai bộ so sánh PDF đơn lớp, đường gọi Hybrid nguyên trạng, bộ đo tuần tự, hồ sơ wheel ba nền tảng x64, phân tích ghép cặp và workflow thủ công |
| TESTED | 564 lượt pytest trọng điểm. Chạy riêng 32 lượt nghiên cứu. Smoke 19/19. Actionlint hợp lệ. Xuất và xác minh bundle C8 trên cùng máy |
| MEASURED | Một pilot LOCAL-WIN hoàn tất với 3 khối khởi động và 6 khối đo. Có 45 lượt khởi động, 90 lượt đo, 168 dòng thời gian đo, 0 lỗi hoặc lượt bị loại |
| NOT RUN | CI-WIN, CI-LINUX, CI-MAC, chuyển C8 giữa môi trường và mọi chiến dịch main |
| BLOCKED | REMOTE WORKFLOW NOT REGISTERED. Cần đăng ký có phê duyệt trên `main` và xác nhận quyền cùng hạn mức Actions |
| UNSUPPORTED | Hồ sơ này dành cho x64. ARM64, chạy GUI desktop trên Linux/macOS và tệp từ 40 MiB trở lên nằm ngoài hồ sơ |
| PENDING HUMAN ACCEPTANCE | Chấp nhận kho khóa quản lý, worker và hộp thoại native trên Windows. Xem checklist riêng |

[Đặc tả giao thức](phase5-5a-research-protocol.md) · [Checklist GUI](phase5-5a-windows-gui-checklist.md)

## 1. Điểm xuất phát và tính toàn vẹn

Làm việc trong `D:\Final_Thesis_GitHub`, kho `june2605/falconv1.2-ed25519-thesis`, nhánh `thesis/ui-demo`. Git thực tế cho thấy HEAD `6cb9b903caa6ef93728b8133449e2d9f513881e7`. Cây làm việc và index sạch trước tác vụ. So với `d93b0be`, commit bổ sung tài liệu, hình và mã phân tích Phase 5.3. Mã lõi và các benchmark Phase 5.2 giữ nguyên.

Manifest được tạo trước khi sửa mã và giữ nguyên SHA-256 `c9ce64fc5ceaac40e984e36982c862e1ff76dc4b8b97c2253135a91c77dd63ec`. Sau chạy đã đối chiếu lại 37 tệp nguồn và nghiên cứu, hai fixture đông cứng và mẫu công khai, 15 mục dữ liệu kế thừa tại `D:\Final_Thesis`, 138 tệp portable và 3 tệp phát hành. Tất cả khớp, gồm bộ cài đã thẩm định, EXE portable và ZIP portable. Mọi hiện vật phát hành được liệt kê đều có mặt. Thư mục làm việc chỉ thêm 14 tệp bên dưới. [Manifest ban đầu](phase5-5a-baseline.json) · [Dữ liệu phát hành](phase4c3-final-release-review.md)

Các bộ đơn lớp chỉ thuộc `research/`. Chúng kiểm tra riêng cấu trúc và khóa theo đúng thuật toán, rồi dùng lại thao tác đường dẫn và giao dịch tệp đã có. Hybrid đi qua đúng hai API ở `sign.py` và `verify.py`, với kiểm tra khóa và hai self-test thực thi trong thời gian ký. Thời gian ký và xuất có xác minh ứng viên và công bố. Đọc/xác minh tệp đã xuất được tính riêng. Các chức năng kho khóa, GUI, chính sách parser cặp và hợp đồng 11 phần tử đã được giữ theo baseline. [Bộ so sánh](../research/benchmarks/p55/pdf.py) · [Ranh giới và đối chứng](phase5-5a-research-protocol.md)

## 2. Hồ sơ Python và môi trường

Hồ sơ độc lập `p55a-cp3119-x64-v1` dùng CPython 3.11.9, PyNaCl 1.6.2, pqcrypto 0.3.4 và cffi 2.0.0. Ba phiên bản đầu trùng bộ đo Phase 5.2. `cryptography` 50.0.2 có trong môi trường lịch sử và `.venv` ứng dụng hiện tại. Quy trình lõi và các bài kiểm tra được chọn ở đây không nhập kho khóa nên hồ sơ nghiên cứu không cần gói đó. Môi trường ứng dụng giữ nguyên. Đã tải và đối chiếu byte của 19 wheel PyPI phân biệt theo filename, băm SHA-256 và kiến trúc, bao gồm các phụ thuộc kiểm thử. Cài đặt chỉ từ wheel xác thực. Không dựng mã nguồn khi thiếu wheel. [Hồ sơ đầy đủ](../research/benchmarks/p55/wheels.json) · [Bản phát hành pqcrypto trên PyPI](https://pypi.org/project/pqcrypto/0.3.4/) · [PyNaCl binary wheel](https://pynacl.readthedocs.io/en/latest/install/) · [Manifest CPython cho runner](https://github.com/actions/python-versions/blob/main/versions-manifest.json)

| Nền tảng x64 | Wheel Falcon-512 | SHA-256 của mô-đun Falcon lấy từ wheel | Thực thi |
| --- | --- | --- | --- |
| Windows | `pqcrypto-0.3.4-cp311-cp311-win_amd64.whl` | `ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237` | Khớp binary nạp thực tế trong LOCAL-WIN, cùng băm với bản Windows lịch sử |
| Linux | `pqcrypto-0.3.4-cp311-cp311-manylinux_2_17_x86_64.manylinux2014_x86_64.whl` | Xem `wheels.linux.pqcrypto.native_sha256` | NOT RUN |
| macOS Intel | `pqcrypto-0.3.4-cp311-cp311-macosx_10_9_x86_64.whl` | Xem `wheels.macos.pqcrypto.native_sha256` | NOT RUN |

Mỗi phiên đối chiếu lại phiên bản đã cài, băm wheel, tên và băm mô-đun được nạp của Falcon, PyNaCl và cffi. Metadata cũng chứa image/build, CPU, lõi, RAM, đĩa, hệ tệp và thông số GC khi có. Truy nguyên Falcon là pqcrypto 0.3.4 và PQClean clean `2cc64716044832eea747234ddbffc06746ab815d`. Kết quả chưa xác nhận dựng lại binary hoặc phù hợp đầy đủ Falcon v1.2. Hồ sơ Windows, Linux và macOS chứa băm binary riêng. Wheel phù hợp là điều kiện đầu vào, còn chấp nhận giao dịch trên filesystem yêu cầu smoke thật trên từng runner. [Truy nguyên Falcon](falcon-implementation-provenance.md)

## 3. Pilot đã đo trên máy hiện có

Ngày 20/11/2026, LOCAL-WIN chạy từ 14:35:20 đến 14:35:44 giờ Bangkok. Một tiến trình CPython x64 có PID **21120**, session `25f5500877594bd38815907e4a30ca39`, seed `5501`. Cấu hình ghi Intel Core i7-10850H 2,70 GHz danh định, 6 lõi vật lý, 12 luồng logic, RAM 16 762 388 480 byte, Windows 11 Pro AMD64 build `26200.9974`, ổ NTFS cục bộ, AC và Balanced. Khi vào phiên còn 6 600 421 376 byte RAM và 15 803 494 400 byte đĩa, vượt hai ngưỡng tiền kiểm. GC mặc định bật với ngưỡng `700, 10, 10`. Có một luồng Python ở lúc ghi metadata, affinity ghi `unknown`, độ phân giải được báo là 100 ns. Không chạy GUI hoặc benchmark cạnh tranh trong thời gian đo. `pilot-local-win-b4334e3e/session.json`

Vòng nhận lượt mất **18,283 s**, gồm đối chứng ngoài khoảng đo. Khoảng từ đầu đến cuối ghi trong outcome là **23,887 s**. Một khối cuối `measured-06` đủ cả 15 lượt. Tổng CSV có 252 dòng dữ liệu, gồm 84 dòng khởi động và 168 dòng đo. Trong 90 lượt đo có 12 lượt sinh khóa, 24 lượt ký/xác minh mức thuật toán và 54 lượt PDF. Nhật ký ngoài bộ đếm có 306 bản ghi đối chứng đạt, gồm 270 bản ghi C0-C3 cho PDF theo lớp áp dụng và 36 bản ghi kiểm tra primitive, tính cả khởi động. Smoke riêng đạt 19/19. `pilot-local-win-b4334e3e/raw.csv` · `pilot-local-win-b4334e3e/outcome.json` · `pilot-local-win-b4334e3e/smoke.json`

### Tính đúng trong các mẫu đã thử

| Kiểm tra cặp | Cấu trúc | Ed25519 | Falcon-512 | Hybrid |
| --- | --- | --- | --- | --- |
| C0 | Hợp lệ | Đúng | Đúng | Đúng |
| C1 | Hợp lệ | Sai | Sai | Sai |
| C2 | Hợp lệ | Sai | Đúng | Sai |
| C3 | Hợp lệ | Đúng | Sai | Sai |
| C5 | Hợp lệ | Đúng | Sai | Sai |
| C6 | Hợp lệ | Sai | Đúng | Sai |
| `C4.remove_falcon` | `pair.markers` | NOT EVALUATED | NOT EVALUATED | Sai |
| `C4.remove_ed25519` | `pair.markers` | NOT EVALUATED | NOT EVALUATED | Sai |
| `C4.reverse` | `byte_range.gap` | NOT EVALUATED | NOT EVALUATED | Sai |
| `C7.byte_range` | `byte_range.syntax` | NOT EVALUATED | NOT EVALUATED | Sai |
| `C7.length` | `metadata.length` | NOT EVALUATED | NOT EVALUATED | Sai |
| `C7.padding` | `contents.padding` | NOT EVALUATED | NOT EVALUATED | Sai |
| `C7.cardinality` | `pair.markers` | NOT EVALUATED | NOT EVALUATED | Sai |

C5 và C6 dùng khóa thử sinh trong bộ nhớ. Lớp giữ lại có byte giống bản gốc và kết quả xác minh lớp còn lại đúng như giả thiết đối chứng. C8 đã tạo một PDF lai từ mẫu 742 byte và hai tệp khóa công khai. Bộ xác minh đọc lại đúng byte, đối chiếu băm rồi trả hợp lệ. Kết quả này xác nhận hợp đồng xuất/nhập trên cùng máy. C8 liên môi trường vẫn NOT RUN. `c8-local-win-b4334e3e/bundle.json` · [Bộ đối chứng](../research/benchmarks/p55/controls.py)

### Thời gian mô tả, n = 6 mỗi dòng

| Đầu vào | Phương pháp | Thao tác | Đơn vị | Trung vị | IQR |
| --- | --- | --- | --- | ---: | ---: |
| Sinh khóa | Ed25519 | Sinh khóa | µs | 45,950 | 4,350 |
| Sinh khóa | Falcon-512 | Sinh khóa | µs | 12251,450 | 3602,200 |
| 1 MiB | Ed25519 | Ký và xuất | ms | 30,819 | 1,426 |
| 1 MiB | Ed25519 | Xác minh sau xuất | ms | 4,931 | 0,150 |
| 1 MiB | Falcon-512 | Ký và xuất | ms | 34,941 | 2,458 |
| 1 MiB | Falcon-512 | Xác minh sau xuất | ms | 3,977 | 0,128 |
| 1 MiB | Hybrid | Ký và xuất | ms | 48,682 | 1,850 |
| 1 MiB | Hybrid | Xác minh sau xuất | ms | 7,787 | 1,432 |
| 10 MiB | Ed25519 | Ký và xuất | ms | 171,543 | 3,697 |
| 10 MiB | Ed25519 | Xác minh sau xuất | ms | 47,192 | 0,756 |
| 10 MiB | Falcon-512 | Ký và xuất | ms | 135,323 | 6,685 |
| 10 MiB | Falcon-512 | Xác minh sau xuất | ms | 37,532 | 0,219 |
| 10 MiB | Hybrid | Ký và xuất | ms | 262,544 | 7,510 |
| 10 MiB | Hybrid | Xác minh sau xuất | ms | 73,227 | 2,571 |
| 742 byte | Ed25519 | Ký và xuất | ms | 14,575 | 2,388 |
| 742 byte | Ed25519 | Xác minh sau xuất | ms | 0,354 | 0,071 |
| 742 byte | Falcon-512 | Ký và xuất | ms | 22,852 | 1,021 |
| 742 byte | Falcon-512 | Xác minh sau xuất | ms | 0,346 | 0,086 |
| 742 byte | Hybrid | Ký và xuất | ms | 25,167 | 2,179 |
| 742 byte | Hybrid | Xác minh sau xuất | ms | 0,428 | 0,036 |
| 1024 byte | Ed25519 | Ký | µs | 42,200 | 3,200 |
| 1024 byte | Ed25519 | Xác minh | µs | 92,550 | 0,850 |
| 1024 byte | Falcon-512 | Ký | µs | 4257,900 | 12,925 |
| 1024 byte | Falcon-512 | Xác minh | µs | 48,450 | 0,400 |
| 64 byte | Ed25519 | Ký | µs | 37,350 | 2,500 |
| 64 byte | Ed25519 | Xác minh | µs | 90,100 | 1,775 |
| 64 byte | Falcon-512 | Ký | µs | 4304,100 | 104,375 |
| 64 byte | Falcon-512 | Xác minh | µs | 44,500 | 0,475 |

Kết quả chi tiết giữ cả Q1, Q3, trung bình, SD mẫu và cực trị. P95 để trống cho n = 6. Bảng ghép cặp bên dưới dùng cùng khối, kích thước và thao tác. Tỷ số là trung vị của tỷ số từng cặp.

| PDF | Thao tác | So với | Trung vị chênh lệch Hybrid (ms) | IQR chênh lệch (ms) | Trung vị tỷ số |
| --- | --- | --- | ---: | ---: | ---: |
| 1 MiB | Ký và xuất | Ed25519 | 17,641 | 1,895 | 1,573 |
| 1 MiB | Ký và xuất | Falcon-512 | 13,611 | 5,071 | 1,390 |
| 1 MiB | Xác minh sau xuất | Ed25519 | 2,859 | 1,461 | 1,584 |
| 1 MiB | Xác minh sau xuất | Falcon-512 | 3,909 | 1,363 | 2,008 |
| 10 MiB | Ký và xuất | Ed25519 | 93,912 | 9,489 | 1,557 |
| 10 MiB | Ký và xuất | Falcon-512 | 125,025 | 7,542 | 1,936 |
| 10 MiB | Xác minh sau xuất | Ed25519 | 26,782 | 2,232 | 1,574 |
| 10 MiB | Xác minh sau xuất | Falcon-512 | 35,731 | 2,796 | 1,955 |
| 742 byte | Ký và xuất | Ed25519 | 10,925 | 1,202 | 1,758 |
| 742 byte | Ký và xuất | Falcon-512 | 2,220 | 1,839 | 1,099 |
| 742 byte | Xác minh sau xuất | Ed25519 | 0,065 | 0,103 | 1,195 |
| 742 byte | Xác minh sau xuất | Falcon-512 | 0,050 | 0,121 | 1,152 |

Ở cả 81 tệp PDF quan sát được, 27 tệp mỗi phương pháp, tăng trưởng tương ứng là **394 byte** Ed25519, **4 232 byte** Falcon-512 và **4 626 byte** Hybrid. Chữ ký Ed25519 rời dài 64 byte trong mọi PDF chứa nó. Falcon-512 rời có khoảng quan sát 650-659 byte. Ô dự trữ vẫn dài 128 hoặc 2 048 byte trước mã hóa. CSV giữ riêng số byte đệm ASCII và khung metadata. Kích thước tăng là đặc tính của vùng chứa mặc định trong nghiên cứu này. Một phiên trên một máy mới chỉ kiểm tra thiết kế và ghi nhận độ trễ mô tả. Chưa dùng kết quả pilot để sửa kết luận luận văn. `summary-local-win-b4334e3e.json`

### Vị trí lưu bền vững

Các tệp nằm trong `%LOCALAPPDATA%\HybridSignResearch\phase5-5a`, ngoài Git và Temp. Danh mục ở dưới bao phủ bảy tệp bằng chứng. SHA-256 của tập mã nguồn ghi trong metadata là `d03a44651b357bb6d9c771289e4d5966ea79236f2fd56e81a1f95cf924e558ed`. Metadata của pilot giữ commit cơ sở và trạng thái dirty vì các tệp nghiên cứu mới chưa commit. Băm các tệp nguồn thực chạy khớp khi kiểm tra lại. SHA-256 bản thống kê dẫn xuất là `3cc82e9eb3f29284e07f9d92dfeb297006a4ec667b7e86767334060c2560ac38`.

| Tệp | SHA-256 |
| --- | --- |
| `pilot-local-win-b4334e3e/checksums.sha256` | `60dfb31efc54b27b504c45f36102df8fe1d2f7a44c5cd47d39ef011a6f105b21` |
| `pilot-local-win-b4334e3e/controls.jsonl` | `ce6b6ce9819af18973180a73680ccc12152e8c5d1ff9160f65f8b8b260da6ac7` |
| `pilot-local-win-b4334e3e/outcome.json` | `858cf35b59ef9f3832564b311fd18f4837e6e3fb4e1237425cbdc94c5d2c1f55` |
| `pilot-local-win-b4334e3e/progress.jsonl` | `7bfa18f82f1f8d73b39d710b28372d125f1f03175686100966e6ad80f5f02ce6` |
| `pilot-local-win-b4334e3e/raw.csv` | `a102a0f49d361489bf19e95ea875b988bd3ee33e5edd52632a637a566c0264c0` |
| `pilot-local-win-b4334e3e/schedule.json` | `c387cbb1ab188e731becc844123c9433ff9c103861c4eb0d41e0c7b8b1e127a1` |
| `pilot-local-win-b4334e3e/session.json` | `f95079726705ccd80ec6ff1795b865824f8d87a693b2604f42fe9140e56ee70c` |
| `pilot-local-win-b4334e3e/smoke.json` | `660c853a9aa1e85d7907c2d7d521e7b602762e42ac68f01c5059a637c4ab3e61` |

## 4. Lệnh cục bộ

Các lệnh chạy từ gốc repo bằng Windows PowerShell. Tạo môi trường và cài wheel đã thực hiện trong môi trường nghiên cứu tách riêng. Khi dùng các đường dẫn đã tồn tại, dùng lại chúng. Các lệnh tạo smoke, phiên đo và bundle nhận thư mục chưa tồn tại. `--help` đã kiểm tra trên hai điểm vào CLI.

```powershell
$research55 = Join-Path $env:LOCALAPPDATA 'HybridSignResearch\phase5-5a'
New-Item -ItemType Directory -Path $research55 -Force | Out-Null
$venv55 = Join-Path $research55 'venv-win-cp3119'
if (!(Test-Path -LiteralPath $venv55)) { .\.venv\Scripts\python.exe -B -m venv $venv55 }
$p55 = Join-Path $venv55 'Scripts\python.exe'
$wheels55 = Join-Path $research55 'wheelhouse-win'
& $p55 -B -m research.benchmarks.p55 install-wheels --wheelhouse $wheels55
& $p55 -B -m research.benchmarks.p55 --help
& $p55 -B -m research.benchmarks.p55.ci --help
& $p55 -B -m research.benchmarks.p55 config --mode pilot --seed 5501
& $p55 -B -m research.benchmarks.p55 smoke --environment LOCAL-WIN --wheelhouse $wheels55 --output (Join-Path $research55 ('smoke-' + [Guid]::NewGuid().ToString('N')))
```

Lệnh dưới tương ứng với pilot đã chạy. Mỗi lần gọi mở một chiến dịch mới. Chỉ chạy khi cần lặp lại pilot và các tác vụ GUI/benchmark khác đã kết thúc.

```powershell
$pilot55 = Join-Path $research55 ('pilot-local-win-' + [Guid]::NewGuid().ToString('N'))
& $p55 -B -m research.benchmarks.p55 run --mode pilot --seed 5501 --environment LOCAL-WIN --wheelhouse $wheels55 --output $pilot55
```

Kiểm tra và tái tính từ pilot hiện có, rồi xuất và xác minh bundle mới. Các thao tác này đã thực hiện. Giá trị `$source55` phải là commit ghi trên màn hình khi xuất bundle của chính phiên đó.

```powershell
$pilot55 = Join-Path $research55 'pilot-local-win-b4334e3e'
$summary55 = Join-Path $research55 ('summary-' + [Guid]::NewGuid().ToString('N') + '.json')
$bundle55 = Join-Path $research55 ('c8-' + [Guid]::NewGuid().ToString('N'))
$source55 = git rev-parse HEAD
& $p55 -B -m research.benchmarks.p55 check-inventory --campaign $pilot55
& $p55 -B -m research.benchmarks.p55 summarize --campaign $pilot55 --output $summary55
& $p55 -B -m research.benchmarks.p55 export-bundle --environment LOCAL-WIN --wheelhouse $wheels55 --output $bundle55
& $p55 -B -m research.benchmarks.p55 verify-bundle --environment LOCAL-WIN --wheelhouse $wheels55 --bundle $bundle55 --expect-source $source55 --expect-producer LOCAL-WIN
```

Lệnh main là **chuẩn bị cho tương lai, NOT RUN**. `config --mode main` đã kiểm tra và xác nhận 450 lượt đo, 840 dòng đo mỗi phiên. Chỉ dùng lệnh `run` sau khi pilot và chính sách nghiên cứu được chấp nhận. Chương trình yêu cầu cùng bộ băm nguồn, môi trường và hồ sơ.

```powershell
& $p55 -B -m research.benchmarks.p55 config --mode main --seed 5502
$main55 = Join-Path $research55 ('main-local-win-' + [Guid]::NewGuid().ToString('N'))
& $p55 -B -m research.benchmarks.p55 run --mode main --seed 5502 --environment LOCAL-WIN --wheelhouse $wheels55 --accepted-pilot $pilot55 --output $main55
```

## 5. Chuẩn bị đám mây và điều kiện đăng ký

Máy vật lý hiện có đủ cho LOCAL-WIN. Kế hoạch sau pilot địa phương là dùng GitHub-hosted x64 chuẩn cho CI-WIN `windows-2022`, CI-LINUX `ubuntu-24.04` và CI-MAC `macos-15-intel`. Ba nhãn có trong tài liệu chính thức ngày kiểm tra. Windows Server CI không đại diện chấp nhận Windows 11 GUI. ID vật lý và parent của runner giữ `unknown`. Tên job, run, attempt và UUID thực thi chỉ định danh phiên logic. So sánh đa hệ điều hành còn phụ thuộc CPU, cấu hình ảo hóa, hệ tệp và binary. Không cần máy bổ sung hoặc dual boot cho thiết kế này. [GitHub-hosted runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners) · [Image Windows Server 2022](https://github.com/actions/runner-images/blob/main/images/windows/Windows2022-Readme.md)

Workflow chỉ có `workflow_dispatch`, mặc định pilot. Nó chạy tuần tự với `max-parallel: 1`, nhóm concurrency chung và `cancel-in-progress: false`. GitHub có thể thay thế lượt đang chờ bằng lượt mới, nên chỉ yêu cầu mỗi chiến dịch một lần và chờ hết trước khi yêu cầu tiếp. Checkout, setup-python, upload-artifact và download-artifact chính thức được khóa theo SHA đã đối chiếu tag. Quyền đọc nội dung và Actions dùng token tự cấp của GitHub. Các đầu vào đi qua biến môi trường, sau đó gate kiểm tra mode, HEAD ref, SHA và ID. Main và C8 yêu cầu pilot được đánh giá thủ công, giao thức đúng, run/attempt thành công và nguồn đúng. Main tải session pilot của từng môi trường để kiểm tra danh mục và hồ sơ. [Workflow](../.github/workflows/phase5-5a-research.yml) · [Chính sách concurrency](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency)

**REMOTE WORKFLOW NOT REGISTERED.** Kiểm tra qua metadata GitHub và remote HEAD cho thấy repo vẫn private, nhánh mặc định `main`. Để đăng ký sau khi có phê duyệt, đưa riêng điểm vào `.github/workflows/phase5-5a-research.yml` lên `main` qua thay đổi được review. Chuẩn bị commit đã review chứa mã nghiên cứu trên `thesis/ui-demo`. Dispatch trên `main` và truyền đủ 40 ký tự SHA của HEAD nhánh nghiên cứu. Gate và từng job kiểm tra SHA đó sau checkout. Nếu nhánh tiến lên, phiên yêu cầu SHA cũ sẽ từ chối để tránh đo nhầm nguồn. Việc chỉ để YAML trên nhánh nghiên cứu chưa mở điểm vào chạy thủ công. [Điều kiện workflow thủ công](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)

Cloud pilot dùng ba job đo. Mỗi job tiến hành 45 lượt khởi động, 90 lượt đo và 168 dòng đo. Tổng ba job là **135 / 270 / 504**. Main chỉ chạy sau khi chấp nhận pilot. Ba job được cấp riêng mỗi môi trường, tổng chín job đo. Mỗi job có 45 lượt khởi động, 450 lượt đo và 840 dòng đo. Mỗi môi trường có **135 / 1 350 / 2 520**, cả ba môi trường có **405 / 4 050 / 7 560**. Có 90 quan sát mỗi điều kiện mỗi môi trường, gom trong ba phiên, cùng ba job phụ xác minh C8 nếu chạy đủ. Một chiến dịch Windows địa phương về sau là phần bổ sung riêng.

C8 dùng ba bundle do pilot cloud xuất, tên gắn commit, run ID, attempt và môi trường. Mode `compat` tải đúng ba tên thuộc run/attempt đã chốt và mỗi runner xác minh cả ba bundle. Điều này chuẩn bị ma trận **3 bên tạo × 3 bên xác minh**. Lượt C8 địa phương hiện tại không tạo bằng chứng cho ô nào của ma trận cloud. Mọi trạng thái phụ thuộc vào artifact thật được nhận. C8 audit file chỉ chứa PDF nhỏ công khai, hai khóa công khai và manifest. Không tải cả workspace, môi trường ảo hay các tệp làm việc 10 MiB.

### Ước lượng ngân sách

| Hạng mục | Số job | Giới hạn mỗi job | Tổng thời gian job ước lượng | Chi phí danh nghĩa ước lượng |
| --- | ---: | ---: | ---: | ---: |
| Cloud pilot | 3 | 25 phút | 9-24 phút | USD 0,234-0,624 |
| Main | 9 | 25 phút | 45-135 phút | USD 1,170-3,510 |
| C8, xác minh 3 bundle trên mỗi OS | 3 | 15 phút | 9-24 phút | USD 0,234-0,624 |
| Gate phụ, một job Ubuntu mỗi lần dispatch | 3 | 5 phút | 3-6 phút | USD 0,018-0,036 |
| Cộng, chưa gồm lưu trữ và chạy lại | 18 | theo dòng | 66-189 phút | USD 1,656-4,794 |

Giả định 3-8 phút/job cho pilot và C8, 5-15 phút/job cho main và 1-2 phút/gate. Các khoảng lập kế hoạch gồm checkout, cài đặt, pytest, smoke, phép đo hoặc C8, tóm tắt và upload. Pilot Windows tại chỗ là căn cứ quy mô công việc, chưa phải thời gian job Windows Server, Linux hay macOS. Giá đơn vị runner chuẩn private ngày kiểm tra là USD 0,006/phút Ubuntu x64 2 lõi, 0,010 Windows x64 2 lõi và 0,062 macOS Intel. GitHub làm tròn phút theo job. Giới hạn timeout là biên an toàn vận hành, không phải dự báo chi phí. [Bảng giá chính thức](https://docs.github.com/en/billing/reference/actions-runner-pricing)

**Allowance tài khoản, mức ngân sách còn lại, giới hạn chi và kế hoạch thanh toán: UNKNOWN.** Trong GitHub Billing and licensing, chủ tài khoản cần kiểm tra loại plan, usage Actions, included compute còn lại, storage và budget/spending cap trước khi đăng ký chạy. Tài liệu hiện biểu thị quyền dùng theo USD quy đổi, tùy plan. Không áp con số gói Free cho tài khoản khi chưa xác minh. Các bước đọc metadata repo đã xác nhận private. Không thay đổi quyền, gói hay cài đặt thanh toán. [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)

### Lệnh cloud dự kiến, chưa chạy

Dùng tài khoản có quyền repo và GitHub CLI sau khi đăng ký và kiểm tra allowance. `$approvedSha55` là SHA đã review thực tế, không lấy từ nhánh khác.

```powershell
$repo55 = 'june2605/falconv1.2-ed25519-thesis'
$workflow55 = 'phase5-5a-research.yml'
$approvedSha55 = Read-Host 'SHA day du da duyet tren thesis/ui-demo'
gh workflow run $workflow55 --repo $repo55 --ref main -f mode=pilot -f source_commit=$approvedSha55
```

Sau pilot, chốt run và attempt bằng log và artifact. Hai lệnh kế tiếp là lựa chọn độc lập, do người có thẩm quyền thực hiện khi được duyệt, mỗi lần một chiến dịch.

```powershell
$pilotRun55 = Read-Host 'Run ID pilot da duyet'
$attempt55 = Read-Host 'Attempt da duyet'
gh workflow run $workflow55 --repo $repo55 --ref main -f mode=compat -f source_commit=$approvedSha55 -f pilot_run=$pilotRun55 -f pilot_attempt=$attempt55 -f accepted_protocol=hybridsign-5.5a-v1
gh workflow run $workflow55 --repo $repo55 --ref main -f mode=main -f source_commit=$approvedSha55 -f pilot_run=$pilotRun55 -f pilot_attempt=$attempt55 -f accepted_protocol=hybridsign-5.5a-v1
```

GitHub giữ artifact 30 ngày theo workflow. Tải vào thư mục bền vững theo run và attempt rồi kiểm tra manifest của từng session trước hạn. Giữ cả các lần lỗi hoặc dở dang. Mốc setup/install/test/benchmark ghi trong JSON tại job. Dùng mốc start/completion từ Jobs API để lấy tổng thời gian có cả upload và bước kết thúc. Khả năng upload sau khi timeout cưỡng bức không được đảm bảo. Thiếu artifact hoặc danh mục phải ghi rõ và giữ log khả dụng. [Quy trình tải bằng run ID](https://cli.github.com/manual/gh_run_download) · [Jobs API theo attempt](https://docs.github.com/en/rest/actions/workflow-jobs#list-jobs-for-a-workflow-run-attempt)

```powershell
$run55 = Read-Host 'Run ID can luu'
$attempt55 = Read-Host 'Attempt can luu'
$archive55 = Join-Path $research55 ("ci-$run55-a$attempt55-" + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $archive55 -ErrorAction Stop | Out-Null
gh run download $run55 --repo $repo55 --pattern "p55a-$approvedSha55-$run55-a$attempt55-*" --dir $archive55
gh api "repos/$repo55/actions/runs/$run55/attempts/$attempt55/jobs" | Set-Content -Encoding utf8 -LiteralPath (Join-Path $archive55 'jobs.json')
Get-ChildItem -LiteralPath $archive55 -Recurse -Filter 'checksums.sha256' | ForEach-Object {
    & $p55 -B -m research.benchmarks.p55 check-inventory --campaign $_.DirectoryName
    if ($LASTEXITCODE -ne 0) { throw 'Inventory mismatch' }
}
```

## 6. Xác nhận cuối và danh sách tệp

- Nhóm pytest gồm nghiên cứu mới, cặp chữ ký, ByteRange, độ dài/padding, khóa và giao dịch đạt **564 passed trong 19,19 s**, 0 lỗi, skip, xfail hoặc xpass. Chạy riêng kiểm thử nghiên cứu đạt **32 passed trong 1,79 s**.
- Đọc lại CSV và tính độc lập trung vị, Q1, Q3 và tương phản ghép cặp, đối chiếu 28 chuỗi thao tác, 12 tương phản, toàn bộ 252 dòng và 306 đối chứng cùng 19 smoke trong phiên. Bảng pilot trích từ kết quả đã kiểm băm.
- Static YAML và tham số CLI đã kiểm tra bằng pytest, `actionlint v1.7.12` và các trang trợ giúp CLI. Actionlint chạy trên workflow thật nhưng không khởi tạo runner.
- Câu hỏi về mã hóa Falcon thay thế trong vùng lưu chữ ký ngoài vẫn mở. Phép thử không chứng minh mọi thay đổi tệp cuối đều bị phát hiện. Danh tính người ký, dấu thời gian tin cậy, CMS/PAdES, Adobe, FIPS và chứng minh an toàn tổ hợp nằm ngoài kết quả pilot. [Kiểm toán Phase 5.1A](phase5-1a-signature-integrity-audit.md)

| Tệp mới | Vai trò |
| --- | --- |
| [docs/phase5-5a-baseline.json](phase5-5a-baseline.json) | Manifest trước sửa |
| [docs/phase5-5a-research-protocol.md](phase5-5a-research-protocol.md) | Giao thức và quy tắc diễn giải |
| [docs/phase5-5a-research-comparison-readiness.md](phase5-5a-research-comparison-readiness.md) | Báo cáo và chứng cứ |
| [docs/phase5-5a-windows-gui-checklist.md](phase5-5a-windows-gui-checklist.md) | Chấp nhận GUI riêng |
| [.github/workflows/phase5-5a-research.yml](../.github/workflows/phase5-5a-research.yml) | Workflow thủ công |
| [research/benchmarks/p55/__main__.py](../research/benchmarks/p55/__main__.py) | CLI nghiên cứu |
| [research/benchmarks/p55/analysis.py](../research/benchmarks/p55/analysis.py) | Tái tính mô tả và ghép cặp |
| [research/benchmarks/p55/ci.py](../research/benchmarks/p55/ci.py) | Gate, C8 cloud và thời lượng job |
| [research/benchmarks/p55/controls.py](../research/benchmarks/p55/controls.py) | Đối chứng và bundle công khai |
| [research/benchmarks/p55/environment.py](../research/benchmarks/p55/environment.py) | Wheel, metadata và tiền kiểm |
| [research/benchmarks/p55/pdf.py](../research/benchmarks/p55/pdf.py) | Bộ so sánh và PDF công khai |
| [research/benchmarks/p55/protocol.py](../research/benchmarks/p55/protocol.py) | Lịch, bộ đo, bằng chứng |
| [research/benchmarks/p55/wheels.json](../research/benchmarks/p55/wheels.json) | Hồ sơ wheel và băm theo nền tảng |
| [tests/test_research_phase55.py](../tests/test_research_phase55.py) | Kiểm tra nghiên cứu |
