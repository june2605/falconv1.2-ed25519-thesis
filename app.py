import streamlit as st
import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
import re
from nacl.signing import SigningKey
from sign import sign_file
from verify import verify_file
from keygen import generate_keys


@contextmanager
def upload_directory():
    """Own one upload directory and clean it before rendering any result.

    Retry one ordinary cleanup failure (e.g. a transient Windows sharing
    violation). Permanent OS denial is reported; it cannot be made leak-free
    by a Python finally block. Preserve any original operation exception.
    """
    temporary = tempfile.TemporaryDirectory(prefix="esign-upload-")
    primary = None
    try:
        yield Path(temporary.name)
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            temporary.cleanup()
        except OSError:
            try:
                temporary.cleanup()
            except OSError as cleanup_error:
                reported = primary if primary is not None else cleanup_error
                reported.upload_cleanup_path = temporary.name
                reported.add_note("Upload temporary-file cleanup failed")
                if primary is None:
                    raise


def read_uploads(**uploads):
    """Capture browser uploads before creating disk copies; never use their names."""
    captured = {}
    for name, uploaded in uploads.items():
        if uploaded is None:
            raise ValueError("Missing upload")
        data = uploaded.getvalue()
        if not isinstance(data, bytes) or not data:
            raise ValueError("Empty or invalid upload")
        captured[name] = data
    # This is a header check, not a complete PDF syntax/content validator.
    if re.match(rb"%PDF-[0-9]\.[0-9](?:\r\n|\r|\n)", captured["document"]) is None:
        raise ValueError("Expected a PDF header")
    return captured


def report_error(operation, error):
    """Do not echo exception strings that might contain uploaded key material."""
    if isinstance(error, PermissionError):
        reason = "Không thể truy cập tệp. Hãy kiểm tra quyền và đóng ứng dụng đang giữ tệp."
    elif isinstance(error, ValueError):
        reason = "Tệp, khóa hoặc chữ ký không hợp lệ; hãy kiểm tra các tệp đã tải lên."
    else:
        reason = "Thao tác không hoàn tất. Hãy kiểm tra tệp và thử lại."
    st.error(f"{operation}: {reason}")
    cleanup_path = getattr(error, "upload_cleanup_path", None)
    backend_cleanup = any("Signing temporary-file cleanup failed" in note
                          for note in getattr(error, "__notes__", ()))
    if cleanup_path or backend_cleanup:
        message = "Không thể xóa hết tệp tạm. Đóng ứng dụng đang giữ tệp và kiểm tra thư mục tạm."
        if cleanup_path:
            message += f" Thư mục: {cleanup_path}"
        st.warning(message)


st.set_page_config(
    page_title="PQC Hybrid Signature",
    page_icon="logobig.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
    }
    /* Card */
    [data-testid="stVerticalBlock"] > div:has(div.stFrame) {
        background-color: #ffffff;
        border-radius: 0.75rem;
        padding: 1.5rem;
        border: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
        margin-bottom: 1.5rem;
    }

    /* Header */
    .section-header {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 0.75rem;
    }

    /* Nút bấm Primary */
    .stButton>button {
        background-color: #2563eb !important; 
        color: white !important;
        border-radius: 0.5rem !important;
        height: 3rem !important;
        font-weight: 600 !important;
        border: none !important;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #1d4ed8 !important;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.4);
    }

    /* Nút Download */
    .stDownloadButton>button {
        background-color: #f1f5f9 !important;
        color: #334155 !important;
        border: 1px solid #cbd5e1 !important;
    }
    .stDownloadButton>button:hover {
        background-color: #e2e8f0 !important;
        color: #0f172a !important;
    }

    /* Cảnh báo */
    div[data-testid="stAlert"] {
        border-radius: 0.5rem;
        border: none;
    }
    
    /* Upload file */
    div[data-testid="stFileUploader"] {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8fafc;
        border: 1px dashed #cbd5e1;
    }
    </style>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown(
    "<h2 style='color:#1d4ed8; font-weight:700;'>PQC Hybrid System</h2>",
    unsafe_allow_html=True)
    st.caption("Bảo mật đa tầng Ed25519 + Falcon-512")
    st.markdown("---")
    
    if "menu" not in st.session_state:
        st.session_state.menu = "QUẢN LÝ KHÓA"

    st.markdown("### ĐIỀU HƯỚNG")

    if st.button("QUẢN LÝ KHÓA", use_container_width=True):
        st.session_state.menu = "QUẢN LÝ KHÓA"

    if st.button("KÝ SỐ TÀI LIỆU", use_container_width=True):
        st.session_state.menu = "KÝ SỐ TÀI LIỆU"

    if st.button("XÁC THỰC TÀI LIỆU", use_container_width=True):
        st.session_state.menu = "XÁC THỰC TÀI LIỆU"

    menu = st.session_state.menu
    st.markdown("---")
    st.info("Nguyên mẫu nghiên cứu chữ ký hybrid. Hãy kiểm tra nguồn tin cậy của các khóa công khai.")


