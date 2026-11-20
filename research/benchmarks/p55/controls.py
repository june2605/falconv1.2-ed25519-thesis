"""Disposable fixture controls and public compatibility bundles."""
import json
from pathlib import Path
import re

import utils
from . import pdf
from .environment import file_hash, write_json
from .protocol import PROTOCOL

BUNDLE_SCHEMA = "hybridsign-public-bundle-v1"
FILES = {"sample-hybrid.pdf": 5368, "ed25519.pub": 32, "falcon.pub": 897}
EXPECTATIONS = {
    "C0": (True, True, True), "C1": (False, False, False),
    "C2": (False, True, False), "C3": (True, False, False),
    "C5": (True, False, False), "C6": (False, True, False),
}
REJECTED = (pdf.NOT_EVALUATED, pdf.NOT_EVALUATED, False)


def expected(method, control):
    if control not in EXPECTATIONS:
        return REJECTED
    ed, falcon, result = EXPECTATIONS[control]
    return (ed if method != pdf.FALCON else pdf.NOT_APPLICABLE,
            falcon if method != pdf.ED else pdf.NOT_APPLICABLE, result)


def evaluate(method, control, data, public, expected_structure="valid"):
    result = pdf.assess(data, method, public)
    criteria = expected(method, control)
    observed = result["ed25519"], result["falcon"], result["valid"]
    return dict(control=control, method=method, expected=list(criteria), expected_structure=expected_structure,
                **result, passed=observed == criteria and result["structure"] == expected_structure)


def positive_controls(data, method, pair, wrong):
    for control, specimen, public, _ in pdf.control_cases(data, method, pair, wrong):
        yield evaluate(method, control, specimen, public)


def smoke(directory):
    """Create public 742-byte fixtures and check the C0-C7 expectations."""
    source = directory / "sample.pdf"
    with source.open("xb") as stream:
        stream.write(pdf.fixture("demo"))
    pair, wrong = pdf.generated_keys()
    report = []
    for method in pdf.METHODS:
        target = directory / f"sample-{method}.pdf"
        pdf.sign_document(source, target, method, pair)
        pdf.require(pdf.verify_document(target, method, pdf.publics(pair)) is True, "smoke.file_verify")
        data = target.read_bytes()
        pdf.require(source.read_bytes() == pdf.fixture("demo") and data[:742] == pdf.fixture("demo"),
                    "smoke.source")
        report.extend(positive_controls(data, method, pair, wrong))
        if method == pdf.HYBRID:
            report.extend(_hybrid_fixture_cases(data, pair))
        target.unlink()
    source.unlink()
    return report


def _hybrid_fixture_cases(data, pair):
    public = pdf.publics(pair)
    parsed = utils.parse_signature_pair(data)
    ed, falcon = parsed.ed25519, parsed.falcon
    # Only invoked on the fresh public fixture and the generated test keys above.
    for name, shape in (("C4.remove_falcon", data[:ed.marker_end]),
                        ("C4.remove_ed25519", data[:ed.marker_start] + data[falcon.marker_start:]),
                        ("C4.reverse", data[:ed.marker_start] + data[falcon.marker_start:] +
                         data[ed.marker_start:ed.marker_end])):
        structure = "byte_range.gap" if name == "C4.reverse" else "pair.markers"
        yield evaluate(pdf.HYBRID, name, shape, public, structure)

    edited = pdf.covered_edit(data)
    for name, container in (("C5", ed), ("C6", falcon)):
        method = pdf.METHODS[container.sign_type]
        one_key = pdf.to_single(pair, method)
        signature = pdf.algorithm_signer(method, one_key)(pdf.message_for(edited, container))
        specimen = utils.embed_signature_into_pdf(edited, signature, container.sign_type)
        # The other layer's byte representation must be unchanged.
        unaffected = falcon if container.sign_type == 0 else ed
        pdf.require(specimen[unaffected.marker_start:unaffected.marker_end] ==
                    data[unaffected.marker_start:unaffected.marker_end], "control.other_layer_changed")
        yield evaluate(pdf.HYBRID, name, specimen, public)

    br_digit = falcon.marker_start + len(utils.SIG_MARKER_START[1]) + len(b"ByteRange: [ ")
    len_digit = falcon.gap_start + len(b"SigLength: ") + 9
    padding = falcon.contents_end - 1
    for name, position, byte, structure in (
        ("C7.byte_range", br_digit, b"-", "byte_range.syntax"),
        ("C7.length", len_digit, b"1", "metadata.length"),
        ("C7.padding", padding, b"1", "contents.padding"),
    ):
        specimen = data[:position] + byte + data[position + 1:]
        yield evaluate(pdf.HYBRID, name, specimen, public, structure)
    yield evaluate(pdf.HYBRID, "C7.cardinality", data + utils.SIG_MARKER_START[1], public, "pair.markers")


