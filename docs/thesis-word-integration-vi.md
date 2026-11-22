# Đoạn cập nhật để tích hợp vào luận văn Word

Các đoạn dưới đây dùng cho bản Word đang biên tập theo bố cục năm chương. Mốc chèn được xác định theo nội dung mục. Kiểu trình bày, đánh số và danh mục hình bảng áp dụng theo mẫu luận văn Trường Đại học Thăng Long khi dàn trang. [Hướng dẫn tích hợp và truy vết](phase5-5d-thesis-integration.md)

| Chương | Phần dùng trong bản Word |
| --- | --- |
| 1. Mở đầu | Đoạn vấn đề, mục tiêu, câu hỏi và phạm vi ở tài liệu này |
| 2. Cơ sở lý thuyết | Giữ phần lý thuyết đã duyệt. Dùng [1]-[4] để thống nhất tên thuật toán, đặc tả và thuộc tính chữ ký lai |
| 3. Thiết kế và triển khai | Đoạn cấu trúc hai lớp, quy tắc xác minh, kho khóa và vị trí của bộ so sánh nghiên cứu |
| 4. Phương pháp và kết quả thực nghiệm | Chương thực nghiệm cập nhật, bảng PDF và các hình Phase 5.5D |
| 5. Bàn luận và kết luận | Chương bàn luận cập nhật và đoạn kết luận thay thế ở tài liệu này |

## Tóm tắt

Luận văn phát triển và đánh giá HybridSign, một nguyên mẫu ký số PDF kế thừa từ nghiên cứu FALCON/eSign. Ed25519 ký trạng thái thứ nhất. Falcon-512 ký trên tiền băm của trạng thái sau, bao phủ toàn bộ vùng chứa Ed25519. Bộ xác minh yêu cầu cấu trúc đúng và cả hai chữ ký hợp lệ theo cặp khóa công khai được cung cấp. Mục đích của phối hợp hai họ thuật toán là giảm phụ thuộc vào một giả thiết mật mã trong quá trình chuyển đổi hậu lượng tử.

Kết quả thực nghiệm so sánh quy trình lai với hai quy trình PDF đơn lớp trên Windows Server 2022, Ubuntu 24.04 và macOS Intel. Chín phiên logic tạo 4 050 lượt đo và 2 430 PDF trong phần đo. Với PDF 10 MiB, trung vị ký và xuất Hybrid lần lượt là 253,525 ms, 253,174 ms và 727,286 ms trên ba môi trường. Theo khuôn mặc định, phần tăng của PDF là 394 byte với Ed25519, 4 232 byte với Falcon-512 và 4 626 byte với Hybrid. Các đối chứng sửa đổi và sai khóa đã thử đều bị từ chối. Thử nghiệm tương thích trước đó ghi 9 trên 9 phép xác minh thành công khi trao đổi tệp thử và khóa công khai giữa các môi trường. Bằng chứng giới hạn ở nguyên mẫu, tập đầu vào và cấu hình đã kiểm tra. Danh tính người ký, thời gian ký tin cậy và tính duy nhất của biểu diễn byte Falcon còn cần bằng chứng riêng.

**Từ khóa** - chữ ký số lai, Ed25519, Falcon-512, PDF, mật mã hậu lượng tử.

## Chương 1 - Vấn đề, mục tiêu và câu hỏi nghiên cứu

### Đặt vấn đề

Ed25519 là thành phần chữ ký truyền thống dựa trên mật mã đường cong elliptic. Falcon-512 là thành phần hậu lượng tử sử dụng cấu trúc mạng NTRU theo đặc tả Falcon. Thiết kế đặt hai họ thuật toán trong cùng một chính sách xác minh để giảm phụ thuộc vào một họ giả thiết trong giai đoạn chuyển đổi hậu lượng tử. Nguyên mẫu được đánh giá qua quy tắc xác minh của nó, chi phí trên PDF và các trường hợp sử dụng đã thử. [1], [2]

Luận văn kế thừa thứ tự Ed25519 rồi Falcon-512, cách hình thành thông điệp và khuôn vùng chứa từ nghiên cứu FALCON/eSign. Phần phát triển của luận văn bổ sung kiểm tra cấu trúc, giao dịch xuất tệp, quản lý cặp khóa cục bộ và phương pháp đánh giá có đối chứng. [Xuất xứ và tác giả nghiên cứu gốc](PROJECT_PROVENANCE.md) · [Trích dẫn phần mềm gốc](../CITATION.cff)

### Mục tiêu nghiên cứu

Mục tiêu tổng quát là xây dựng nguyên mẫu ký số lai và đánh giá tính đúng chức năng, chi phí và phạm vi sử dụng bằng bằng chứng tái lập. Các mục tiêu cụ thể gồm