PK_ED, SK_ED = "ed25519_pub.key", "ed25519_priv.key"
PK_FALCON, SK_FALCON = "falcon_pub.key", "falcon_priv.key"

def render_page_header(title, desc):
    st.markdown(f"<h1 style='color: #0f172a; font-size: 2.25rem; font-weight: 700; margin-bottom: 0.5rem;'>{title}</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='color: #64748b; font-size: 1.1rem; margin-bottom: 2rem;'>{desc}</p>", unsafe_allow_html=True)


if menu == "QUẢN LÝ KHÓA":
    generation_failed = False
    render_page_header("Khởi tạo bộ khóa Hybrid", "Tạo và lưu trữ các cặp khóa an toàn kết hợp thuật toán cổ điển và hậu lượng tử.")
    
    with st.container(border=True):
        st.markdown('<div class="section-header">Bảng điều khiển sinh khóa</div>', unsafe_allow_html=True)
        
        if st.button("BẮT ĐẦU TẠO BỘ KHÓA MỚI", use_container_width=True):
            try:
                with st.spinner("Đang tính toán các tham số mạng tinh thể và đường cong elliptic..."):
                    generate_keys(PK_ED, SK_ED, PK_FALCON, SK_FALCON)
                st.success("Bộ khóa Hybrid đã được khởi tạo.")
            except Exception as error:
                generation_failed = True
                report_error("Lỗi tạo khóa", error)

    st.markdown("<br>", unsafe_allow_html=True)
    
    if not generation_failed and all(os.path.exists(path) for path in (PK_ED, SK_ED, PK_FALCON, SK_FALCON)):
        try:
            # Read all keys and close every handle before rendering downloads.
            key_downloads = {path: Path(path).read_bytes() for path in (PK_ED, SK_ED, PK_FALCON, SK_FALCON)}
            with st.container(border=True):
                st.markdown('<div class="section-header">Tải bộ khóa về máy</div>', unsafe_allow_html=True)
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Hệ mật mã Ed25519")
                    st.download_button("Tải Public Key", key_downloads[PK_ED], PK_ED, use_container_width=True)
                    st.download_button("Tải Private Key (Bảo mật)", key_downloads[SK_ED], SK_ED, use_container_width=True)
                with col2:
                    st.markdown("#### Hệ mật mã Falcon-512")
                    st.download_button("Tải Public Key", key_downloads[PK_FALCON], PK_FALCON, use_container_width=True)
                    st.download_button("Tải Private Key (Bảo mật)", key_downloads[SK_FALCON], SK_FALCON, use_container_width=True)
        except Exception as error:
            report_error("Lỗi tải khóa", error)
    
    st.info("""
    **Hướng dẫn sử dụng**

    1. Nhấn **"BẮT ĐẦU TẠO BỘ KHÓA MỚI"** để hệ thống sinh khóa.
    2. Hệ thống sẽ tạo ra:
    - 2 khóa công khai (Public Key)
    - 2 khóa bí mật (Private Key)
    3. Sau khi tạo xong, tải các file khóa về máy.

    **Lưu ý quan trọng**
    - Không chia sẻ Private Key cho bất kỳ ai.
    - Nếu mất Private Key, bạn sẽ không thể ký tài liệu.
    - Public Key dùng để xác thực, có thể chia sẻ.
    """)

