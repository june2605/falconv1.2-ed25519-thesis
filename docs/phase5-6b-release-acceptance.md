# Phase 5.6B - Dựng và nghiệm thu HybridSign 0.1.0-rc1 trên Windows

**PASS** cho nghiệm thu portable và lượt lặp lại toàn bộ vòng đời bộ cài trên máy phát triển. Lỗi mở hộp thoại xác minh của lượt cài thử đầu vẫn nằm trong hồ sơ. **CLEAN-MACHINE ACCEPTANCE: NOT RUN.** Gói ứng viên đang chờ phê duyệt phát hành.

## Nguồn và nhận diện bản ứng viên

- Phase 5.6A bắt đầu từ nội dung biên tập chưa commit trên `thesis/ui-demo` tại `09833ecb81567d920e80b6fe6c6bdf4a5e82a05e`. Danh sách kiểm tra khớp 44 tệp sửa và 3 tài liệu mới. Sau hồi quy, commit nội bộ `d7c9edede446d19116b0269d0f4d5fb2531a9bd6` chốt đúng 47 tệp đó. Cây Git là `9225df42b96dcd3309f5ebdd693b35875707a705`. [Danh mục tệp Phase 5.6A](phase5-6a-repository-editorial-audit.md#danh-mục-tệp-thay-đổi) · [Danh sách phát hiện](phase5-6a-editorial-findings.json)
- EXE portable được dựng từ checkout sạch của `d7c9ede`. Ứng viên Setup dùng từng byte của payload đó, với hai tệp cấu hình đóng gói bổ sung bên ngoài commit. `phase5-6a-source.json` ghi SHA-256 từng tệp thay đổi, thông số build và dependency. `installer-provenance.json` ghi mã băm của patch, cấu hình Setup, compiler và manifest đã duyệt. SHA-256 lockfile frontend là `7104f882d4ff0e6f615604c28e4745602f4708f9b1831a232166497a0b098321`.
- GUI hiển thị **HybridSign 0.1.0**. ZIP và Setup dùng nhãn **0.1.0-rc1**. Setup giữ AppId `{3699C4A8-8612-4F01-BB26-F014797A9CBE}`, đường dẫn mặc định `%LOCALAPPDATA%\Programs\HybridSign` và quyền per-user. Khi đã có đăng ký, điều kiện trong `PrepareToInstall` yêu cầu đúng phiên bản và đúng đường dẫn. `AppVersion=0.1.0-rc1` vì vậy chặn đường bảo trì bản đăng ký `0.1.0`. Việc nâng phiên bản trên máy người dùng cần phê duyệt riêng. [Inno Setup](../packaging/HybridSign.iss) · [Kiểm tra sở hữu gốc](phase4c2b-installer-release.md#ownership-running-sessions-and-user-files)

Hồ sơ ở `%LOCALAPPDATA%\HybridSignResearch\phase5-6b\candidate-1d5adecd`, ngoài Git. Thư mục chứa ứng viên, mã băm, ảnh, log, XML và bản vá.

## Tệp thay đổi

| Tệp Phase 5.6B | Mục thay đổi |
| --- | --- |
| `packaging/build-installer.py` | `--candidate-manifest-sha256` yêu cầu đường dẫn payload và thư mục xuất mới. Kiểm tra băm manifest được duyệt, từ chối manifest của inventory cũ, kiểm tra đầy đủ payload rồi đối chiếu lại khi sao chép staging. Mặc định dùng manifest Phase 4C.2A. |
| `packaging/HybridSign.iss` | Chế độ ứng viên dùng version và tên Setup riêng. Giữ AppId và kiểm tra quyền, sở hữu, tiến trình đang chạy, đường dẫn và runtime. |
| `packaging/zip-portable.py` | `--candidate` ghi ZIP và checksum với tên riêng và cơ chế tạo tệp mới. |
| `tests/test_installer_payload.py` | Sáu ca bổ sung về manifest ghim băm, manifest lịch sử, tên ZIP và checksum. Năm ca cũ tiếp tục chạy. |
| `docs/phase5-6b-release-acceptance.md` | Hồ sơ này. |

Bốn probe Windows được sao sang `native-acceptance-driver` trong hồ sơ. Các bản sao dùng chuỗi tên cửa sổ, nút, version và tên PDF Unicode của ứng viên. `driver-manifest.json` lưu từng thay đổi và mã băm. AST sau khi bỏ giá trị hằng chuỗi khớp probe gốc. Điều kiện kiểm tra và cách tương tác giữ nguyên. Bản EXE dùng mã mật mã, định dạng PDF/vault, ByteRange và các API hiện có.

## Build và kết quả hồi quy

Windows 11 Pro 25H2 x64, build 26200.9974, .NET Framework 4.8.09221 (Release 533509), WebView2 Evergreen 157.0.4341.60, WebView2 SDK 1.0.3856.49. Dùng Python 3.11.9 x64, PyInstaller 6.22.3, hooks-contrib 2026.10, Inno Setup 6.7.1, Node.js 26.13.0, npm 11.20.0, TypeScript 5.9.3, Vite 8.3.6 và Playwright 1.64.1. Authenticode của compiler hợp lệ và băm khớp compiler Phase 4C.2B.

PyNaCl 1.6.2, pqcrypto 0.3.4 và cryptography 50.0.2 có binding native trùng băm với tệp trong môi trường Python. Runtime desktop dùng pywebview 6.2.1, pythonnet 3.2.1, clr_loader 0.3.1, cffi 2.1.1, pycparser 3.12, bottle 0.13.4, proxy_tools 0.1.0 và typing_extensions 4.16.0. Dùng lại môi trường và lockfile sẵn có. [Danh sách runtime](../requirements-portable.txt) · [Danh sách build](../requirements-packaging.txt)

| Kiểm tra | Trạng thái | Kết quả |
| --- | --- | --- |
| `npm run typecheck` và `npm run build` | PASS | Cả hai exit 0, build portable chạy lại TypeScript và Vite. |
| `npm run test:e2e` trên mã Phase 5.6A cuối | PASS | 266 đạt, 0 lỗi, 0 bỏ qua, 4,1 phút. |
| Hai ca Windows từng lỗi focus | PASS | 2 đạt, 0 lỗi, 0 bỏ qua, 63,70 giây. |
| Nhóm pytest desktop và payload của Phase 5.6A | PASS | 225 đạt, 0 lỗi, 0 bỏ qua, 171,84 giây. |
| Nhóm pytest đóng gói, tài nguyên, parser và ranh giới chữ ký trên mã cuối | PASS | 158 đạt, 0 lỗi, 0 bỏ qua, 1,98 giây. Gồm 11 ca trong `test_installer_payload.py`. |
| Pytest toàn repository | NOT RUN | Phạm vi kiểm tra gồm các nhóm trên. |

Trình duyệt và native GUI chạy tuần tự. `run-private-desktop.py` tạo Win32 input desktop riêng trong phiên đăng nhập hiện tại, chạy probe với giới hạn thời gian và khôi phục desktop ban đầu. Checkout, log và ảnh mỗi lượt nằm riêng. EXE khớp đủ 12 tệp frontend của checkout dùng để dựng. So với build dùng ở Playwright, 11/12 tệp trùng từng byte. `index.html` chỉ khác LF/CRLF và một dòng trống, JS và CSS trùng byte.

| Ca focus | Đối chứng trên desktop dùng chung tại Phase 5.6A | Chạy trên desktop thử riêng |
| --- | --- | --- |
| `tests/test_desktop_demo.py::test_real_desktop_create_sign_verify_tamper_lock_and_restart` | `native dialog deadline` khi lưu kho để thử hủy hộp thoại mật khẩu. `dialogForeground=false`, `ownedForeground=false`, `focusedEdit=true`, `filenameControlMatched=false`. Tên tệp chưa được xác nhận. | PASS ở lượt riêng và trong nhóm 225 ca. |
| `tests/test_desktop_responsive_native.py::test_real_webview_default_maximized_restored_and_minimum` | `Owned WebView2 window did not receive foreground` trước khi đợi sự kiện con trỏ. PDF đã xác minh thành công trước điểm dừng. | PASS ở lượt riêng và trong nhóm 225 ca. |

Để tái hiện điều kiện cũ, chạy hai ID pytest theo quy trình Phase 5.6A trên desktop mặc định. Hai lượt nhóm khi đó có 223 đạt và 2 lỗi. Chạy riêng trên commit `09833ec` và mã biên tập đều tái hiện hai lỗi dưới điều kiện đó. Kết quả thay đổi theo điều kiện desktop. Log cũ không xác định được tiến trình giữ foreground. Lượt mới dùng nguyên điều kiện và thời hạn của hai ca. [Chi tiết và log đối chứng](phase5-6a-repository-editorial-audit.md#kiểm-tra)

## SHA-256 và kiểm kê

| Hiện vật | Phase 4C đã duyệt | Phase 5.6B rc1 |
| --- | --- | --- |
| `HybridSign.exe` | `1fa00d14171336bfcd8a16aabff776e3905946f5bb15bb6f389cd81c1322bfdc` | `3df62547f4645283038ea49763a9324674bcbbba77a4f5594a5da11b1d8cce0a` |
| ZIP portable | `6f6364e0c53921aa0370e75def1b07e4e36d0b52739563058d778db3c447a293` | `313a7ad56fbb1ef61ce43631df1becad7abf32c764b2191e367f889e36d0cdfb` |
| Setup | `7e1dc008c8238a8df93ca8c5cbc75db11a5b8fe77b09ed708ab0daf7ab89d8ae` | `6c7094d2ef9432674368df5f13552d96e4099e9f97343ee0a25f2fd46d888090` |

- **Portable.** `portable/HybridSign/` có 138 tệp, 33.968.034 byte. `HybridSign-0.1.0-rc1-win-x64-portable.zip` có 14.911.013 byte, 140 mục. Đối chiếu CRC và SHA-256 từng mục. EXE là AMD64 GUI `asInvoker`, 4.267.208 byte.
- **Installer.** `installer/HybridSign-Setup-0.1.0-rc1-win-x64.exe` có 13.482.844 byte. SHA-256 manifest được duyệt là `912cac0cd3c345d7f9b91369bcc74b004dbde26879c08ea2fcbe971cafde48ce`. `installer/payload-manifest.json` trùng byte với `portable/HybridSign.manifest.json`. Bộ cài ghi đúng 138/138 tệp. Bảng băm từng tệp nằm tại `portable/HybridSign.sha256`. EXE và Setup có Authenticode **NotSigned**.
- **Bảo toàn bằng chứng.** Trước và sau nghiệm thu, đối chiếu khớp 3 hiện vật cũ, 138 tệp portable đã duyệt, 49 ảnh QA lịch sử, 37 tệp baseline nghiên cứu, 15 dataset gốc, PDF mẫu và hai chữ ký Phase 1. Đủ 96 mục pilot/C8 và 179 mục Phase 5.5C đều khớp. 14 Git blob nguồn đo khớp `613a46d06930ffd9224afa557fa90992e3a56a2a`, với mã băm tập nguồn đo `d2c84e532ebba4b062d25e8f078238d7736b51fc545e3a27aa0b7311d8f4de91`. Năm tệp trong checkout Windows hiện tại có CRLF từ trước. Git blob chuẩn LF khớp bằng chứng đo, còn tệp trong workspace được giữ nguyên. [Baseline](phase5-5a-baseline.json) · [Nguồn và kết quả đo](phase5-5c-cross-platform-main.md)

SHA-256 của `candidate-checksums.sha256` là `ca1c9302e33b5883c1773fc07b2ef6619d83be9a418d9bdbc63de6b34be3ac43`. `release-integrity-final.json` ghi đối chiếu nguồn, tệp và kết quả xác minh độc lập.

## Nghiệm thu EXE portable

| Thao tác | Trạng thái | Quan sát |
| --- | --- | --- |
| Khởi chạy, đóng, tạo kho, khóa/mở và khởi động lại | PASS | Hai tiến trình EXE thật từ ZIP đã giải nén, đóng exit 0. Kho mã hóa 2.416 byte, hộp thoại che ký tự. Mở lại với cùng Hybrid Key ID. |
| Ký PDF mẫu, xác minh đúng khóa, tệp sửa và khóa sai | PASS | `Signed PDF saved` và `Both signatures verified`. PDF mẫu 742 byte tạo PDF ký 5.368 byte. Tệp gốc hợp lệ, tệp sửa và khóa sai bị từ chối. Kiểm tra độc lập với khóa công khai fixture khớp kết quả. |
| Native Open/Save, tiếng Việt, theme và kích thước | PASS | Focus trong trường tên tệp, đường dẫn có khoảng trắng và chữ Việt. Tên đầu vào 111 ký tự, đường dẫn 243 ký tự. Tên đầu ra sau khởi động lại 94 ký tự. Đã chạy sáng/tối, mặc định/phóng to/khôi phục/tối thiểu, sao chép đúng ID và kiểm tra nhãn Auto. |
| Chặn lưu vào thư mục app, gửi ký trùng và đóng khi ký | PASS | Hai vị trí lưu trong thư mục app bị từ chối. Lượt ký đã nhận tiếp tục và xác minh hợp lệ. |
| Windows Shell Open và lỗi tài nguyên khởi động | PASS | Shell Open exit 0. Ba bản sao lỗi thiếu assets, thiếu metadata và sai version hiện hộp thoại native, rồi exit 1 theo dự kiến. |
| Trạng thái ký chưa xác nhận | PASS / NOT RUN | Playwright dùng phản hồi giả lập, kiểm tra trạng thái chưa xác nhận, giữ nguyên ID tác vụ, không báo thành công hoặc gửi ký lại. JS trong EXE chứa đúng nhãn. NOT RUN đối với gây lỗi bất định thật trên native EXE. |

Bộ ảnh và 25 điểm kiểm tra chính nằm ở `portable-acceptance/screenshots`. Đã xem ảnh giao diện tối và kết quả xác minh sau cài lại ở chế độ sáng. Python, Falcon, libsodium và cryptography nạp từ `_internal` của ứng viên. Kiểm kê payload chỉ có tệp runtime và notice. Thư mục fixture có kho mã hóa, PDF, lock và log kiểm thử. Password ngẫu nhiên được nhập qua điều khiển mật khẩu Windows và giữ ở tiến trình driver. Biên native giữ khóa riêng ở phía Python. Quan sát này không kiểm được tất cả bản sao trong bộ nhớ và cache hệ điều hành. [Biên native và worker](phase4c3-final-release-review.md#desktop-architecture-and-observed-data-flow)

## Nghiệm thu bộ cài

Trước khi cài thử, AppId trống trong cả hai registry view của HKCU và HKLM. Thư mục mặc định và shortcut HybridSign đều trống. Setup chạy với quyền thường trong thư mục thử riêng. Vault/PDF thử đặt ngoài thư mục ứng dụng. Máy này đã có hai runtime.

- **FAIL lần đầu.** Setup đã cài xong và EXE đã ghi PDF ký. Probe dừng tại `Packaged UI did not settle at waiting for native file dialog: Choose signed PDF`. Màn hình Verify đang mở, nút Choose signed PDF khả dụng, HybridSign có foreground và không có hộp thoại đang mở. Gọi đúng nút qua UI Automation Invoke trong cùng tiến trình vẫn gặp lỗi. Xác minh độc lập PDF đã lưu cho kết quả đúng. Đóng ứng dụng bình thường và tháo bản thử qua uninstaller đã đăng ký của fixture. Giữ đủ băm của ba tệp thử. Hồ sơ gồm `installer-native.log`, `installer-resume.log`, ảnh và `installer-acceptance/first-install-recovery.json`.
- **PASS khi chạy lại toàn bộ.** Thư mục thử mới, cùng SHA-256 Setup và cùng probe. Wizard, Start Menu, shortcut Desktop tùy chọn, ký và xác minh thật, tệp sửa, khóa sai và khởi động lại đều đạt. Với ứng dụng đang ký, Setup từ chối với mã 7, uninstaller từ chối với mã 1. Tệp thử thay vào một vị trí do installer quản lý được bảo toàn khi cả hai đường bảo trì từ chối. Cài lại cùng version thành công, gỡ cài đặt giữ nguyên 6 tệp ngoài ứng dụng và 2 tệp thêm bên trong. Cài mới vào thư mục còn tệp thêm bị từ chối. Cài lại ở thư mục mới, mở kho cũ vẫn cho ID cũ và PDF cũ vẫn VALID. Gỡ cuối cùng exit 0, sạch tệp ứng dụng, entry và shortcut của bản thử. [Hành vi dự kiến của bộ cài](phase4c2b-installer-release.md#acceptance-and-release-evidence)
- Lỗi hộp thoại xuất hiện ở lượt đầu và không lặp lại ở lượt đầy đủ thứ hai. Nguyên nhân chưa xác định. Giữ hai kết quả trong `installer-repeat.log` và `installer-acceptance-repeat/screenshots/installer-checks.json` cùng hồ sơ lỗi đầu tiên. Cần chạy thủ công **Choose signed PDF** ngay sau ký trên máy nghiệm thu.
- **NOT RUN** khi thiếu hoặc dùng runtime cũ hơn yêu cầu. Setup nhận .NET và WebView2 đang cài. **CLEAN-MACHINE ACCEPTANCE: NOT RUN.**

## Mạng, giấy phép và bước phê duyệt

**PASS** cho ký và xác minh EXE khi proxy HTTP của WebView2 không tiếp cận được. App phục vụ tài nguyên qua loopback với CSP `connect-src 'none'`. Lấy mẫu trong lượt chạy thông thường thấy kết nối TCP ngoài loopback ở tiến trình WebView2 con. Chưa xác định nội dung hoặc mục đích các kết nối. Trong phép thử riêng, trỏ proxy cấp tiến trình vào cổng loopback dành riêng và không có listener. Đã xác nhận WebView2 nhận cờ. EXE ký, lưu và cho **HYBRID VALID**. Hai mẫu TCP trước và sau không thấy kết nối ngoài loopback của cây ứng dụng trong phép thử đó. Thử offline toàn máy và kiểm mọi loại lưu lượng vẫn **NOT RUN**. [Server và CSP](../desktop/assets.py) · [Cờ WebView2](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/webview-features-flags) · [Hành vi proxy Chromium](https://www.chromium.org/developers/design-documents/network-settings/)

`THIRD-PARTY-NOTICES.txt` giữ notice thu được từ Python, thư viện native, npm và font. Gói cài `proxy_tools` thiếu bản văn license riêng. Ngoại lệ bootloader của PyInstaller cho phép phân phối bundle với điều kiện tuân thủ license của phụ thuộc. Cần đối chiếu quyền phân phối WebView2 SDK và VC runtime cụ thể. Compiler Inno chỉ dùng để dựng. [Giấy phép PyInstaller](https://pyinstaller.org/en/v6.22.3/license.html) · [Phân phối WebView2](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution#files-to-ship-with-the-app) · [Điều khoản VC runtime](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170) · [Giấy phép Inno Setup](https://jrsoftware.org/inno-setup/purchase)

**BLOCKED** cho phát hành công khai cho đến khi xác nhận quyền dùng biểu tượng, mã nguyên mẫu kế thừa và các notice còn thiếu. Hồ sơ trích dẫn ghi nguồn gốc nghiên cứu. [Nguyên mẫu](https://github.com/luluon-cyper/FALCON) · [Provenance](PROJECT_PROVENANCE.md)

**PENDING HUMAN ACCEPTANCE** cho Windows sạch, hộp thoại Verify sau ký, DPI/màn hình và trình đọc màn hình thật, SmartScreen và quyết định nâng bản người dùng. RC1 hiện phục vụ nghiệm thu nội bộ.

## Tái tạo trên máy thử

Tạo checkout sạch tại `d7c9ede`. Dùng junction tới `.venv` và `frontend/node_modules` đã kiểm tra phiên bản. Cấp đường dẫn build mới và ghi băm mới cho mỗi lần dựng, vì timestamp PE có thể thay đổi.

```powershell
# Trong checkout sạch d7c9ede. $out là thư mục ứng viên mới.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File packaging\build-portable.ps1 `
  -DistPath "$out\portable" -WorkPath "$out\portable-work"

# Trong workspace có bản vá Phase 5.6B đã đối chiếu.
$python = '.\.venv\Scripts\python.exe'
$payload = "$out\portable\HybridSign"
& $python -B packaging\zip-portable.py $payload --candidate

# Sau khi probe portable đạt, dùng băm manifest đã duyệt.
& $python -B packaging\build-installer.py `
  --iscc 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' `
  --payload $payload --output "$out\installer" --candidate-manifest-sha256 $reviewedPin
```

`$reviewedPin` là SHA-256 của manifest đã nghiệm thu. Với chính payload ghi ở đây, dùng băm đầy đủ trong mục SHA-256. Trình duyệt chạy `npm run typecheck`, `npm run build` và `npm run test:e2e` trong checkout riêng. Hai ID focus và nhóm `tests/test_desktop_*.py` cộng `test_installer_payload.py` chạy bằng `python -X utf8 -B -m pytest -q -p no:cacheprovider`, với basetemp và XML mới. Nhóm 158 ca gồm `test_installer_payload.py`, `test_desktop_packaging.py`, `test_container_parsing.py` và `test_signature_integrity_boundary.py`.

`run-private-desktop.py` nhận thư mục làm việc, đường dẫn log mới, thời hạn tính bằng giây và lệnh tuyệt đối. Chạy `native-acceptance-driver/tests/portable_probe.py` với thư mục EXE giải nén, thư mục fixture mới, thư mục ảnh và PDF mẫu. `installer_probe.py` nhận Setup rc1, thư mục cài trống, thư mục fixture trống và thư mục ảnh. Kiểm tra AppId trống và đường dẫn riêng trước khi chạy. [Lệnh và giới hạn của probe portable](phase4c2a-portable-packaging.md#packaged-exe-acceptance) · [Probe installer](phase4c2b-installer-release.md#acceptance-and-release-evidence)

Commit `d7c9ede` nằm trên `thesis/ui-demo` nội bộ. Bốn tệp bản vá và hồ sơ Phase 5.6B còn trong working tree. Chưa push, tag hay phát hành.
