"""Global pair policy; adversarial files are built independently of the signer."""

import hashlib
from unittest.mock import patch

import pytest
from nacl.signing import SigningKey, VerifyKey
from pqcrypto.sign import falcon_512

from conftest import make_pdf
from container_cases import make_container, replace_range
import utils
import verify
from sign import sign_file
from utils import SignatureFormatError, parse_completed_signature


MARKERS = (
    b"%%ED25519_PQ_SIG_START\n", b"%%ED25519_PQ_SIG_END\n",
    b"%%FALCON_PQ_SIG_START\n", b"%%FALCON_PQ_SIG_END\n",
)
STEMS = tuple(marker[:-1] for marker in MARKERS)


def _message(data, byte_range, falcon=False):
    a, b, c, d = byte_range
    message = data[a:a + b] + data[c:c + d]
    return hashlib.shake_256(message + data[c + d:]).digest(64) if falcon else message


def _legacy_layer(prefix, sign_type, keys):
    """Test-only raw construction bypasses new signing-input/pair restrictions."""
    case = make_container(sign_type, prefix=prefix)
    message = _message(case.data, case.byte_range, falcon=bool(sign_type))
    signature = (
        SigningKey(keys.sk_ed.read_bytes()).sign(message).signature if sign_type == 0
        else falcon_512.sign(keys.sk_falcon.read_bytes(), message)
    )
    payload = signature.hex().encode().ljust(case.contents_end - case.contents_start, b"0")
    assert len(payload) == case.contents_end - case.contents_start
    data = case.data[:case.contents_start] + payload + case.data[case.contents_end:]
    left = case.gap_start + len(b"SigLength: ")
    data = data[:left] + b"%010d" % (len(signature) * 2) + data[left + 10:]
    return data, case.byte_range, signature


def _legacy_pair(prefix, keys, gap=b""):
    ed_data, ed_range, ed_sig = _legacy_layer(prefix, 0, keys)
    data, fal_range, fal_sig = _legacy_layer(ed_data + gap, 1, keys)
    # Positive crypto controls: rejection must be a global policy decision.
    assert VerifyKey(keys.pk_ed.read_bytes()).verify(_message(data, ed_range), ed_sig) == _message(data, ed_range)
    assert falcon_512.verify(keys.pk_falcon.read_bytes(), _message(data, fal_range, True), fal_sig) is True
    return data


@pytest.fixture
def local_pair():
    ed = make_container(0)
    falcon = make_container(1, prefix=ed.data)
    assert parse_completed_signature(falcon.data, 0).marker_end == falcon.start
    assert parse_completed_signature(falcon.data, 1).marker_end == falcon.end
    return ed, falcon


def _assert_rejected_before_crypto(data, keys, tmp_path, expected=None):
    path = tmp_path / "adversarial.pdf"
    path.write_bytes(data)
    with patch.object(verify, "VerifyKey", wraps=verify.VerifyKey) as ed_verify, \
            patch.object(falcon_512, "verify", wraps=falcon_512.verify) as fal_verify, \
            patch.object(verify, "compute_sha512_digest_for_byte_range", wraps=verify.compute_sha512_digest_for_byte_range) as ed_message, \
            patch.object(verify, "compute_shake256_digest_for_byte_range", wraps=verify.compute_shake256_digest_for_byte_range) as fal_message:
        result = verify.verify_file(path, keys.pk_ed, keys.pk_falcon)
        assert isinstance(result, tuple) and len(result) == 11
        assert result[0] is False
        ed_verify.assert_not_called()
        fal_verify.assert_not_called()
        ed_message.assert_not_called()
        fal_message.assert_not_called()
    assert path.read_bytes() == data
    with pytest.raises(SignatureFormatError) as error:
        utils.parse_signature_pair(data)
    if expected is not None:
        assert error.value.code == expected


def test_valid_pair_has_one_ordered_adjacent_revision(signed_pdf, keys):
    data = signed_pdf.read_bytes()
    pair = utils.parse_signature_pair(data)
    ed, falcon = pair.ed25519, pair.falcon
    assert ed.marker_end == falcon.marker_start
    assert falcon.marker_end == len(data)
    assert ed.byte_range[2] + ed.byte_range[3] == ed.marker_end
    assert falcon.byte_range[0] == 0 and falcon.byte_range[1] >= ed.marker_end
    assert verify.verify_file(signed_pdf, keys.pk_ed, keys.pk_falcon)[0] is True


