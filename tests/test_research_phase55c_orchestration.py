"""Focused tests for main orchestration, with no changes to the measurement checkout."""

from io import BytesIO
from pathlib import Path
import re
from zipfile import ZipFile

import pytest
import yaml

from research.benchmarks.p55 import protocol
from research.benchmarks.p55.__main__ import build_parser
from research.orchestration import phase55c as main

WORKFLOW = Path(".github/workflows/phase5-5c-main.yml")


def test_main_workflow_is_manual_bounded_and_separates_exact_checkouts():
    workflow = yaml.load(WORKFLOW.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_dispatch"}
    assert workflow["on"]["workflow_dispatch"]["inputs"]["approved"]["default"] == "false"
    assert workflow["concurrency"] == {"group": "hybridsign-phase55a-research", "cancel-in-progress": "false"}
    assert workflow["permissions"] == {"contents": "read", "actions": "read"}
    assert set(workflow["jobs"]) == {"main"}
    job = workflow["jobs"]["main"]
    strategy = job["strategy"]
    assert strategy["max-parallel"] == "1" and strategy["fail-fast"] == "false"
    pairs = [(entry["environment"], entry["slot"]) for entry in strategy["matrix"]["include"]]
    assert len(pairs) == len(set(pairs)) == 9
    assert set(pairs) == {(label, str(slot)) for label in main.RUNNERS for slot in range(1, 4)}
    assert all(main.RUNNERS[x["environment"]] == x["runner"] for x in strategy["matrix"]["include"])
    assert workflow["env"]["P55_PILOT"] == str(main.PILOT)
    assert workflow["env"]["P55_ATTEMPT"] == str(main.ATTEMPT)
    assert int(job["timeout-minutes"]) * 60 > protocol.ADMISSION_SECONDS
    checkout = [step["with"] for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")]
    assert checkout == [{"ref": "$" + "{{ github.workflow_sha }}", "path": "orchestration", "persist-credentials": "false"},
                        {"ref": main.SOURCE, "path": "measurement", "persist-credentials": "false"}]
    assert all(re.fullmatch(r"actions/[\w-]+@[a-f0-9]{40}", s["uses"]) for s in job["steps"] if "uses" in s)
    scripts = "\n".join(step.get("run", "") for step in job["steps"])
    assert "--slot $env:P55_SLOT" in scripts and "--slot 1" not in scripts
    command = next(step for step in job["steps"] if "p55 run --mode main" in step.get("run", ""))
    assert command["working-directory"] == "measurement"
    assert "'pilot-session'" in command["run"] and "--accepted-pilot $pilot" in command["run"]
    assert "run --mode main" in scripts and "p55.ci gate" not in scripts
    upload = next(step["with"] for step in job["steps"] if step.get("uses", "").startswith("actions/upload-artifact@"))
    assert "matrix.slot" in upload["name"] and "matrix.environment" in upload["name"]
    assert upload["retention-days"] == "30"
    assert {"workflow.json", "acceptance.json", "job-timings.json", "summary.json",
            *("session/" + name for name in {*main.SESSION_FILES, "checksums.sha256"})} == {
                line.split("}}/", 1)[1] for line in upload["path"].splitlines()
            }


def test_frozen_cli_accepts_existing_main_flags_and_counts():
    args = build_parser().parse_args(["run", "--mode", "main", "--seed", "3", "--environment", "CI-MAC",
                                      "--wheelhouse", "w", "--accepted-pilot", "p", "--output", "o"])
    assert args.accepted_pilot == Path("p")
    config = protocol.config(args.mode, args.seed)
    assert (config["warmup_blocks"], config["measured_blocks"], config["measured_trials"],
            config["measured_positive_rows"], config["admission_seconds"]) == (3, 30, 450, 840, 600)


def accepted_api(number, mode):
    prefix = f"/actions/runs/{number}/attempts/1"
    return {
        prefix: dict(id=number, run_attempt=1, event="workflow_dispatch", head_branch="main", status="completed",
                     conclusion="success", workflow_id=main.PILOT_WORKFLOW, path=".github/workflows/phase5-5a-research.yml",
                     head_sha=main.PILOT_WORKFLOW_SHA, display_title=f"Phase 5.5A {mode} / {main.SOURCE}"),
        prefix + "/jobs?per_page=100": {"jobs": [{"name": name, "conclusion": "success"} for name in main.RUNNERS]},
        f"/actions/runs/{number}/artifacts?per_page=100": {"artifacts": [{"id": 11}]}
    }


@pytest.mark.parametrize("run,mode", [(main.PILOT, "pilot"), (main.C8, "compat")])
@pytest.mark.parametrize("key,bad", [("status", "in_progress"), ("conclusion", "failure"),
                                     ("run_attempt", 2), ("head_sha", "wrong")])
def test_wrong_run_or_attempt_never_passes(run, mode, key, bad):
    replies = accepted_api(run, mode)
    api = type("FakeApi", (), {"get": staticmethod(replies.__getitem__)})()
    assert main.exact_run(api, run, mode) == {11: {"id": 11}}
    replies[f"/actions/runs/{run}/attempts/1"][key] = bad
    with pytest.raises(ValueError, match="Unaccepted run or attempt"):
        main.exact_run(api, run, mode)


def test_artifact_identity_archive_digest_and_layout_are_checked():
    label = "CI-WIN"
    content = BytesIO()
    with ZipFile(content, "w") as archive:
        archive.writestr("session/checksums.sha256", "data")
    body = content.getvalue()
    digest = main.sha(body)
    name = main.expected_name(main.PILOT, label, "s1")
    metadata = {11: {"id": 11, "name": name, "expired": False, "digest": "sha256:" + digest}}
    pin = 11, digest, "unused"
    api = type("FakeApi", (), {"zip": staticmethod(lambda _: body)})()
    args = (api, metadata, main.PILOT, label, "s1", pin)
    assert main.files_from(*args, {"session/checksums.sha256"}) == {"session/checksums.sha256": b"data"}
    with pytest.raises(ValueError, match="Unexpected archive layout"):
        main.files_from(*args, {"not-allowed"})
    body += b"modified"
    with pytest.raises(ValueError, match="ZIP digest mismatch"):
        main.files_from(*args, {"session/checksums.sha256"})
    metadata[11]["name"] = "unrelated"
    with pytest.raises(ValueError, match="Unaccepted artifact"):
        main.files_from(*args, {"session/checksums.sha256"})
