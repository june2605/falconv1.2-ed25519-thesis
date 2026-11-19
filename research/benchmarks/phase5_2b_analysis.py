"""Recompute multi-session statistics from Phase 5.2B raw CSVs."""

import argparse
from collections import defaultdict
import csv
from datetime import datetime
import json
import math
from pathlib import Path
import statistics
import tempfile

from research.benchmarks import phase5_2a as pilot
from research.benchmarks import phase5_2b_collect as collector


KEY_FIELDS = ("category", "mode", "workload", "algorithm", "operation", "unit")
STAT_FIELDS = ("n", "median", "mean", "sd", "minimum", "maximum", "p95")
VALUE_FIELDS = {"elapsed_ns": ("ns", int), "legacy_seconds": ("s", float), "observed_bytes": ("B", int)}


def load_json(path):
    return json.loads(path.read_bytes())


def expected_order(metadata, repetition):
    order = []
    algorithms = ("Ed25519", "Falcon-512") if repetition % 2 else ("Falcon-512", "Ed25519")
    for size in pilot.INPUT_LENGTHS:
        order.extend(("primitive", f"{size}-B", algorithm, size) for algorithm in ("shared", *algorithms))
    files = metadata["pdf_inputs"]
    offset = (repetition - 1) % len(files)
    modes = ("unprofiled", "profiled") if repetition % 2 else ("profiled", "unprofiled")
    for file in files[offset:] + files[:offset]:
        order.extend((mode, file["workload"], "Hybrid", file["input_bytes"]) for mode in modes)
    return order


def expected_metrics(mode, algorithm):
    if mode == "primitive" and algorithm == "shared":
        return {("A", "prepare_public_message", "ns")}
    if mode == "primitive":
        return {("A", name, "ns") for name in ("keygen", "sign", "verify")} | {
            ("C", name, "B") for name in ("public_key_bytes", "private_key_bytes", "native_signature_bytes")
        }
    stages = ((*pilot.PROFILE_ORDER, "profiled_sign_and_publish") if mode == "profiled"
              else ("sign_and_publish", "verify_published_file"))
    metrics = {("B", name, "ns") for name in stages}
    metrics.update(("B", f"sign_slot_{name}", "s") for name in pilot.SIGN_SLOTS)
    if mode == "unprofiled":
        metrics.update(("B", f"verify_slot_{name}", "s") for name in pilot.VERIFY_SLOTS)
    metrics.update(("C", name, "B") for name in (
        "ed25519_signature_bytes", "falcon_signature_bytes", "ed25519_message_bytes",
        "falcon_message_bytes", "signed_file_bytes", "pdf_overhead_bytes",
    ))
    return metrics


def read_raw(path, metadata):
    """Require complete recorded trials, exact schedules and all operation boundaries."""
    counts = {"warmup": metadata["warmups"], "measured": metadata["repetitions"]}
    schedule = {(phase, repetition, order): identity
                for phase, repetitions in counts.items()
                for repetition in range(1, repetitions + 1)
                for order, identity in enumerate(expected_order(metadata, repetition), 1)}
    observed = defaultdict(set)
    values = defaultdict(list)
    raw_count = 0
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != pilot.RAW_FIELDS:
            raise ValueError(f"Unexpected raw CSV header in {path}")
        for record in reader:
            raw_count += 1
            if None in record or None in record.values():
                raise ValueError(f"Malformed raw CSV row in {path}")
            if record["status"] != "ok" or record["failure_code"]:
                raise ValueError(f"Failed or excluded trials remain in {path}. Review raw evidence before aggregation.")
            if record["experiment_id"] != metadata["experiment_id"]:
                raise ValueError(f"Unexpected experiment identity in {path}")
            phase = record["phase"]
            trial = (phase, int(record["repetition"]), int(record["order_in_block"]))
            mode, workload, algorithm = (record[field] for field in ("mode", "workload", "algorithm"))
            if schedule.get(trial) != (mode, workload, algorithm, int(record["input_bytes"])):
                raise ValueError(f"Unexpected workload or trial order in {path}")
            present = [field for field in VALUE_FIELDS if record[field] != ""]
            if len(present) != 1:
                raise ValueError(f"Expected one value and unit in {path}")
            field, = present
            unit, convert = VALUE_FIELDS[field]
            value = convert(record[field])
            if value < 0 or not math.isfinite(value):
                raise ValueError(f"Invalid observation in {path}")
            category, operation = record["category"], record["operation"]
            metric = (category, operation, unit)
            if metric not in expected_metrics(mode, algorithm) or metric in observed[trial]:
                raise ValueError(f"Unexpected or duplicate operation in {path}")
            observed[trial].add(metric)
            if phase == "measured":
                values[(category, mode, workload, algorithm, operation, unit)].append(value)
    for trial, (mode, _, algorithm, _) in schedule.items():
        if observed[trial] != expected_metrics(mode, algorithm):
            raise ValueError(f"Incomplete raw trial in {path}")
    return values, raw_count, len(schedule)


