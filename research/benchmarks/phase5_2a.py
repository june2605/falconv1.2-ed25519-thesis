"""Windows pilot for the inherited hybrid PDF signer. Run from the repository root."""

import argparse
from contextlib import ExitStack, contextmanager
import csv
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import statistics
import subprocess
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey
import pqcrypto._sign.falcon_512 as falcon_native
from pqcrypto.sign import falcon_512

from desktop.pdf_io import MAX_PDF_BYTES
from keygen import generate_hybrid_key_pair
import sign
from utils import parse_signature_pair, validate_unsigned_input
from verify import verify_bytes, verify_file_with_public_keys


VERSION = "1.0.0"
MIB = 1024 ** 2
ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "demo_assets" / "sample-unsigned.pdf"
FALCON_PIN = "2cc64716044832eea747234ddbffc06746ab815d"
FALCON_SHA256 = "ad5983a68922b01d84332ee800e16b55f001d1353ef62b32efd8d5d1216da237"
INPUT_LENGTHS = (64, 1024)
TRAILER = re.compile(rb"startxref\n([0-9]+)\n%%EOF\n\Z")
RAW_FIELDS = (
    "experiment_id", "category", "mode", "workload", "algorithm", "operation",
    "input_bytes", "phase", "repetition", "order_in_block", "elapsed_ns",
    "legacy_seconds", "observed_bytes", "status", "failure_code",
)
SIGN_SLOTS = tuple(f"{layer}_{slot}" for layer in ("ed25519", "falcon")
                   for slot in ("parse", "hash", "crypto", "io", "total"))
VERIFY_SLOTS = tuple(f"{layer}_{slot}" for layer in ("ed25519", "falcon")
                     for slot in ("parse", "hash", "crypto", "total")) + ("io", "total")
PROFILE_ORDER = (
    "capture_source", "prepare_ed25519", "assemble_ed25519_message", "ed25519_sign",
    "embed_ed25519", "prepare_falcon", "shake256_prehash", "falcon_sign",
    "embed_falcon", "write_and_fsync_candidate", "self_verify_candidate", "publish_candidate",
)


class PilotError(Exception):
    """Controlled failure codes are public and contain no paths or key material."""


def require(condition, code):
    if not condition:
        raise PilotError(code)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def message_bytes(length):
    label = f"HybridSign Phase 5.2A public message, {length} bytes".encode("ascii")
    return hashlib.shake_256(label).digest(length)


def validate_pdf(data, expected_size):
    """Validate the exact generated fixture profile, including offsets and stream length."""
    require(len(data) == expected_size <= MAX_PDF_BYTES, "pdf_size")
    require(data.startswith(b"%PDF-1.4\n") and data.count(b"APPROVED") == 1, "pdf_header_or_text")
    validate_unsigned_input(data)
    tail = TRAILER.search(data)
    require(tail is not None, "pdf_trailer")
    offset = int(tail[1])
    lines = data[offset:tail.start()].splitlines()
    require(lines[:3] == [b"xref", b"0 6", b"0000000000 65535 f "], "pdf_xref")
    require(lines[8:] == [b"trailer", b"<< /Size 6 /Root 1 0 R >>"], "pdf_trailer")
    for index, entry in enumerate(lines[3:8], 1):
        require(re.fullmatch(rb"[0-9]{10} 00000 n ", entry) is not None, "pdf_xref_entry")
        start = int(entry[:10])
        require(start < offset and data.startswith(f"{index} 0 obj\n".encode(), start), "pdf_object_offset")
    streams = list(re.finditer(rb"/Length ([0-9]+) >>\nstream\n(.*?)endstream", data, re.DOTALL))
    require(len(streams) == 1 and len(streams[0][2]) == int(streams[0][1]), "pdf_stream_length")
    return tail


