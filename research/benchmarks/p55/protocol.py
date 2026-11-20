"""Paired schedule, timing boundaries and interruption-resistant evidence."""
from dataclasses import dataclass, asdict
import csv
import itertools
import json
import os
from pathlib import Path
import random
import time
from uuid import uuid4

from . import environment as env
from . import pdf

PROTOCOL = env.PROTOCOL
SCHEMA = "hybridsign-5.5a-raw-v1"
ADMISSION_SECONDS = 600
WARMUP = 3
MODES = {"pilot": 6, "main": 30}
PRIMITIVE = (64, 1024)
SIZE_FIELDS = ("input_bytes", "output_bytes", "growth_bytes") + tuple(
    f"{alg}_{name}_bytes" for alg in ("ed", "falcon")
    for name in ("native", "capacity", "padding_ascii", "metadata", "container")
)
RAW_FIELDS = (
    "schema", "protocol", "campaign", "environment", "execution_kind", "physical_host_id",
    "physical_parent_id", "session", "process_id", "runner_instance_id", "run_id", "job", "attempt",
    "schedule_sha256", "block", "trial", "phase", "layer", "workload", "input_sha256",
    "method", "operation", "method_order", "trial_order", "elapsed_ns", *SIZE_FIELDS, "status", "failure_code",
)
EVIDENCE_FILES = ("session.json", "schedule.json", "outcome.json", "raw.csv", "controls.jsonl", "progress.jsonl", "smoke.json")
PRODUCTION = ("keygen.py", "hybrid_keys.py", "sign.py", "signing_io.py", "utils.py", "verify.py")


@dataclass(frozen=True)
class Trial:
    phase: str
    block: int
    trial_order: int
    layer: str
    workload: str
    method: str
    method_order: int

    @property
    def id(self):
        return f"{self.phase}-{self.block:02d}-{self.trial_order:02d}"

    @property
    def operations(self):
        return {"keygen": ("keygen",), "primitive": ("sign", "verify"),
                "pdf": ("sign_and_publish", "verify_published_file")}[self.layer]


def schedule(mode, seed):
    if mode not in MODES or type(seed) is not int or not 0 <= seed < 2**64:
        raise ValueError("schedule.mode_or_seed")
    rng = random.Random(seed)
    trials = []
    for phase, blocks in (("warmup", WARMUP), ("measured", MODES[mode])):
        def balanced(items):
            patterns = [*itertools.islice(itertools.cycle(itertools.permutations(items)), blocks)]
            rng.shuffle(patterns)
            return patterns

        orders = zip(balanced(pdf.METHODS[:2]), balanced(PRIMITIVE), balanced(pdf.WORKLOADS),
                     balanced(pdf.METHODS), strict=True)
        for block, (alg_order, message_order, pdf_order, methods) in enumerate(orders, 1):
            conditions = [("keygen", "keygen", alg, rank) for rank, alg in enumerate(alg_order, 1)]
            conditions.extend(("primitive", f"{size}-B", alg, rank)
                              for size in message_order for rank, alg in enumerate(alg_order, 1))
            conditions.extend(("pdf", workload, alg, rank)
                              for workload in pdf_order for rank, alg in enumerate(methods, 1))
            trials.extend(Trial(phase, block, index, *condition) for index, condition in enumerate(conditions, 1))
    return trials


def schedule_file(mode, seed, trials):
    return dict(protocol=PROTOCOL, mode=mode, seed=seed, trials=[dict(**asdict(t), id=t.id) for t in trials])


def source_hashes():
    sources = [env.ROOT / name for name in PRODUCTION]
    sources += sorted(Path(__file__).parent.glob("*.py")) + [env.LOCK]
    return {p.relative_to(env.ROOT).as_posix(): env.file_hash(p) for p in sources}


def config(mode, seed):
    trials = schedule(mode, seed)
    return dict(protocol=PROTOCOL, schema=SCHEMA, mode=mode, seed=seed, admission_seconds=ADMISSION_SECONDS,
                trial_units_per_block=15, positive_rows_per_block=28, warmup_blocks=WARMUP,
                measured_blocks=MODES[mode], measured_trials=sum(t.phase == "measured" for t in trials),
                measured_positive_rows=sum(len(t.operations) for t in trials if t.phase == "measured"),
                schedule_sha256=pdf.sha(env.json_bytes(schedule_file(mode, seed, trials))),
                fixtures=pdf.WORKLOADS, primitive_message_bytes=PRIMITIVE,
                min_ram_bytes=env.MIN_RAM, min_disk_bytes=env.MIN_DISK)


def inventory(directory):
    names = [n for n in EVIDENCE_FILES if (directory / n).is_file()]
    with (directory / "checksums.sha256").open("x", encoding="utf-8", newline="\n") as out:
        for name in names:
            out.write(f"{env.file_hash(directory / name)}  {name}\n")


