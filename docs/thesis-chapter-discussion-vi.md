# Chương 5. Bàn luận và kết luận

## 5.1. Động cơ mật mã và chính sách xác minh

Ed25519 là chữ ký số truyền thống dựa trên mật mã đường cong elliptic. Falcon-512 là thành phần hậu lượng tử dựa trên mạng NTRU. Việc dùng hai họ giả thiết có mục đích giảm phụ thuộc vào một thuật toán trong bối cảnh chuyển đổi hậu lượng tử. Lập luận này phụ thuộc vào tính an toàn của các thành phần, cách ràng buộc thông điệp, nguồn tin cậy của khóa và tính đúng của triển khai. RFC 9955 phân biệt mục tiêu xác thực lai, khả năng xây dựng chứng minh và thuộc tính chống tách chữ ký thành phần. [1], [2], [4] [Truy nguyên lựa chọn thuật toán](phase5-1-research-audit.md)

Nguyên mẫu triển khai một quy tắc cụ thể. Ed25519 ký vùng byte của trạng thái thứ nhất. Falcon-512 ký trên tiền băm 64 byte của trạng thái sau, trong đó có toàn bộ vùng chứa Ed25519. Sau khi phân tích đúng một cặp vùng chứa liền nhau và đúng thứ tự, bộ xác minh yêu cầu cả hai phép kiểm tra đều thành công với hai khóa được cung cấp. Kiểm thử xác nhận quy tắc này ở các trường hợp hợp lệ, trường hợp chỉ một lớp hợp lệ và các lỗi cấu trúc đã thử. Chứng minh chống giả mạo lai và chống tách thành phần cho định dạng PDF cụ thể vẫn cần mô hình đối thủ, giả thiết và phân tích riêng. Điều kiện chấp nhận hai lớp tự nó không cung cấp một thước đo định lượng về mức an toàn. [4] [Cấu trúc và xác minh](phase5-1a-signature-integrity-audit.md#exact-signed-messages) · [Thử riêng từng lớp](thesis-chapter-experiments-vi.md#410-tính-đúng-và-khả-năng-xác-minh-giữa-các-môi-trường)

Hai khóa riêng cùng nằm trong ranh giới bảo mật của ứng dụng bản địa và máy người dùng. Trên đường ký qua kho khóa được quản lý, một lần mở kho cung cấp cặp khóa đã tạo trước đó cho tiến trình xử lý. Nếu tiến trình đã mở khóa hoặc thiết bị bị kiểm soát, đối thủ có thể tiếp cận cả hai thành phần hoặc điều khiển đầu vào được ký. Một sai sót dùng chung trong bộ phân tích, quy trình chọn khóa công khai hoặc giao dịch tệp cũng có thể ảnh hưởng tới toàn bộ kết quả xác minh. Đa dạng thuật toán đáp ứng rủi ro ở lớp giả thiết mật mã, còn rủi ro dùng chung đòi hỏi biện pháp ở lớp quản lý khóa, thiết bị và phần mềm. [Ranh giới của kho khóa và tiến trình ký](phase3-2b3-regression.md) · [Ranh giới tin cậy](phase5-1-implementation-evidence.md#hybrid-key-lifecycle-and-trust-boundary)

## 5.2. Chi phí thời gian và biến thiên

Phase 5.5C so sánh ba quy trình cùng chính sách tự xác minh trước khi xuất. Phần chênh lệch bao gồm số lần kiểm tra khóa, xử lý vùng chứa, tiền xử lý dữ liệu, xác minh ứng viên và I/O thực tế. Trung vị thời gian Hybrid cao hơn các trung vị đơn lớp ở mọi điều kiện đo. Các tỷ số ghép cặp cho thấy mức tăng phụ thuộc vào phương pháp đối chiếu. Ví dụ ở 10 MiB, trung vị tỷ số ký và xuất Hybrid so với Falcon-512 là 2,049 trên Windows, 1,810 trên Ubuntu và 5,856 trên macOS Intel. Với xác minh độc lập, các giá trị tương ứng là 1,972, 1,973 và 5,562. Đây là tỷ số tính từng cặp cùng khối. Phân bố của tổng thời gian quy trình được đo trực tiếp, bao gồm các khâu ngoài hai lời gọi mật mã thành phần. [Kết quả và tương phản ghép cặp](tables/phase5-5d-pdf-vi.md#so-sánh-ghép-cặp)

Đối với PDF 10 MiB, trung vị ký và xuất Ed25519 ở macOS Intel cao trong cả ba phiên. P95 gộp trên môi trường này là 1 113,937 ms. Dữ liệu giữ các lượt chậm và thể hiện biến thiên giữa các phiên. Windows ghi nhận hai loại CPU, còn Ubuntu thay đổi CPU, image và kernel giữa các phiên. Môi trường macOS Intel dùng cấu hình phần cứng quan sát được khác các runner kia. Với từng điều kiện, 90 quan sát thuộc ba phiên logic. Metadata không nhận diện chín máy độc lập về vật lý. Giả thuyết liên quan đến thời gian quét byte, mô-đun native, I/O hoặc cấp phát bộ nhớ có thể được kiểm tra bằng cách cố định các yếu tố còn lại. Dữ liệu hiện tại xác lập chênh lệch quan sát được ở cấp quy trình, chưa phân lập nguyên nhân. [Thông số từng runner](phase5-5c-cross-platform-main.md#môi-trường-thực-tế) · [Bảng P95 và trung vị từng phiên](tables/phase5-5d-pdf-vi.md#ký-và-xuất)

Khác biệt giữa các tầng đo giải thích cách đọc kết quả. Ed25519 nhận các đoạn byte đã ghép, nên số byte đưa vào lời gọi tăng theo dung lượng PDF. Falcon nhận bản tiền băm SHAKE256 dài 64 byte, nhưng tính bản tiền băm vẫn phải xử lý các vùng thuộc thông điệp. Ngoài ra, giao dịch tệp phải đọc, ghi và kiểm tra lại ứng viên. Các phân rã công đoạn của Phase 5.2B trên Windows hỗ trợ cách giải thích này trong cấu hình đã đo. Muốn kiểm tra nguyên nhân của chênh lệch macOS cần đo từng công đoạn trong một thiết kế kiểm soát riêng. [3] [Phân rã Phase 5.2B](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai)

## 5.3. Chi phí lưu trữ

So với tệp chỉ có Ed25519, Hybrid tăng thêm 4 232 byte. So với tệp chỉ có Falcon-512, Hybrid tăng thêm 394 byte. Mức tăng so với tệp gốc là 4 626 byte. Vì kích thước phần thêm cố định trong cấu hình đo, tỷ lệ theo dung lượng gốc là khoảng 623,45% với mẫu 742 byte và 0,044% với PDF 10 MiB. [Số đo kích thước](tables/phase5-5d-pdf-vi.md#kích-thước-đầu-ra)

Cách tính bắt đầu từ khuôn vùng chứa. Ed25519 dùng 128 ký tự hex cho chữ ký gốc 64 byte và 128 ký tự đệm. Falcon-512 ở PDF lai dùng từ 1 298 đến 1 324 ký tự hex cho chữ ký 649-662 byte, phần còn lại của ô 4 096 byte là đệm ASCII `0`. Hai phần khung cộng 274 byte. API của binding Falcon công bố giới hạn chữ ký rời 752 byte, còn mức dành trước 2 048 byte do nguyên mẫu quy định. Chi phí ghi thêm phụ thuộc cách mã hóa, dung lượng dành trước và cú pháp của định dạng thử nghiệm. [Giới hạn API đã ghim](https://raw.githubusercontent.com/PQClean/PQClean/2cc64716044832eea747234ddbffc06746ab815d/crypto_sign/falcon-512/clean/api.h) · [Khuôn mặc định](../utils.py#L223)

## 5.4. Giới hạn của bằng chứng mật mã và sử dụng thực tế

<a id="y6-giới-hạn-của-bằng-chứng-mật-mã-và-sử-dụng-thực-tế"></a>

### 5.4.1. Toàn vẹn của vùng đã ký và biểu diễn byte cuối

Các kiểm thử hỗ trợ kết luận về từ chối sửa đổi đã thử ở vùng nội dung được bảo vệ và sai khóa. Khoảng lưu chữ ký Falcon ngoài cùng nằm ngoài thông điệp của chính lớp Falcon. Parser kiểm tra cú pháp, độ dài, hex thường và đệm ASCII `0`. Sau khi giải mã, bộ xác minh native kiểm tra chữ ký trên thông điệp đã cấu tạo. Phase 5.1A chỉ ra từ mã nguồn rằng bộ giải mã native chấp nhận phạm vi biểu diễn rộng hơn dạng nén do trình ký xuất. Kiểm toán chưa quan sát được tệp PDF đã đổi byte vẫn hợp lệ dưới cặp khóa gốc mà không tạo chữ ký mới. Sự duy nhất của biểu diễn native và kết luận phát hiện mọi biến đổi của toàn bộ dãy byte cuối vẫn chưa được xác lập. [Kiểm toán ranh giới toàn vẹn](phase5-1a-signature-integrity-audit.md#impact-assessment)

### 5.4.2. Danh tính, thời gian và tương thích

Kết quả xác minh là tính hợp lệ của hai chữ ký theo cặp khóa công khai đã chọn. Hybrid Key ID định danh cặp khóa có thứ tự. Để xác thực danh tính người ký, nguồn cung cấp cặp khóa phải có ràng buộc tin cậy riêng. Định dạng hiện tại thiếu cơ chế chứng nhận danh tính và dấu thời gian tin cậy. Nếu nguồn khóa bị tráo, kết quả xác minh dương tính chỉ có ý nghĩa theo khóa đã thay. [Mô hình khóa công khai](../hybrid_keys.py#L50) · [Ranh giới nguồn khóa](phase4b3b-real-verification-regression.md#public-key-source-trust)

C8 kiểm tra việc trao đổi tệp và khóa công khai giữa ba môi trường chạy cùng lõi xác minh. Phạm vi desktop được nghiệm thu riêng trên Windows. Hỗ trợ GUI Linux hoặc macOS và bảng chữ ký của trình đọc PDF cần phép thử độc lập. CMS và PAdES có cấu trúc và yêu cầu riêng, trong khi phép đo dùng vùng chứa tùy chỉnh của HybridSign. Đặc tả Falcon v1.2 là tài liệu lý thuyết. Kết quả hiện tại nhận diện binding đã chạy và hành vi trên mẫu thử, chưa xác lập tuân thủ toàn bộ Falcon v1.2, FIPS 206, CMS, PAdES hay chứng nhận mô-đun. [2], [6], [7] [C8 đã chấp nhận](phase5-5b-cloud-pilot.md#c8-giữa-các-môi-trường) · [Phạm vi nghiệm thu desktop](phase4c3-final-release-review.md#readiness-and-remaining-acceptance)

### 5.4.3. Phạm vi suy rộng của phép đo

Ba cỡ PDF được sinh từ một mẫu công khai. Số liệu mô tả thời gian trên các biến thể kích thước của mẫu và cấu hình runner đã ghi. Mức độ phức tạp cấu trúc PDF, thiết bị đầu cuối, tải đồng thời, kho khóa và tương tác GUI có thể thay đổi độ trễ thực tế. P95 là phân vị mô tả của các quan sát trong mẫu. Để ước lượng ảnh hưởng riêng của hệ điều hành, cần kiểm soát phần cứng, filesystem, bản dựng thư viện và tải nền trong thiết kế thực nghiệm khác. [Thiết kế và giới hạn phép đo](phase5-5a-research-protocol.md#4-thống-kê-và-diễn-giải)

## 5.5. Bằng chứng bổ trợ của Phase 5.2 và dữ liệu kế thừa

Các mục Y giữ phần phân tích của nghiên cứu Windows cục bộ và đối chiếu lịch sử. Phần đo chi tiết theo công đoạn giúp lý giải cấu trúc chi phí, còn so sánh trực tiếp ba quy trình PDF dùng dữ liệu đồng thời của Phase 5.5C. [Phương pháp Phase 5.2A](phase5-2a-benchmark-methodology.md) · [Kết quả Phase 5.2B](phase5-2b-experimental-results.md)

### Y.1. Đánh đổi hiệu năng giữa hai thuật toán

Cùng một hệ thống đo cho thấy Falcon-512 có trung vị ký lớn hơn Ed25519 ở cả hai thông điệp ngắn, còn trung vị xác minh Falcon-512 thấp hơn. Khi gộp ba phiên, các tỷ số ký lần lượt là 115,884 và 108,384. Hai tỷ số xác minh là 0,486 và 0,519. Đây là tỷ số của trung vị chưa làm tròn ở mức thuật toán trong Phase 5.2B. Độ dài thông điệp ở đây chỉ nhận hai giá trị. Các phép đo bao gồm đường gọi thư viện từ Python và thao tác mật mã tương ứng. Chi phí sinh khóa được ghi riêng. Kết quả áp dụng cho đúng các cấu hình thư viện được kiểm tra. [Bảng X.3-X.5](thesis-chapter-experiments-vi.md#x3-kết-quả-thời-gian-ở-mức-thuật-toán)

Đặc tả Falcon mô tả cách ký dựa vào lấy mẫu trên mạng NTRU và sử dụng biến đổi Fourier nhanh. Lấy mẫu trong đường ký là một nguyên nhân có thể góp phần tạo ra chênh lệch. Đường xác minh kiểm tra một chữ ký đã có và thực hiện các phép toán khác với đường ký. Ed25519 trong thực nghiệm được gọi qua PyNaCl và cài đặt EdDSA của libsodium. Đây là giải thích dựa trên cấu trúc thuật toán và mã gọi, chứ dữ liệu thời gian thực nghiệm chỉ đo tổng độ trễ ở biên API. Phần đo không tách thời gian lấy mẫu, số lần lặp của thuật toán, chi phí liên kết Python và tối ưu hóa ở mức lệnh máy. Vì vậy, thứ tự độ trễ quan sát được không đủ để khẳng định ưu thế tổng quát cho mọi cài đặt hay thiết bị. [Falcon Specification v1.2](https://falcon-sign.info/falcon.pdf) · [RFC 8032, mục 5.1](https://www.rfc-editor.org/rfc/rfc8032.html#section-5.1) · [Mã PyNaCl 1.6.2](https://github.com/pyca/pynacl/blob/1.6.2/src/nacl/signing.py)

### Y.2. Ảnh hưởng của dung lượng PDF và chi phí giao dịch

Từ 1 lên 10 MiB, trung vị của toàn lời gọi ký và xuất tăng khoảng 5,35 lần, từ 48,253 lên 257,992 ms. Trung vị của phép xác minh độc lập tăng khoảng 9,61 lần, từ 7,677 lên 73,749 ms. Tỉ lệ tăng của từng thao tác phụ thuộc nguồn chi phí ở biên đo. Các kích thước chính chỉ có ba mức và PDF được dựng từ cùng một mẫu. Kết quả chứng minh xu hướng tăng đối với nhóm đầu vào kiểm soát này. Việc suy ra quy luật tăng trưởng cho mọi PDF hoặc ngoài miền đo cần dữ liệu khác. [Bảng X.6-X.7 và Hình X.3-X.4](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai)

Khi PDF lớn hơn, các lời gọi xử lý nhiều byte hơn. Đường ký Ed25519 nhận nội dung ghép dài hơn, trong khi Falcon nhận đầu ra SHAKE256 dài 64 byte ở mọi kích thước. Theo bảng đo chi tiết, từ 1 lên 10 MiB, trung vị của lời gọi ký Ed25519 tăng từ 5,663 lên 57,604 ms, còn trung vị của lời gọi ký Falcon-512 xấp xỉ 4,39 ms ở cả hai kích thước. Trung vị tiền băm Falcon tăng từ 2,617 lên 25,762 ms. Tự xác minh tệp tạm tăng từ 14,791 lên 82,890 ms. Các quan sát này phù hợp với việc nhiều công đoạn phụ thuộc lượng dữ liệu và Falcon nhận thông điệp đã rút gọn có độ dài cố định. Phép đo minh họa vị trí phát sinh chi phí trong quy trình. Các trung vị cấp bước không cộng lại thành một thời gian giao dịch và chưa định lượng tác động nhân quả của từng bước. [Bảng X.9](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai) · [Bộ đo cấp bước](../research/benchmarks/phase5_2a.py#L184)

Có thêm chi phí kiểm tra khóa trong bộ nhớ, sao chép, tạo và điền hai vùng chứa, ghi và đồng bộ tệp tạm, tự xác minh, dọn dữ liệu làm việc và thay thế tệp đích. Cấu trúc này giải thích vì sao so sánh giữa hai lời gọi ký ở mức thuật toán và phép đo toàn quy trình có phạm vi khác nhau. Phase 5.2B chỉ đo quy trình PDF lai. Chi phí tăng thêm khi so với từng quy trình đơn thuật toán được đo riêng ở Phase 5.5C. Phép xác minh của tệp đã xuất độc lập với khoảng tính giờ ký. GUI, hộp thoại và kho khóa nằm ngoài phạm vi các số liệu đã đo. [Bộ ký](../sign.py#L43) · [Giao dịch tệp](../signing_io.py#L114)

Phiên bổ sung 40 MiB cung cấp thêm một điểm thực nghiệm trên cùng máy. Trung vị của phiên đó đạt 1 081,842 ms đối với ký và xuất và 309,516 ms đối với xác minh độc lập. Cả kích thước lẫn tiến trình đều thay đổi so với ba nhóm chính. Điểm bổ sung hỗ trợ thảo luận xu hướng ở kích thước đã thử. Nó không ước lượng được biến thiên giữa các tiến trình đối với 40 MiB. [Bảng X.8 và tiền kiểm](thesis-chapter-experiments-vi.md#x25-điều-kiện-bổ-sung-40-mib)

### Y.3. Biến thiên nội phiên và giữa phiên

Độ phân tán của các lượt ký và xuất thể hiện rõ ở đuôi trên. Đối với mẫu 742 byte, trung vị gộp là 24,542 ms, IQR 2,349 ms, SD mẫu 18,420 ms và P95 74,695 ms. Trung vị giữa từng phiên dao động từ 24,395 đến 24,747 ms. Ở 10 MiB, trung vị theo phiên từ 254,529 đến 262,827 ms, trong khi IQR gộp là 11,100 ms, SD mẫu là 41,327 ms và P95 là 338,591 ms. IQR mô tả độ rộng của phần trung tâm. SD và P95 phản ánh mạnh hơn các lượt chậm được giữ trong dữ liệu. Hình X.5 xếp đủ 30 quan sát của từng phiên theo thời gian tăng dần, cho thấy những điểm chậm được giữ ở đầu mút mỗi chuỗi. Số thứ hạng trong hình khác với thứ tự thực thi trong CSV. [Bảng X.6-X.7 và Hình X.5](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai)

Phiên 40 MiB có IQR ký 42,526 ms và SD mẫu 295,140 ms. Quan sát ký chậm nhất đạt 2 599,060 ms. Phân bố xác minh cùng phiên có IQR 14,691 ms, SD mẫu 10,467 ms và P95 327,227 ms. Các lượt ký chậm vẫn hoàn tất kiểm tra dương tính và âm tính. Giả thuyết có thể xem xét là tác động của bộ đệm tệp, độ trễ I/O, lịch hệ điều hành, cấp phát bộ nhớ hoặc thu gom rác. Nhật ký ghi thời gian và kết quả ở biên lời gọi, không ghi sự kiện đồng thời đủ chi tiết để quy nguyên nhân cho từng lượt. [Bảng X.8-X.9](thesis-chapter-experiments-vi.md#x4-kết-quả-quy-trình-pdf-lai) · [Cực trị trong bảng tính thống kê Phase 5.2B](phase5-2b-statistical-analysis.md#hybrid-pdf-signing-and-independent-verification)

Ba phiên là ba lần khởi động tiến trình trên cùng một thiết bị, được chạy liên tiếp. Ngay cả trong mỗi phiên, các quan sát có thể chia sẻ trạng thái hệ thống, thiết bị lưu trữ và thứ tự của khối. Khoảng Q1-Q3 mô tả phân bố mẫu, còn khoảng nhỏ nhất-lớn nhất của các trung vị mô tả chênh lệch quan sát giữa các phiên. Chúng không được diễn giải thành khoảng tin cậy của tham số tổng thể. P95 nội suy từ 30 hoặc 90 quan sát tương ứng, phù hợp với mục đích mô tả. Kết quả không đưa ra giá trị p, mức bảo đảm dịch vụ hoặc suy luận về quần thể máy Windows. Thử nghiệm trên các máy và loại lưu trữ khác nhau cần được thiết kế riêng để đo độ nhạy theo nền tảng. [Cách tính phân vị và phương pháp báo cáo](thesis-chapter-experiments-vi.md#x24-thiết-bị-đo-và-thống-kê)

### Y.4. Chi phí lưu trữ của định dạng mặc định

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

### Y.5. Đặt kết quả vào bối cảnh dữ liệu kế thừa

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

Dữ liệu kế thừa và Phase 5.2B đều cho thấy thời gian trung vị tăng từ nhóm 1 đến nhóm 10 MiB trong phạm vi tương ứng. So sánh định tính này có thể trình bày theo từng bộ đo. Việc lấy tỷ số trực tiếp giữa hai tập sẽ đồng thời thay đổi phạm vi đo, quy trình, tệp và điều kiện vận hành. Tập lịch sử thiếu cấu hình CPU, RAM, lưu trữ, bản dựng hệ điều hành và thư viện, thứ tự, mốc thời gian, quy tắc khởi động và mã băm đầu vào theo từng lượt. Môi trường được ghi ở các giai đoạn phát triển sau không khôi phục được các thông số đó. Dữ liệu gốc, thử nghiệm thăm dò Phase 5.2A và kết quả chính Phase 5.2B được lưu theo ba nguồn riêng biệt. [Báo cáo khoảng trống thực nghiệm](phase5-1-experiment-gap-analysis.md) · [Báo cáo chạy thăm dò](phase5-2a-pilot-analysis.md)

## 5.6. Kết luận

Luận văn xác định chính xác hai thông điệp ký nối tiếp, kiểm chứng quy tắc chấp nhận hai lớp ở các trường hợp đã thử và đo chi phí bổ sung bằng hai bộ so sánh cùng ranh giới giao dịch. Kết quả cho phép định lượng độ trễ và số byte thêm vào trong phạm vi cấu hình đã chốt. C8 cung cấp bằng chứng về khả năng xác minh tệp thử giữa ba môi trường của lõi HybridSign. Các kết quả về toàn vẹn ở vùng đã ký, tương thích bản dựng và chi phí vận hành có phạm vi riêng.

Những câu hỏi tiếp theo gồm tính chuẩn tắc của mã hóa Falcon trong vùng loại trừ, phân tích chính thức thuộc tính chống giả mạo hoặc tách thành phần, nguồn tin cậy của khóa công khai và nguyên nhân chênh lệch hiệu năng trên các runner macOS Intel. Mỗi câu hỏi cần thiết kế kiểm tra và tiêu chí chấp nhận riêng. [Chỉ mục bằng chứng Phase 5.5D](phase5-5d-thesis-integration.md) · [Tài liệu tham khảo IEEE](thesis-word-integration-vi.md#tài-liệu-tham-khảo-dùng-cho-các-đoạn-cập-nhật)
