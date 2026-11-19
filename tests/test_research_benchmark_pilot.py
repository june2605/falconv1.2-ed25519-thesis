import csv
import io
import re

import pytest

from research.benchmarks import phase5_2a as pilot


@pytest.mark.parametrize("length", pilot.INPUT_LENGTHS)
def test_public_messages_have_exact_reproducible_lengths(length):
    message = pilot.message_bytes(length)
    assert type(message) is bytes and len(message) == length
    assert message == pilot.message_bytes(length)
    assert message != pilot.message_bytes(length + 1)[:length]


@pytest.mark.parametrize("size", [743, 1024, pilot.MIB])
def test_public_pdf_extension_preserves_objects_and_exact_size(size):
    sample = pilot.SAMPLE.read_bytes()
    original = pilot.validate_pdf(sample, len(sample))
    data = pilot.extend_pdf(sample, size)
    generated = pilot.validate_pdf(data, size)
    assert data == pilot.extend_pdf(sample, size)
    assert data[:int(original[1])] == sample[:int(original[1])]
    assert data[int(generated[1]):generated.start(1)] == sample[int(original[1]):original.start(1)]


@pytest.mark.parametrize("damage", ["size", "xref", "stream", "trailer"])
def test_invalid_pdf_fixture_is_rejected(damage):
    sample = pilot.SAMPLE.read_bytes()
    if damage == "size":
        changed = sample + b" "
    elif damage == "xref":
        changed = sample.replace(b"xref\n0 6", b"XXXX\n0 6", 1)
    elif damage == "stream":
        changed = re.sub(rb"/Length [0-9]+", b"/Length 000", sample, count=1)
    else:
        changed = sample.replace(b"%%EOF", b"%%END")
    assert changed != sample
    with pytest.raises(pilot.PilotError, match="pdf_"):
        pilot.validate_pdf(changed, len(sample))


def test_output_root_rejects_checkout_without_writing(tmp_path):
    assert pilot.output_parent(tmp_path) == tmp_path.resolve()
    with pytest.raises(pilot.PilotError, match="output_must_be_outside_git"):
        pilot.output_parent(pilot.ROOT)
    (tmp_path / ".git").write_text("gitdir: elsewhere", encoding="ascii")
    with pytest.raises(pilot.PilotError, match="output_must_be_outside_git"):
        pilot.output_parent(tmp_path)


def raw_writer(stream):
    writer = csv.DictWriter(stream, fieldnames=pilot.RAW_FIELDS)
    writer.writeheader()
    return writer


def test_trial_order_alternates_and_algorithms_are_given_identical_messages(tmp_path, monkeypatch):
    primitive_calls = []
    hybrid_calls = []

    def primitive(meter, algorithm, message):
        primitive_calls.append((algorithm, message))

    def hybrid(meter, source, output, size, pair, wrong, profiled):
        hybrid_calls.append(profiled)

    monkeypatch.setattr(pilot, "primitive_trial", primitive)
    monkeypatch.setattr(pilot, "hybrid_trial", hybrid)
    stream = io.StringIO()
    inputs = [("demo", pilot.SAMPLE, pilot.SAMPLE.stat().st_size, "fixture-hash")]
    pilot.run_trials(raw_writer(stream), "test", inputs, None, None, tmp_path / "out.pdf", 1, 2, 30)
    assert len(primitive_calls) == 12
    for left, right in zip(primitive_calls[::2], primitive_calls[1::2], strict=True):
        assert left[1] is right[1]
        assert {left[0], right[0]} == {"Ed25519", "Falcon-512"}
    assert [call[0] for call in primitive_calls[::4]] == ["Ed25519", "Ed25519", "Falcon-512"]
    assert hybrid_calls == [False, True, False, True, True, False]
    stream.seek(0)
    rows = list(csv.DictReader(stream))
    assert {(row["phase"], row["repetition"]) for row in rows} == {
        ("warmup", "1"), ("measured", "1"), ("measured", "2")
    }


@pytest.mark.parametrize("algorithm", ["Ed25519", "Falcon-512"])
def test_primitive_times_verified_keygen_sign_and_verify(algorithm):
    meter = pilot.Measurements()
    pilot.primitive_trial(meter, algorithm, pilot.message_bytes(64))
    assert [item["operation"] for item in meter.rows[:3]] == ["keygen", "sign", "verify"]
    assert all(type(item["elapsed_ns"]) is int and item["elapsed_ns"] >= 0 for item in meter.rows[:3])
    lengths = {item["operation"]: item["observed_bytes"] for item in meter.rows[3:]}
    assert lengths["public_key_bytes"] == (32 if algorithm == "Ed25519" else 897)
    assert lengths["private_key_bytes"] == (32 if algorithm == "Ed25519" else 1281)
    assert 0 < lengths["native_signature_bytes"] <= (64 if algorithm == "Ed25519" else 752)


