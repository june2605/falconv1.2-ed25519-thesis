# Phase 5.5A - Giao thức so sánh PDF dùng trong nghiên cứu

Giao thức `hybridsign-5.5a-v1`, lược đồ `hybridsign-5.5a-raw-v1` và hồ sơ `p55a-cp3119-x64-v1` là một thiết kế mới. Phase 5.2A và 5.2B dùng ranh giới phép đo và lịch khác. Dữ liệu của chúng được giữ riêng. Mục tiêu là đo chi phí bổ sung khi ứng dụng yêu cầu hai lớp chữ ký, so với hai quy trình PDF đơn lớp có chính sách xác minh và xuất tệp tương đương. [Giao thức trước đây](phase5-2a-benchmark-methodology.md) · [Dữ liệu Phase 5.2B](phase5-2b-experimental-results.md)

## 1. Tầng đo và đơn vị

| Tầng | Phương pháp | Phạm vi |
| --- | --- | --- |
| A - Lời gọi thuật toán | Ed25519 và Falcon-512 | Đo sinh khóa riêng từng thuật toán, một sự kiện mỗi thuật toán trong một khối. Với từng thông điệp 64 hoặc 1 024 byte, ghi riêng thời gian ký và xác minh |
| B - Quy trình PDF | Ed25519, Falcon-512 và Hybrid | Cùng tệp PDF nguyên bản cho cả ba phương pháp trong một khối. Ghi ký và xuất, rồi đọc và xác minh tệp đã xuất |
| C - Chấp nhận desktop | Windows, kho khóa quản lý, hộp thoại thật | Kiểm tra chức năng với người thao tác. Kết quả tách khỏi CSV thời gian của hai tầng trên |

Tầng A chuẩn bị một khóa mỗi thuật toán trong mỗi khối và dùng khóa đó ở cả hai điều kiện thông điệp. Thời gian ký Ed25519 gồm `SigningKey.sign()` và lấy `.signature`. Hai wrapper ký và xác minh được chuẩn bị trước khi tính giờ. Hai thuật toán nhận các mảng byte giống nhau theo từng kích thước. Báo cáo tầng A dùng µs. Sinh khóa có hai chuỗi đo và không được nhân đôi theo kích thước thông điệp. [Bộ lập lịch và đường đo](../research/benchmarks/p55/protocol.py)

