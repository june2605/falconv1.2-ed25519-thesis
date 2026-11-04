"""Path identity and captured input tests; all files are disposable fixtures."""

import importlib
import os
from pathlib import Path
import stat
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from conftest import make_pdf
import sign
from verify import verify_file


def _symlink(link, target):
    try:
        link.symlink_to(target)
    except OSError as error:
        if getattr(error, "winerror", None) == 1314:
            pytest.skip("Windows symlink creation requires Developer Mode or symlink privilege")
        raise


@pytest.mark.parametrize("alias", ["same", "relative", "hard-link", "source-symlink", "destination-symlink"])
def test_unsigned_source_alias_is_rejected_without_overwrite(pdf_path, keys, tmp_path, monkeypatch, alias):
    original = pdf_path.read_bytes()
    source, output = pdf_path, pdf_path
    if alias == "relative":
        (tmp_path / "nested").mkdir()
        monkeypatch.chdir(tmp_path)
        source, output = Path("original.pdf"), Path("nested/../original.pdf")
    elif alias == "hard-link":
        output = tmp_path / "hardlink.pdf"
        os.link(pdf_path, output)
    elif alias == "source-symlink":
        source = tmp_path / "source-link.pdf"
        _symlink(source, pdf_path)
    elif alias == "destination-symlink":
        output = tmp_path / "destination-link.pdf"
        _symlink(output, pdf_path)
    with patch("sign.SigningKey", wraps=sign.SigningKey) as crypto:
        with pytest.raises(ValueError) as error:
            sign.sign_file(source, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
        assert error.value.code == "path.alias"
        crypto.assert_not_called()
    assert pdf_path.read_bytes() == original


@pytest.mark.parametrize("key_name", ["sk_ed", "sk_falcon"])
@pytest.mark.parametrize("hard_link", [False, True])
def test_signer_protects_private_key_destinations(pdf_path, keys, tmp_path, key_name, hard_link):
    key_path = getattr(keys, key_name)
    original = key_path.read_bytes()
    output = key_path
    if hard_link:
        output = tmp_path / "key-alias.pdf"
        os.link(key_path, output)
    with pytest.raises(ValueError) as error:
        sign.sign_file(pdf_path, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
    assert error.value.code == "path.alias"
    assert key_path.read_bytes() == original


@pytest.mark.parametrize("mutation", ["changed-content", "inserted-reserved-marker"])
def test_preflight_and_signing_use_the_same_snapshot(pdf_path, keys, tmp_path, monkeypatch, mutation):
    original = pdf_path.read_bytes()
    changed = make_pdf("Changed after capture" if mutation == "changed-content" else "Literal %%FALCON_PQ_SIG_START")
    validate = sign.validate_unsigned_input
    checked = []

    def change_after_check(data):
        checked.append(data)
        validate(data)
        pdf_path.write_bytes(changed)

    monkeypatch.setattr(sign, "validate_unsigned_input", change_after_check)
    output = tmp_path / "captured.pdf"
    result = sign.sign_file(pdf_path, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
    assert result[0] == output and len(result) == 11
    assert checked == [original]
    assert output.read_bytes().startswith(original)
    assert pdf_path.read_bytes() == changed
    assert verify_file(output, keys.pk_ed, keys.pk_falcon)[0] is True


@pytest.mark.parametrize("layer", ["ed25519", "falcon"])
@pytest.mark.parametrize("existing_output", [False, True])
def test_new_signature_validation_preserves_destination(pdf_path, keys, tmp_path, monkeypatch, layer, existing_output):
    source = pdf_path.read_bytes()
    output = tmp_path / "preserved.pdf"
    sentinel = b"Pre-existing output must not be used as an intermediate"
    if existing_output:
        output.write_bytes(sentinel)
    if layer == "ed25519":
        monkeypatch.setattr(sign, "SigningKey", lambda seed: SimpleNamespace(
            sign=lambda message: SimpleNamespace(signature=b"e" * 65),
        ))
    else:
        monkeypatch.setattr(sign.falcon_512, "sign", lambda key, message: b"f" * (sign.falcon_512.SIGNATURE_SIZE + 1))
    with pytest.raises(ValueError) as error:
        sign.sign_file(pdf_path, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
    assert error.value.code == "signature.size"
    assert pdf_path.read_bytes() == source
    if existing_output:
        assert output.read_bytes() == sentinel
    else:
        assert not output.exists()


@pytest.fixture
def signing_io():
    return importlib.import_module("signing_io")


def test_capture_reads_source_once_into_immutable_bytes(signing_io, pdf_path, monkeypatch):
    expected = pdf_path.read_bytes()
    original_open = Path.open
    reads = []

    def record_open(path, mode="r", *args, **kwargs):
        if path == pdf_path.resolve() and mode == "rb":
            reads.append(path)
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", record_open)
    snapshot = signing_io.capture_source(pdf_path)
    assert reads == [pdf_path.resolve()]
    assert type(snapshot.data) is bytes and snapshot.data == expected
    pdf_path.write_bytes(b"Later live source contents")
    assert snapshot.data == expected


def test_capture_rejects_observed_changes_during_read(signing_io, pdf_path):
    info = pdf_path.stat()
    fields = {name: getattr(info, name) for name in (
        "st_mode", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns",
    )}
    changed = SimpleNamespace(**{**fields, "st_mtime_ns": fields["st_mtime_ns"] + 1})
    with patch.object(signing_io.os, "fstat", side_effect=[info, changed]):
        with pytest.raises(ValueError) as error:
            signing_io.capture_source(pdf_path)
    assert error.value.code == "source.changed"


@pytest.mark.parametrize("key_name", ["pk_ed", "pk_falcon", "sk_ed", "sk_falcon"])
def test_generic_path_validator_protects_all_supplied_key_files(signing_io, pdf_path, keys, tmp_path, key_name):
    snapshot = signing_io.capture_source(pdf_path)
    key_path = getattr(keys, key_name)
    original = key_path.read_bytes()
    output = tmp_path / "protected-key-link.pdf"
    os.link(key_path, output)
    with pytest.raises(ValueError) as error:
        signing_io.validate_signing_paths(snapshot, output, protected_paths=(key_path,))
    assert error.value.code == "path.alias"
    assert key_path.read_bytes() == original


def test_path_validator_allows_distinct_destination(signing_io, pdf_path, keys, tmp_path):
    snapshot = signing_io.capture_source(pdf_path)
    output = tmp_path / "distinct.pdf"
    assert signing_io.validate_signing_paths(snapshot, output, protected_paths=(keys.sk_ed, keys.sk_falcon)) == output.resolve()
    assert not output.exists()


@pytest.mark.parametrize("kind", ["directory", "dangling-symlink", "unrelated-symlink"])
def test_unsupported_destination_types_are_rejected(signing_io, pdf_path, tmp_path, kind):
    snapshot = signing_io.capture_source(pdf_path)
    output = tmp_path / "invalid-target"
    if kind == "directory":
        output.mkdir()
    elif kind == "dangling-symlink":
        _symlink(output, tmp_path / "missing-target")
    else:
        other = tmp_path / "other.pdf"
        other.write_bytes(b"Unrelated content")
        _symlink(output, other)
    with pytest.raises(ValueError) as error:
        signing_io.validate_signing_paths(snapshot, output)
    assert error.value.code in ("path.destination", "path.destination_link")


def test_nonregular_source_is_rejected_before_open(signing_io, tmp_path):
    source = tmp_path / "not-regular"
    source.write_bytes(b"Stat control")
    info = SimpleNamespace(st_mode=stat.S_IFIFO)
    with patch.object(Path, "stat", return_value=info), patch.object(Path, "open") as opened:
        with pytest.raises(ValueError) as error:
            signing_io.capture_source(source)
        assert error.value.code == "source.type"
        opened.assert_not_called()


def test_destination_stat_permission_error_is_not_assumed_safe(signing_io, pdf_path, tmp_path):
    snapshot = signing_io.capture_source(pdf_path)
    output = tmp_path / "protected.pdf"
    sentinel = b"Protected destination"
    output.write_bytes(sentinel)
    with patch.object(Path, "stat", side_effect=PermissionError("Simulated stat denial")):
        with pytest.raises(PermissionError):
            signing_io.validate_signing_paths(snapshot, output)
    assert output.read_bytes() == sentinel


@pytest.mark.skipif(os.name != "nt", reason="Windows device and alternate-data-stream paths")
@pytest.mark.parametrize("kind", ["alternate-stream", "device"])
def test_windows_special_destinations_are_rejected(signing_io, pdf_path, tmp_path, kind):
    snapshot = signing_io.capture_source(pdf_path)
    output = str(pdf_path) + ":alternate" if kind == "alternate-stream" else tmp_path / "NUL"
    with pytest.raises(ValueError) as error:
        signing_io.validate_signing_paths(snapshot, output)
    assert error.value.code == "path.destination"


def test_resolved_alias_check_without_native_symlink_privilege(signing_io, pdf_path, tmp_path):
    snapshot = signing_io.capture_source(pdf_path)
    output = tmp_path / "simulated-link.pdf"
    resolve = Path.resolve

    def resolve_link(path, *args, **kwargs):
        return snapshot.path if path == output else resolve(path, *args, **kwargs)

    with patch.object(Path, "resolve", resolve_link):
        with pytest.raises(ValueError) as error:
            signing_io.validate_signing_paths(snapshot, output)
    assert error.value.code == "path.alias"
    assert not output.exists()


def test_destination_link_metadata_is_rejected_without_native_symlink_privilege(signing_io, pdf_path, tmp_path):
    snapshot = signing_io.capture_source(pdf_path)
    output = tmp_path / "simulated-link.pdf"
    output.write_bytes(b"Other target")
    lstat = Path.lstat

    def link_metadata(path, *args, **kwargs):
        return SimpleNamespace(st_mode=stat.S_IFLNK) if path == output else lstat(path, *args, **kwargs)

    with patch.object(Path, "lstat", link_metadata):
        with pytest.raises(ValueError) as error:
            signing_io.validate_signing_paths(snapshot, output)
    assert error.value.code == "path.destination_link"
    assert output.read_bytes() == b"Other target"