def export_bundle(directory, *, environment, source_commit, run_id, attempt):
    from tempfile import TemporaryDirectory

    with TemporaryDirectory(prefix=".public-bundle-", dir=directory.parent) as owned:
        raw = Path(owned) / "sample.pdf"
        signed = directory / "sample-hybrid.pdf"
        raw.write_bytes(pdf.fixture("demo"))
        pair = pdf.generate_hybrid_key_pair()
        directory.mkdir()
        pdf.sign_document(raw, signed, pdf.HYBRID, pair)
        pdf.require(pdf.verify_document(signed, pdf.HYBRID, pdf.publics(pair)) is True, "bundle.self_verify")
        for name, material in zip(("ed25519.pub", "falcon.pub"), pdf.publics(pair), strict=True):
            with (directory / name).open("xb") as stream:
                stream.write(material)
    checksums = {name: file_hash(directory / name) for name in FILES}
    write_json(directory / "bundle.json", dict(schema=BUNDLE_SCHEMA, protocol=PROTOCOL,
              producer=environment, source_commit=source_commit, run_id=run_id, attempt=attempt,
              public_sample_sha256=pdf.WORKLOADS["demo"][1], checksums=checksums))


def verify_bundle(directory, *, source_commit, producer, run_id=None, attempt=None):
    from .environment import ENVIRONMENTS

    pdf.require(not directory.is_symlink() and {p.name for p in directory.iterdir()} ==
                {"bundle.json", *FILES}, "bundle.inventory")
    manifest_path = directory / "bundle.json"
    pdf.require(manifest_path.is_file() and not manifest_path.is_symlink() and
                manifest_path.stat().st_size < 4096, "bundle.manifest")
    manifest = json.loads(manifest_path.read_bytes())
    pdf.require(set(manifest) == {"schema", "protocol", "producer", "source_commit", "run_id", "attempt",
                "public_sample_sha256", "checksums"} and manifest["schema"] == BUNDLE_SCHEMA and
                manifest["protocol"] == PROTOCOL and producer in ENVIRONMENTS and manifest["producer"] == producer and
                re.fullmatch("[0-9a-f]{40}", source_commit) and manifest["source_commit"] == source_commit and
                (run_id is None or manifest["run_id"] == run_id) and (attempt is None or manifest["attempt"] == attempt) and
                manifest["public_sample_sha256"] == pdf.WORKLOADS["demo"][1] and
                set(manifest["checksums"]) == set(FILES), "bundle.provenance")
    loaded = {}
    for name, length in FILES.items():
        path = directory / name
        pdf.require(path.is_file() and not path.is_symlink() and path.stat().st_size == length, "bundle.size_or_type")
        loaded[name] = path.read_bytes()
        pdf.require(len(loaded[name]) == length and pdf.sha(loaded[name]) == manifest["checksums"][name], "bundle.hash")
    data = loaded["sample-hybrid.pdf"]
    pdf.require(pdf.sha(data[:742]) == pdf.WORKLOADS["demo"][1], "bundle.sample")
    public = loaded["ed25519.pub"], loaded["falcon.pub"]
    # Verify the same bytes whose hashes were checked through the production hybrid verifier.
    pdf.require(pdf.assess(data, pdf.HYBRID, public) ==
                {"structure": "valid", "ed25519": True, "falcon": True, "valid": True}, "bundle.hybrid_verify")
    return dict(producer=producer, source_commit=source_commit, protocol=PROTOCOL, valid=True,
                bundle_inventory_sha256=pdf.sha(manifest_path.read_bytes()),
                run_id=manifest["run_id"], attempt=manifest["attempt"])