elif menu == "KÝ SỐ TÀI LIỆU":
    render_page_header("Ký số tài liệu PDF", "Sử dụng khóa bí mật để đóng dấu điện tử lên tài liệu của bạn.")

    with st.container(border=True):
        st.markdown('<div class="section-header">1. Tải lên tài liệu cần ký</div>', unsafe_allow_html=True)
        pdf_file = st.file_uploader("Kéo thả file PDF vào đây", type=["pdf"], label_visibility="collapsed")
        
    if pdf_file is not None:
        with st.container(border=True):
            st.markdown('<div class="section-header">2. Cung cấp khóa ký và khóa công khai Falcon</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            sk_ed = col1.file_uploader("Khóa Ed25519 Private (.key)", type=["key"])
            sk_fal = col2.file_uploader("Khóa Falcon Private (.key)", type=["key"])
            pk_fal_sign = col2.file_uploader("Khóa Falcon Public để kiểm tra chữ ký (.key)", type=["key"], key="signing_falcon_public")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("THỰC HIỆN KÝ SỐ HYBRID", use_container_width=True):
                if all(item is not None for item in (sk_ed, sk_fal, pk_fal_sign)):
                    try:
                        captured = read_uploads(document=pdf_file, ed_private=sk_ed,
                                                falcon_private=sk_fal, falcon_public=pk_fal_sign)
                        with st.spinner("Đang xử lý chữ ký kép..."):
                            with upload_directory() as work:
                                source = work / "source.pdf"
                                ed_private = work / "ed25519-private.key"
                                falcon_private = work / "falcon-private.key"
                                falcon_public = work / "falcon-public.key"
                                output = work / "signed.pdf"
                                source.write_bytes(captured["document"])
                                ed_private.write_bytes(captured["ed_private"])
                                falcon_private.write_bytes(captured["falcon_private"])
                                falcon_public.write_bytes(captured["falcon_public"])
                                sign_file(source, output, ed_private, falcon_private, pk_falcon=falcon_public)
                                signed_bytes = output.read_bytes()
                                # Check exactly the immutable bytes offered to Streamlit,
                                # independently of the signer's return value/live output.
                                download_copy = work / "download.pdf"
                                ed_public = work / "ed25519-public.key"
                                download_copy.write_bytes(signed_bytes)
                                ed_public.write_bytes(bytes(SigningKey(captured["ed_private"]).verify_key))
                                if verify_file(download_copy, ed_public, falcon_public)[0] is not True:
                                    raise ValueError("Signed download verification failed")
                        
                        st.success("Tài liệu đã được ký và kiểm tra bằng cả hai khóa công khai.")
                        st.download_button("TẢI XUỐNG PDF ĐÃ KÝ", signed_bytes, file_name=f"signed_{Path(pdf_file.name).name}", mime="application/pdf", use_container_width=True)
                    except Exception as e:
                        report_error("Lỗi ký tài liệu", e)
                else:
                    st.warning("Vui lòng tải lên 2 khóa bí mật và khóa công khai Falcon tương ứng.")
                    
    st.info("""
    **Hướng dẫn sử dụng**

    1. Tải lên file PDF cần ký.
    2. Tải lên khóa ký và khóa công khai Falcon tương ứng:
    - Ed25519 Private Key
    - Falcon Private Key
    - Falcon Public Key tương ứng để kiểm tra trước khi xuất file
    3. Nhấn **"THỰC HIỆN KÝ SỐ HYBRID"**.
    4. Tải xuống file PDF đã được ký.

    **Lưu ý**
    - File đầu vào phải là PDF.
    - Không chỉnh sửa file sau khi ký nếu không sẽ mất hiệu lực.
    """)

else:
    render_page_header("Xác thực tính toàn vẹn", "Kiểm tra tài liệu đã ký có bị chỉnh sửa trái phép hay không.")

    with st.container(border=True):
        st.markdown('<div class="section-header">1. Tải lên tài liệu đã ký</div>', unsafe_allow_html=True)
        pdf_v = st.file_uploader("Kéo thả file PDF cần kiểm tra vào đây", type=["pdf"], label_visibility="collapsed")
        
    if pdf_v is not None:
        with st.container(border=True):
            st.markdown('<div class="section-header">2. Cung cấp khóa công khai (Public Keys)</div>', unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            pk_ed = col1.file_uploader("Khóa Ed25519 Public (.key)", type=["key"])
            pk_fal = col2.file_uploader("Khóa Falcon Public (.key)", type=["key"])

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("TIẾN HÀNH XÁC THỰC", use_container_width=True):
                if all(item is not None for item in (pk_ed, pk_fal)):
                    try:
                        captured = read_uploads(document=pdf_v, ed_public=pk_ed, falcon_public=pk_fal)
                        with st.spinner("Đang đối soát chuỗi mã hóa đa tầng..."):
                            with upload_directory() as work:
                                document = work / "document.pdf"
                                ed_public = work / "ed25519-public.key"
                                falcon_public = work / "falcon-public.key"
                                document.write_bytes(captured["document"])
                                ed_public.write_bytes(captured["ed_public"])
                                falcon_public.write_bytes(captured["falcon_public"])
                                is_valid = verify_file(document, ed_public, falcon_public)[0] is True
                        
                        if is_valid:
                            st.balloons()
                            st.success("### KẾT QUẢ: HỢP LỆ\nCả hai chữ ký hợp lệ với các khóa công khai đã cung cấp.")
                        else:
                            st.error("### KẾT QUẢ: KHÔNG HỢP LỆ\nCảnh báo: Tài liệu đã bị sửa đổi trái phép hoặc bộ khóa không khớp!")
                    except Exception as e:
                        report_error("Lỗi xác thực", e)
                else:
                    st.warning("Vui lòng tải lên đầy đủ cả 2 file khóa công khai.")
    
    st.info("""
    **Hướng dẫn sử dụng**

    1. Tải lên file PDF đã ký.
    2. Tải lên 2 khóa công khai:
    - Ed25519 Public Key
    - Falcon Public Key
    3. Nhấn **"TIẾN HÀNH XÁC THỰC"**.

    **Lưu ý**
    - Phải dùng đúng Public Key tương ứng với Private Key đã ký.
    - Nếu file bị chỉnh sửa dù chỉ 1 ký tự → xác thực sẽ thất bại.
    """)