Ba tệp PDF là mẫu công khai 742 byte, `1-MiB` (1 048 576 byte) và `10-MiB` (10 485 760 byte). Bộ tạo xác định đặt các dòng chú thích PDF trước xref và cập nhật `startxref`. Bộ đo kiểm tra lại SHA-256, kích thước, xref, độ dài stream và điểm neo nội dung. Tệp đệm kiểm soát dung lượng. Tính đa dạng cấu trúc PDF thực tế nằm ngoài bộ mẫu. Các tệp từ 40 MiB trở lên nằm ngoài giao thức này. [Bộ tạo và SHA-256 kỳ vọng](../research/benchmarks/p55/pdf.py) · [Dữ liệu đầu vào đã giữ](phase5-2b-experimental-results.md#conditions-and-per-process-counts)

## 2. Phạm vi PDF và kiểm tra khóa

- Ed25519 đơn lớp thêm đúng một vùng chứa và ký các đoạn `ByteRange` đã ghép. Falcon-512 đơn lớp thêm đúng một vùng chứa và ký đầu ra SHAKE256 dài 64 byte của nội dung được bảo vệ ở phiên bản đó. Cấu hình mặc định dành 128 và 2 048 byte sức chứa, tương ứng. Thông điệp ở cấp thư viện khác nhau do cách đóng vùng chứa, ngay cả khi PDF đầu vào giống nhau.
- Cặp lai đi thẳng qua `sign.sign_with_key_material()` và `verify.verify_file_with_public_keys()`. Hàm `compute_sha512_digest_for_byte_range()` ghép các đoạn byte thô. Falcon ký bản băm dài 64 byte của phiên bản sau, bao phủ toàn bộ vùng chứa Ed25519 và loại khoảng lưu chữ ký của lớp Falcon. Bộ xác minh yêu cầu đúng cấu trúc cặp và cả hai phép kiểm tra. Harness kiểm tra tuple 11 phần tử và dùng đúng giá trị Boolean đầu tiên khi xác minh. [Bộ ký sản xuất](../sign.py#L43) · [Ranh giới thông điệp](phase5-1a-signature-integrity-audit.md#exact-signed-messages)
- Cả ba phương pháp chụp tệp nguồn, chống đè hoặc alias, ghi vào vùng tạm sở hữu riêng, đóng tệp ứng viên sau flush và fsync, xác minh ứng viên rồi mới xuất bằng thay thế nguyên tử. Chúng dùng lại các helper kiểm tra đường dẫn và giao dịch trong `signing_io.py`. Đơn lớp dùng parser nghiên cứu kiểm tra số lượng marker, loại vùng chứa, `ByteRange`, độ dài, padding và điểm cuối tệp. Phương pháp đơn lớp chỉ ghi những bản trung gian thật sự cần cho các bước của nó. Parser và chính sách cặp của ứng dụng giữ nguyên. [Comparator](../research/benchmarks/p55/pdf.py) · [Giao dịch sản xuất](../signing_io.py#L114)
- `validate_key_pair()` chạy trong từng lời gọi ký lai. Nó kiểm tra kiểu, cỡ, tính tương ứng và thách thức ngẫu nhiên mới, với self-test ký/xác minh Ed25519, tiếp theo là Falcon. Bộ so sánh đơn lớp dùng một thách thức riêng và thử ký/xác minh thuật toán tương ứng. Riêng Ed25519 đối chiếu thêm khóa công khai dẫn xuất từ seed. Sinh cặp dùng cho PDF nằm ngoài hai bộ đếm. Hai thí nghiệm chứa số phép toán cần thiết cho chính sách của từng phương pháp. [Kiểm tra cặp khóa](../hybrid_keys.py#L100) · [Kiểm tra khóa đơn lớp](../research/benchmarks/p55/pdf.py)

`sign_and_publish` tính từ lời gọi wrapper trước khi chụp nguồn đến khi xuất thành công và kiểm tra hợp đồng trả về. `verify_published_file` là lời gọi đọc và xác minh riêng tiếp sau. SHAKE256 và các phép kiểm tra phát sinh trong giao dịch thuộc phạm vi tính giờ. Mã băm truy vết, kiểm tra đối chứng, ghi nhật ký, sinh cặp khóa dùng cho PDF, kho khóa, nhập mật khẩu, hộp thoại và bộ lập lịch desktop nằm ngoài hai khoảng. Báo cáo PDF dùng ms. `perf_counter_ns()` ghi thời gian nguyên bằng ns. [Phạm vi đo trong harness](../research/benchmarks/p55/protocol.py)

## 3. Lịch, kiểm soát và bằng chứng

Bộ đo ghi `schedule.json` và SHA-256 trước khi tính giờ. Seed chỉ điều khiển thứ tự thí nghiệm. Hai thông điệp dùng thứ tự 3/3 trong pilot và 15/15 trong main. Với từng kích thước thông điệp, thứ tự hai thuật toán có số lượt AB và BA bằng nhau. Cả sáu thứ tự của ba kích thước PDF và của ba phương pháp PDF xuất hiện một lần trong 6 khối đo pilot và 5 lần trong 30 khối đo main. Mỗi khối có 2 lượt sinh khóa, 4 lượt thuật toán và 9 lượt PDF. Mỗi khối ghi 15 lượt và 28 dòng thời gian. Ba khối khởi động được lưu riêng. Dữ liệu phản ánh tải lặp lại. Chiến dịch giữ nguyên GC, cấu hình luồng, affinity và nguồn điện của hệ điều hành.

| Đối chứng | Kỳ vọng của production Hybrid |
| --- | --- |
| C0 - Tệp nguyên, khóa đúng | Ed25519 đúng, Falcon đúng, kết quả đúng |
| C1 - Sửa nội dung được bảo vệ | Ed25519 sai, Falcon sai, kết quả sai |
| C2 - Sai khóa Ed25519, đúng Falcon | Ed25519 sai, Falcon đúng, kết quả sai |
| C3 - Đúng khóa Ed25519, sai Falcon | Ed25519 đúng, Falcon sai, kết quả sai |
| C4 - Bỏ một lớp hoặc đảo vị trí hai vùng chứa | Từ chối cấu trúc. Hai phép kiểm tra native ghi NOT EVALUATED |
| C5 - Sửa nội dung, ký lại Ed25519 bằng khóa thử gốc, giữ Falcon cũ | Ed25519 đúng, Falcon sai, kết quả sai |
| C6 - Sửa nội dung, giữ Ed25519 cũ, ký lại Falcon bằng khóa thử gốc | Ed25519 sai, Falcon đúng, kết quả sai |
| C7 - Sai ByteRange, độ dài, padding hoặc số lượng marker | Từ chối theo mã lỗi parser cụ thể. Hai phép kiểm tra native ghi NOT EVALUATED |
| C8 - Tệp và khóa công khai do môi trường khác tạo | Kiểm tra nguồn và băm rồi xác minh cặp bằng production. Chỉ thực hiện so sánh liên môi trường khi đã chuyển đúng bundle qua job khác |

C0 đến C3 áp dụng ngoài bộ đếm cho từng kết quả PDF, theo thuật toán có trong tệp. Bộ đo cũng đối chiếu byte của nguồn và tiền tố tệp đầu ra. Các đối chứng C4 đến C7 dùng mẫu 742 byte và khóa sinh trong bộ nhớ của lần smoke. C5 và C6 mô phỏng quyền sử dụng đúng một khóa thử đã biết. Thử nghiệm đánh giá điều kiện chấp nhận hai lớp, không mô phỏng máy tính lượng tử. C8 chỉ cho phép bốn tệp công khai gồm PDF nhỏ, hai khóa công khai và metadata. Bundle không mang khóa bí mật, không yêu cầu hai chữ ký Falcon được sinh độc lập phải giống byte và không thử chế độ dự phòng. [Đối chứng và bundle](../research/benchmarks/p55/controls.py)

Thông số đầu vào, ID phiên, run/job/attempt, dấu băm nguồn và binary, danh sách thứ tự và trạng thái được lưu theo phiên. Bản ghi `raw.csv` định danh khối, lượt, loại phép đo, SHA-256 đầu vào, thứ tự phương pháp, thời gian và kích thước theo từng thuật toán. Kích thước gồm chữ ký native, sức chứa trước khi mã hóa, padding ASCII, siêu dữ liệu của vùng chứa, tổng vùng chứa, tệp xuất và mức tăng. `controls.jsonl` và `smoke.json` giữ đúng kết quả từng lớp hoặc lý do chưa đánh giá. `progress.jsonl` đánh dấu lượt đã bắt đầu và trạng thái kết thúc rồi flush dữ liệu. `checksums.sha256` kiểm tra các tệp bằng chứng được phép lưu. Các tệp đầu vào lớn có mã băm trong metadata và có thể tạo lại. Chúng nằm ngoài gói upload.

Mỗi tiến trình kiểm tra RAM tối thiểu `max(512 MiB, 48 × 10 MiB)`, tương đương 536 870 912 byte. Biên đĩa 150 994 944 byte dự trù các đầu vào 11 MiB cộng mẫu nhỏ, bốn tệp trung gian của quy trình hai lớp, ứng viên và tệp đầu ra lớn nhất có thể hiện diện trong giao dịch, cùng vùng dự phòng 64 MiB. Đây là ngưỡng nhận lượt. Bộ đo không ghi đỉnh RAM hay đĩa. Sau tiền kiểm, bộ đo có 600 giây nhận lượt. Lượt đã bắt đầu được phép hoàn tất. Trạng thái, dữ liệu lỗi và kết quả dở dang được giữ. Một lần dừng cưỡng bức bởi bên ngoài có thể để lại một lượt thiếu dấu kết thúc, thiếu inventory hoặc tệp tạm. Không suy ra đã dọn thành công từ trường hợp đó. [Tiền kiểm và thông số máy](../research/benchmarks/p55/environment.py) · [Lưu tiến độ](../research/benchmarks/p55/protocol.py)

## 4. Thống kê và diễn giải

Báo cáo tách phiên theo môi trường, kiến trúc, nguồn, hồ sơ phụ thuộc, giao thức và chế độ chạy. Nó ghi n, trung vị, Q1, Q3, IQR, trung bình, SD mẫu và P95 kiểu 7 khi có ít nhất 30 quan sát. Quy tắc phân vị dùng thứ hạng một gốc `1 + (n - 1)p` và nội suy tuyến tính. Pilot có 6 quan sát mỗi điều kiện. P95 để trống và không xây dựng khoảng tin cậy. Nhóm dở dang có trạng thái và số dòng rõ ràng, không đưa vào tương phản ghép cặp.

Với mỗi thao tác PDF, ghép theo đúng môi trường, job, process, khối và kích thước. Tính `Hybrid - Ed25519` và `Hybrid - Falcon-512` trên từng cặp rồi tóm tắt bằng trung vị và IQR. Tỷ số chia theo từng cặp với mẫu số dương. Một mẫu số bằng 0 được đếm riêng. Cách tổng hợp này không suy ra từ tỷ số hay hiệu hai trung vị biên. Giữ các lượt chậm và kiểm tra đủ ba phương pháp trước khi báo cáo ghép cặp. [Mã phân tích](../research/benchmarks/p55/analysis.py)

Ba job trên một môi trường tạo ba phiên logic. Với main, 90 quan sát của một điều kiện thuộc ba cụm, không đại diện cho 90 máy. Mã hiển thị CPU và phiên bản image theo từng phiên trong kết quả gộp mô tả. Khi khác image hoặc CPU, giải thích biến thiên đó trước khi trích kết quả. Các yếu tố còn lại gồm native binary, hệ thống tệp, cấp phát máy ảo, tải nền và đặc tính phần cứng. Kết quả không cô lập tác động riêng của hệ điều hành. Sự chấp nhận qua bộ so sánh, phép thử và benchmark không xác lập danh tính, thời gian ký đáng tin, tính duy nhất của biểu diễn Falcon, mức an toàn hậu lượng tử, CMS/PAdES hay sự phù hợp với Falcon v1.2 và FIPS. [Giới hạn đã kiểm toán](phase5-1a-signature-integrity-audit.md) · [Kế hoạch chạy theo giai đoạn](phase5-5a-research-comparison-readiness.md)
