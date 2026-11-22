# Phase 5.6A - Thay đổi chính về ngôn ngữ giao diện

| Vị trí | Trước | Sau |
| --- | --- | --- |
| Cửa sổ Windows và chỉ báo | HybridSign Desktop Preview, Desktop Connected | **HybridSign 0.1.0**, **Desktop**. Trình duyệt vẫn ghi **UI PREVIEW** |
| Dashboard | Your digital signing workspace, A fresh start for your documents | **Dashboard**, **No demo activity yet**. Trạng thái ký thực nằm ở Sign Document |
| Ký chưa có kết quả xác nhận | Reconcile native status, Native communication could not confirm the outcome | **Check signing status**. Thông báo nêu rằng PDF có thể đã được lưu và cần kiểm tra vị trí lưu trước khi thử lại |
| Ký hoàn tất | Completed self-verification | **Both signatures verified**, chỉ hiển thị bên dưới **Signed PDF saved** khi ứng dụng đã xác nhận kết quả |
| Chọn PDF để xác minh | Its bytes stay in Python for snapshot verification | **Choose a signed PDF to check on this device.** |
| Nguồn khóa xác minh | Use authenticated vault, Authenticated at selection | **Use unlocked vault keys**, **Vault unlocked when selected**. Khóa được chọn vẫn dùng để xác minh sau khi khóa kho |
| Xác minh chưa có kết quả | Reconcile native status | **Check verification status**. Kết quả chỉ hiện khi phép xác minh hoàn tất |
| Key Vault | Confirmed by Python, Recovery needs key material | **Private keys stay on this device**, **Keep your vault and password** |
| Settings và About | Tên Phase 4A/4B, A clearer way to sign | **Version 0.1.0**, **About HybridSign**. Nội dung mô tả khả năng của bản đang chạy |
| Hộp thoại mật khẩu | Password stays in local Python/.NET memory | **Enter your vault password here. It stays on this device.** |
| Nhãn hỗ trợ bàn phím và trình đọc màn hình | Expand preview layout, About this prototype | **Expand document illustration**, **About this app**. Chú giải Auto cũng nêu hành vi theo trạng thái bật hoặc tắt |

**HYBRID VALID** và **HYBRID INVALID** vẫn áp dụng cho cả cặp chữ ký theo khóa đã chọn. **UNAUTHENTICATED** vẫn đánh dấu khóa công khai đọc từ tệp kho chưa mở. Các nhãn này mô tả kết quả hoặc nguồn khóa. Danh tính và thời điểm ký cần bằng chứng riêng.

Nhãn trong bảng áp dụng cho bản chạy từ mã nguồn hiện tại. Gói Windows đã nghiệm thu và ảnh lưu trước đó dùng lời văn của lần phát hành đó. [Bảng đối chiếu cho buổi bảo vệ](thesis-demo-checklist.md#nhãn-trên-bản-phát-hành-và-bản-từ-mã-nguồn) · [Báo cáo biên tập](phase5-6a-repository-editorial-audit.md)