def extend_pdf(sample, size):
    """Insert legal PDF comment lines before xref and update startxref."""
    tail = validate_pdf(sample, len(sample))
    require(len(sample) < size <= 40 * MIB, "pilot_pdf_limit")
    old_offset = int(tail[1])
    for width in range(len(tail[1]), len(str(size)) + 1):
        padding = size - len(sample) - width + len(tail[1])
        new_offset = str(old_offset + padding).encode("ascii")
        if padding > 0 and len(new_offset) == width:
            break
    else:
        raise PilotError("pdf_size_unrepresentable")
    blocks, remaining = divmod(padding, 72)
    comment = b"%" + b"p" * 70 + b"\n"
    end = b"%" + b"p" * (remaining - 2) + b"\n" if remaining >= 2 else b"\n" * remaining
    data = (sample[:old_offset] + comment * blocks + end + sample[old_offset:tail.start(1)]
            + new_offset + sample[tail.end(1):])
    validate_pdf(data, size)
    return data


class Measurements:
    def __init__(self):
        self.rows = []

    def timed(self, operation, function, *args, **kwargs):
        start = time.perf_counter_ns()
        try:
            return function(*args, **kwargs)
        finally:
            elapsed = time.perf_counter_ns() - start
            self.rows.append({"operation": operation, "elapsed_ns": elapsed})

    def legacy(self, prefix, slots, result):
        require(type(result) is tuple and len(result) == 11, "legacy_result_contract")
        for name, value in zip(slots, result[1:], strict=True):
            require(type(value) in (float, int) and math.isfinite(value) and value >= 0,
                    "uninterpretable_legacy_timing")
            self.rows.append({"operation": f"{prefix}_{name}", "legacy_seconds": value})

    def sizes(self, **sizes):
        for name, size in sizes.items():
            self.rows.append({"category": "C", "operation": name, "observed_bytes": size})


def record_trial(writer, identity, operation, *args):
    meter = Measurements()
    try:
        result = operation(meter, *args)
    except (Exception, KeyboardInterrupt) as error:
        failure = str(error) if isinstance(error, PilotError) else type(error).__name__
        for row in (*meter.rows, {"operation": "trial_failure"}):
            writer.writerow({**identity, **row, "status": "failed", "failure_code": failure})
        raise
    for row in meter.rows:
        writer.writerow({**identity, **row, "status": "ok"})
    return result


def primitive_trial(meter, algorithm, message):
    changed = bytes((message[0] ^ 1,)) + message[1:]
    if algorithm == "Ed25519":
        key = meter.timed("keygen", SigningKey.generate)
        public, secret = bytes(key.verify_key), key.encode()
        require(len(public) == 32 and len(secret) == 32, "ed25519_key_lengths")
        sig = meter.timed("sign", key.sign, message).signature
        require(len(sig) == 64, "ed25519_signature_length")
        check = key.verify_key.verify
        require(meter.timed("verify", check, message, sig) == message, "ed25519_verify")
        try:
            check(changed, sig)
        except BadSignatureError:
            pass
        else:
            raise PilotError("ed25519_modified_message_accepted")
    else:
        public, secret = meter.timed("keygen", falcon_512.generate_keypair)
        require((len(public), len(secret)) == (falcon_512.PUBLIC_KEY_SIZE, falcon_512.SECRET_KEY_SIZE),
                "falcon_key_lengths")
        sig = meter.timed("sign", falcon_512.sign, secret, message)
        require(0 < len(sig) <= falcon_512.SIGNATURE_SIZE, "falcon_signature_length")
        require(meter.timed("verify", falcon_512.verify, public, message, sig) is True, "falcon_verify")
        require(falcon_512.verify(public, changed, sig) is False, "falcon_modified_message_accepted")
    meter.sizes(public_key_bytes=len(public), private_key_bytes=len(secret), native_signature_bytes=len(sig))


