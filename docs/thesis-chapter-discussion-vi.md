# Chương Y. Bàn luận và giới hạn của kết quả

> **Bản thảo tạm thời.** Số chương, bảng và mục cần điều chỉnh theo đề cương được phê duyệt. Các số liệu mới trong chương này dẫn chiếu đến chương thực nghiệm và CSV của Phase 5.2B. [Chương thực nghiệm](thesis-chapter-experiments-vi.md) · [Chỉ mục bằng chứng](phase5-3-evidence-index.md)

## Y.1. Đánh đổi hiệu năng giữa hai thuật toán

Cùng một hệ thống đo cho thấy Falcon-512 có trung vị ký lớn hơn Ed25519 ở cả hai thông điệp ngắn, còn trung vị xác minh Falcon-512 thấp hơn. Khi gộp ba phiên, các tỷ số ký lần lượt là 115,884 và 108,384. Hai tỷ số xác minh là 0,486 và 0,519. Tỷ số được tính từ trung vị chưa làm tròn. Độ dài thông điệp ở đây chỉ nhận hai giá trị. Các phép đo bao gồm đường gọi thư viện từ Python và thao tác mật mã tương ứng. Chi phí sinh khóa được ghi riêng. Kết quả áp dụng cho đúng các cấu hình thư viện được kiểm tra. [Bảng X.3–X.5](thesis-chapter-experiments-vi.md#x3-kết-quả-thời-gian-ở-mức-thuật-toán)

Đặc tả Falcon mô tả cách ký dựa vào lấy mẫu trên mạng NTRU và sử dụng biến đổi Fourier nhanh. Lấy mẫu trong đường ký là một nguyên nhân có thể góp phần tạo ra chênh lệch. Đường xác minh kiểm tra một chữ ký đã có và thực hiện các phép toán khác với đường ký. Ed25519 trong thực nghiệm được gọi qua PyNaCl và cài đặt EdDSA của libsodium. Đây là giải thích dựa trên cấu trúc thuật toán và mã gọi, chứ dữ liệu thời gian thực nghiệm chỉ đo tổng độ trễ ở biên API. Phần đo không tách thời gian lấy mẫu, số lần lặp của thuật toán, chi phí liên kết Python và tối ưu hóa ở mức lệnh máy. Vì vậy, thứ tự độ trễ quan sát được không đủ để khẳng định ưu thế tổng quát cho mọi cài đặt hay thiết bị. [Falcon Specification v1.2](https://falcon-sign.info/falcon.pdf) · [RFC 8032, mục 5.1](https://www.rfc-editor.org/rfc/rfc8032.html#section-5.1) · [Mã PyNaCl 1.6.2](https://github.com/pyca/pynacl/blob/1.6.2/src/nacl/signing.py)

## Y.2. Ảnh hưởng của dung lượng PDF và chi phí giao dịch

Từ 1 lên 10 MiB, trung vị của toàn lời gọi ký và xuất tăng khoảng 5,35 lần, từ 48,253 lên 257,992 ms. Trung vị của phép xác minh độc lập tăng khoảng 9,61 lần, từ 7,677 lên 73,749 ms. Tỉ lệ tăng của từng thao tác phụ thuộc nguồn chi phí ở biên đo. Các kích thước chính chỉ có ba mức và PDF được dựng từ cùng một mẫu. Kết quả chứng minh xu hướng tăng đối với nhóm đầu vào kiểm soát này. Việc suy ra quy luật tăng trưởng cho mọi PDF hoặc ngoài miền đo cần dữ liệu khác. [Bảng X.6–X.7 và Hình X.3–X.4](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai)

Khi PDF lớn hơn, các lời gọi xử lý nhiều byte hơn. Đường ký Ed25519 nhận nội dung ghép dài hơn, trong khi Falcon nhận đầu ra SHAKE256 dài 64 byte ở mọi kích thước. Theo bảng đo chi tiết, từ 1 lên 10 MiB, trung vị của lời gọi ký Ed25519 tăng từ 5,663 lên 57,604 ms, còn trung vị của lời gọi ký Falcon-512 xấp xỉ 4,39 ms ở cả hai kích thước. Trung vị tiền băm Falcon tăng từ 2,617 lên 25,762 ms. Tự xác minh tệp tạm tăng từ 14,791 lên 82,890 ms. Các quan sát này phù hợp với việc nhiều công đoạn phụ thuộc lượng dữ liệu và Falcon nhận thông điệp đã rút gọn có độ dài cố định. Phép đo minh họa vị trí phát sinh chi phí trong quy trình. Các trung vị cấp bước không cộng lại thành một thời gian giao dịch và chưa định lượng tác động nhân quả của từng bước. [Bảng X.9](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai) · [Bộ đo cấp bước](../research/benchmarks/phase5_2a.py#L184)

Có thêm chi phí kiểm tra khóa trong bộ nhớ, sao chép, tạo và điền hai vùng chứa, ghi và đồng bộ tệp tạm, tự xác minh, dọn dữ liệu làm việc và thay thế tệp đích. Cấu trúc này giải thích vì sao so sánh giữa hai lời gọi ký ở mức thuật toán và phép đo toàn quy trình có phạm vi khác nhau. Dữ liệu không có quy trình PDF chỉ ký Ed25519 hoặc chỉ ký Falcon-512 chạy theo cùng chính sách xuất tệp. Phần chi phí tăng thêm so với từng quy trình đơn thuật toán vì thế chưa được đo. Phép xác minh của tệp đã xuất độc lập với khoảng tính giờ ký. GUI, hộp thoại và kho khóa nằm ngoài phạm vi các số liệu đã đo. [Bộ ký](../sign.py#L43) · [Giao dịch tệp](../signing_io.py#L114)

Phiên bổ sung 40 MiB cung cấp thêm một điểm thực nghiệm trên cùng máy. Trung vị của phiên đó đạt 1 081,842 ms đối với ký và xuất và 309,516 ms đối với xác minh độc lập. Cả kích thước lẫn tiến trình đều thay đổi so với ba nhóm chính. Điểm bổ sung hỗ trợ thảo luận xu hướng ở kích thước đã thử. Nó không ước lượng được biến thiên giữa các tiến trình đối với 40 MiB. [Bảng X.8 và tiền kiểm](thesis-chapter-experiments-vi.md#x25-điều-kiện-bổ-sung-40-mib)

## Y.3. Biến thiên nội phiên và giữa phiên

Độ phân tán của các lượt ký và xuất thể hiện rõ ở đuôi trên. Đối với mẫu 742 byte, trung vị gộp là 24,542 ms, IQR 2,349 ms, SD mẫu 18,420 ms và P95 74,695 ms. Trung vị giữa từng phiên dao động từ 24,395 đến 24,747 ms. Ở 10 MiB, trung vị theo phiên từ 254,529 đến 262,827 ms, trong khi IQR gộp là 11,100 ms, SD mẫu là 41,327 ms và P95 là 338,591 ms. IQR mô tả độ rộng của phần trung tâm. SD và P95 phản ánh mạnh hơn các lượt chậm được giữ trong dữ liệu. Hình X.5 xếp đủ 30 quan sát của từng phiên theo thời gian tăng dần, cho thấy những điểm chậm được giữ ở đầu mút mỗi chuỗi. Số thứ hạng trong hình khác với thứ tự thực thi trong CSV. [Bảng X.6–X.7 và Hình X.5](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai)

Phiên 40 MiB có IQR ký 42,526 ms và SD mẫu 295,140 ms. Quan sát ký chậm nhất đạt 2 599,060 ms. Phân bố xác minh cùng phiên có IQR 14,691 ms, SD mẫu 10,467 ms và P95 327,227 ms. Các lượt ký chậm vẫn hoàn tất kiểm tra dương tính và âm tính. Giả thuyết có thể xem xét là tác động của bộ đệm tệp, độ trễ I/O, lịch hệ điều hành, cấp phát bộ nhớ hoặc thu gom rác. Nhật ký ghi thời gian và kết quả ở biên lời gọi, không ghi sự kiện đồng thời đủ chi tiết để quy nguyên nhân cho từng lượt. [Bảng X.8–X.9](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai) · [Cực trị trong bảng tính thống kê Phase 5.2B](phase5-2b-statistical-analysis.md#hybrid-pdf-signing-and-independent-verification)

Ba phiên là ba lần khởi động tiến trình trên cùng một thiết bị, được chạy liên tiếp. Ngay cả trong mỗi phiên, các quan sát có thể chia sẻ trạng thái hệ thống, thiết bị lưu trữ và thứ tự của khối. Khoảng Q1–Q3 mô tả phân bố mẫu, còn khoảng nhỏ nhất–lớn nhất của các trung vị mô tả chênh lệch quan sát giữa các phiên. Chúng không được diễn giải thành khoảng tin cậy của tham số tổng thể. P95 nội suy từ 30 hoặc 90 quan sát tương ứng, phù hợp với mục đích mô tả. Kết quả không đưa ra giá trị p, mức bảo đảm dịch vụ hoặc suy luận về quần thể máy Windows. Thử nghiệm trên các máy và loại lưu trữ khác nhau cần được thiết kế riêng để đo độ nhạy theo nền tảng. [Cách tính phân vị và phương pháp báo cáo](thesis-chapter-experiments-vi.md#x24-thiết-bị-đo-và-thống-kê)

## Y.4. Chi phí lưu trữ của định dạng mặc định

Phần ký được nối vào đúng sau dữ liệu gốc. Mỗi lớp gồm dấu mở, dòng `ByteRange`, vùng chứa dòng `SigLength` và `Contents`, rồi dấu đóng. Giá trị `SigLength` trong vùng chứa đã hoàn tất là số ký tự hex có ích. Khuôn dành trước 128 byte sức chứa cho Ed25519 và 2 048 byte sức chứa cho Falcon-512. Hai ký tự ASCII lưu một byte chữ ký, nên các ô `Contents` dành 256 và 4 096 byte trên đĩa cho cả chữ ký đã mã hóa và đệm ASCII `0`. Kích thước ô cố định ngay cả khi chữ ký Falcon-512 gốc thay đổi độ dài. [Hằng số, ngữ pháp và trình ghi](../utils.py#L9) · [Vùng chứa hoàn tất và phần đệm](../utils.py#L164) · [Hàm tạo vùng chứa](../utils.py#L223)

**Bảng Y.1. Phân rã số byte ghi thêm theo khuôn vùng chứa mặc định.**

| Thành phần | Ed25519 (byte) | Falcon-512 (byte) | Tổng (byte) |
| --- | --- | --- | --- |
| Dấu mở | 23 | 22 | 45 |
| Dòng ByteRange | 59 | 59 | 118 |
| Dòng SigLength | 22 | 22 | 44 |
| Cú pháp dòng Contents và LF | 13 | 13 | 26 |
| Ô ký tự hex (gồm chữ ký và đệm) | 256 | 4096 | 4352 |
| Dấu đóng | 21 | 20 | 41 |
| Tổng số byte ghi thêm | 394 | 4232 | 4626 |

Phần hex chiếm 4 352 byte, phần dấu, siêu dữ liệu và cú pháp chiếm 274 byte. Tổng cộng hai vùng chứa tăng tệp 4 626 byte. Ed25519 tạo chữ ký rời 64 byte. Trong toàn bộ 734 kết quả PDF, chữ ký Falcon-512 rời ghi nhận từ 649 đến 662 byte. Số 752 byte trong siêu dữ liệu PQClean là giới hạn chữ ký rời của biến thể được tham chiếu, khác với dung lượng ô dành trước của nguyên mẫu. Bảng X.10 cho thấy chênh lệch cố định ở cả bốn kích thước đã thử. Dung lượng mặc định, mã hóa hex và phần đệm là lựa chọn tuần tự hóa của HybridSign. Dung lượng cấu hình khác hoặc định dạng khác sẽ có phép tính riêng. [Bảng X.10](thesis-chapter-experiments-vi.md#x5-kết-quả-xác-minh-và-kích-thước) · [Siêu dữ liệu Falcon-512 đã chốt](https://raw.githubusercontent.com/PQClean/PQClean/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/META.yml)

## Y.5. Đặt kết quả vào bối cảnh dữ liệu kế thừa

Tập dữ liệu FALCON/eSign được tạo trong nghiên cứu gốc. Bản thảo này tính lại các thống kê mô tả từ 10 CSV và đối chiếu 5 PDF lưu trữ theo danh mục SHA-256. Mỗi cặp CSV theo nhãn có 100 lượt ký và 100 lượt xác minh. Kích thước trong Bảng Y.2 lấy từ PDF trên đĩa. Các nhãn `50mb` và `500mb` là tên kế thừa và không được dùng làm số đo byte. Cùng nhãn không chứng minh PDF có cùng nội dung hoặc từng lượt gốc đã dùng chính xác bản tệp lưu trữ. [Tác giả nghiên cứu gốc](../CITATION.cff) · [Nguồn gốc dự án](PROJECT_PROVENANCE.md) · [Phân tích dữ liệu kế thừa](phase5-1-experiment-gap-analysis.md)

**Bảng Y.2. Kết quả lịch sử tính lại theo ranh giới đo của dữ liệu gốc.**

| Nhãn gốc | Byte đầu vào | Lượt ký | Lượt xác minh | ok=True | Trung vị tổng các bước ký (ms) | Trung vị tổng xác minh đã lưu (ms) | Số lần Falcon verify crypto = 0 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1mb | 1 048 576 | 100 | 100 | 100 | 83,77 | 25,90 | 97 |
| 10mb | 10 485 760 | 100 | 100 | 100 | 270,30 | 92,82 | 92 |
| 50mb | 55 715 200 | 100 | 100 | 100 | 1228,09 | 387,73 | 95 |
| 200mb | 209 715 200 | 100 | 100 | 100 | 4653,20 | 1409,56 | 96 |
| 500mb | 509 715 200 | 100 | 100 | 100 | 11331,84 | 3400,96 | 97 |

Trong Bảng Y.2, thời gian ký là `ed_total + fal_total` của từng dòng, bỏ cột sinh khóa. Thời gian xác minh lấy từ trường `total` đã ghi. Mã gốc lấy hiệu `time.time()` cho các trường cấp bước và ghi `ok` đối với phép xác minh dương tính. Các trường này chưa đo cùng ranh giới với lời gọi ký, tự xác minh và xuất tệp nguyên tử hiện tại. Nhiều phép đo cấp bước xác minh Falcon ghi 0, từ 92 đến 97 lượt trên mỗi nhóm 100. Điều này phù hợp với khả năng thời gian của bước quá nhỏ so với độ phân giải quan sát, trong khi độ phân giải lịch sử chưa được ghi nhận. Các giá trị đó được giữ nguyên khi đọc lại. [Phương pháp và đồng hồ gốc](phase5-1-experiment-gap-analysis.md#a--inherited-artifacts-and-provenance)

Cả hai tập dữ liệu cho thấy thời gian trung vị tăng từ nhóm 1 đến nhóm 10 MiB trong phạm vi tương ứng. So sánh định tính này có thể trình bày theo từng bộ đo. Việc lấy tỷ số trực tiếp giữa hai tập sẽ đồng thời thay đổi phạm vi đo, quy trình, tệp và điều kiện vận hành. Tập lịch sử thiếu cấu hình CPU, RAM, lưu trữ, bản dựng hệ điều hành và thư viện, thứ tự, mốc thời gian, quy tắc khởi động và mã băm đầu vào theo từng lượt. Môi trường được ghi ở các giai đoạn phát triển sau không khôi phục được các thông số đó. Dữ liệu gốc, thử nghiệm thăm dò Phase 5.2A và kết quả chính Phase 5.2B được lưu theo ba nguồn riêng biệt. [Báo cáo khoảng trống thực nghiệm](phase5-1-experiment-gap-analysis.md) · [Báo cáo chạy thăm dò](phase5-2a-pilot-analysis.md)

## Y.6. Giới hạn của bằng chứng mật mã và sử dụng thực tế

### Y.6.1. Tính hợp lệ với khóa đã chọn

Các phép thử chứng minh cặp chữ ký được chấp nhận với khóa tương ứng và các sửa đổi nội dung hoặc cặp khóa sai đã thử bị từ chối. Bộ xác minh hiện hành kiểm tra cấu trúc một cặp theo thứ tự Ed25519 rồi Falcon-512, vị trí và phạm vi byte, giá trị đệm và kết thúc tệp. Sau khi cấu trúc hợp lệ, kết quả tổng hợp yêu cầu cả hai chữ ký hợp lệ. Quy tắc chấp nhận trong chương trình và độ bao phủ các mẫu thử hỗ trợ nhận định về hành vi đã xem xét. Một chứng minh chống giả mạo hoặc không thể tách các thành phần cần mô hình đối thủ, phát biểu thuộc tính và giả thiết về khóa, mã hóa và giao thức. Các khái niệm đó được phân loại riêng trong RFC 9955. [Trình phân tích cặp](../utils.py#L190) · [Trình xác minh](../verify.py#L48) · [Bindel và cộng sự, RFC 9955](https://www.rfc-editor.org/rfc/rfc9955.html)

### Y.6.2. Tính duy nhất của biểu diễn tệp

Vùng chứa Falcon có một khoảng lưu chữ ký được loại khỏi thông điệp dùng cho chính lớp Falcon. Bộ phân tích ràng buộc cách viết thập phân, hex thường và đệm ASCII `0`. Kiểm toán Phase 5.1A nhận diện từ mã nguồn rằng bộ kiểm tra Falcon có phạm vi chấp nhận biểu diễn rộng hơn dạng nén do bộ ký tạo. Khả năng có hai dãy byte PDF cuối khác nhau cùng được chấp nhận dưới cặp khóa ban đầu vẫn là câu hỏi mở ở mức tích hợp. Kiểm toán chưa quan sát được trường hợp dương tính như vậy. Những phát hiện này giới hạn tuyên bố về tính duy nhất của biểu diễn, đồng thời giữ nguyên giá trị bằng chứng về các phép sửa thuộc vùng ký đã bị từ chối. [Kiểm toán ranh giới toàn vẹn](phase5-1a-signature-integrity-audit.md#impact-assessment)

### Y.6.3. Ràng buộc danh tính và chuẩn trao đổi

Mã định danh Hybrid Key ID nhận diện một cặp khóa công khai có thứ tự. Kết quả xác minh toán học phụ thuộc cặp khóa được trình xác minh chọn. Chữ ký và vùng chứa đang đo không cung cấp một ràng buộc định danh người ký đã xác thực, dấu thời gian tin cậy hoặc thông tin trạng thái chứng thư. Kho khóa cục bộ bảo vệ vật liệu khóa của người dùng trong phạm vi thiết kế của nó. Bằng chứng về sở hữu hay kiểm tra khóa và bằng chứng về danh tính thực là hai yêu cầu riêng. [Mô hình khóa công khai và mã định danh](../hybrid_keys.py#L50) · [Ranh giới tin cậy](phase5-1-implementation-evidence.md#hybrid-key-lifecycle-and-trust-boundary)

HybridSign sử dụng vùng chứa riêng của dự án. CMS và PAdES mô tả cấu trúc và điều kiện tương tác theo chuẩn riêng. Công việc hiện tại cung cấp bằng chứng tái lập về hành vi của nguyên mẫu và phép đo nội bộ. Tuân thủ CMS, PAdES, FIPS 206, khả năng tương tác với trình đọc PDF và khả năng dùng làm sản phẩm ký số cần bằng chứng độc lập tương ứng. Phase 5.1 truy nguyên gói và tệp nhị phân đã dùng, nhưng chưa xác nhận việc dựng lại tệp nhị phân, sự phù hợp toàn bộ với Falcon v1.2 hoặc sự tương thích theo bộ véc-tơ độc lập. [RFC 5652, CMS](https://www.rfc-editor.org/rfc/rfc5652.html) · [ETSI EN 319 142-1 V1.3.1, PAdES](https://www.etsi.org/deliver/etsi_en/319100_319199/31914201/01.03.01_60/en_31914201v010301p.pdf) · [NIST, PQC standardization](https://csrc.nist.gov/projects/post-quantum-cryptography/post-quantum-cryptography-standardization) · [Bằng chứng truy nguyên Falcon](falcon-implementation-provenance.md)

## Y.7. Kết luận trong phạm vi nghiên cứu

Phép đo cho thấy sự đánh đổi giữa độ trễ ký và xác minh của hai thư viện trên các thông điệp giống nhau, và cho thấy chi phí quy trình PDF tăng theo kích thước của các tệp đã thử. Bộ ký thực hiện hai lớp mật mã, các bước chuẩn bị dữ liệu và kiểm tra tính hợp lệ trước xuất. Phần tăng 4 626 byte có thể giải thích hoàn toàn bằng khuôn vùng chứa mặc định. Những kết quả đó có thể kiểm tra lại từ dữ liệu, phiên bản mã và phương pháp đã lưu. Phạm vi suy rộng phụ thuộc độ đa dạng của nền tảng và đầu vào, tính duy nhất của biểu diễn Falcon và nguồn tin cậy của khóa công khai. [Chỉ mục bằng chứng và tái tạo](phase5-3-evidence-index.md)