@pytest.mark.parametrize("profiled", [False, True])
def test_real_hybrid_separates_wall_timing_profile_and_legacy_slots(tmp_path, profiled, monkeypatch):
    output = tmp_path / "trial.pdf"
    source = pilot.SAMPLE
    pair = pilot.generate_hybrid_key_pair()
    wrong = pilot.generate_hybrid_key_pair().public_keys
    core = pilot.sign._sign_captured
    if not profiled:
        def unexpected_profile(_):
            pytest.fail("Unprofiled trial must not install instrumentation")
        monkeypatch.setattr(pilot, "profile_pipeline", unexpected_profile)

    meter = pilot.Measurements()
    pilot.hybrid_trial(meter, source, output, source.stat().st_size, pair, wrong, profiled)
    clocked = [row["operation"] for row in meter.rows if "elapsed_ns" in row]
    if profiled:
        assert tuple(clocked) == (*pilot.PROFILE_ORDER, "profiled_sign_and_publish")
    else:
        assert clocked == ["sign_and_publish", "verify_published_file"]
    assert sum("legacy_seconds" in row for row in meter.rows) == (10 if profiled else 20)
    sizes = {row["operation"]: row["observed_bytes"] for row in meter.rows if "observed_bytes" in row}
    assert sizes["ed25519_message_bytes"] > 64 and sizes["falcon_message_bytes"] == 64
    assert sizes["pdf_overhead_bytes"] == 4626 and sizes["signed_file_bytes"] == 5368
    assert not output.exists() and pilot.sign._sign_captured is core


def test_existing_output_is_preserved(tmp_path):
    output = tmp_path / "existing.pdf"
    output.write_bytes(b"owner content")
    with pytest.raises(pilot.PilotError, match="benchmark_destination_exists"):
        pilot.hybrid_trial(pilot.Measurements(), pilot.SAMPLE, output, 742, None, None, False)
    assert output.read_bytes() == b"owner content"


def test_failed_verification_marks_raw_rows_and_aborts(monkeypatch):
    monkeypatch.setattr(pilot.falcon_512, "verify", lambda *args: False)
    stream = io.StringIO()
    with pytest.raises(pilot.PilotError, match="falcon_verify"):
        pilot.record_trial(raw_writer(stream), {"experiment_id": "test"}, pilot.primitive_trial,
                           "Falcon-512", pilot.message_bytes(64))
    stream.seek(0)
    rows = list(csv.DictReader(stream))
    assert [row["operation"] for row in rows] == ["keygen", "sign", "verify", "trial_failure"]
    assert all(row["status"] == "failed" and row["failure_code"] == "falcon_verify" for row in rows)
    assert all(row["observed_bytes"] == "" for row in rows)


def test_failed_published_output_check_preserves_failure_and_cleans_staged_pdf(tmp_path, monkeypatch):
    source = pilot.SAMPLE
    output = tmp_path / "trial.pdf"
    pair = pilot.generate_hybrid_key_pair()
    wrong = pilot.generate_hybrid_key_pair().public_keys
    monkeypatch.setattr(pilot, "verify_file_with_public_keys", lambda *args: (False,) + (0,) * 10)
    stream = io.StringIO()
    with pytest.raises(pilot.PilotError, match="hybrid_verify"):
        pilot.record_trial(raw_writer(stream), {"experiment_id": "test"}, pilot.hybrid_trial,
                           source, output, source.stat().st_size, pair, wrong, False)
    stream.seek(0)
    rows = list(csv.DictReader(stream))
    assert all(row["status"] == "failed" and row["failure_code"] == "hybrid_verify" for row in rows)
    assert any(row["operation"] == "verify_published_file" for row in rows)
    assert not output.exists()


def test_unexpected_failure_only_reports_exception_type():
    def failure(_):
        raise RuntimeError("secret detail from a test double")
    stream = io.StringIO()
    with pytest.raises(RuntimeError):
        pilot.record_trial(raw_writer(stream), {"experiment_id": "test"}, failure)
    assert "secret detail" not in stream.getvalue()
    stream.seek(0)
    row, = csv.DictReader(stream)
    assert row["failure_code"] == "RuntimeError" and row["status"] == "failed"


def test_time_budget_records_exclusion_before_work(tmp_path, monkeypatch):
    ticks = iter((0, 1_000_000_000))
    monkeypatch.setattr(pilot.time, "perf_counter_ns", lambda: next(ticks))
    stream = io.StringIO()
    with pytest.raises(pilot.PilotError, match="pilot_time_budget"):
        pilot.run_trials(raw_writer(stream), "test", [], None, None, tmp_path / "out.pdf", 1, 1, 1)
    stream.seek(0)
    row, = csv.DictReader(stream)
    assert row["operation"] == "admission" and row["status"] == "excluded" and row["elapsed_ns"] == ""


def test_summary_keeps_slow_samples_and_separates_units(tmp_path):
    raw = tmp_path / "raw.csv"
    with raw.open("w", newline="", encoding="utf-8") as file:
        writer = raw_writer(file)
        base = dict(experiment_id="test", category="B", mode="unprofiled", workload="demo",
                    algorithm="Hybrid", operation="sign_and_publish", phase="measured", status="ok")
        for elapsed in [10] * 29 + [1000]:
            writer.writerow({**base, "elapsed_ns": elapsed})
        writer.writerow({**base, "phase": "warmup", "elapsed_ns": 100_000})
        writer.writerow({**base, "status": "failed", "elapsed_ns": 100_000})
        writer.writerow({**base, "operation": "short_series", "elapsed_ns": 10})
        writer.writerow({**base, "legacy_seconds": 0.02})
        writer.writerow({**base, "observed_bytes": 42})
    rows = {(row["operation"], row["unit"]): row for row in pilot.summarize(raw)}
    main = rows["sign_and_publish", "ns"]
    assert (main["n"], main["median"], main["mean"], main["maximum"], main["p95"]) == (30, 10, 43, 1000, 10)
    assert rows["sign_and_publish", "s"]["median"] == 0.02
    assert rows["sign_and_publish", "B"]["median"] == 42
    assert rows["short_series", "ns"]["p95"] is None and rows["short_series", "ns"]["sd"] is None