def check_inventory(directory, *, complete=False):
    names = set()
    for line in (directory / "checksums.sha256").read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        pdf.require(name in EVIDENCE_FILES and name not in names, "inventory.entry")
        path = directory / name
        pdf.require(not path.is_symlink() and env.file_hash(path) == digest, "inventory.hash")
        names.add(name)
    present = {n for n in EVIDENCE_FILES if (directory / n).is_file()}
    pdf.require(names == present and "outcome.json" in names, "inventory.coverage")
    if complete:
        pdf.require(names == set(EVIDENCE_FILES), "inventory.incomplete")
    return sorted(names)


def read_json(directory, name):
    return json.loads((directory / name).read_bytes())


def accepted_pilot(directory, *, environment, hashes, profile, source, ci):
    check_inventory(directory, complete=True)
    data = read_json(directory, "session.json")
    outcome = read_json(directory, "outcome.json")
    fields = data["configuration"]
    pdf.require(outcome["status"] == "complete" and fields["mode"] == "pilot" and
                fields["protocol"] == PROTOCOL and outcome["measured_positive_rows"] == 168 and
                data["execution"]["environment"] == environment and data["source_sha256"] == hashes and
                data["profile"]["file_sha256"] == profile["file_sha256"] and
                (not ci or (data["source_commit"] == source and data["execution"]["run_id"] == os.environ.get("P55_PILOT")
                            and data["execution"]["attempt"] == os.environ.get("P55_ATTEMPT"))),
                "main.pilot_not_accepted")
    return {"session": data["session"], "sha256": env.file_hash(directory / "checksums.sha256")}


def error_code(error):
    if isinstance(error, (pdf.ResearchError, env.EnvironmentError)):
        return str(error)
    if hasattr(error, "code") and isinstance(error.code, str):
        return error.code
    return type(error).__name__


def append_json(stream, payload):
    stream.write(json.dumps(payload, sort_keys=True, allow_nan=False) + "\n")
    stream.flush()


class TrialTiming:
    def __init__(self):
        self.samples = []

    def measure(self, operation, call, *args):
        start = time.perf_counter_ns()
        try:
            return call(*args)
        finally:
            self.samples.append((operation, time.perf_counter_ns() - start))


class TrialLoop:
    def __init__(self, inputs, work, controls):
        self.inputs = inputs
        self.work = work
        self.controls = controls
        self.messages = {f"{size}-B": pdf.primitive_input(size) for size in PRIMITIVE}
        self.keys = {}
        self.pdf_keys = None

    def input_info(self, trial):
        if trial.layer == "pdf":
            return pdf.WORKLOADS[trial.workload]
        if trial.layer == "primitive":
            message = self.messages[trial.workload]
            return len(message), pdf.sha(message)
        return None, None

    def run(self, trial, timer, sizes, identity):
        method = trial.method
        if trial.layer == "keygen":
            if trial.trial_order == 1:
                self.keys = {}
                self.pdf_keys = None
            self.keys[method] = timer.measure("keygen", pdf.generate_single, method)
            return
        if trial.layer == "primitive":
            message = self.messages[trial.workload]
            key = self.keys[method]
            signer = pdf.algorithm_signer(method, key)
            verifier = pdf.algorithm_verifier(method, key.public)
            signature = timer.measure("sign", signer, message)
            with_verification = timer.measure("verify", verifier, message, signature)
            changed = bytes((message[0] ^ 1,)) + message[1:]
            wrong = pdf.generate_single(method)
            valid = (pdf.valid_signature_size(method, signature) and with_verification is True
                     and verifier(changed, signature) is False and wrong.public != key.public
                     and pdf.algorithm_verifier(method, wrong.public)(message, signature) is False)
            append_json(self.controls, dict(**identity, control="primitive", passed=valid))
            pdf.require(valid, "primitive.correctness")
            sizes["ed_native_bytes" if method == pdf.ED else "falcon_native_bytes"] = len(signature)
            return
        if self.pdf_keys is None:
            self.pdf_keys = pdf.generated_keys()
        pair, wrong = self.pdf_keys
        source = self.inputs / f"{trial.workload}.pdf"
        output = self.work / f"{trial.id}.pdf"
        pdf.require(not output.exists(), "trial.destination_exists")
        timer.measure("sign_and_publish", pdf.sign_document, source, output, method, pair)
        correct = timer.measure("verify_published_file", pdf.verify_document, output, method, pdf.publics(pair))
        pdf.require(correct is True, "pdf.positive_verify")
        data = output.read_bytes()
        original = source.read_bytes()
        input_bytes, digest = pdf.WORKLOADS[trial.workload]
        pdf.require(pdf.sha(original) == digest and data[:input_bytes] == original, "pdf.source_preservation")
        sizes.update(pdf.sizes(data, input_bytes, method))
        for result in _pdf_controls(data, method, pair, wrong):
            # The measured method is already present in both records.
            append_json(self.controls, {**identity, **result})
            pdf.require(result["passed"], f"pdf.{result['control']}")
        output.unlink()


def _pdf_controls(data, method, pair, wrong):
    from .controls import positive_controls

    return positive_controls(data, method, pair, wrong)


