import csv
import json

import pytest

from research.benchmarks import phase5_2b_analysis as analysis
from research.benchmarks import phase5_2b_collect as collection


def test_preserve_pilot_copies_the_original_bytes_without_replacement(tmp_path, monkeypatch):
    source = tmp_path / "source"
    source.mkdir()
    (source / "raw.csv").write_bytes(b"a,b\r\n1,2\r\n")
    (source / "summary.json").write_bytes(b"{}\n")
    expected = {file.name: collection.file_hash(file) for file in source.iterdir()}
    monkeypatch.setattr(collection, "PILOT_ARTIFACTS", expected)
    archive = tmp_path / "archive"
    collection.preserve_pilot(source, archive)
    for name, digest in expected.items():
        assert collection.file_hash(archive / name) == digest
        assert (archive / name).read_bytes() == (source / name).read_bytes()
    with pytest.raises(FileExistsError):
        collection.preserve_pilot(source, archive)
    assert json.loads((archive / "archive-checksums.json").read_bytes()) == expected


@pytest.mark.parametrize("missing", [False, True])
def test_preservation_rejects_missing_or_untrusted_evidence_before_copying(tmp_path, monkeypatch, missing):
    source = tmp_path / "source"
    source.mkdir()
    if not missing:
        (source / "raw.csv").write_bytes(b"unexpected")
    monkeypatch.setattr(collection, "PILOT_ARTIFACTS", {"raw.csv": "a" * 64})
    archive = tmp_path / "archive"
    with pytest.raises(ValueError, match="Missing.*raw.csv" if missing else "hash mismatch: raw.csv"):
        collection.preserve_pilot(source, archive)
    assert not archive.exists()


def metadata():
    return {"experiment_id": "synthetic-unit-test", "warmups": 1, "repetitions": 2,
            "pdf_inputs": [{"workload": "demo", "input_bytes": 742}]}


def raw_observations(meta):
    columns = {unit: field for field, (unit, _) in analysis.VALUE_FIELDS.items()}
    for phase, count in (("warmup", meta["warmups"]), ("measured", meta["repetitions"])):
        for rep in range(1, count + 1):
            for order, (mode, workload, algorithm, input_bytes) in enumerate(analysis.expected_order(meta, rep), 1):
                for category, operation, unit in sorted(analysis.expected_metrics(mode, algorithm)):
                    yield dict(
                        phase=phase, repetition=rep, order_in_block=order, mode=mode, workload=workload,
                        algorithm=algorithm, input_bytes=input_bytes, category=category, operation=operation,
                        experiment_id=meta["experiment_id"], status="ok",
                        **{columns[unit]: 9000 if phase == "warmup" else rep * 10}
                    )


def test_order_matches_the_rotating_plan():
    meta = metadata()
    meta["pdf_inputs"].extend([{"workload": "1-MiB", "input_bytes": 1048576},
                               {"workload": "10-MiB", "input_bytes": 10485760}])
    order = analysis.expected_order(meta, 2)
    assert order[:3] == [
        ("primitive", "64-B", "shared", 64),
        ("primitive", "64-B", "Falcon-512", 64),
        ("primitive", "64-B", "Ed25519", 64),
    ]
    assert [x[1] for x in order[6:]] == ["1-MiB", "1-MiB", "10-MiB", "10-MiB", "demo", "demo"]
    assert [x[0] for x in order[6:]] == ["profiled", "unprofiled"] * 3


def test_raw_excludes_warmups_but_requires_complete_records(tmp_path):
    meta = metadata()
    raw = tmp_path / "raw.csv"
    rows = list(raw_observations(meta))
    analysis.write_csv(raw, analysis.pilot.RAW_FIELDS, rows)
    values, observations, trials = analysis.read_raw(raw, meta)
    assert trials == 24 and observations == len(rows)
    assert values["A", "primitive", "64-B", "Ed25519", "sign", "ns"] == [10, 20]
    assert values["B", "unprofiled", "demo", "Hybrid", "sign_slot_falcon_total", "s"] == [10.0, 20.0]
    assert values["C", "unprofiled", "demo", "Hybrid", "pdf_overhead_bytes", "B"] == [10, 20]