@contextmanager
def profile_pipeline(meter):
    """Temporarily time real operations in the synchronous signer, with no substitute implementation."""
    def wrapped(function, operation):
        def call(*args, **kwargs):
            return meter.timed(operation, function, *args, **kwargs)
        return call

    def by_revision(function, prefix):
        def call(*args, **kwargs):
            sign_type = kwargs.get("sign_type", kwargs.get("type_sign", args[2] if len(args) > 2 else 0))
            operation = f"{prefix}_{('ed25519', 'falcon')[sign_type]}"
            return meter.timed(operation, function, *args, **kwargs)
        return call

    core = sign._sign_captured

    def profiled_core(*args, **kwargs):
        stages = (
            (sign, "compute_sha512_digest_for_byte_range", "assemble_ed25519_message"),
            (SigningKey, "sign", "ed25519_sign"),
            (sign, "compute_shake256_digest_for_byte_range", "shake256_prehash"),
            (falcon_512, "sign", "falcon_sign"),
            (sign.SigningTransaction, "write_candidate", "write_and_fsync_candidate"),
            (sign, "verify_file_with_public_keys", "self_verify_candidate"),
            (sign.SigningTransaction, "publish", "publish_candidate"),
        )
        with ExitStack() as stack:
            for owner, name, operation in stages:
                stack.enter_context(patch.object(owner, name, wrapped(getattr(owner, name), operation)))
            for name, prefix in (("prepare_bytes_with_placeholder", "prepare"), ("embed_signature_into_pdf", "embed")):
                stack.enter_context(patch.object(sign, name, by_revision(getattr(sign, name), prefix)))
            return core(*args, **kwargs)

    with patch.object(sign, "capture_source", wrapped(sign.capture_source, "capture_source")):
        with patch.object(sign, "_sign_captured", profiled_core):
            yield


def hybrid_trial(meter, source, output, size, pair, wrong, profiled):
    require(not output.exists(), "benchmark_destination_exists")
    try:
        if profiled:
            with profile_pipeline(meter):
                signed_result = meter.timed("profiled_sign_and_publish", sign.sign_with_key_material, source, output, pair)
            require(tuple(row["operation"] for row in meter.rows[:-1]) == PROFILE_ORDER,
                    "unexpected_pipeline_profile")
        else:
            signed_result = meter.timed("sign_and_publish", sign.sign_with_key_material, source, output, pair)
        require(type(signed_result) is tuple and len(signed_result) == 11 and signed_result[0] == output
                and output.is_file(), "sign_output_contract")
        meter.legacy("sign_slot", SIGN_SLOTS, signed_result)

        keys = pair.public_keys
        check_args = (output, keys.ed25519_public_key, keys.falcon_public_key)
        if profiled:
            verified = verify_file_with_public_keys(*check_args)
        else:
            verified = meter.timed("verify_published_file", verify_file_with_public_keys, *check_args)
        require(type(verified) is tuple and len(verified) == 11 and verified[0] is True, "hybrid_verify")
        if not profiled:
            meter.legacy("verify_slot", VERIFY_SLOTS, verified)

        data = output.read_bytes()
        containers = parse_signature_pair(data)
        require(containers.ed25519.marker_start == size and data[:size] == source.read_bytes()
                and data[:size].count(b"APPROVED") == 1, "signed_source_mismatch")
        edited = data.replace(b"APPROVED", b"REJECTED", 1)
        require(verify_bytes(edited, keys.ed25519_public_key, keys.falcon_public_key)[0] is False,
                "hybrid_covered_edit_accepted")
        require(verify_bytes(data, wrong.ed25519_public_key, wrong.falcon_public_key)[0] is False,
                "hybrid_wrong_keys_accepted")
        meter.sizes(
            ed25519_signature_bytes=containers.ed25519.signature_length // 2,
            falcon_signature_bytes=containers.falcon.signature_length // 2,
            ed25519_message_bytes=containers.ed25519.byte_range[1] + containers.ed25519.byte_range[3],
            falcon_message_bytes=64, signed_file_bytes=len(data), pdf_overhead_bytes=len(data) - size,
        )
    finally:
        output.unlink(missing_ok=True)