def describe(values):
    count = len(values)
    return dict(n=count, median=statistics.median(values), mean=statistics.mean(values),
                sd=statistics.stdev(values) if count > 1 else None,
                minimum=min(values), maximum=max(values),
                p95=statistics.quantiles(values, n=100, method="inclusive")[94] if count >= 30 else None)


def aggregate_matched(sessions):
    keys = set(sessions[0])
    if any(set(session) != keys for session in sessions):
        raise ValueError("Matched sessions must have identical metric groups")
    aggregate = {}
    for key in sorted(keys):
        observations = [number for session in sessions for number in session[key]]
        medians = [statistics.median(session[key]) for session in sessions]
        aggregate[key] = {**describe(observations), "sessions": len(medians),
                          "session_median_min": min(medians), "session_median_max": max(medians),
                          "median_of_session_medians": statistics.median(medians)}
    return aggregate


def median_ratios(label, metrics):
    ratios = []
    for size in pilot.INPUT_LENGTHS:
        workload = f"{size}-B"
        for operation in ("sign", "verify"):
            ed = metrics[("A", "primitive", workload, "Ed25519", operation, "ns")]["median"]
            falcon = metrics[("A", "primitive", workload, "Falcon-512", operation, "ns")]["median"]
            ratios.append(dict(session=label, workload=workload, operation=operation,
                               ed25519_median_ns=ed, falcon_median_ns=falcon, falcon_over_ed25519=falcon / ed))
    return ratios


def read_session(campaign, label):
    context = load_json(campaign / label / "session.json")
    directory = (campaign / context["data_path"]).resolve(strict=True)
    if not directory.is_relative_to(campaign / label) or context["status"] != "complete":
        raise ValueError(f"Invalid completed session manifest: {label}")
    metadata = load_json(directory / "experiment.json")
    if (metadata["experiment_id"] != context["experiment_id"] or metadata["commit"] != context["source_commit"]
            or metadata["status"] != "complete" or metadata["harness_sha256"] != collector.PILOT_HARNESS_SHA256
            or metadata["warmups"] != context["planned_warmups"]
            or metadata["repetitions"] != context["planned_repetitions"] or metadata["pdf_mib"] != context["pdf_mib"]):
        raise ValueError(f"Session plan or identity does not match: {label}")
    return context, metadata, directory


def check_inputs(context, metadata, directory, optional_preflight):
    expected = {name: digest for name, digest in collector.PILOT_ARTIFACTS.items() if name.endswith(".pdf")}
    if context["kind"] != "matched":
        expected["40-MiB.pdf"] = optional_preflight["public_input_sha256"]
    expected_names = ["demo.pdf", *(f"{size}-MiB.pdf" for size in context["pdf_mib"])]
    if [item["filename"] for item in metadata["pdf_inputs"]] != expected_names:
        raise ValueError(f"Unexpected PDF workload inventory: {directory}")
    for item in metadata["pdf_inputs"]:
        path = directory / item["filename"]
        if (path.stat().st_size != item["input_bytes"] or
                collector.file_hash(path) != item["sha256"] or item["sha256"] != expected[path.name]):
            raise ValueError(f"PDF fixture bytes do not match the preflight or pilot: {path}")
    if metadata["primitive_input_sha256"] != {str(n): pilot.sha256(pilot.message_bytes(n)) for n in pilot.INPUT_LENGTHS}:
        raise ValueError("Primitive public input hash mismatch")


