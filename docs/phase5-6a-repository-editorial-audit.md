# Phase 5.6A - Rà soát ngôn ngữ HybridSign

HybridSign 0.1.0 dùng tên sản phẩm và nhãn thao tác nhất quán trong giao diện Windows, hộp thoại và hướng dẫn. Bản xem trước trong trình duyệt vẫn ghi **UI PREVIEW**. Các thông báo ký và xác minh chưa có kết quả xác nhận hướng người dùng đến đúng thao tác đang chờ. [Thay đổi chính về ngôn ngữ](phase5-6a-ui-wording.md)

## Phạm vi và kết quả rà soát

Workspace `D:\Final_Thesis_GitHub` bắt đầu sạch trên `thesis/ui-demo`, tại commit `09833ecb81567d920e80b6fe6c6bdf4a5e82a05e`. Đã kiểm kê **605 tệp Git theo dõi** và quét **278 tệp văn bản**. 327 tệp nhị phân gồm ảnh, biểu tượng và mẫu PDF được kiểm kê theo loại tệp. Đã đọc nội dung hiển thị ở cả năm màn hình, các thông báo gốc, hướng dẫn phát hành và bản thảo luận văn hiện hành. Mẫu dò tìm phát hiện dấu câu, mã thoát, chữ dùng trong các nhãn và tham chiếu nội bộ. Các gợi ý về lời văn được xem lại theo ngữ cảnh.

| Nhóm | Văn bản đã quét | Bản ghi phát hiện | Đã xử lý | Giữ làm ngoại lệ |
| --- | ---: | ---: | ---: | ---: |
| A. Giao diện, hộp thoại, trình cài | 56 | 116 | 116 | 0 |
| B. Hướng dẫn sử dụng hiện hành | 5 | 62 | 62 | 0 |
| C. Tài liệu nghiên cứu và luận văn hiện hành | 6 | 11 | 11 | 0 |
| D. Báo cáo lịch sử, trích dẫn gốc và bằng chứng | 80 | 141 | 0 | 141 |
| E. Mã, kiểm thử và dữ liệu kỹ thuật | 131 | 66 | 59 | 7 |
| Tổng | 278 | 396 | 248 | 148 |

Danh sách JSON ghi đường dẫn, dòng tại commit gốc, loại vấn đề, câu ban đầu, câu sau sửa hoặc lý do giữ nguyên, mức ưu tiên và khả năng sửa an toàn. Một đoạn biên tập có thể trùng với dòng được dò ra vì dấu câu. Bảng đếm bản ghi rà soát, kể cả trường hợp trùng vị trí và ngoại lệ. [Danh sách phát hiện đọc được bằng máy](phase5-6a-editorial-findings.json)

### Dấu câu và ngoại lệ

| Dấu | Trước | Sau |
| --- | ---: | ---: |
| U+2014 trong văn bản | 74 | 61 |
| U+2013 trong văn bản | 102 | 88 |
| U+2212 trong văn bản | 3 | 3 |
| Dòng có mã thoát của các dấu trên | 16 | 7 |

Cả ba nhóm A, B và C có 0 dấu U+2014 hoặc U+2013 và 0 mã thoát còn sinh các dấu này trong nhãn. 22 tệp còn ký tự dấu dài nằm trong báo cáo lịch sử và tiêu đề gốc ở `CITATION.cff`. Ba dấu trừ thuộc công thức hoặc tài liệu đã ghi nhận. Bảy mã thoát giữ đúng tiêu đề cửa sổ và hộp thoại mà các probe của bộ cài và bản portable đã nghiệm thu tìm theo chữ. Các probe chạy từ mã nguồn đã được cập nhật tên hiển thị tương ứng. Những ngoại lệ này tránh thay đổi bằng chứng và bảng đối chiếu phiên bản.

## Thay đổi lời văn có ý nghĩa