- Đặc tả ranh giới byte, thứ tự hai chữ ký và điều kiện chấp nhận của bộ xác minh.
- Định lượng thời gian ký và xuất, thời gian xác minh riêng và số byte tăng thêm so với từng bộ so sánh đơn lớp trên cùng PDF.
- Mô tả biến thiên giữa phiên và giữa ba môi trường thực thi, đồng thời đánh giá khả năng xác minh các tệp và khóa công khai được trao đổi trong thử nghiệm C8.
- Xác định giới hạn liên quan đến quản lý khóa cục bộ, xác thực danh tính, thời gian ký và chuẩn hóa biểu diễn chữ ký.

### Câu hỏi nghiên cứu

1. Hai chữ ký được phối hợp nhằm đáp ứng nhu cầu nào, hai thông điệp ký được xây dựng ra sao và trong điều kiện nào bộ xác minh chấp nhận cặp chữ ký?
2. So với PDF chỉ ký Ed25519 hoặc chỉ ký Falcon-512, quy trình lai tăng bao nhiêu thời gian ký và xuất, thời gian xác minh độc lập và dung lượng lưu trữ?
3. Kết quả thay đổi thế nào giữa các phiên logic trên Windows Server 2022, Ubuntu 24.04 và macOS Intel, và khả năng xác minh chéo được quan sát đến đâu?
4. Từ các đối chứng có thể kết luận gì về hành vi khi nội dung hoặc khóa sai, và những thuộc tính mật mã, danh tính và chuẩn trao đổi nào còn cần bằng chứng?

Phạm vi thực nghiệm so sánh gồm PDF 742 byte, 1 MiB và 10 MiB của Phase 5.5C. Đo chi tiết từng công đoạn và khảo sát PDF 40 MiB nằm trong phần hỗ trợ Phase 5.2. Nghiệm thu giao diện desktop dùng hồ sơ chức năng Windows riêng. [Phương pháp ở Chương 4](thesis-chapter-experiments-vi.md)

## Chương 3 - Cấu trúc chữ ký lai và phạm vi triển khai

Gọi P là dãy byte của PDF nguồn đã chụp, E là trạng thái có vùng chứa Ed25519 hoàn tất và F là tệp có thêm vùng chứa Falcon-512. Mỗi vùng chứa có một khoảng lưu chữ ký, bắt đầu tại dòng `SigLength` và kết thúc trước dấu đóng vùng chứa. Gọi g0, g1 là hai đầu khoảng và end là điểm cuối loại trừ của vùng chứa tương ứng. `ByteRange` có bốn số chỉ hai đoạn được nối theo thứ tự tệp. Quy tắc yêu cầu bắt đầu ở byte 0, bỏ đúng khoảng lưu chữ ký của lớp đó và kết thúc tại end.

```text
E = P || container Ed25519
F = E || container Falcon-512

M_E = E[0:g0_E] || E[g1_E:end_E]
M_F = SHAKE256(F[0:g0_F] || F[g1_F:end_F], 512 bit)
```

