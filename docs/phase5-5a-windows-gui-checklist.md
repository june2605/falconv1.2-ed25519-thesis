# Phase 5.5A - Checklist chấp nhận desktop trên Windows

**Trạng thái NOT RUN.** Checklist này dùng cho buổi kiểm tra có người thao tác trên Windows. Báo cáo thời gian lõi của pilot được lưu riêng. Windows Server trên CI chưa cung cấp bằng chứng chấp nhận GUI Windows 11. [Báo cáo Phase 5.5A](phase5-5a-research-comparison-readiness.md)

- [ ] Ghi phiên bản Windows, build ứng dụng hoặc SHA-256 bản portable, thời điểm, vị trí lưu riêng và người thực hiện. Dùng bản phát hành đã duyệt nếu mục tiêu là chấp nhận bản phát hành.
- [ ] Tạo kho khóa quản lý dùng thử ở thư mục mới. Đặt mật khẩu thử riêng. Ghi Hybrid Key ID và tên tệp công khai trong phiếu kiểm tra. Giữ mật khẩu và vật liệu bí mật ngoài ảnh chụp, nhật ký và bằng chứng xuất.
- [ ] Khóa và mở ứng dụng lại. Chọn kho đã tạo qua hộp thoại native bằng thao tác của người dùng. Kiểm tra mật khẩu sai bị từ chối, sau đó mật khẩu đúng mở đúng kho và vẫn cho cùng ID.
- [ ] Chọn `demo_assets/sample-unsigned.pdf` bằng hộp thoại mở tệp thật. Dùng hộp thoại lưu để chọn tên đầu ra riêng. Thử hủy hộp thoại và xác nhận chưa có tệp xuất.
- [ ] Ký qua desktop worker. Ghi nhận trạng thái tiến độ và phản hồi cuối. Xác nhận tệp chỉ xuất hiện sau giao dịch thành công và tệp nguồn vẫn nguyên byte.
- [ ] Xác minh qua GUI bằng cặp khóa công khai đúng. Kiểm tra báo cáo hiển thị hai chữ ký hợp lệ. Dùng bản thử riêng để xác minh từ chối khi sửa nội dung thuộc vùng ký, hoặc khi lần lượt dùng sai khóa Ed25519 và sai khóa Falcon.
- [ ] Thử một đích không thể ghi hoặc thao tác bị hủy phù hợp với giao diện. Xác nhận bản đích có sẵn và kho thử được giữ nguyên khi giao dịch thất bại.
- [ ] Khóa kho, thoát ứng dụng và kiểm tra không còn worker đang ký. Chỉ lưu kết quả PASS, FAIL hoặc NOT RUN cho từng mục và các ảnh đã kiểm tra dữ liệu riêng tư.

Khi dùng tự động hóa, ghi rõ bước đã thực sự điều khiển hộp thoại native. Seam chọn tệp dùng trong unit test là bằng chứng kiểm thử mô phỏng ở mức API. Chỉ dùng kết quả thao tác hộp thoại thật làm bằng chứng cho các mục chọn tệp thủ công. [Quy trình demo của bản phát hành](thesis-demo-checklist.md)
