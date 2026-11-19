# Chuẩn bị và nghiệm thu HybridSign trên máy bảo vệ

Mọi ô kiểm bên dưới đang **chờ người thực hiện trên máy trình chiếu thực tế**.
Kiểm thử tự động trên máy phát triển và ảnh từ các lần thử trước là bằng chứng
khác. Kiểm thử trên máy ảo Windows sạch **chưa thực hiện**.

## 1. Chuẩn bị bản phát hành

- [ ] Ghi ngày, người kiểm tra, máy, phiên bản Windows, kiến trúc, WebView2,
  .NET Framework, cấu hình màn hình và phương thức chạy. Bản đã thử dùng
  Windows 11 x64. Setup yêu cầu Windows x64. Ghi nhận tương thích theo
  cấu hình thực tế đã thử.
- [ ] Đối chiếu SHA-256 của đúng **HybridSign 0.1.0** với
  [bảng phát hành](phase4c3-final-release-review.md#release-integrity). Giữ
  bộ cài hoặc ZIP portable đã duyệt từ nguồn do nhóm kiểm soát. Giữ kèm
  `THIRD-PARTY-NOTICES.txt`.
- [ ] Xác nhận **Microsoft Edge WebView2 Evergreen 111+** và **.NET Framework
  4.6.2+** trước buổi bảo vệ. Nếu thiếu, dùng nguồn Microsoft và quy trình
  được quản trị máy cho phép. Hai runtime nằm ngoài gói ứng dụng.
  [WebView2 Evergreen](https://developer.microsoft.com/microsoft-edge/webview2/) ·
  [.NET Framework](https://dotnet.microsoft.com/en-us/download/dotnet-framework)
- [ ] Kiểm tra chính sách chạy tệp chưa ký Authenticode. Nếu chính sách từ chối,
  dùng máy hoặc bản dự phòng đã được chấp thuận. Giữ nguyên Defender và SmartScreen.
- [ ] Bản cài đặt theo người dùng → **Start Menu** → **HybridSign**. Kiểm
  tra lối tắt Desktop nếu đã chọn lúc cài. Với bản portable, giải nén toàn
  bộ ZIP trên ổ đĩa cục bộ, giữ thư mục `HybridSign` cùng `_internal`,
  rồi mở `HybridSign.exe` từ Explorer. Trên sân khấu chỉ cần ứng dụng và
  Explorer. Không cần VS Code, PowerShell, Python, Node hoặc máy chủ phát triển.
- [ ] Kiểm tra **Desktop Connected**. Nếu cần trình bày ngoại tuyến, tập mở
  ứng dụng và chạy quy trình khi máy đã ngắt mạng theo chính sách cơ sở.
  Ghi kết quả thực tế. Ứng dụng dùng tài nguyên cục bộ nhưng việc có sẵn
  và hoạt động của runtime trên máy này cần được xác nhận.

## 2. Chuẩn bị bộ tệp trình diễn

Chọn thư mục riêng do tài khoản trình bày quản lý trên ổ **NTFS cố định, cục bộ**,
nằm ngoài cả thư mục mã nguồn và thư mục chứa ứng dụng. Kiểm tra quyền tạo, đọc
và ghi tệp bằng tài khoản đó. Tránh thư mục đồng bộ, ổ mạng, USB và đường dẫn
chuyển hướng. Nếu bị từ chối, chọn thư mục được cấp quyền phù hợp và giữ nguyên
các kiểm tra ACL và đường dẫn của ứng dụng.

| Tên tệp | Vai trò |
| --- | --- |
| `sample-unsigned.pdf` | Bản sao nguyên byte của [mẫu công khai](../demo_assets/sample-unsigned.pdf) 742 byte. |
| `presentation.hvault` | Kho mã hóa dùng riêng cho buổi trình diễn. Mật khẩu do người trình bày tự đặt và chỉ gõ vào hộp thoại native. |
| `rehearsal-signed.pdf` | Bản hợp lệ đã ký và kiểm tra từ trước với cặp khóa trong `presentation.hvault`. |
| `rehearsal-tampered.pdf` | Bản sao của `rehearsal-signed.pdf` đã đổi `APPROVED` thành `REJECTED`. |
| `wrong-keys.hvault` | Kho thử thứ hai với cặp khóa độc lập. Chỉ đọc metadata công khai khi thử sai khóa. |
| `live-signed.pdf` | Tên đầu ra mới, để trống trước khi bắt đầu. |

- [ ] Bật hiển thị phần mở rộng trong Explorer. Sao chép mẫu từ kho mã nguồn,
  giữ bản gốc nguyên vẹn. Chỉ dùng mẫu công khai trong suốt buổi trình diễn.
- [ ] Trong **Key Vault**, chọn **Create Vault** và đặt tên mới
  `presentation.hvault`. Nhập và xác nhận mật khẩu có ít nhất 15 ký tự
  qua hộp thoại được che. Kho mới ở trạng thái **Locked**. Không lưu mật khẩu
  trong lệnh, biến môi trường, clipboard, ảnh chụp, tài liệu hay Git.
- [ ] Mở đúng kho, ghi lại Hybrid Key ID công khai bằng **View full ID**.
  Ký mẫu theo kịch bản và lưu thành `rehearsal-signed.pdf`. Kiểm tra bản
  vừa lưu bằng **Use authenticated vault** và ghi nhận **HYBRID VALID**.
- [ ] Sao chép riêng bản đã ký thành `rehearsal-tampered.pdf`. Với chính
  mẫu ASCII này, mở bản sao bằng Notepad (**File → Open**, chọn **All files**).
  Thay đúng một `APPROVED` bằng `REJECTED` (cùng 8 byte ASCII) rồi lưu bản sao
  với đuôi `.pdf` và mã hóa UTF-8 không BOM. Một số trình soạn thảo đổi dấu xuống dòng hoặc mã
  hóa. Nếu không đối chiếu được byte, chỉ trình bày rằng bản sao đã thay đổi.
  Kiểm tra lại bản gốc **VALID** và bản sao **INVALID** với cùng nguồn khóa.
- [ ] Khóa kho chính. Tạo một kho thử mới `wrong-keys.hvault` bằng
  **Create Vault**. Giữ nguyên `rehearsal-signed.pdf` trong **Verify Signature**,
  chọn **Choose encrypted vault** rồi chọn kho thử. Xác nhận ID khác kho chính,
  **UNAUTHENTICATED**, và **HYBRID INVALID**. Chọn lại kho chính qua
  **Choose encrypted vault** và xác nhận **HYBRID VALID** ngay cả khi đang khóa.
  Giữ các kho thử, sidecar và đầu ra trong thư mục đã chọn, ngoài kho mã nguồn.
- [ ] Thoát bình thường, mở lại từ lối tắt, kiểm tra ứng dụng khởi động
  trong trạng thái chưa mở kho. Mở lại kho chính và xác nhận cùng ID, rồi
  khóa. Giữ bản đã kiểm tra để dùng khi cần chuyển sang phương án dự phòng.
- [ ] Nếu tập cài rồi gỡ, chỉ thử với bản cài và dữ liệu dùng riêng đã được
  xác định. Đóng ứng dụng trước khi gỡ trong **Settings → Apps → Installed apps**.
  Kiểm tra kho và PDF ngoài thư mục ứng dụng còn nguyên, rồi chuẩn bị lại cách
  chạy đã chọn. Không gỡ bản cài đang dùng cho công việc khác.

## 3. Nghiệm thu giao diện trên máy thực tế

- [ ] Với máy chiếu hoặc màn hình ngoài, thử chế độ Duplicate/Extend sẽ dùng.
  Ghi độ phân giải và tỷ lệ **Display scale** thực tế. Ở mỗi màn hình dự định
  trình chiếu, kiểm tra cỡ chữ, góc cửa sổ, cuộn, thanh thao tác, tệp dài,
  cửa sổ mặc định, tối đa hóa, khôi phục và kích thước nhỏ nhất.
- [ ] Mở đủ **Dashboard**, **Sign Document**, **Verify Signature**,
  **Key Vault** và **Settings**. Kiểm tra giao diện Light/Dark và **Reduce
  motion**. Với phòng sáng, chọn chế độ cho chữ dễ đọc trên máy chiếu.
- [ ] Thử **Auto on** bằng chuột và bàn phím. Rời thanh bên để xem tự thu.
  Thử **Pin sidebar** khi cửa sổ đủ rộng, rồi unpin. Kiểm tra việc chuyển
  màn hình, độ rộng nội dung và không che nút thao tác. Nếu cửa sổ hẹp, dùng
  nút mở tay khi cần.
- [ ] Dùng Tab/Shift+Tab, Enter/Space và Escape cho điều hướng, nút, chi tiết
  About và hộp thoại. Kiểm tra focus trở về đúng chỗ. Bấm **View full ID** để mở rồi bấm lại để thu gọn.
  Thử **Copy full ID** và xác nhận dán ra đúng ID công khai. Thử công cụ
  đọc màn hình nếu người trình bày hoặc hội đồng cần sử dụng.
- [ ] Xác nhận các hộp thoại Open, Save, xác nhận ghi đè và mật khẩu nằm
  trên màn hình chiếu mong muốn, hỗ trợ bàn phím và chuột. Kiểm tra ô mật
  khẩu được che. Thử **Cancel**, sau đó chọn tệp rõ ràng và xem đúng tên
  trước khi ký hoặc kiểm tra.
- [ ] Tập theo [kịch bản](thesis-demo-script-vi.md) và bảng xử lý sự cố. Kiểm tra đủ ba kết quả dưới đây. Sau đó chọn một tên đầu ra mới cho lần bảo vệ.

| Kiểm tra | Kết quả cần thấy | Máy bảo vệ |
| --- | --- | --- |
| Tệp đã ký + khóa kho chính | HYBRID VALID | Chờ |
| Bản đã sửa + cùng nguồn khóa | HYBRID INVALID | Chờ |
| Tệp đã ký + khóa kho thử | HYBRID INVALID | Chờ |
| Khóa kho, xác minh bằng khóa công khai, sau đó mở lại kho chính | Xác minh thành công khi đã khóa, cùng Hybrid Key ID sau khi mở lại | Chờ |

## Xử lý sự cố trong buổi bảo vệ

| Tình huống | Xử lý |
| --- | --- |
| Nhập sai mật khẩu | Chọn **Try Again** khi ứng dụng còn giữ đúng lựa chọn, rồi dùng hộp thoại mới. Nếu tệp đã thay đổi hoặc lựa chọn hết hiệu lực, chọn lại kho. Nếu quên mật khẩu, dùng bản ký thử với khóa công khai của kho đã chuẩn bị. Tạo kho mới chỉ khi chủ động bắt đầu một quy trình ký mới. |
| Chọn nhầm PDF hoặc nhầm nguồn khóa | Dừng trước khi trình bày kết quả, chọn lại đúng tên tệp và Hybrid Key ID. Chạy **Verify PDF** sau khi đổi lựa chọn. Phân biệt bản hợp lệ, bản đã sửa và kho thử. |
| Hủy picker hoặc đóng hộp thoại | Đọc thông báo hủy và xem lại tệp và nguồn khóa đang hiển thị vì lựa chọn trước có thể còn tồn tại. Sau đó chọn lại. Nếu hủy Save trước khi xếp hàng, giao diện xác nhận chưa có job mới. |
| Tên đầu ra đã tồn tại | Chọn **No** hoặc **Cancel** và đặt tên mới trong thư mục thử. Giữ bản ký và bản đối chứng đã kiểm tra. Không xác nhận ghi đè chỉ để tiếp tục buổi trình diễn. |
| Đang ký mất nhiều thời gian | Chờ trạng thái cuối, giữ ứng dụng mở và không bấm **Sign PDF** nhiều lần. Nếu cần chuyển nội dung trong khi chờ, dùng ảnh ghi rõ là kết quả lần thử trước. Chỉ dùng luồng kiểm tra trong app khi thao tác đã ổn định. |
| Trạng thái ký không chắc chắn | Dùng **Reconcile native status** cho cùng thao tác nếu nút xuất hiện. Kiểm tra thư mục đích và xác minh đúng tệp, cặp khóa và phiên bản đầu vào đã chọn. Tệp tồn tại có thể là bản cũ. Nếu vẫn chưa phân biệt được, giữ nguyên tệp và trình bày trạng thái chưa xác nhận. Chỉ bắt đầu thao tác mới sau khi xác minh trạng thái và ý định lưu. |
| Quyền ghi/đọc bị từ chối | Chọn thư mục NTFS riêng đã được kiểm tra, ngoài thư mục ứng dụng và repo. Giữ nguyên dữ liệu cũ, ACL và chính sách bảo vệ. |
| Thiếu WebView2 hoặc .NET Framework | Ghi đúng thông báo và chuẩn bị runtime chính thức trước khi thử lại. Bản portable cũng cần hai runtime này. Dùng máy dự phòng đã nghiệm thu nếu máy hiện tại chưa sẵn sàng. |
| Setup hoặc EXE không mở | Đối chiếu gói, kiến trúc và checksum. Kiểm tra giải nén đủ, lối tắt đúng, runtime và chính sách máy. Thử bản portable đã kiểm tra sẵn hoặc máy dự phòng nếu được phép. Nếu không thể chạy trực tiếp, trình bày ảnh kết quả đã lưu, ghi rõ xuất xứ và sự cố hiện tại. |

Ảnh dự phòng có sẵn về [VALID](../frontend/qa/phase4c2b/packaged-valid.png),
[INVALID do sửa tệp](../frontend/qa/phase4c2b/packaged-tampered.png) và
[INVALID do sai khóa](../frontend/qa/phase4c2b/packaged-wrong-keys.png).
Chúng ghi lại thử nghiệm bản cài Phase 4C.2B trên máy phát triển.