def run_trials(directory, identity, trials, deadline):
    progress = directory / "progress.jsonl"
    counts = dict(warmup_trials=0, measured_trials=0, warmup_positive_rows=0, measured_positive_rows=0)
    admitted = {"status": "complete", "failure_code": "", "last_trial": None}
    with ((directory / "raw.csv").open("x", encoding="utf-8", newline="") as raw,
          (directory / "controls.jsonl").open("x", encoding="utf-8", newline="\n") as controls,
          progress.open("x", encoding="utf-8", newline="\n") as journal):
        runner = TrialLoop(directory / "inputs", directory / "work", controls)
        writer = csv.DictWriter(raw, fieldnames=RAW_FIELDS)
        writer.writeheader()
        raw.flush()
        for trial in trials:
            offered = dict(**identity, **asdict(trial), trial=trial.id,
                           input_sha256=runner.input_info(trial)[1])
            sizes = {"input_bytes": runner.input_info(trial)[0]}
            timer = TrialTiming()
            status, code = "ok", ""
            if time.perf_counter_ns() >= deadline:
                status, code = "incomplete", "admission.budget"
                append_json(journal, dict(trial=trial.id, status=status, failure_code=code, utc=env.utc()))
            else:
                append_json(journal, dict(trial=trial.id, status="started", utc=env.utc()))
                try:
                    runner.run(trial, timer, sizes, offered)
                    pdf.require(tuple(op for op, _ in timer.samples) == trial.operations, "trial.operations")
                except (Exception, KeyboardInterrupt) as error:
                    status, code = "failed", error_code(error)
            for op, elapsed in timer.samples or [("admission" if status == "incomplete" else "failure", None)]:
                writer.writerow(dict(**offered, **sizes, operation=op, elapsed_ns=elapsed, status=status,
                                     failure_code=code))
            raw.flush()
            if status != "incomplete":
                append_json(journal, dict(trial=trial.id, status=status, failure_code=code, utc=env.utc()))
            admitted["last_trial"] = trial.id
            if status != "ok":
                admitted.update(status=status, failure_code=code)
                break
            counts[f"{trial.phase}_trials"] += 1
            counts[f"{trial.phase}_positive_rows"] += len(timer.samples)
    return {**admitted, **counts}


def run_campaign(path, *, mode, seed, environment, wheelhouse, pilot_directory=None):
    from .controls import smoke

    local = environment == "LOCAL-WIN"
    directory = env.safe_output(path, local=local)
    directory.mkdir()
    start = env.utc()
    outcome = dict(status="failed", failure_code="setup.unfinished")
    try:
        if local:
            env.check_idle()
        profile = env.runtime_profile(environment, wheelhouse)
        state = env.host_state(env.ENVIRONMENTS[environment], directory)
        run = env.execution(environment)
        trials = schedule(mode, seed)
        plan = config(mode, seed)
        source = env.git("rev-parse", "HEAD")
        hashes = source_hashes()
        session = uuid4().hex
        identity = {name: value for name, value in run.items() if name in RAW_FIELDS}
        campaign = directory.name if local else f"gh-{run['run_id']}-a{run['attempt']}"
        identity.update(schema=SCHEMA, protocol=PROTOCOL, campaign=campaign,
                        session=session, schedule_sha256=plan["schedule_sha256"])
        acceptance = None
        if mode == "main":
            pdf.require(pilot_directory is not None, "main.requires_pilot")
            acceptance = accepted_pilot(pilot_directory, environment=environment, hashes=hashes,
                                        profile=profile, source=source, ci=not local)
        env.write_json(directory / "session.json", dict(configuration=plan, execution=run, session=session,
                       campaign=campaign, utc_start=start, source_commit=source,
                       worktree_dirty=bool(env.git("status", "--porcelain")), source_sha256=hashes,
                       source_set_sha256=pdf.sha(env.json_bytes(hashes)), profile=profile,
                       before=state, accepted_pilot=acceptance))
        env.write_json(directory / "schedule.json", schedule_file(mode, seed, trials))
        env.preflight(state)
        inputs, work = directory / "inputs", directory / "work"
        inputs.mkdir()
        work.mkdir()
        for name in pdf.WORKLOADS:
            (inputs / f"{name}.pdf").write_bytes(pdf.fixture(name))
        smoke_report = smoke(work)
        env.write_json(directory / "smoke.json", smoke_report)
        pdf.require(all(row["passed"] for row in smoke_report), "smoke.control_failed")
        started = time.perf_counter_ns()
        outcome = run_trials(directory, identity, trials, started + ADMISSION_SECONDS * 10**9)
        outcome["trial_loop_ns"] = time.perf_counter_ns() - started
        # Post-run metadata failure must be visible without losing completed measurements.
        try:
            outcome["after"] = env.host_state(env.ENVIRONMENTS[environment], directory)
        except (ValueError, OSError) as error:
            outcome["after"] = "unavailable"
            outcome["after_failure_code"] = error_code(error)
    except (Exception, KeyboardInterrupt) as error:
        outcome.update(status="failed", failure_code=error_code(error))
    finally:
        env.write_json(directory / "outcome.json", dict(**outcome, utc_start=start, utc_end=env.utc()))
        inventory(directory)
    print(f"{directory}: {outcome['status']} {outcome.get('failure_code', '')}", flush=True)
    return outcome