def summarize(raw):
    groups = {}
    columns = (("elapsed_ns", "ns", int), ("legacy_seconds", "s", float), ("observed_bytes", "B", int))
    with raw.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row["status"] != "ok" or row["phase"] != "measured":
                continue
            for field, unit, convert in columns:
                if row[field] != "":
                    key = tuple(row[k] for k in ("category", "mode", "workload", "algorithm", "operation"))
                    groups.setdefault((*key, unit), []).append(convert(row[field]))
    return [
        dict(zip(("category", "mode", "workload", "algorithm", "operation", "unit"), key, strict=True),
             n=len(values), mean=statistics.mean(values), median=statistics.median(values),
             sd=statistics.stdev(values) if len(values) > 1 else None, minimum=min(values), maximum=max(values),
             p95=statistics.quantiles(values, n=100, method="inclusive")[94] if len(values) >= 30 else None)
        for key, values in sorted(groups.items())
    ]


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def environment():
    require(platform.system() == "Windows", "windows_pilot_required")
    script = r"""
      $ErrorActionPreference='Stop'
      $os=Get-CimInstance Win32_OperatingSystem
      $cpu=Get-CimInstance Win32_Processor
      $computer=Get-CimInstance Win32_ComputerSystem
      $release=Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion'
      @{
        windows=$os.Caption; windows_build=("{0}.{1}" -f $os.BuildNumber,$release.UBR)
        cpu_models=@($cpu | ForEach-Object {$_.Name.Trim()})
        logical_processors=[int]$computer.NumberOfLogicalProcessors
        ram_bytes=[long]$computer.TotalPhysicalMemory
        available_ram_bytes=([long]$os.FreePhysicalMemory*1024)
      } | ConvertTo-Json -Compress
    """
    machine = json.loads(subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        text=True, encoding="utf-8", timeout=20,
    ))
    native_hash = sha256(Path(falcon_native.__file__).read_bytes())
    require(version("pqcrypto") == "0.3.4" and native_hash == FALCON_SHA256, "falcon_build_mismatch")
    git = lambda *args: subprocess.check_output(["git", *args], cwd=ROOT, text=True, timeout=10).strip()
    build_sources = ("keygen.py", "hybrid_keys.py", "sign.py", "signing_io.py", "utils.py", "verify.py")
    require(not git("diff", "HEAD", "--name-only", "--", *build_sources), "production_source_changed")
    return {
        **machine, "python": platform.python_version(), "architecture": platform.machine(),
        "commit": git("rev-parse", "HEAD"), "worktree_dirty": bool(git("status", "--porcelain")),
        "production_sha256": {name: sha256((ROOT / name).read_bytes()) for name in build_sources},
        "harness_version": VERSION, "harness_sha256": sha256(Path(__file__).read_bytes()),
        "packages": {name: version(name) for name in ("PyNaCl", "pqcrypto", "cryptography")},
        "falcon": {"binding": "falcon_512", "variant": "PQClean clean", "pqclean_commit": FALCON_PIN,
                   "native_sha256": native_hash},
        "perf_counter_resolution_ns": time.get_clock_info("perf_counter").resolution * 1e9,
    }


def output_parent(path):
    resolved = path.resolve(strict=True)
    linked_checkout = any((folder / ".git").exists() for folder in (resolved, *resolved.parents))
    require(resolved.is_dir() and not resolved.is_relative_to(ROOT) and not linked_checkout,
            "output_must_be_outside_git")
    return resolved


def workloads(run, sizes):
    sample = SAMPLE.read_bytes()
    validate_pdf(sample, len(sample))
    for name, size in (("demo", len(sample)), *((f"{mib}-MiB", mib * MIB) for mib in sizes)):
        data = sample if name == "demo" else extend_pdf(sample, size)
        path = run / f"{name}.pdf"
        with path.open("xb") as file:
            require(file.write(data) == size, "pdf_input_write")
        reread = path.read_bytes()
        validate_pdf(reread, size)
        require(reread == data, "pdf_input_changed")
        yield name, path, size, sha256(data)


