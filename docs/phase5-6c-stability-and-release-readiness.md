# Phase 5.6C - Độ ổn định và mức sẵn sàng của HybridSign 0.1.0-rc1

Giữ **RC1** để trình diễn luận văn có giám sát trên máy đã diễn tập. Lỗi mở hộp thoại chọn PDF ở Phase 5.6B chưa tái hiện trong 9 lượt chọn PDF của giai đoạn này. Nguyên nhân lần đầu vẫn chưa rõ. Bản trình diễn cần được chấp nhận thủ công trên máy đích. **CLEAN-MACHINE ACCEPTANCE: NOT RUN.**

## Nguồn và hiện vật đã đối chiếu

| Giai đoạn | Commit đầy đủ | Phạm vi |
| --- | --- | --- |
| Điểm xuất phát của nhánh nghiên cứu | `09833ecb81567d920e80b6fe6c6bdf4a5e82a05e` | HEAD của remote `thesis/ui-demo` khi bắt đầu rà soát. |
| Phase 5.6A | `d7c9edede446d19116b0269d0f4d5fb2531a9bd6` | 47 tệp giao diện, tài liệu và kỳ vọng nhãn đã được rà. Đây là mã ứng dụng trong RC1. [Danh sách đủ 47 tệp](phase5-6a-repository-editorial-audit.md#danh-mục-tệp-thay-đổi) |
| Phase 5.6B | `5d45d6d451b4e6757fa5284e89e47bc2dbdc2254` | `packaging/HybridSign.iss`, `packaging/build-installer.py`, `packaging/zip-portable.py`, `tests/test_installer_payload.py` và `docs/phase5-6b-release-acceptance.md`. Bản vá đóng gói khớp snapshot lúc biên dịch Setup. |
| Phase 5.6C | Commit chứa tài liệu này | `docs/phase5-6c-stability-and-release-readiness.md`. |

Phạm vi công bố gồm ba commit Phase 5.6A, 5.6B và 5.6C, chỉ trên `refs/heads/thesis/ui-demo`. Đối chiếu tên tệp, nội dung và diff trước khi stage. Không phát hiện khóa riêng, mật khẩu thật, đường dẫn profile cá nhân, PDF cá nhân, log, fixture sinh trong lúc chạy hay binary trong phạm vi công bố. `source-audit-pre.json` lưu kết quả rà 52 phiên bản tệp của hai commit nguồn, trong đó `HybridSign.iss` xuất hiện ở cả hai giai đoạn. Phiếu `publication.json` trong hồ sơ cục bộ ghi SHA của commit báo cáo và ref đã đối chiếu sau push.

| Hiện vật RC1 gốc | SHA-256 |
| --- | --- |
| `HybridSign.exe` | `3df62547f4645283038ea49763a9324674bcbbba77a4f5594a5da11b1d8cce0a` |
| `HybridSign-0.1.0-rc1-win-x64-portable.zip` | `313a7ad56fbb1ef61ce43631df1becad7abf32c764b2191e367f889e36d0cdfb` |
| `HybridSign-Setup-0.1.0-rc1-win-x64.exe` | `6c7094d2ef9432674368df5f13552d96e4099e9f97343ee0a25f2fd46d888090` |

Đối chiếu khớp 16 mục trong checksum inventory RC1, 138 tệp payload portable RC1, 138 tệp payload Phase 4C, 3 hiện vật Phase 4C và 49 ảnh QA cũ. Tập nguồn đo gồm 14 Git blob khớp commit đã đo `613a46d06930ffd9224afa557fa90992e3a56a2a`. Đã kiểm lại 37 tệp baseline, 15 tập dữ liệu gốc, 96 mục pilot/C8 và 179 mục chiến dịch chính. Mã ký/xác minh, định dạng PDF/vault và nguồn đo không có diff trong các commit công bố. [Nghiệm thu RC1 và manifest](phase5-6b-release-acceptance.md#sha-256-và-kiểm-kê) · [Nguồn và kết quả đo](phase5-5c-cross-platform-main.md)

## Điều tra hộp thoại xác minh

**Sự cố gốc.** Bộ cài đã chạy, EXE lưu PDF ký và kiểm tra độc lập trả kết quả hợp lệ với khóa công khai đúng. Probe dừng tại `Packaged UI did not settle at waiting for native file dialog: Choose signed PDF`. Ảnh và ảnh chụp trạng thái sau lỗi cho thấy trang Verify, nút **Choose signed PDF** khả dụng và cửa sổ chính có foreground. Không thấy cửa sổ chọn PDF ở thời điểm lấy trạng thái. Gọi nút qua UI Automation Invoke trong cùng tiến trình vẫn dẫn đến cùng lỗi chờ. Lượt cài đầy đủ sau đó qua được bước này. Giữ ảnh, log và tệp ký của lượt gốc ở hồ sơ Phase 5.6B. [Biên bản lượt đầu và lượt lặp](phase5-6b-release-acceptance.md#nghiệm-thu-bộ-cài)

- **WebView2 và điều phối.** Nút gọi `NativeVerificationProvider.select()` qua `choosePdf`. Trang tính trạng thái bận từ ký, xác minh và vault. Provider kiểm tra trạng thái và yêu cầu đang xử lý, rồi gửi `choose_verification_pdf`. Sau khi ký hoàn tất, điều kiện bận của job ký dựa trên trạng thái hiện hành. Cửa sổ chính có foreground khi quan sát chỉ xác nhận trạng thái tại thời điểm đó. Windows có điều kiện riêng khi một tiến trình yêu cầu kích hoạt foreground. [Nút xác minh](../frontend/src/pages/NativeVerifySignature.tsx) · [Provider](../frontend/src/native/verification.tsx) · [Windows foreground](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setforegroundwindow)
- **Bridge, picker và worker.** `VerificationBridge._verification_selection()` kiểm tra trạng thái đóng, nguồn tin cậy, bận và khóa thao tác trước khi gọi picker. `NativeDialogs._on_gui()` dùng `BeginInvoke` để chạy trên luồng GUI. `_pdf_dialog()` tạo `OpenFileDialog` và gọi `ShowDialog` với cửa sổ ứng dụng làm owner. `finally` dọn `_active` và dispose. Chỉ sau khi chọn tệp xong, worker mới nhận yêu cầu capture PDF. Hủy Open trả `cancelled`. Lỗi chọn tệp và lỗi ngoài dự kiến đi qua phản hồi lỗi của bridge. [Bridge](../desktop/verification_bridge.py) · [Hộp thoại](../desktop/dialogs.py) · [Worker](../desktop/verification_worker.py) · [WinForms BeginInvoke](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.control.begininvoke)
- **Giới hạn chẩn đoán.** Mốc 25 giây là giới hạn đợi của probe dành cho bước UI, không phải thời hạn chọn tệp của ứng dụng. UI có thời hạn hai giây cho truy vấn trạng thái. Worker có thời hạn năm giây cho capture/preflight ngắn sau khi chọn. Log gốc chưa ghi dispatch trong WebView2, lần gọi bridge, lần tạo/hủy modal hoặc mã lỗi tại thời điểm nhấn. Do đó chưa xác định được yêu cầu có tới native, tạo modal thoáng qua, bị chặn trước picker hay bị tác vụ/cửa sổ khác cản trở. Ảnh trạng thái loại được khả năng hộp thoại còn mở tại lúc quan sát. [Vòng đời xác minh và timeout](phase4b3b-real-verification-regression.md#native-bridge-and-lifecycle)

## Lượt thử có giới hạn trên RC1

Chạy tuần tự trên Win32 input desktop riêng trong phiên Windows phát triển 25H2. Kiểm tra AppId và shortcut trống trước lượt thử. Setup, EXE và native Open/Save là bản thật. Driver ghi sự kiện Win32 bằng `SetWinEventHook` ngoài tiến trình, lọc đúng PID và ghi owner cùng foreground ở lúc UI Automation thấy picker. Giữ điều kiện, thời hạn chờ và thao tác thật từ bộ probe đã nghiệm thu. Không thay đổi binary, cấu hình máy hoặc kiểm tra ACL. [WinEvent ngoài tiến trình](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-setwineventhook)

| Điều kiện thử | Lượt chọn PDF | Kết quả |
| --- | ---: | --- |
| Cài mới bằng wizard, EXE đầu tiên ký và ngay lập tức chọn PDF để xác minh. Lặp trên tệp sửa, khóa đúng khi khóa vault, nguồn khóa công khai và khóa sai. | 5 | PASS. Ba VALID, hai INVALID đúng dự kiến. Lần chọn đầu ngay sau ký mở đúng picker. |
| Khởi động lại qua Start Menu, mở lại kho cũ, ký lại rồi xác minh | 1 | PASS. VALID trong tiến trình mới. |
| Cài lại ở thư mục mới, dùng PDF đã ký trước đó | 1 | PASS. VALID trong tiến trình chưa ký. |
| Cài mới và mở Verify trực tiếp từ Start Menu, rồi đóng và lặp trong tiến trình mới. Dùng PDF fixture đã ký và đọc công khai từ kho thử gốc. | 2 | PASS. Hai VALID, cả hai tiến trình chưa thực hiện ký. |

**9/9 lần chọn PDF trong 5 tiến trình** có sự kiện hiển thị hộp thoại. Cả 9 lần picker có owner đúng, nắm foreground khi quan sát và khóa tương tác cửa sổ chính trong lúc mở. Bảy kết quả VALID và hai INVALID đúng kỳ vọng. Lượt wizard hoàn tất kiểm tra vòng đời bộ cài, các từ chối khi ký và khi tệp quản lý đổi, cài lại và gỡ. Đã xác nhận các cài đặt thử được tháo, shortcut và đăng ký biến mất, còn tệp ngoài ứng dụng vẫn giữ.

**Một lỗi chuẩn bị fixture cũng được giữ trong hồ sơ.** Lượt thử Verify trực tiếp ban đầu dừng sau bước Open encrypted vault, trước bước chọn PDF. Probe báo nhãn chờ cũ vì điều kiện thiếu là badge **UNAUTHENTICATED**, còn hộp thoại đã đóng. Tệp kho sao chép khớp SHA-256 với tệp gốc nhưng có DACL kế thừa và bốn ACE. Tệp gốc có DACL được bảo vệ và hai ACE. `capture_vault()` nhận tệp gốc và từ chối bản sao với `vault.security`. Lượt thử lại đọc kho fixture gốc ở chế độ chỉ lấy khóa công khai và đối chiếu băm trước/sau. Đây là từ chối đúng theo chính sách tệp vault, không phải lỗi mở hộp thoại PDF. [Kiểm tra DACL](../vault_io.py)

**Quyết định RC.** Chưa có lỗi ứng dụng có thể tái hiện cho picker PDF. Giữ RC1 và hồ sơ lỗi gốc. Phase 5.6C không sửa runtime, nên không có căn cứ dựng RC2.

## Hồi quy và mức sẵn sàng

Pytest Phase 5.6C đạt **258 passed, 0 failed, 0 skipped** trong 50,15 giây. Gồm các nhóm payload, tài nguyên desktop, ByteRange, ranh giới chữ ký, dialog, ký, xác minh và bảo vệ bridge. Kết quả Phase 5.6B của cùng nguồn RC1 gồm TypeScript và production build đạt, Playwright 266/266, pytest desktop/payload 225/225, nhóm đóng gói và chữ ký 158/158. Không chạy lại toàn bộ Playwright hoặc pytest trong giai đoạn tập trung này. [Số liệu Phase 5.6B](phase5-6b-release-acceptance.md#build-và-kết-quả-hồi-quy)

| Tiêu chí | Trạng thái | Căn cứ |
| --- | --- | --- |
| Chức năng portable | PASS | 25 điểm nghiệm thu RC1 trên EXE thật, băm đối chiếu lại. |
| Hộp thoại native | PENDING HUMAN ACCEPTANCE | 9/9 lượt chọn PDF mới đạt. Sự cố gốc vẫn chưa rõ nguyên nhân, cần thao tác trực tiếp trên máy trình diễn. |
| Vòng đời installer | PASS | 138/138 tệp đúng băm, từ chối bảo trì theo điều kiện và gỡ bảo toàn fixture trên Windows phát triển. |
| Hồi quy, nguồn và payload | PASS | 258 ca tập trung mới đạt. Mã và hiện vật kiểm kê khớp. |
| Windows sạch và thiếu runtime | NOT RUN | Không có môi trường sạch trong lượt này. |
| Authenticode | BLOCKED | EXE và Setup ở trạng thái `NotSigned`. Việc ký phát hành còn chờ phê duyệt. |
| Quyền phân phối | BLOCKED | Chờ xác nhận quyền với mã và biểu tượng kế thừa cùng license/notice của các phụ thuộc đóng gói. [Rà soát quyền phân phối](phase5-6b-release-acceptance.md#mạng-giấy-phép-và-bước-phê-duyệt) |
| Trình diễn trực tiếp | PENDING HUMAN ACCEPTANCE | RC1 đạt các bước kỹ thuật cho demo có giám sát. Cần thử trên đúng máy và đúng tài khoản dự kiến. |

Trước buổi bảo vệ, chạy portable từ thư mục đầy đủ đã kiểm băm, thử **Choose signed PDF** ngay sau ký và sau khởi động lại trên máy trình diễn. Chuẩn bị từ trước PDF công khai đã ký, bản sửa và kho đúng cặp khóa. Nếu picker trục trặc sau khi lưu, giữ tệp đã ký, đóng bình thường rồi xác minh tệp đó từ tiến trình mới. Chỉ phát hành công khai sau nghiệm thu Windows sạch, kiểm tra SmartScreen và giải quyết quyền phân phối cùng việc ký bản phát hành. [Checklist trình diễn](thesis-demo-checklist.md)

## Lặp lại và tra cứu bằng chứng

Bằng chứng mới nằm ngoài Git ở `%LOCALAPPDATA%\HybridSignResearch\phase5-6c\stability-14da715d`. `picker-events.jsonl` và `direct-retry/picker-events.jsonl` ghi từng lần mở. `follow-up.json` giữ lượt wizard đạt và lỗi fixture. `direct-retry/follow-up.json` giữ lượt trực tiếp đạt, kèm đối chiếu ACL và ảnh. `regressions.xml` ghi số ca và thời gian. Phase 5.6B giữ nguyên ảnh, log, manifest và hiện vật gốc ở `%LOCALAPPDATA%\HybridSignResearch\phase5-6b\candidate-1d5adecd`.

Chạy trên desktop tương tác khi chưa có HybridSign đăng ký hoặc đang chạy. Dùng thư mục kết quả mới, kiểm SHA-256 Setup ở trên và giữ kho fixture gốc ở chế độ chỉ đọc.

```powershell
$store = Join-Path $env:LOCALAPPDATA 'HybridSignResearch'
$rc = Join-Path $store 'phase5-6b\candidate-1d5adecd'
$qa = Join-Path $store 'phase5-6c\stability-14da715d'
$python = (Resolve-Path '.\.venv\Scripts\python.exe').Path

# Điền $out và $direct bằng hai thư mục kết quả mới, trống.
# Driver đầu chạy wizard và giữ phép đối chứng bản sao vault bị từ chối.
& $python -B "$rc\run-private-desktop.py" $out "$out\native.log" 660 `
  $python -B "$qa\observe-rc1-picker.py" $rc $out
# Driver sau xác minh từ vault fixture gốc và lặp từ tiến trình mới.
& $python -B "$rc\run-private-desktop.py" $direct "$direct\native.log" 255 `
  $python -B "$qa\direct-retry\observe-direct-verification.py" $rc $direct

& $python -B -m pytest -q -p no:cacheprovider `
  tests/test_installer_payload.py tests/test_desktop_packaging.py `
  tests/test_container_parsing.py tests/test_signature_integrity_boundary.py `
  tests/test_desktop_dialogs.py tests/test_desktop_verification.py `
  tests/test_desktop_signing.py tests/test_desktop_security.py
```
