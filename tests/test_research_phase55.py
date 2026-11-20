"""Research-only comparator, evidence and workflow regressions."""
import csv
import itertools
import json
from collections import Counter
from pathlib import Path
import re
from types import SimpleNamespace

import pytest
import yaml

import sign
import utils
import verify
from research.benchmarks.p55 import analysis, ci, controls, environment as env, pdf, protocol
from research.benchmarks.p55.__main__ import build_parser


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "public.pdf"
    path.write_bytes(pdf.fixture("demo"))
    return path


@pytest.fixture
def keys():
    return pdf.generated_keys()


@pytest.mark.parametrize("workload", pdf.WORKLOADS)
def test_public_fixture_provenance(workload):
    data = pdf.fixture(workload)
    assert (len(data), pdf.sha(data)) == pdf.WORKLOADS[workload]


@pytest.mark.parametrize("method,growth", [(pdf.ED, 394), (pdf.FALCON, 4232)])
def test_single_comparators_verify_and_never_fall_back(source, keys, method, growth):
    pair, wrong = keys
    out = source.with_name("signed.pdf")
    assert pdf.sign_document(source, out, method, pair) == out
    data = out.read_bytes()
    original = source.read_bytes()
    parsed = pdf.parse_single(data, method)
    kind = pdf.KINDS[method]
    assert parsed.marker_start == len(original)
    assert parsed.marker_end == len(data)
    assert parsed.capacity_bytes == utils.DEFAULT_SIGNATURE_CAPACITIES[kind]
    assert parsed.signature_length % 2 == 0
    assert data[:len(original)] == original == pdf.fixture("demo")
    assert data[parsed.contents_start + parsed.signature_length:parsed.contents_end].strip(b"0") == b""
    assert pdf.verify_document(out, method, pdf.publics(pair)) is True
    assert pdf.verify_document(out, method, pdf.publics(wrong)) is False
    assert verify.verify_bytes(data, *pdf.publics(pair))[0] is False
    assert pdf.sizes(data, len(original), method)["growth_bytes"] == growth
    assert all(case["passed"] for case in controls.positive_controls(data, method, pair, wrong))


@pytest.mark.parametrize("method", [pdf.ED, pdf.FALCON])
@pytest.mark.parametrize("mutation", ["trailing", "duplicate", "other_marker", "gap", "length", "padding"])
def test_single_parser_enforces_its_own_boundary(source, keys, method, mutation):
    pair, _ = keys
    out = source.with_name("single.pdf")
    pdf.sign_document(source, out, method, pair)
    data = out.read_bytes()
    container = pdf.parse_single(data, method)
    kind = pdf.KINDS[method]
    cases = {
        "trailing": (data + b"\n", "single.trailing"),
        "duplicate": (data + utils.SIG_MARKER_START[kind], "single.markers"),
        "other_marker": (data + utils.SIG_MARKER_END[1 - kind], "single.markers"),
    }
    for name, at, text, reason in (
        ("gap", container.marker_start + len(utils.SIG_MARKER_START[kind]) + len(b"ByteRange: [ "),
         b"9", "byte_range.bounds"),
        ("length", container.gap_start + len(b"SigLength: ") + 9, b"1", "metadata.length"),
        ("padding", container.contents_end - 1, b"1", "contents.padding"),
    ):
        cases[name] = (data[:at] + text + data[at + 1:], reason)
    changed, reason = cases[mutation]
    with pytest.raises(utils.SignatureFormatError) as err:
        pdf.parse_single(changed, method)
    assert err.value.code == reason
    assert pdf.verify_single_bytes(changed, method, pdf.publics(pair)[kind]) is False


