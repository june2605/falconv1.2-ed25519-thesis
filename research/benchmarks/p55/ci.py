"""Validation, job envelopes and exact cross-job selection for the manual workflow."""
import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen

from . import environment as env

WORKFLOW = ".github/workflows/phase5-5a-research.yml"
REPO = "june2605/falconv1.2-ed25519-thesis"
RESEARCH_REF = "refs/heads/thesis/ui-demo"
DEFAULT_REF = "refs/heads/main"
STAMPS = ("job_start", "setup_end", "install_end", "test_end", "benchmark_end", "job_local_end")


def source_sha(value):
    if re.fullmatch("[0-9a-f]{40}", value) is None:
        raise ValueError("A full lowercase source commit is required.")
    return value


def positive_id(value):
    if re.fullmatch(r"[1-9][0-9]{0,19}", value) is None:
        raise ValueError("A positive GitHub run or attempt identifier is required.")
    return value


def check_pilot_attempt(source, run_id, attempt, token):
    endpoint = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/attempts/{attempt}"
    call = Request(endpoint, headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}"})
    with urlopen(call, timeout=25) as response:
        record = json.load(response)
    if not (record["status"] == "completed" and record["conclusion"] in {"success", "failure", "cancelled", "timed_out"}
            and record["event"] == "workflow_dispatch"
            and record["head_branch"] == "main" and record["path"] == WORKFLOW
            and record["display_title"] == f"Phase 5.5A pilot / {source}"
            and str(record["id"]) == run_id and str(record["run_attempt"]) == attempt):
        raise ValueError("The selected pilot run, attempt, workflow or source commit does not match.")


def gate(mode, source, pilot_run, attempt, accepted_protocol):
    if os.environ.get("GITHUB_REF") != DEFAULT_REF or os.environ.get("GITHUB_REPOSITORY") != REPO:
        raise ValueError("Run the registered entry point on the expected default branch.")
    source_sha(source)
    if env.git("rev-parse", "HEAD") != source or env.git("status", "--porcelain"):
        raise ValueError("The checked-out thesis/ui-demo commit must match the explicit clean source commit.")
    if mode not in {"pilot", "compat"}:
        raise ValueError("Only the bounded pilot and C8 verification are registered.")
    if mode == "compat":
        if accepted_protocol != env.PROTOCOL:
            raise ValueError("Explicit acceptance of the current pilot protocol is required.")
        check_pilot_attempt(source, positive_id(pilot_run), positive_id(attempt), os.environ["GH_TOKEN"])
    elif pilot_run or accepted_protocol:
        raise ValueError("Pilot mode does not consume an earlier pilot.")


def schedule_seed(environment, slot):
    run = positive_id(os.environ["GITHUB_RUN_ID"])
    attempt = positive_id(os.environ["GITHUB_RUN_ATTEMPT"])
    return int.from_bytes(hashlib.sha256(f"{run}/{attempt}/{environment}/{slot}".encode()).digest()[:8], "big")


def stamp(directory, stage):
    directory.mkdir(exist_ok=True)
    env.write_json(directory / (stage + ".json"), {"utc": env.utc()})


def job_times(directory, output):
    times = {stage: json.loads((directory / f"{stage}.json").read_bytes())["utc"]
             for stage in STAMPS if (directory / f"{stage}.json").is_file()}
    durations = {}
    for label, begin, end in (
        ("setup_s", "job_start", "setup_end"), ("install_s", "setup_end", "install_end"),
        ("test_s", "install_end", "test_end"), ("benchmark_or_compat_s", "test_end", "benchmark_end"),
        ("local_job_envelope_s", "job_start", "job_local_end"),
    ):
        durations[label] = ((datetime.fromisoformat(times[end]) - datetime.fromisoformat(times[begin])).total_seconds()
                            if begin in times and end in times else None)
    env.write_json(output, {"stamps": times, "durations": durations,
                          "overall_job_duration": "use Actions jobs API after upload and job completion"})


def verify_matrix(downloads, environment, source, run_id, attempt, wheelhouse, output):
    from .controls import verify_bundle

    profile = env.runtime_profile(environment, wheelhouse)
    source_sha(source)
    positive_id(run_id)
    positive_id(attempt)
    results = []
    for producer in env.RUNNERS:
        name = f"p55a-{source}-{run_id}-a{attempt}-{producer}-c8"
        bundle = downloads / name
        if not bundle.exists():
            results.append({"producer": producer, "status": "NOT RUN", "valid": False,
                            "reason": "bundle unavailable for the selected attempt"})
            continue
        try:
            observed = verify_bundle(bundle, source_commit=source,
                                     producer=producer, run_id=run_id, attempt=attempt)
            observed["status"] = "VALID"
        except (OSError, ValueError, TypeError, KeyError) as error:
            observed = {"producer": producer, "status": "FAILED", "valid": False,
                        "failure_class": type(error).__name__}
        results.append(observed)
    env.write_json(output, {"verifier": env.execution(environment), "source_commit": source,
                          "producer_run": run_id, "producer_attempt": attempt, "profile": profile, "observations": results})
    return int(not all(row["valid"] for row in results))


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_subparsers(dest="command", required=True)
    parent = cmd.add_parser("gate")
    parent.add_argument("--mode", required=True, choices=("pilot", "compat"))
    parent.add_argument("--source", required=True)
    parent.add_argument("--pilot-run", default="")
    parent.add_argument("--pilot-attempt", default="1")
    parent.add_argument("--accepted-protocol", default="")
    seed = cmd.add_parser("seed")
    seed.add_argument("--environment", choices=env.RUNNERS, required=True)
    seed.add_argument("--slot", type=int, choices=(1, 2, 3), required=True)
    marker = cmd.add_parser("stamp")
    marker.add_argument("--directory", type=Path, required=True)
    marker.add_argument("--stage", choices=STAMPS, required=True)
    times = cmd.add_parser("job-times")
    times.add_argument("--directory", type=Path, required=True)
    times.add_argument("--output", type=Path, required=True)
    verify = cmd.add_parser("verify-matrix")
    verify.add_argument("--environment", choices=env.RUNNERS, required=True)
    for option in ("source", "run-id", "attempt"):
        verify.add_argument("--" + option, required=True)
    for option in ("downloads", "wheelhouse", "output"):
        verify.add_argument("--" + option, type=Path, required=True)
    return parser


def main():
    args = build_parser().parse_args()
    if args.command == "gate":
        gate(args.mode, args.source, args.pilot_run, args.pilot_attempt, args.accepted_protocol)
    elif args.command == "seed":
        print(schedule_seed(args.environment, args.slot))
    elif args.command == "stamp":
        stamp(args.directory, args.stage)
    elif args.command == "job-times":
        job_times(args.directory, args.output)
    else:
        return verify_matrix(args.downloads, args.environment, args.source, args.run_id,
                             args.attempt, args.wheelhouse, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