def write_csv(path, fields, rows):
    with path.open("x", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def completed_collection(campaign):
    run_book = load_json(campaign / "collection.json")
    if run_book["status"] != "complete":
        raise ValueError("Review the incomplete collection and preserve its raw outcomes")
    extension_path = campaign / "optional-extension.json"
    if extension_path.is_file():
        extension = load_json(extension_path)
        if (extension["status"] != "complete" or extension["session"] in run_book["sessions"]
                or extension["prior_feasibility"] not in run_book["sessions"]):
            raise ValueError("Review the incomplete or conflicting optional supplement")
        run_book["sessions"].append(extension["session"])
        run_book["optional_40"] = "complete_in_separate_supplement"
    return run_book


def analyze(campaign):
    run_book = completed_collection(campaign)
    preflight_path = campaign / "optional-40-preflight.json"
    preflight = load_json(preflight_path) if preflight_path.exists() else None
    records, individual, matched, ratios = [], [], [], []
    previous_exit = None
    matched_environment = None
    hardware_and_build = ("windows", "windows_build", "python", "architecture", "packages", "cpu_models",
                          "logical_processors", "ram_bytes", "production_sha256", "falcon")
    for label in run_book["sessions"]:
        context, metadata, directory = read_session(campaign, label)
        started, ended = (datetime.fromisoformat(context[name]) for name in ("utc_launch", "utc_exit"))
        if ended < started or previous_exit is not None and started < previous_exit:
            raise ValueError("Session timestamps show overlap or invalid order")
        previous_exit = ended
        check_inputs(context, metadata, directory, preflight)
        values, raw_count, trials = read_raw(directory / "raw.csv", metadata)
        stats = {key: describe(numbers) for key, numbers in sorted(values.items())}
        individual.extend({"session": label, "kind": context["kind"], **dict(zip(KEY_FIELDS, key, strict=True)), **row}
                          for key, row in stats.items())
        records.append({"session": label, "kind": context["kind"], "pid": context["pid"],
                        "experiment_id": metadata["experiment_id"], "source_commit": metadata["commit"],
                        "warmup_blocks": metadata["warmups"], "measured_blocks": metadata["repetitions"],
                        "measured_trials": (6 + 2 * len(metadata["pdf_inputs"])) * metadata["repetitions"],
                        "total_trials": trials, "raw_rows": raw_count})
        if context["kind"] == "matched":
            if context["pdf_mib"] != [1, 10] or metadata["repetitions"] != collector.REPETITIONS:
                raise ValueError(f"Different experiment conditions in {label}")
            environment = {name: metadata[name] for name in hardware_and_build}
            if matched_environment is not None and environment != matched_environment:
                raise ValueError(f"Matched host or build changed in {label}")
            matched_environment = environment
            matched.append(values)
            ratios.extend(median_ratios(label, stats))
    if len(matched) < 3 or len({r["pid"] for r in records}) != len(records):
        raise ValueError("Expected at least three matched sessions with distinct Python process IDs")
    if len({r["experiment_id"] for r in records}) != len(records) or len({r["source_commit"] for r in records}) != 1:
        raise ValueError("Duplicate experiment IDs or inconsistent source commits")
    aggregate = aggregate_matched(matched)
    ratios.extend(median_ratios("matched-pooled", aggregate))
    directory = Path(tempfile.mkdtemp(prefix="analysis-", dir=campaign))
    write_csv(directory / "per-session.csv", ("session", "kind", *KEY_FIELDS, *STAT_FIELDS), individual)
    write_csv(directory / "matched-aggregate.csv",
              (*KEY_FIELDS, *STAT_FIELDS, "sessions", "session_median_min", "session_median_max", "median_of_session_medians"),
              ({**dict(zip(KEY_FIELDS, key, strict=True)), **row} for key, row in aggregate.items()))
    write_csv(directory / "matched-ratios.csv",
              ("session", "workload", "operation", "ed25519_median_ns", "falcon_median_ns", "falcon_over_ed25519"), ratios)
    pilot.write_json(directory / "analysis.json", {
        "sessions": records, "matched_sessions": len(matched), "optional_40": run_book["optional_40"],
        "pooled_series": len(aggregate), "per_session_series": len(individual),
    })
    print(f"Analysis directory: {directory}", flush=True)
    return directory


def checksum_inventory(campaign, analysis):
    if analysis.parent != campaign or not analysis.name.startswith("analysis-"):
        raise ValueError("Use the analysis directory created by the collector's summary command")
    inputs = [campaign / "collection.json"]
    for name in ("optional-40-preflight.json", "optional-extension.json", "optional-supplement-command.py"):
        optional = campaign / name
        if optional.is_file():
            inputs.append(optional)
    preserved = campaign / "phase5-2a-preserved"
    for name, expected in collector.PILOT_ARTIFACTS.items():
        if collector.file_hash(preserved / name) != expected:
            raise ValueError(f"Preserved pilot bytes changed: {name}")
        inputs.append(preserved / name)
    inputs.append(preserved / "archive-checksums.json")
    for label in completed_collection(campaign)["sessions"]:
        _, metadata, directory = read_session(campaign, label)
        inputs.extend(campaign / label / name for name in ("session.json", "process.log"))
        inputs.extend(directory / name for name in ("raw.csv", "experiment.json", "summary.json"))
        inputs.extend(directory / item["filename"] for item in metadata["pdf_inputs"])
    inputs.extend(analysis / name for name in (
        "analysis.json", "per-session.csv", "matched-aggregate.csv", "matched-ratios.csv",
        "primitive-sign.png", "primitive-verify.png", "hybrid-sign.png", "hybrid-verify.png",
    ))
    with (analysis / "checksums.sha256").open("x", encoding="utf-8", newline="\n") as out:
        for file in sorted(inputs):
            out.write(f"{collector.file_hash(file)}  {file.relative_to(campaign).as_posix()}\n")


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--campaign", type=Path, required=True)
    args.add_argument("--inventory", type=Path)
    options = args.parse_args()
    campaign = options.campaign.resolve(strict=True)
    if options.inventory is None:
        analyze(campaign)
    else:
        checksum_inventory(campaign, options.inventory.resolve(strict=True))


if __name__ == "__main__":
    main()
