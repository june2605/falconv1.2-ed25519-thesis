# Hỏi đáp kỹ thuật khi bảo vệ HybridSign

Các câu trả lời dưới đây mô tả HybridSign 0.1.0 và những gì đã được quan sát
trong kiểm thử. [Báo cáo kỹ thuật và bằng chứng](phase4c3-final-release-review.md)

## Vì sao kết hợp Ed25519 và Falcon-512?

Ed25519 là chữ ký số truyền thống dựa trên đường cong elliptic. Falcon-512 là
chữ ký hậu lượng tử dựa trên mạng NTRU.
Bộ kiểm tra yêu cầu đồng thời cả hai lớp với cặp khóa đã chọn. Mục đích kết hợp
hai họ thuật toán là giảm phụ thuộc vào một họ giả thiết mật mã.
Bảo đảm tổng thể còn phụ thuộc cách kết hợp, chất lượng triển khai và việc
người xác minh có xác định đúng nguồn khóa. Hai khóa vẫn dùng chung thiết bị
và tiến trình ký, nên sự cố tại đó có thể ảnh hưởng cả hai lớp.

## Vì sao dùng thứ tự Ed25519 rồi Falcon-512?

Ed25519 nhận trực tiếp phép nối hai vùng byte của trạng thái thứ nhất theo
`ByteRange`, bỏ qua vùng chứa chữ ký của chính nó. Tên hàm
`compute_sha512_digest_for_byte_range()` trong mã cũ dễ gây nhầm. Hàm thực tế chỉ
nối byte. Đây là thông điệp đưa vào thư viện Ed25519, nơi thuật toán vẫn thực
hiện xử lý nội bộ của nó.

Sau khi chèn chữ ký Ed25519, chương trình thêm container Falcon. Toàn bộ
container Ed25519 nằm trong vùng được Falcon bao phủ. Falcon-512 ký giá trị
SHAKE256 dài 64 byte do ứng dụng tính từ các byte được bao phủ của trạng thái
thứ hai. Cấu trúc bắt buộc không có byte nối thêm sau container Falcon. Thứ tự
này giữ đúng giao thức kế thừa và tạo mối quan hệ lồng giữa hai chữ ký.
[`sign._sign_captured()`](../sign.py) · [Xử lý ByteRange](../utils.py)

## Điều gì xảy ra nếu sửa tài liệu?