- **Ký.** **Check signing status** hỏi lại trạng thái của yêu cầu đã có. Khi chưa xác nhận được kết quả, thông báo nêu khả năng PDF đã được lưu và yêu cầu kiểm tra vị trí lưu trước khi thử lại. **Signed PDF saved** và **Both signatures verified** chỉ xuất hiện khi kết quả lưu và tự xác minh đáp ứng điều kiện cũ. [Màn hình ký](../frontend/src/pages/NativeSignDocument.tsx) · [Theo dõi trạng thái](../frontend/src/native/signing.tsx)
- **Xác minh.** **Check verification status** đọc trạng thái phép xác minh. **Use unlocked vault keys** giải thích nguồn khóa dễ hiểu hơn, và **UNAUTHENTICATED** vẫn chỉ nguồn đọc khóa công khai từ tệp kho chưa mở. Hai kết quả **HYBRID VALID** và **HYBRID INVALID** áp dụng cho cặp chữ ký với khóa đã chọn. Danh tính, quyền nắm giữ khóa và thời gian ký tin cậy là những thuộc tính cần bằng chứng riêng. [Màn hình xác minh](../frontend/src/pages/NativeVerifySignature.tsx)
- **Dashboard, Key Vault, Settings và khả năng truy cập.** Trạng thái **Desktop** thay cho **Desktop Connected**. Phần hoạt động ghi rõ là dữ liệu demo. Câu trên thẻ ký được rút ngắn để tránh chạm hình minh họa. **About HybridSign** và **Version 0.1.0** thay tên giai đoạn phát triển. Đã làm rõ nhãn mở hình minh họa, chú giải sidebar Auto, trợ giúp về khóa và đơn vị KiB/MiB. [Danh sách thay đổi giao diện](phase5-6a-ui-wording.md)
- **Windows và tài liệu.** Hộp thoại dùng dấu gạch ASCII. Đã làm rõ lỗi vị trí lưu và thông báo khi Setup chưa xác nhận được tệp đã cài. README mô tả thiết lập Windows, bản cài và portable, mở kho, ký, xác minh, xử lý sự cố và đường chạy từ mã nguồn. Hướng dẫn trình diễn có bảng đối chiếu nhãn với gói đã nghiệm thu. Hỏi đáp kỹ thuật làm rõ tiền tố độ dài 4 byte của Hybrid Key ID và trích kết quả so sánh Phase 5.5C. Bố cục năm chương, danh mục IEEE và các giới hạn về định dạng Falcon/CMS/PAdES giữ theo tài liệu nghiên cứu. [README](../README.md) · [Hướng dẫn frontend](../frontend/README.md) · [Checklist trình diễn](thesis-demo-checklist.md) · [Hỏi đáp kỹ thuật](thesis-technical-qa-vi.md)

## Kiểm tra

Môi trường kiểm tra dùng Python 3.11.9, Node.js 26.13.0, npm 11.20.0, Microsoft Edge đã cài và WebView2 trên Windows. Playwright chạy trong bản sao frontend riêng để ảnh tạo ra nằm ngoài `frontend/qa` đã chốt. Kiểm thử GUI Python bắt đầu sau khi lượt Playwright kết thúc.

| Kiểm tra | Kết quả |
| --- | --- |
| TypeScript và Vite production build tại `frontend` | Đạt trên mã cuối |
| Playwright toàn bộ | 266 đạt, 0 lỗi, 0 bỏ qua (4,5 phút), trước lượt rút gọn nhãn cuối |
| Playwright sau chỉnh độ dài nhãn và KiB/MiB | 118 đạt, 0 lỗi, 0 bỏ qua (2,5 phút). Gồm `workspace`, `responsive-native`, `desktop-ux` và `accessibility` |
| Pytest desktop và kiểm tra payload installer | Hai lượt theo nhóm đều 223 đạt, 2 lỗi, 0 bỏ qua, ở 131,22 và 129,80 giây. Chạy riêng hai ca lỗi trên commit gốc và mã cuối cho cùng kết quả (0 đạt, 2 lỗi, 0 bỏ qua ở mỗi lượt). |
| Rà liên kết và dấu câu | 752 tham chiếu Markdown nội bộ trong các tệp đã theo dõi đều trỏ tới đích hiện có. Hai URL tải runtime đã được đối chiếu trên trang Microsoft. Các tài liệu bổ sung cũng qua kiểm tra liên kết nội bộ và dấu ASCII |
| Soát ảnh | Đã xem cả năm màn hình ở 1366x768 sáng. Đã xem lại Dashboard và Settings sau khi rút gọn nhãn. Các bài kiểm tra responsive và axe bao phủ nhiều kích thước, chế độ sáng/tối và thao tác bàn phím |