@pytest.mark.parametrize("method", [pdf.ED, pdf.FALCON])
def test_candidate_is_verified_before_publication(source, keys, method, monkeypatch):
    pair, _ = keys
    destination = source.with_name("occupied.pdf")
    destination.write_bytes(b"old destination")
    real_verify = pdf.verify_single_file
    seen = []

    def observe(path, selected, public):
        assert path != destination
        assert destination.read_bytes() == b"old destination"
        assert real_verify(path, selected, public) is True
        seen.append(path)
        return False

    monkeypatch.setattr(pdf, "verify_single_file", observe)
    with pytest.raises(pdf.ResearchError, match="candidate.verify"):
        pdf.sign_document(source, destination, method, pair)
    assert len(seen) == 1 and not seen[0].exists()
    assert sorted(p.name for p in source.parent.iterdir()) == ["occupied.pdf", "public.pdf"]
    assert destination.read_bytes() == b"old destination"
    assert source.read_bytes() == pdf.fixture("demo")


@pytest.mark.parametrize("method", [pdf.ED, pdf.FALCON])
def test_single_method_protects_input_and_rejects_mismatched_key(source, keys, method):
    pair, wrong = keys
    own = pdf.to_single(pair, method)
    other = pdf.to_single(wrong, method)
    with pytest.raises(pdf.SigningPathError, match="path.alias"):
        pdf.sign_single_file(source, source, method, own)
    with pytest.raises(pdf.ResearchError, match="key.correspondence|key.self_test"):
        pdf.sign_single_file(source, source.with_name("out.pdf"), method, pdf.SingleKey(other.public, own.private))
    assert list(source.parent.iterdir()) == [source]
    assert source.read_bytes() == pdf.fixture("demo")


def test_hybrid_calls_production_apis_with_the_original_contract(source, keys, monkeypatch):
    pair, _ = keys
    seen = []
    sign_original = sign.sign_with_key_material
    verify_original = verify.verify_file_with_public_keys

    def sign_spy(*args):
        seen.append(("sign", args))
        return sign_original(*args)

    def verify_spy(*args):
        seen.append(("verify", args))
        return verify_original(*args)

    monkeypatch.setattr(sign, "sign_with_key_material", sign_spy)
    monkeypatch.setattr(verify, "verify_file_with_public_keys", verify_spy)
    target = source.with_name("hybrid.pdf")
    pdf.sign_document(source, target, pdf.HYBRID, pair)
    assert pdf.verify_document(target, pdf.HYBRID, pdf.publics(pair))
    assert seen == [("sign", (source, target, pair)), ("verify", (target, *pdf.publics(pair)))]
    assert pdf.hybrid_result((False,) + (0,) * 10) is False
    with pytest.raises(pdf.ResearchError, match="hybrid.verify_contract"):
        pdf.hybrid_result((1,) + (0,) * 10)


def test_c0_to_c7_exercise_both_layers_or_report_not_evaluated(tmp_path):
    report = controls.smoke(tmp_path)
    assert len(report) == 19
    assert all(row["passed"] is True for row in report)
    hybrid = {row["control"]: row for row in report if row["method"] == pdf.HYBRID}
    for code, expected in controls.EXPECTATIONS.items():
        row = hybrid[code]
        assert (row["ed25519"], row["falcon"], row["valid"]) == expected
    for case in ("C4.remove_ed25519", "C4.remove_falcon", "C4.reverse", "C7.byte_range",
                 "C7.length", "C7.padding", "C7.cardinality"):
        assert hybrid[case]["ed25519"] == hybrid[case]["falcon"] == pdf.NOT_EVALUATED
        assert hybrid[case]["valid"] is False
    assert not list(tmp_path.iterdir())


def test_c8_exact_allowlisted_files_and_precrypto_hash_check(tmp_path, monkeypatch):
    directory = tmp_path / "bundle"
    source = "a" * 40
    options = dict(source_commit=source, producer="LOCAL-WIN", run_id="123", attempt="1")
    controls.export_bundle(directory, environment="LOCAL-WIN", source_commit=source, run_id="123", attempt="1")
    assert set(p.name for p in directory.iterdir()) == {"bundle.json", *controls.FILES}
    assert controls.verify_bundle(directory, **options)["valid"] is True
    with pytest.raises(pdf.ResearchError, match="bundle.provenance"):
        controls.verify_bundle(directory, **(options | {"run_id": "124"}))
    public = directory / "ed25519.pub"
    public.write_bytes(bytes(32))
    monkeypatch.setattr(pdf, "assess", lambda *a: pytest.fail("hash failure must short circuit native verification"))
    with pytest.raises(pdf.ResearchError, match="bundle.hash"):
        controls.verify_bundle(directory, **options)