Khi thay nội dung thuộc vùng đã ký, thông điệp kiểm tra không còn khớp với
chữ ký của bản gốc. Bộ phân tích cũng kiểm tra riêng số lượng container,
thứ tự, ranh giới, ByteRange, metadata, mã hex và padding chuẩn. Nhờ đó có
thể bác bỏ thêm byte cuối tệp, cắt tệp, hoặc đổi padding Falcon dù phần
padding ấy nằm ngoài thông điệp Falcon. Bài trình diễn giữ nguyên nguồn khóa
và chỉ đổi bản PDF để cô lập nguyên nhân.
Phạm vi kiểm thử là các biến đổi đã thử. Tính duy nhất của biểu diễn chữ ký
Falcon trong vùng lưu bên ngoài thông điệp ký vẫn là câu hỏi mở.
[Kiểm tra phần đệm](phase2b2-regression.md) · [Kiểm tra cặp chữ ký](phase2b3-regression.md) · [Kiểm toán biểu diễn byte](phase5-1a-signature-integrity-audit.md#impact-assessment)

## HYBRID VALID nghĩa là gì? Nếu một chữ ký lỗi thì sao?

Với đúng bản byte được chụp cho lần kiểm tra, cặp container hợp lệ về cấu
trúc và cả Ed25519 lẫn Falcon-512 đều qua xác minh bằng hai khóa công khai
đã chọn. Một lớp thất bại là đủ để không có kết quả hợp lệ. INVALID cũng
có thể do PDF sai cấu trúc hoặc chọn sai khóa. Việc chọn tệp chưa thực hiện
kiểm tra. Lỗi I/O hoặc trạng thái chưa xác nhận được hiển thị theo luồng lỗi.
API công khai trả một boolean tổng hợp cùng dữ liệu thời gian, nên màn hình
không suy ra kết quả riêng từng lớp. [Bộ kiểm tra Python](../verify.py) ·
[Giao diện native](phase4b3b-real-verification-regression.md)

## Hai loại khóa được dùng thế nào?

Khóa riêng Ed25519 và Falcon tạo chữ ký. Hai khóa công khai tương ứng đủ
cho bộ kiểm tra và có thể được cung cấp qua nguồn đã xác minh. HybridSign 0.1.0
cho phép dùng khóa từ kho đã mở hoặc đọc khóa công khai từ tệp kho. Các khóa
công khai đã chọn vẫn dùng được sau khi khóa kho. Tệp kho vẫn chứa phần
khóa riêng đã mã hóa và cần được lưu ở thư mục riêng.

## Khóa riêng được bảo vệ ra sao?

Hai cặp khóa được tạo và tự kiểm tra trong Python. Argon2id dùng muối ngẫu
nhiên để dẫn xuất khóa 32 byte từ mật khẩu. Cấu hình vault v1 dùng 64 MiB,
ba vòng và bốn làn xử lý (lanes). AES-256-GCM mã hóa phần chứa khóa riêng và xác thực
header dưới dạng dữ liệu liên kết. Mật khẩu nhập trong hộp thoại native được
che, còn khóa riêng đã giải mã nằm trong bộ nhớ của tiến trình cục bộ. Khóa
kho kết thúc quyền truy cập quản lý. Mật khẩu yếu vẫn có thể bị đoán ngoại
tuyến nếu kẻ khác lấy được tệp, và tiến trình bị xâm phạm vẫn là rủi ro. Việc
khóa kho không bảo đảm xóa sạch mọi bản sao bộ nhớ. [Đặc tả vault v1](phase3-2-vault-format.md)

## Hybrid Key ID là gì? Có thể bị tráo khóa công khai không?

ID dạng `hybrid-v1:<hex>` là SHA-256 của một miền dành riêng cho ID, tiếp theo
là tên thuật toán và khóa công khai Ed25519, rồi tên thuật toán và khóa công
khai Falcon. Mỗi trường có tiền tố 4 byte theo thứ tự big-endian để ghi độ dài. Đổi khóa làm thay đổi
giá trị băm như kỳ vọng. ID có ích để đối chiếu đúng cặp qua lần mở kho hoặc
qua một kênh tin cậy riêng. Riêng giá trị ID không chứng minh người dùng
nắm giữ khóa riêng.

Nếu chỉ đọc header trong **Choose encrypted vault**, dữ liệu được kiểm tra
cấu trúc và đối chiếu ID nhưng chưa xác thực bằng mật khẩu. Nguồn này mang
nhãn **UNAUTHENTICATED**. Kẻ thay cả tài liệu, cặp khóa và nguồn khóa có thể
cung cấp một bộ dữ liệu tự nhất quán. Người nhận cần khóa hoặc ID đã biết
qua kênh độc lập. Mở vault đã xác thực ràng buộc header với ciphertext của
chính vault đó và mật khẩu. Nó vẫn không tạo chứng thư danh tính.
[Định danh](../hybrid_keys.py) · [Nguồn khóa native](../desktop/verification_service.py)

## Danh tính người ký và thời điểm ký được chứng minh đến đâu?

Phiên mở kho cấp quyền dùng cặp khóa cục bộ. Bản PDF không chứa danh tính,
Hybrid Key ID đã xác thực hay dấu thời gian tin cậy. Phiên bản này chưa có
cơ quan chứng thực, hệ thống đăng ký khóa, thu hồi hay xác minh danh tính.
Kết quả toán học dựa trên tệp và khóa đã chọn, nên không đủ để kết luận về
một cá nhân hoặc hiệu lực pháp lý.

## Có tương thích bảng chữ ký Adobe hoặc có chứng nhận hậu lượng tử không?

HybridSign dùng hai container PDF riêng của nguyên mẫu nghiên cứu. Một
trình đọc PDF có thể hiển thị mẫu, nhưng khả năng tích hợp bảng chữ ký Adobe
hoặc tuân thủ CMS/PAdES chưa được thiết lập. Thành phần được đóng gói là
`pqcrypto==0.3.4` với binding PQClean clean cho `falcon_512`. Khảo sát truy
vết mã nguồn cho thấy nhãn phiên bản triển khai `20211101` cùng bản vá
PQClean. Nhãn đó, phiên bản gói Python và đặc tả Falcon v1.2 là các thông
tin khác nhau. Kết quả thử nghiệm không xác nhận tuân thủ đầy đủ đặc tả
v1.2, FIPS 206 hay chứng nhận hệ thống.
[Khảo sát nguồn gốc Falcon](falcon-implementation-provenance.md)

## Chi phí hiệu năng đã được đo như thế nào?

Phase 5.5C so sánh ba quy trình trên cùng PDF 742 byte, 1 MiB và 10 MiB.
Chín phiên logic trên Windows, Ubuntu và macOS Intel ghi 4 050 lượt đo.
Khoảng ký và xuất gồm kiểm tra khóa, tạo chữ ký, ghi và kiểm tra ứng viên
trước khi xuất. Xác minh tệp đã lưu là phép đo riêng. Nhập mật khẩu, mở
kho và thao tác giao diện nằm ngoài hai khoảng đo.

Với PDF 10 MiB trên Windows, trung vị hiệu ghép cặp của Hybrid là
90,438 ms so với Ed25519 và 129,408 ms so với Falcon-512 khi ký và xuất.
Mức tăng tệp là 4 626 byte theo khuôn vùng chứa mặc định. Độ trễ cao hơn
của Ed25519 trên các runner macOS Intel lặp lại trong ba phiên. Môi trường
thử khác phần cứng và cấu hình, nên chưa xác định được nguyên nhân.

Phase 5.2 ghi riêng kết quả Windows cục bộ và số đo công đoạn. Các CSV
FALCON/eSign vẫn là dữ liệu kế thừa với ranh giới đo riêng.
[Bảng so sánh Phase 5.5C](tables/phase5-5d-pdf-vi.md) · [Kết quả Phase 5.2](phase5-2b-experimental-results.md) · [Dữ liệu kế thừa](phase5-1-experiment-gap-analysis.md)

## Giới hạn của nguyên mẫu và điều kiện để dùng trong thực tế?

Nguyên mẫu trình bày quy trình ký cục bộ, hai chữ ký lồng nhau, lưu khóa mã
hóa và phát hiện bản bị sửa. Nó kiểm tra envelope PDF và định dạng chữ ký
riêng, không phân tích hết nội dung hoặc mã hoạt động của PDF. An toàn của tệp và khóa phụ thuộc vào thiết bị, quyền truy cập Windows và
chất lượng mật khẩu. Khóa phiên
không xóa chắc chắn bộ nhớ. Công bố nguyên tử không bảo đảm bền vững khi
mất điện. Quên mật khẩu có thể mất khả năng ký với cặp đó. Ứng dụng chưa có
quy trình khôi phục mật khẩu.

Nếu triển khai rộng, cần mô hình tin cậy cho khóa, chính sách vòng đời và
thu hồi, cùng định dạng/timestamp tương thích theo yêu cầu sử dụng. Cũng cần
rà soát mật mã và chuỗi cung ứng độc lập, quyết định về bảo vệ khóa trên
thiết bị, kiểm thử tương thích trên máy sạch, ký Authenticode và rà soát quyền
phân phối phụ thuộc. Không suy ra các bảo đảm trên từ số lượng kiểm thử đã qua.
