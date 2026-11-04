"""Small valid PDFs and fresh, disposable keys; never use benchmark datasets."""

from dataclasses import dataclass
from pathlib import Path

import pytest

from keygen import generate_keys
from sign import sign_file


@dataclass(frozen=True)
class HybridKeys:
    pk_ed: Path
    sk_ed: Path
    pk_falcon: Path
    sk_falcon: Path


def make_pdf(text: str) -> bytes:
    """Build a one-page PDF with a font, content stream and correct xref offsets."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET\n".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode("ascii")
        + stream + b"endstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode("ascii") + body + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


@pytest.fixture(params=["Phase 1 regression", "Phase 1 alternate document"],
                ids=["short-pdf", "alternate-pdf"])
def pdf_bytes(request):
    return make_pdf(request.param)


@pytest.fixture
def pdf_path(tmp_path, pdf_bytes):
    path = tmp_path / "original.pdf"
    path.write_bytes(pdf_bytes)
    return path


@pytest.fixture
def key_factory(tmp_path):
    counter = 0

    def create():
        nonlocal counter
        counter += 1
        folder = tmp_path / f"keys-{counter}"
        folder.mkdir()
        keys = HybridKeys(*(folder / name for name in (
            "ed25519_pub.key", "ed25519_priv.key",
            "falcon_pub.key", "falcon_priv.key",
        )))
        generate_keys(keys.pk_ed, keys.sk_ed, keys.pk_falcon, keys.sk_falcon)
        return keys

    return create


@pytest.fixture
def keys(key_factory):
    return key_factory()


@pytest.fixture
def signed_pdf(tmp_path, pdf_path, keys):
    path = tmp_path / "signed.pdf"
    sign_file(pdf_path, path, keys.sk_ed, keys.sk_falcon)
    return path
