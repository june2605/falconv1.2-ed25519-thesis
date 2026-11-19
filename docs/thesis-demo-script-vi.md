# Kịch bản bảo vệ HybridSign 0.1.0

**Thời lượng 4 phút 45 giây · Giao diện tiếng Anh**

Dùng ứng dụng Windows cài sẵn từ Start Menu hoặc mở `HybridSign.exe` trong
thư mục portable đã giải nén đầy đủ. Dùng [bộ tệp đã chuẩn bị](thesis-demo-checklist.md)
và mở sẵn thư mục mẫu trong File Explorer. Giữ mật khẩu trong ô nhập được che.
Các mốc dưới đây dành cho lời trình bày. Nếu hộp thoại hoặc thao tác xử lý chậm,
chờ kết quả thực tế và bỏ qua phần mở rộng ở cuối.

| Thời gian | Thao tác | Màn hình dự kiến | Lời nói | Điểm kỹ thuật |
| --- | --- | --- | --- | --- |
| 0:00–0:35 | Mở **HybridSign** và vào **Dashboard**. | Thanh trên cùng hiển thị **Desktop Connected**. | “Em xin giới thiệu HybridSign, nguyên mẫu ký và kiểm tra chữ ký PDF trên Windows. Hệ thống kết hợp Ed25519, một thuật toán chữ ký cổ điển, với Falcon-512, một thuật toán chữ ký hậu lượng tử. Bộ kiểm tra yêu cầu cả hai chữ ký hợp lệ.” | Ứng dụng desktop đã kết nối trình xử lý Python cục bộ. |
| 0:35–1:15 | Vào **Key Vault**, chỉ vị trí `presentation.hvault` trong Explorer, chọn **Unlock Vault** trong ứng dụng rồi chọn đúng tệp. Nhập mật khẩu trong hộp thoại Windows. | Ban đầu là **No vault unlocked** hoặc **Locked**. Khi mở thành công xuất hiện **Unlocked** và **Hybrid key ID**. | “Tệp này lưu hai khóa riêng dưới dạng mã hóa. Argon2id dẫn xuất khóa từ mật khẩu và AES-256-GCM bảo vệ dữ liệu trong kho. Mở kho cho phép tiến trình ký dùng đúng cặp khóa đã tạo khi chuẩn bị.” | Mật khẩu vào hộp thoại native. Khóa riêng được phục hồi trong bộ nhớ Python. ID hiển thị nhận diện cặp khóa công khai. |
| 1:15–2:05 | Vào **Sign Document** → **Choose PDF** → chọn `sample-unsigned.pdf`. Kiểm tra vault đang **unlocked**, chọn **Continue to review** → **Sign PDF**. Lưu dưới tên mới `live-signed.pdf`. | Có thể hiện trạng thái đang ký và tự kiểm tra. Đợi **Signed PDF saved** và **Completed self-verification**. | “Ed25519 ký trước. Falcon-512 ký trạng thái tiếp theo, trong đó đã có toàn bộ phần chữ ký Ed25519. Chương trình kiểm tra cặp chữ ký trên bản tạm trước khi công bố tệp.” | Chữ ký thứ hai bao phủ chữ ký thứ nhất. Ký và tự kiểm tra chỉ hoàn tất khi kết quả trên màn hình xác nhận. |
| 2:05–2:45 | Vào **Verify Signature** → **Choose signed PDF** → `live-signed.pdf` → **Use authenticated vault** → **Verify PDF**. | **HYBRID VALID** với tên tài liệu đã chọn và Hybrid Key ID của kho. | “Kết quả này cho biết cả hai chữ ký trên phiên bản tệp vừa chọn đều hợp lệ với cặp khóa công khai này. Định danh trên màn hình là định danh cặp khóa. Danh tính người ký cần một cơ chế tin cậy riêng.” | Kiểm tra độc lập lại tệp vừa lưu bằng khóa công khai. |
| 2:45–3:45 | Với cùng nguồn khóa, chọn `rehearsal-signed.pdf` rồi **Verify PDF**. Sau khi thấy **HYBRID VALID**, chọn `rehearsal-tampered.pdf` rồi **Verify PDF** lần nữa. | Kết quả cũ được xóa khi chọn lại. Bản đối chứng hợp lệ, bản đã sửa hiển thị **HYBRID INVALID**. | “Đây là hai tệp em đã chuẩn bị từ lần ký thử bằng chính kho này. Bản thứ hai đổi chữ APPROVED thành REJECTED. Em giữ nguyên nguồn khóa để chỉ thay đổi nội dung đầu vào. Ứng dụng bác bỏ bản sửa vì chữ ký gắn với các byte đã ký.” | So sánh hai bản của cùng lần ký, giữ nguyên nguồn khóa. Trạng thái INVALID áp dụng cho cả cặp, không chỉ ra lớp nào lỗi. |
| 3:45–4:45 | Vào **Key Vault** → **Lock Vault**. Nếu còn thời gian, đóng bình thường, mở lại bằng lối tắt, vào **Key Vault** và mở lại `presentation.hvault`. So sánh ID đã ghi trước. | **Locked**. Sau khi mở lại ứng dụng, **No vault unlocked**. Mở đúng kho đưa về **Unlocked** và cùng ID. | “Khóa kho kết thúc phiên truy cập khóa riêng. Tệp đã ký vẫn kiểm tra được bằng khóa công khai. Sau khi mở lại ứng dụng, kho trả về đúng cặp khóa cũ. Nguyên mẫu minh họa tạo khóa, lưu khóa mã hóa, ký hai lớp và phát hiện sửa tệp. Định dạng chữ ký PDF là định dạng nghiên cứu riêng.” | Tách quyền ký khỏi khả năng kiểm tra công khai. Mở lại kho bảo toàn cặp khóa. Bản phát hành chưa có chứng nhận hay xác thực danh tính người ký. |

**Nếu hội đồng yêu cầu thử sai khóa.** Giữ `rehearsal-signed.pdf`, chọn
**Choose encrypted vault** → `wrong-keys.hvault` → **Verify PDF**.
Màn hình ghi **UNAUTHENTICATED** và kết quả dự kiến là **HYBRID INVALID**.
“Lần này nội dung giữ nguyên, em đổi cặp khóa công khai. Một kết quả INVALID
có thể do nhiều nguyên nhân.” Chọn lại nguồn khóa đúng và chạy **Verify PDF**
trước khi nói kết quả đã phục hồi.

**Nếu phần ký trực tiếp bị gián đoạn.** Nói đúng trạng thái trên màn hình.
Dùng cặp `rehearsal-signed.pdf` và `rehearsal-tampered.pdf` đã kiểm tra trước
đó với khóa của `presentation.hvault`, theo
[bảng xử lý sự cố](thesis-demo-checklist.md#xử-lý-sự-cố-trong-buổi-bảo-vệ).
Trong trường hợp ứng dụng không mở được, dùng ảnh minh chứng đã ghi rõ là ảnh
từ lần thử trước, không giới thiệu như kết quả trực tiếp.