Lượt Playwright đầu có 256 đạt và 10 lỗi so khớp nhãn, tương ứng năm ca ở hai kích thước. Đã cập nhật nhãn được so khớp và giữ các khẳng định về tác vụ, bố cục, không tự gửi lại yêu cầu, và không hiển thị thành công từ phản hồi chưa được xác nhận. `HYBRID INVALID` tiếp tục tách khỏi lỗi chọn tệp và lỗi vận hành.

Tất cả mã băm đã đối chiếu đều khớp. Phạm vi gồm 37 tệp nguồn và nghiên cứu trong baseline, tệp fixture và hai PDF chữ ký đóng băng, PDF mẫu công khai, 15 tệp dữ liệu lịch sử, 138 tệp payload portable và ba hiện vật phát hành. Hai bộ kiểm kê bằng chứng đo có lần lượt 96 mục cho pilot và C8, 179 mục cho lượt đo chính. Tập mã đo `research/benchmarks/p55`, fixture và `frontend/qa` khớp Git. So sánh cú pháp xác nhận bốn tệp Python desktop và kịch bản Inno Setup chỉ sửa chuỗi hiển thị. Mã lỗi, cấu trúc phản hồi và các điều kiện bảo vệ của API giữ nguyên. [Baseline kiểm băm](phase5-5a-baseline.json)

Log và ảnh mới nằm ngoài Git tại `%LOCALAPPDATA%\HybridSignResearch\phase5-6a\editorial-1e3f1c23`. Hai lần chạy Playwright đạt lưu ở `browser-final` và `browser-labels`, kèm `playwright-final.log` và `playwright-labels.log`.

Lượt pytest đầu có 222 đạt và 3 lỗi do kiểm thử còn chờ nhãn cũ. Đã cập nhật các phép so khớp chữ. Hai lượt sau dùng nguyên các điều kiện kiểm tra thao tác thật. Cả hai ca dưới đây đều dừng tại cùng một bước và ghi cùng trạng thái trên commit gốc lẫn mã đã biên tập.

- `tests/test_desktop_demo.py::test_real_desktop_create_sign_verify_tamper_lock_and_restart` dừng với `native dialog deadline` lúc lưu kho để kiểm tra hủy hộp thoại mật khẩu. Probe ghi `dialogForeground=false`, `ownedForeground=false`, `focusedEdit=true` và `filenameControlMatched=false`. Bước nhập tên và xác nhận hộp thoại chưa hoàn tất. [Ca kiểm thử](../tests/test_desktop_demo.py) · [Probe hộp thoại](../tests/desktop_demo_probe.py)
- `tests/test_desktop_responsive_native.py::test_real_webview_default_maximized_restored_and_minimum` xác minh được PDF rồi dừng ở `Owned WebView2 window did not receive foreground` trước khi chờ sự kiện con trỏ. [Ca kiểm thử](../tests/test_desktop_responsive_native.py) · [Probe WebView2](../tests/desktop_verification_probe.py)