@pytest.mark.parametrize(("fault", "reason"), [
    ("failed", "Failed or excluded"),
    ("excluded", "Failed or excluded"),
    ("order", "Unexpected workload or trial order"),
    ("duplicate", "Unexpected or duplicate"),
    ("missing", "Incomplete raw trial"),
    ("wrong-unit", "Unexpected or duplicate"),
    ("invalid", "Invalid observation"),
    ("identity", "Unexpected experiment identity"),
])
def test_raw_rejects_incomplete_invalid_or_conflicting_data(tmp_path, fault, reason):
    meta = metadata()
    raw = tmp_path / "raw.csv"
    rows = list(raw_observations(meta))
    if fault in ("failed", "excluded"):
        rows[0]["status"] = fault
    elif fault == "order":
        rows[0]["order_in_block"] = 2
    elif fault == "duplicate":
        rows.append(rows[0].copy())
    elif fault == "missing":
        rows.pop(0)
    elif fault == "wrong-unit":
        rows[0]["observed_bytes"] = rows[0].pop("elapsed_ns")
    elif fault == "identity":
        rows[0]["experiment_id"] = "different"
    else:
        rows[0]["elapsed_ns"] = -1
    analysis.write_csv(raw, analysis.pilot.RAW_FIELDS, rows)
    with pytest.raises(ValueError, match=reason):
        analysis.read_raw(raw, meta)


def test_summary_reports_interpolated_p95_and_preserves_between_session_variation():
    single = analysis.describe([*range(29), 3000])
    assert single["n"] == 30 and single["maximum"] == 3000
    assert single["p95"] == pytest.approx(27.55)
    assert analysis.describe([1])["sd"] is None and analysis.describe([1])["p95"] is None

    key = ("A", "primitive", "64-B", "Ed25519", "sign", "ns")
    pooled = analysis.aggregate_matched([{key: [10, 20]}, {key: [30, 40]}, {key: [50, 3000]}])[key]
    assert pooled["n"] == 6 and pooled["median"] == 35 and pooled["maximum"] == 3000
    assert (pooled["session_median_min"], pooled["median_of_session_medians"], pooled["session_median_max"]) == (
        15, 35, 1525
    )
    with pytest.raises(ValueError, match="identical metric groups"):
        analysis.aggregate_matched([{key: [10]}, {}])


def test_ratios_use_matched_message_and_operation():
    metrics = {
        ("A", "primitive", f"{size}-B", algorithm, operation, "ns"): {"median": median}
        for size in (64, 1024)
        for algorithm, operation, median in (
            ("Ed25519", "sign", 40), ("Falcon-512", "sign", 4000),
            ("Ed25519", "verify", 100), ("Falcon-512", "verify", 40),
        )
    }
    ratios = analysis.median_ratios("matched-01", metrics)
    assert len(ratios) == 4 and {r["workload"] for r in ratios} == {"64-B", "1024-B"}
    assert {r["operation"]: r["falcon_over_ed25519"] for r in ratios} == {"sign": 100.0, "verify": 0.4}


def test_optional_supplement_does_not_overwrite_collection_manifest(tmp_path):
    collected = {"status": "complete", "sessions": ["matched-01", "optional-40-feasibility"],
                 "optional_40": "not_run_after_feasibility"}
    manifest = tmp_path / "collection.json"
    original = json.dumps(collected).encode()
    manifest.write_bytes(original)
    extension = {"status": "complete", "session": "optional-40-measured",
                 "prior_feasibility": "optional-40-feasibility"}
    extension_file = tmp_path / "optional-extension.json"
    extension_file.write_text(json.dumps(extension), encoding="utf-8")
    combined = analysis.completed_collection(tmp_path)
    assert combined["sessions"] == ["matched-01", "optional-40-feasibility", "optional-40-measured"]
    assert combined["optional_40"] == "complete_in_separate_supplement"
    assert manifest.read_bytes() == original
    extension["status"] = "failed"
    extension_file.write_text(json.dumps(extension), encoding="utf-8")
    with pytest.raises(ValueError, match="optional supplement"):
        analysis.completed_collection(tmp_path)