def run_trials(writer, experiment, inputs, pair, wrong, output, warmups, repetitions, budget_seconds):
    deadline = time.perf_counter_ns() + budget_seconds * 10 ** 9
    for phase, count in (("warmup", warmups), ("measured", repetitions)):
        for repetition in range(1, count + 1):
            order = 0

            def trial(category, mode, workload, algorithm, size, function, *args):
                nonlocal order
                order += 1
                identity = dict(experiment_id=experiment, category=category, mode=mode, workload=workload,
                                algorithm=algorithm, input_bytes=size, phase=phase,
                                repetition=repetition, order_in_block=order)
                if time.perf_counter_ns() >= deadline:
                    writer.writerow({**identity, "operation": "admission", "status": "excluded",
                                     "failure_code": "pilot_time_budget"})
                    raise PilotError("pilot_time_budget")
                return record_trial(writer, identity, function, *args)

            for size in INPUT_LENGTHS:
                name = f"{size}-B"
                message = trial("A", "primitive", name, "shared", size, Measurements.timed,
                                "prepare_public_message", message_bytes, size)
                algorithms = ("Ed25519", "Falcon-512") if repetition % 2 else ("Falcon-512", "Ed25519")
                for algorithm in algorithms:
                    trial("A", "primitive", name, algorithm, size, primitive_trial, algorithm, message)

            offset = (repetition - 1) % len(inputs)
            for name, path, size, _ in inputs[offset:] + inputs[:offset]:
                for profiled in ((False, True) if repetition % 2 else (True, False)):
                    mode = "profiled" if profiled else "unprofiled"
                    trial("B", mode, name, "Hybrid", size, hybrid_trial, path, output, size, pair, wrong, profiled)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, required=True, help="Existing local folder outside Git")
    parser.add_argument("--pdf-mib", type=int, nargs="*", choices=(1, 10, 40), default=[1, 10])
    parser.add_argument("--warmups", type=int, choices=range(1, 6), default=3)
    parser.add_argument("--repetitions", type=int, choices=range(1, 31), default=30)
    parser.add_argument("--budget-seconds", type=int, default=300)
    args = parser.parse_args()
    require(0 < args.budget_seconds <= 600 and len(set(args.pdf_mib)) == len(args.pdf_mib), "invalid_pilot_plan")
    parent = output_parent(args.output_root)
    metadata = environment()
    largest = max(args.pdf_mib, default=1) * MIB
    free_disk = shutil.disk_usage(parent).free
    require(metadata["available_ram_bytes"] >= max(512 * MIB, 48 * largest), "insufficient_available_ram")
    require(free_disk >= 10 * largest + sum(args.pdf_mib) * MIB + 64 * MIB, "insufficient_output_space")
    run = Path(tempfile.mkdtemp(prefix="hybridsign-phase5-2a-", dir=parent))
    experiment = str(uuid4())
    print(f"Pilot output: {run}", flush=True)
    metadata.update(experiment_id=experiment, status="running", utc_start=datetime.now(timezone.utc).isoformat(),
                    initial_free_output_bytes=free_disk, warmups=args.warmups, repetitions=args.repetitions,
                    trial_admission_budget_s=args.budget_seconds, pdf_mib=args.pdf_mib,
                    primitive_message_lengths=list(INPUT_LENGTHS),
                    primitive_input_sha256={str(n): sha256(message_bytes(n)) for n in INPUT_LENGTHS})
    manifest = run / "experiment.json"
    write_json(manifest, metadata)
    raw = run / "raw.csv"
    try:
        inputs = list(workloads(run, args.pdf_mib))
        metadata["pdf_inputs"] = [
            dict(workload=name, filename=path.name, input_bytes=size, sha256=digest)
            for name, path, size, digest in inputs
        ]
        write_json(manifest, metadata)
        pair, wrong_pair = generate_hybrid_key_pair(), generate_hybrid_key_pair()
        wrong = wrong_pair.public_keys
        del wrong_pair
        with raw.open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=RAW_FIELDS)
            writer.writeheader()
            run_trials(writer, experiment, inputs, pair, wrong, run / "trial-output.pdf",
                       args.warmups, args.repetitions, args.budget_seconds)
        write_json(run / "summary.json", summarize(raw))
        metadata["status"] = "complete"
    except (Exception, KeyboardInterrupt) as error:
        metadata.update(status="failed", failure_code=str(error) if isinstance(error, PilotError) else type(error).__name__)
        print(f"Pilot stopped ({metadata['failure_code']}). Review the output directory.", flush=True)
        return 1
    finally:
        metadata["utc_end"] = datetime.now(timezone.utc).isoformat()
        write_json(manifest, metadata)
    print("Pilot complete.", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PilotError as error:
        raise SystemExit(f"Pilot stopped ({error}).") from None