@pytest.mark.parametrize("marker", MARKERS, ids=["ed-start", "ed-end", "falcon-start", "falcon-end"])
@pytest.mark.parametrize("action", ["remove", "duplicate"])
def test_missing_or_duplicated_markers_reject_before_crypto(local_pair, keys, tmp_path, marker, action):
    data = local_pair[1].data
    changed = data.replace(marker, b"" if action == "remove" else marker * 2, 1)
    _assert_rejected_before_crypto(changed, keys, tmp_path, "pair.markers")


@pytest.mark.parametrize("kind", ["ed25519", "falcon", "both"])
def test_duplicate_complete_containers_are_rejected(local_pair, keys, tmp_path, kind):
    ed, falcon = local_pair
    if kind == "ed25519":
        extra_ed = make_container(0, prefix=ed.data)
        data = make_container(1, prefix=extra_ed.data).data
    elif kind == "falcon":
        data = make_container(1, prefix=falcon.data).data
    else:
        extra_ed = make_container(0, prefix=falcon.data)
        data = make_container(1, prefix=extra_ed.data).data
    _assert_rejected_before_crypto(data, keys, tmp_path, "pair.markers")


@pytest.mark.parametrize("kind", ["reversed", "nested", "interleaved"])
def test_reversed_and_overlapping_containers_reject_before_crypto(local_pair, keys, tmp_path, kind):
    ed, falcon = local_pair
    if kind == "reversed":
        first = make_container(1)
        data = make_container(0, prefix=first.data).data
        expected = "pair.order"
    elif kind == "nested":
        data = ed.data[:ed.gap_end] + falcon.data[falcon.start:] + ed.data[ed.gap_end:]
        expected = "container.boundary"
    else:
        # Es Fs Ee Fe: the two intervals cross rather than nest.
        data = ed.data[:ed.gap_end] + falcon.data[falcon.start:falcon.gap_end] + ed.data[ed.gap_end:] + falcon.data[falcon.gap_end:]
        expected = "container.boundary"
    _assert_rejected_before_crypto(data, keys, tmp_path, expected)


@pytest.mark.parametrize("gap", [b" ", b"\r\n", b"\x00", b"\n% intermediate PDF update\n"])
def test_separated_local_containers_are_rejected(local_pair, keys, tmp_path, gap):
    ed, _ = local_pair
    data = make_container(1, prefix=ed.data + gap).data
    # Both individual containers are valid; only their adjacency is wrong.
    assert parse_completed_signature(data, 0).marker_end == ed.end
    assert parse_completed_signature(data, 1).marker_start == ed.end + len(gap)
    _assert_rejected_before_crypto(data, keys, tmp_path, "pair.adjacency")


@pytest.mark.parametrize("suffix", [b" ", b"\n", b"\r\n", b"\t", b"\x00", b"payload", b"\n%%EOF\n", b"\n1 0 obj\n<<>>\nendobj\nstartxref\n0\n%%EOF\n"],
                         ids=["space", "lf", "crlf", "tab", "nul", "data", "extra-eof", "pdf-update"])
def test_any_trailing_bytes_are_rejected_before_crypto(local_pair, keys, tmp_path, suffix):
    _assert_rejected_before_crypto(local_pair[1].data + suffix, keys, tmp_path, "pair.trailing")


@pytest.mark.parametrize("cut", ["ed-start", "ed-metadata", "ed-signature", "ed-end", "fal-start", "fal-metadata", "fal-signature", "fal-end", "final-newline"])
def test_truncation_never_falls_back_to_an_incomplete_pair(local_pair, keys, tmp_path, cut):
    ed, falcon = local_pair
    offsets = {
        "ed-start": ed.start + 3, "ed-metadata": ed.gap_start + 5,
        "ed-signature": ed.contents_start + 1, "ed-end": ed.end,
        "fal-start": falcon.start + 3, "fal-metadata": falcon.gap_start + 5,
        "fal-signature": falcon.contents_start + 1, "fal-end": falcon.gap_end,
        "final-newline": falcon.end - 1,
    }
    _assert_rejected_before_crypto(falcon.data[:offsets[cut]], keys, tmp_path)


@pytest.mark.parametrize("kind", ["ed-past-revision", "fal-skips-prefix", "fal-excludes-ed"])
def test_pair_validation_preserves_local_revision_coverage(local_pair, keys, tmp_path, kind):
    ed, falcon = local_pair
    if kind == "ed-past-revision":
        values = list(ed.byte_range)
        values[3] += 1
        data = replace_range(ed, values) + falcon.data[falcon.start:]
        expected = "byte_range.coverage"
    else:
        values = list(falcon.byte_range)
        if kind == "fal-skips-prefix":
            values[0] = ed.end
            values[1] -= ed.end
            expected = "byte_range.start"
        else:
            values[1] = ed.end - 1
            expected = "byte_range.gap"
        data = replace_range(falcon, values)
    _assert_rejected_before_crypto(data, keys, tmp_path, expected)