Bộ ký chuyển trực tiếp M_E cho Ed25519. Hàm kế thừa mang tên `compute_sha512_digest_for_byte_range()` thực hiện phép nối các đoạn byte. SHA-512 thuộc xử lý nội bộ của Ed25519. Với Falcon-512, M_F là đầu ra 64 byte của tiền băm SHAKE256 ở cấp ứng dụng. Đoạn đầu của thông điệp SHAKE256 bao phủ toàn bộ E, bao gồm chữ ký và phần đệm Ed25519. Bộ xác minh yêu cầu vùng chứa Ed25519 và Falcon-512 liền nhau, theo đúng thứ tự, và vùng chứa cuối kết thúc đúng tại EOF của F. Kết quả hợp lệ yêu cầu điều kiện cấu trúc và cả hai phép xác minh mật mã. [1]-[4] [Ranh giới byte đã kiểm toán](phase5-1a-signature-integrity-audit.md#exact-signed-messages)

Bộ ký chụp nguồn, kiểm tra khóa và chuẩn bị ứng viên trong giao dịch tệp. Ứng viên được ghi, đồng bộ, đóng và xác minh trước khi công bố bằng thay thế nguyên tử. Trên đường quản lý khóa cục bộ, hai khóa riêng được phục hồi trong cùng tiến trình từ một kho khóa đã mở. Định danh Hybrid Key ID giúp đối chiếu cặp khóa công khai. Danh tính người ký cần một ràng buộc tin cậy đối với cặp khóa này. [Giao dịch tệp](../signing_io.py#L114) · [Đường ký qua kho khóa](phase3-2b3-regression.md)

Đặc tả Falcon v1.2 trình bày cơ sở thuật toán. Nguyên mẫu gọi `pqcrypto` 0.3.4, binding `falcon_512` PQClean clean, với wheel và mô-đun native kiểm tra theo hồ sơ đã chốt. Hai đường ký PDF đơn lớp tồn tại trong bộ đo để thực hiện đối chứng. Cả ba đường đo dùng chính sách xác minh ứng viên trước khi xuất. Khoảng ký PDF và xác minh riêng được thống kê từ các khối đo theo phân vị Type 7 ở Chương 4. [2], [5] [Truy nguyên Falcon](falcon-implementation-provenance.md) · [Giao thức đối chiếu PDF](phase5-5a-research-protocol.md)

## Chương 5 - Đoạn kết luận thay thế

Nguyên mẫu thực hiện xác minh hai lớp theo thứ tự Ed25519 rồi Falcon-512 và từ chối các trường hợp đã thử khi một lớp sai hoặc cấu trúc bị thay đổi. Việc kết hợp một chữ ký truyền thống với một chữ ký hậu lượng tử nhằm giảm phụ thuộc vào một họ giả thiết, với điều kiện bảo vệ đúng khóa, thông điệp và quy trình xác minh. Mức an toàn của tổ hợp, đặc biệt chống giả mạo và chống tách thành phần, cần phân tích trong một mô hình đối thủ cụ thể. Hai khóa vẫn có chung ranh giới máy người dùng, nên sự cố ở tiến trình hoặc thiết bị có thể ảnh hưởng cả hai. [4]

Phép đối chiếu PDF 10 MiB trên Windows cho trung vị hiệu ký và xuất của Hybrid là 90,438 ms so với Ed25519 và 129,408 ms so với Falcon-512. Trung vị tỷ số ghép cặp tương ứng là 1,559 và 2,049. Các giá trị là thống kê của từng cặp cùng phiên và khối. Với PDF 10 MiB, mức trễ cao của Ed25519 lặp lại trong ba phiên macOS Intel, đồng thời phần cứng và cấu hình runner khác nhau giữa các môi trường. Nguyên nhân của chênh lệch vẫn cần một phép đo công đoạn có kiểm soát. Hybrid thêm 4 626 byte vào tệp theo khuôn vùng chứa mặc định, gồm phần chữ ký hex, sức chứa đệm và siêu dữ liệu. [So sánh ghép cặp và lưu trữ](tables/phase5-5d-pdf-vi.md)

Chín ô C8 từ Phase 5.5B xác nhận khả năng đọc và xác minh các PDF thử có cùng định dạng khi cung cấp đúng khóa công khai trên ba môi trường. Phạm vi này thuộc lõi xác minh. Nghiệm thu ứng dụng Windows và khả năng đọc chữ ký bằng phần mềm PDF là các đánh giá khác. Toàn bộ byte cuối của một PDF còn phụ thuộc tính duy nhất của biểu diễn native Falcon trong khoảng loại trừ. Danh tính, thời điểm ký tin cậy, tuân thủ Falcon v1.2, FIPS 206, CMS và PAdES vẫn cần bằng chứng tương ứng. [2], [6], [7] [Ma trận C8](phase5-5b-cloud-pilot.md#c8-giữa-các-môi-trường) · [Kiểm toán biểu diễn byte](phase5-1a-signature-integrity-audit.md#impact-assessment)

## Tài liệu tham khảo dùng cho các đoạn cập nhật

Dùng số tham chiếu dưới đây trong các bản thảo Markdown. Đánh lại theo thứ tự xuất hiện trong bản Word hoàn chỉnh.

\[1\] S. Josefsson and I. Liusvaara, “Edwards-Curve Digital Signature Algorithm (EdDSA),” RFC 8032, Jan. 2017. [RFC 8032](https://www.rfc-editor.org/rfc/rfc8032.html)

\[2\] P.-A. Fouque et al., “Falcon: Fast-Fourier Lattice-based Compact Signatures over NTRU,” Specification v1.2, Oct. 2020. [Đặc tả của nhóm tác giả](https://falcon-sign.info/falcon.pdf)

\[3\] National Institute of Standards and Technology, “SHA-3 Standard: Permutation-Based Hash and Extendable-Output Functions,” FIPS PUB 202, Aug. 2015. [FIPS 202](https://csrc.nist.gov/pubs/fips/202/final)

\[4\] N. Bindel, B. Hale, D. Connolly, and F. Driscoll, “Hybrid Signature Spectrums,” RFC 9955, Jul. 2026. [RFC 9955](https://www.rfc-editor.org/rfc/rfc9955.html)

\[5\] R. J. Hyndman and Y. Fan, “Sample quantiles in statistical packages,” The American Statistician, vol. 50, no. 4, pp. 361-365, Nov. 1996, doi: 10.1080/00031305.1996.10473566. [Bài báo do tác giả lưu](https://robjhyndman.com/publications/quantiles/)

\[6\] R. Housley, “Cryptographic Message Syntax (CMS),” RFC 5652, Sep. 2009. [RFC 5652](https://www.rfc-editor.org/rfc/rfc5652.html)

\[7\] ETSI, “Electronic Signatures and Trust Infrastructures (ESI) - PAdES digital signatures - Part 1: Building blocks and PAdES baseline signatures,” ETSI EN 319 142-1 V1.3.1, Nov. 2026. [ETSI EN 319 142-1](https://www.etsi.org/deliver/etsi_en/319100_319199/31914201/01.03.01_60/en_31914201v010301p.pdf)