@pytest.mark.parametrize("mode,n", [("pilot", 6), ("main", 30)])
def test_schedule_balances_orders_and_counts(mode, n):
    trials = protocol.schedule(mode, 5501)
    assert trials == protocol.schedule(mode, 5501)
    assert trials != protocol.schedule(mode, 5502)
    measured = [t for t in trials if t.phase == "measured"]
    assert len(trials) == 15 * (n + 3)
    assert sum(len(t.operations) for t in measured) == 28 * n
    assert len({t.id for t in trials}) == len(trials)
    keys = [t for t in measured if t.layer == "keygen"]
    counts = Counter((t.method, t.workload) for t in keys)
    assert counts == {(pdf.ED, "keygen"): n, (pdf.FALCON, "keygen"): n}
    primitive = [t for t in measured if t.layer == "primitive"]
    for size in (64, 1024):
        first = Counter(t.method for t in primitive if t.workload == f"{size}-B" and t.method_order == 1)
        assert first == {pdf.ED: n // 2, pdf.FALCON: n // 2}
    pdf_trials = [t for t in measured if t.layer == "pdf"]
    for workload in pdf.WORKLOADS:
        orders = Counter(tuple(t.method for t in pdf_trials if t.workload == workload and t.block == b)
                         for b in range(1, n + 1))
        assert orders == {perm: n // 6 for perm in itertools.permutations(pdf.METHODS)}
    for layer, count in (("primitive", n // 2), ("pdf", n // 6)):
        workload_orders = Counter(tuple(dict.fromkeys(t.workload for t in measured if t.layer == layer and t.block == b))
                                  for b in range(1, n + 1))
        assert set(workload_orders.values()) == {count}


def test_host_can_record_unavailable_identifiers_without_inventing_them(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "windows_state", lambda root: {})
    state = env.host_state("windows", tmp_path)
    assert state["available"] == state["cpu"] == state["power"] == "unknown"
    with pytest.raises(env.EnvironmentError, match="preflight.local_filesystem_required"):
        env.preflight(state)
    identity = env.execution("CI-LINUX")
    assert identity["physical_host_id"] == identity["physical_parent_id"] == "unknown"
    assert identity["runner_label"] == "ubuntu-24.04"


def test_admission_and_failed_timing_are_persisted(tmp_path, monkeypatch):
    for failure in (False, True):
        work = tmp_path / str(failure)
        work.mkdir()

        def fail(self, trial, timer, sizes, identity):
            timer.measure("keygen", lambda: 1 / 0)

        monkeypatch.setattr(protocol.TrialLoop, "run", fail)
        result = protocol.run_trials(work, {}, protocol.schedule("pilot", 1), 10**30 if failure else 0)
        rows = list(csv.DictReader((work / "raw.csv").open(encoding="utf-8", newline="")))
        assert len(rows) == 1 and rows[0]["status"] == result["status"]
        assert result["warmup_positive_rows"] == 0
        assert rows[0]["elapsed_ns"].isdecimal() if failure else not rows[0]["elapsed_ns"]
        assert result["failure_code"] == ("ZeroDivisionError" if failure else "admission.budget")
        assert json.loads((work / "progress.jsonl").read_text().splitlines()[-1])["status"] == result["status"]


def test_setup_failure_creates_a_verifiable_evidence_inventory(tmp_path, monkeypatch):
    monkeypatch.setattr(env, "safe_output", lambda path, *, local: path)
    monkeypatch.setattr(env, "check_idle", lambda: None)

    def unavailable(*args, **kwargs):
        raise env.EnvironmentError("profile.wheel_unavailable")

    monkeypatch.setattr(env, "runtime_profile", unavailable)
    location = tmp_path / "failed"
    result = protocol.run_campaign(location, mode="pilot", seed=1, environment="LOCAL-WIN", wheelhouse=tmp_path)
    assert result == {"status": "failed", "failure_code": "profile.wheel_unavailable"}
    assert protocol.check_inventory(location) == ["outcome.json"]
    assert analysis.summary([location])["sessions"][0]["outcome"]["failure_code"] == result["failure_code"]
    with pytest.raises(FileExistsError):
        protocol.run_campaign(location, mode="pilot", seed=1, environment="LOCAL-WIN", wheelhouse=tmp_path)


def test_quantiles_and_pair_matching_are_not_ratios_of_medians():
    assert analysis.describe([0, 10, 20, 30])["iqr"] == 15
    assert analysis.describe(list(range(30)))["p95"] == pytest.approx(27.55)
    assert analysis.describe([1, 2, 3])["p95"] is None
    rows = []
    for block, trio in enumerate([(10, 30, 90), (100, 20, 101), (50, 50, 51)], 1):
        rows.extend(dict(layer="pdf", environment="LOCAL-WIN", run_id="unknown", job="unknown", attempt="unknown",
                         session="A", process_id="1", block=block, workload="demo", operation="sign_and_publish",
                         method=m, elapsed_ns=n * 10**6) for m, n in zip(pdf.METHODS, trio, strict=True))
    stats = analysis.paired_stats(rows)
    ed = next(s for s in stats if s["baseline"] == pdf.ED)
    assert ed["hybrid_minus_baseline_ms"]["median"] == 1
    assert ed["per_pair_ratio"]["median"] == 51 / 50
    assert ed["per_pair_ratio"]["median"] != 90 / 50
    rows[0]["elapsed_ns"] = 0
    assert analysis.paired_stats(rows)[0]["nonpositive_denominator_count"] == 1
    with pytest.raises(pdf.ResearchError, match="paired.missing_method"):
        analysis.paired_stats(rows[:-1])


def test_reconstruct_full_synthetic_pilot_and_reject_repeated_session(tmp_path, monkeypatch):
    # Artificial values are confined to this estimator fixture.
    plan = protocol.config("pilot", 5501)
    trials = protocol.schedule("pilot", 5501)
    execution = env.execution("LOCAL-WIN")
    session = {"execution": execution, "configuration": plan, "session": "test-only", "campaign": "test-only",
               "before": {"cpu": "derived-test", "build": "derived-test"}, "source_set_sha256": "test",
               "profile": {"file_sha256": "test", "architecture": "x64"}}
    identity = {k: v for k, v in execution.items() if k in protocol.RAW_FIELDS}
    identity.update(schema=protocol.SCHEMA, protocol=protocol.PROTOCOL, campaign="test-only",
                    session="test-only", schedule_sha256=plan["schedule_sha256"])
    env.write_json(tmp_path / "session.json", session)
    env.write_json(tmp_path / "schedule.json", protocol.schedule_file("pilot", 5501, trials))
    env.write_json(tmp_path / "smoke.json", [])

    def mock_unit(self, trial, timer, sizes, identity):
        timer.samples.extend((op, 10**6 * trial.method_order) for op in trial.operations)
        if trial.layer == "pdf":
            sizes.update(output_bytes=sizes["input_bytes"] + 1, growth_bytes=1)

    monkeypatch.setattr(protocol.TrialLoop, "run", mock_unit)
    result = protocol.run_trials(tmp_path, identity, trials, 10**30)
    assert (result["measured_trials"], result["measured_positive_rows"]) == (90, 168)
    env.write_json(tmp_path / "outcome.json", result)
    protocol.inventory(tmp_path)
    report = analysis.summary([tmp_path])
    assert len(report["aggregates"]) == 1
    assert all(r["n"] == 6 and r["p95"] is None for r in report["sessions"][0]["statistics"])
    with pytest.raises(pdf.ResearchError, match="analysis.duplicate_session"):
        analysis.summary([tmp_path, tmp_path])


def test_workflow_is_manual_pinned_and_calls_real_cli():
    path = env.ROOT / ci.WORKFLOW
    workflow = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["mode"]["default"] == "pilot"
    assert workflow["concurrency"]["cancel-in-progress"] == "false"
    assert workflow["jobs"]["research"]["strategy"]["max-parallel"] == "1"
    assert workflow["permissions"] == {"contents": "read"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["mode"]["options"] == ["pilot", "compat"]
    assert set(workflow["jobs"]) == {"research"}
    matrix = workflow["jobs"]["research"]["strategy"]["matrix"]["include"]
    assert len(matrix) == 3 and {entry["environment"]: entry["runner"] for entry in matrix} == env.RUNNERS
    checkout = next(step for step in workflow["jobs"]["research"]["steps"]
                    if step.get("uses", "").startswith("actions/checkout@"))
    assert checkout["with"]["ref"] == "$"+"{{ inputs.source_commit }}"
    assert checkout["with"]["persist-credentials"] == "false"
    measure = next(step for step in workflow["jobs"]["research"]["steps"]
                   if step.get("name") == "Run one paired measurement session")
    assert measure["if"] == "inputs.mode == 'pilot'" and "run --mode pilot" in measure["run"]
    parsers = {"research.benchmarks.p55": build_parser(), "research.benchmarks.p55.ci": ci.build_parser()}
    for job in workflow["jobs"].values():
        for step in job["steps"]:
            if "uses" in step:
                assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", step["uses"])
            for module, command, arguments in re.findall(
                    r"-m (research\.benchmarks\.p55(?:\.ci)?) ([\w-]+) ([^\n]+)", step.get("run", "")):
                choices = parsers[module]._subparsers._group_actions[0].choices
                known = choices[command]._option_string_actions
                assert set(re.findall(r"--[\w-]+", arguments)) <= set(known)


def test_ci_compatibility_preserves_partial_matrix(tmp_path, monkeypatch):
    source = "a" * 40
    downloaded = tmp_path / "downloads"
    downloaded.mkdir()
    for label in ("CI-WIN", "CI-LINUX"):
        (downloaded / f"p55a-{source}-123-a1-{label}-c8").mkdir()

    def verify_one(path, **identity):
        assert identity["source_commit"] == source
        assert identity["run_id"] == "123" and identity["attempt"] == "1"
        if identity["producer"] == "CI-LINUX":
            raise ValueError("bundle.hash")
        return {"valid": True, "producer": identity["producer"]}

    monkeypatch.setattr(env, "runtime_profile", lambda *a: {})
    monkeypatch.setattr(controls, "verify_bundle", verify_one)
    output = tmp_path / "compat.json"
    assert ci.verify_matrix(downloaded, "CI-WIN", source, "123", "1", tmp_path, output) == 1
    statuses = {row["producer"]: row["status"] for row in json.loads(output.read_bytes())["observations"]}
    assert statuses == {"CI-WIN": "VALID", "CI-LINUX": "FAILED", "CI-MAC": "NOT RUN"}


@pytest.mark.parametrize("conclusion", ["failure", "success", "in_progress"])
def test_ci_checks_exact_completed_pilot_attempt(monkeypatch, conclusion):
    import io

    source = "b" * 40
    attempt = dict(conclusion=conclusion, status="completed" if conclusion != "in_progress" else "in_progress",
                   event="workflow_dispatch", head_branch="main", path=ci.WORKFLOW, id=123, run_attempt=2,
                   display_title=f"Phase 5.5A pilot / {source}")

    def read(request, **kwargs):
        assert request.full_url.endswith("/actions/runs/123/attempts/2")
        return io.BytesIO(json.dumps(attempt).encode())

    monkeypatch.setattr(ci, "urlopen", read)
    if conclusion == "in_progress":
        with pytest.raises(ValueError, match="selected pilot"):
            ci.check_pilot_attempt(source, "123", "2", "test-token")
    else:
        ci.check_pilot_attempt(source, "123", "2", "test-token")