@pytest.mark.parametrize("damage", ["ed-padding", "fal-padding", "fal-size"])
def test_completed_metadata_is_checked_before_either_crypto_layer(local_pair, keys, tmp_path, damage):
    ed, falcon = local_pair
    selected = ed if damage == "ed-padding" else falcon
    data = falcon.data
    if damage == "fal-size":
        left = selected.gap_start + len(b"SigLength: ")
        data = data[:left] + b"0000002000" + data[left + 10:]
        expected = "metadata.signature_size"
    else:
        at = selected.contents_start + (128 if damage == "ed-padding" else 1300)
        data = data[:at] + b"1" + data[at + 1:]
        expected = "contents.padding"
    _assert_rejected_before_crypto(data, keys, tmp_path, expected)


@pytest.mark.parametrize("kind", ["separated", "repeated", "truncated-repeat", "collision"])
def test_genuine_signatures_do_not_override_global_policy(pdf_bytes, keys, tmp_path, kind):
    if kind == "separated":
        data = _legacy_pair(pdf_bytes, keys, gap=b"\n")
        expected = "pair.adjacency"
    elif kind in ("repeated", "truncated-repeat"):
        data = _legacy_pair(_legacy_pair(pdf_bytes, keys), keys)
        if kind == "truncated-repeat":
            data = data[:-1]
        expected = "pair.markers"
    else:
        prefix = make_pdf("Literal %%ED25519_PQ_SIG_START marker")
        data = _legacy_pair(prefix, keys)
        expected = "pair.markers"
    _assert_rejected_before_crypto(data, keys, tmp_path, expected)


@pytest.mark.parametrize("token", STEMS, ids=["ed-start", "ed-end", "fal-start", "fal-end"])
@pytest.mark.parametrize("suffix", [b"", b"\n", b"\r\n", b"_EXAMPLE"], ids=["bare", "lf", "crlf", "extended"])
def test_verifier_rejects_reserved_names_in_validly_signed_pdf_content(token, suffix, keys, tmp_path):
    prefix = make_pdf("Literal " + (token + suffix).decode("ascii") + " example")
    data = _legacy_pair(prefix, keys)
    _assert_rejected_before_crypto(data, keys, tmp_path, "pair.markers")


def test_same_path_repeat_rejection_preserves_the_signed_input(signed_pdf, keys):
    original = signed_pdf.read_bytes()
    with patch("sign.prepare_file_with_placeholder", wraps=utils.prepare_file_with_placeholder) as prepare:
        with pytest.raises(SignatureFormatError) as error:
            sign_file(signed_pdf, signed_pdf, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
        assert error.value.code == "input.reserved_marker"
        prepare.assert_not_called()
    assert signed_pdf.read_bytes() == original


@pytest.mark.parametrize("token", STEMS, ids=["ed-start", "ed-end", "fal-start", "fal-end"])
@pytest.mark.parametrize("suffix", [b"", b"\n", b"\r\n", b"_EXAMPLE"], ids=["bare", "lf", "crlf", "extended"])
@pytest.mark.parametrize("existing_output", [False, True])
def test_signer_rejects_reserved_marker_collisions_without_writing(token, suffix, existing_output, keys, tmp_path):
    data = make_pdf("Literal " + (token + suffix).decode("ascii") + " example")
    source, output = tmp_path / "collision.pdf", tmp_path / "output.pdf"
    source.write_bytes(data)
    sentinel = b"Existing output must survive preflight rejection"
    if existing_output:
        output.write_bytes(sentinel)
    with patch("sign.prepare_file_with_placeholder", wraps=utils.prepare_file_with_placeholder) as prepare, \
            patch("sign.SigningKey", wraps=SigningKey) as ed_sign, \
            patch.object(falcon_512, "sign", wraps=falcon_512.sign) as fal_sign:
        with pytest.raises(SignatureFormatError) as error:
            sign_file(source, output, keys.sk_ed, keys.sk_falcon, pk_falcon=keys.pk_falcon)
        assert error.value.code == "input.reserved_marker"
        prepare.assert_not_called()
        ed_sign.assert_not_called()
        fal_sign.assert_not_called()
    assert source.read_bytes() == data
    if existing_output:
        assert output.read_bytes() == sentinel
    else:
        assert not output.exists()