Kết quả đối chứng cho thấy hai lỗi xuất hiện cả khi dùng nhãn gốc. Log ghi được việc cửa sổ cần kiểm thử không nhận focus, còn ứng dụng đang giữ focus chưa được xác định. Chưa thể xác nhận trọn vẹn hai luồng tương tác Windows trong lượt nghiệm thu này. Cần chạy lại hai ca trên phiên desktop tương tác dành riêng khi duyệt UI. Hai ca cũng có tiền lệ lỗi tự động hóa được ghi trong đợt ổn định bộ cài. [Hồ sơ kiểm thử phát hành trước](phase4c2b-installer-release.md#original-failures)

Log pytest gồm `native-pytest.log`, `native-final.log`, `native-recheck.log`, `native-parent.log` và `native-focused.log`, kèm các XML cùng tên. Lượt đầu chạy tại workspace và ghi đè 49 ảnh QA đã theo dõi. Đã lưu cả 49 ảnh mới vào `native-initial-captures`, khôi phục từng ảnh gốc từ commit ban đầu rồi đối chiếu byte và mã băm. `native-initial-captures/restoration.json` ghi kết quả đối chiếu. Các lượt sau chạy tại các worktree tách riêng.

## Gói phát hành và nghiệm thu còn lại

EXE portable, bộ cài và ảnh đã nghiệm thu giữ nhãn cũ. Bản build frontend ở bước kiểm tra chỉ cung cấp tài nguyên mới cho ứng dụng chạy từ mã nguồn. Khi duyệt phát hành, cần dựng portable trong thư mục đầu ra mới từ mã đã rà soát, kiểm kê lại payload, dựng Setup từ payload đã duyệt và lưu SHA-256 của cả hai gói. Chạy lại thử nghiệm cài và gỡ, bảo toàn tệp người dùng và kho đã có, chặn đóng/gỡ trong lúc ký, xác minh đúng tệp, sai khóa và tệp đã sửa. Giữ kết quả mới và cũ với tên dễ phân biệt. [Quy trình portable](phase4c2a-portable-packaging.md) · [Quy trình bộ cài](phase4c2b-installer-release.md)

Nghiệm thu trên máy Windows sạch vẫn **NOT RUN**. Trạng thái Authenticode của gói đã duyệt là **Unsigned**. Cần rà chữ và hộp thoại trên máy trình chiếu, tỷ lệ DPI thật, màn hình ngoài và trình đọc màn hình, cùng điều kiện SmartScreen trước khi dùng bộ cài mới. Việc đối chiếu bản Word với số liệu và tài liệu hướng dẫn theo các bước của Phase 5.5D. [Tích hợp vào luận văn](phase5-5d-thesis-integration.md#đưa-vào-bản-word-hiện-hành) [Checklist máy bảo vệ](thesis-demo-checklist.md) · [Phạm vi phát hành đã duyệt](phase4c3-final-release-review.md#readiness-and-remaining-acceptance)

## Danh mục tệp thay đổi

- Hướng dẫn và luận văn (5). `README.md`, `frontend/README.md`, `docs/thesis-demo-checklist.md`, `docs/thesis-demo-script-vi.md`, `docs/thesis-technical-qa-vi.md`.
- Giao diện (19).
  + `frontend/index.html`, `frontend/src/App.tsx`, `frontend/src/services/demo.ts`.
  + `frontend/src/components/DocumentPicker.tsx`, `frontend/src/components/DocumentPreview.tsx`, `frontend/src/components/NativeVault.tsx`, `frontend/src/components/SmartSidebar.tsx`, `frontend/src/components/VaultDialogs.tsx`.
  + `frontend/src/native/contracts.ts`, `frontend/src/native/signing.tsx`, `frontend/src/native/vault.tsx`, `frontend/src/native/verification.tsx`.
  + `frontend/src/pages/Dashboard.tsx`, `frontend/src/pages/KeyVault.tsx`, `frontend/src/pages/NativeSignDocument.tsx`, `frontend/src/pages/NativeVerifySignature.tsx`, `frontend/src/pages/Settings.tsx`, `frontend/src/pages/SignDocument.tsx`, `frontend/src/pages/VerifySignature.tsx`.
- Ứng dụng Windows và kịch bản phát hành (7). `desktop/contracts.py`, `desktop/dialogs.py`, `desktop/launcher.py`, `desktop/runtime.py`, `packaging/HybridSign.iss`, `packaging/INSTALLER-INFO.txt`, `packaging/PORTABLE-README.txt`.
- Kiểm thử (13).
  + `frontend/tests/desktop-ux.spec.ts`, `frontend/tests/native-bridge.spec.ts`, `frontend/tests/native-signing.spec.ts`, `frontend/tests/native-vault.spec.ts`, `frontend/tests/native-verification.spec.ts`, `frontend/tests/responsive-native.spec.ts`, `frontend/tests/sidebar.spec.ts`, `frontend/tests/vault-auth-ux.spec.ts`, `frontend/tests/workspace.spec.ts`.
  + `tests/desktop_demo_probe.py`, `tests/desktop_native_probe.py`, `tests/desktop_vault_probe.py`, `tests/desktop_verification_probe.py`.
- Tài liệu thêm (3). `docs/phase5-6a-repository-editorial-audit.md`, `docs/phase5-6a-editorial-findings.json`, `docs/phase5-6a-ui-wording.md`.

Tổng cộng 44 tệp được sửa và ba tệp báo cáo được thêm. HEAD vẫn ở `09833ec`. Tất cả thay đổi hiện nằm trong working tree.
