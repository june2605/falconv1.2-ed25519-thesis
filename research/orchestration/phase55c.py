"""Main-campaign acceptance and evidence staging outside the frozen measurement source."""

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener, urlopen
from zipfile import ZipFile

REPO = "june2605/falconv1.2-ed25519-thesis"
BASE = f"https://api.github.com/repos/{REPO}"
PILOT = 44701642390
C8 = 44702431300
ATTEMPT = 1
PILOT_WORKFLOW = 424773343
PILOT_WORKFLOW_SHA = "00e8efb55ef58c7a24c0b3c6789667258c94924b"
SOURCE = "613a46d06930ffd9224afa557fa90992e3a56a2a"
PROTOCOL = "hybridsign-5.5a-v1"
PROFILE = "p55a-cp3119-x64-v1"
SOURCE_SET = "d2c84e532ebba4b062d25e8f078238d7736b51fc545e3a27aa0b7311d8f4de91"
PROFILE_HASH = "f3389d41a7efaa590e3619f46eb9a4529ededb6a45f10ed7e51ba6d26cebbbbb"
PROTOCOL_HASH = "625aee7677dd8178f8cb1d6b52578f284a9354e1c29deff10f904f0df357112b"
RUNNERS = {"CI-WIN": "windows-2022", "CI-LINUX": "ubuntu-24.04", "CI-MAC": "macos-15-intel"}
PILOT_SESSIONS = {
    "CI-WIN": (14612434111, "6600479f8c151889b6cfc94d78ecdab0c21fd3b4628b3c620f459aec998c1fd4",
               "26a0985ac8f702e2b0f840102e90ace6488567f6a2949559fbb686f72993db52"),
    "CI-LINUX": (14612454316, "26ad8d885ae3212c5a8a66aded6a593e913244346fb2de41389cc0258db5ab86",
               "269d2667dbb8e25213d8e7a1ea6d5e6e6362f10168593be0a1c0b471a5176b49"),
    "CI-MAC": (14613656412, "cc5e835d070f0d0da19ee8c02b66a302dc2bf20b7b923f41df452f7448259283",
               "9d20ae48e59395a6f5a685ab5b9e53f8b17a5f2d98b1ca1d36c55e7b6536a511"),
}
PILOT_BUNDLES = {
    "CI-WIN": (14613810591, "48db60686a24a590c274ebe7a9dfab4387d76d95bf398b5a23738d5d44ed8092",
               "21218cb1d1a8c80e531833ca80856dbf61ec48b8aecf34c016b3f13f3a1d879e"),
    "CI-LINUX": (14612514055, "0ae0e19fd685558ecc237f2ecc92e158cad5431ceb26524e33e93cf499cae701",
               "2aaf209fec9ebf3502b766b8b73450d0b5e9cace6c2be110d66d6582f07a1aae"),
    "CI-MAC": (14613397006, "19caa3d2753e9269fc38869249b8add86b36be3623f865b681af1a3cdd5e68d3",
               "ef2b762f72f1a50ac6d9150168ac8567c406ed7a2114caa7f9d296a79b5e264b"),
}
C8_REPORTS = {
    "CI-WIN": (14613511618, "a9464e5e0f340c8af55656282674b1462c6d7fac73b5afc8429e63e14ba76e85",
               "a6d2b2f5ce63e42a3c415e38885f82e1c8451ad68994de3f5e60d10a326e2aa8"),
    "CI-LINUX": (14614055354, "a168855129f56125c364e08dca4fe0872a48014d6522fcd19c269b84092ce5a4",
               "19bbe3bbbcd8ce8eadd75457874cc1b195cb892c899b30611686275512e31b50"),
    "CI-MAC": (14614080113, "ba86374c490123436f825fbfbad96e91123ad81fe26bf2b3d097c7a5ac0b5afb",
               "59eabbd2295f2f5192f55dc7231642080fa36a823beebd809a1525fe3403bff2"),
}
SESSION_FILES = {"session.json", "schedule.json", "outcome.json", "raw.csv", "controls.jsonl",
                 "progress.jsonl", "smoke.json"}
PILOT_FILES = {"workflow.json", "summary.json", "job-timings.json", "smoke/smoke.json",
               *("session/" + name for name in {*SESSION_FILES, "checksums.sha256"})}
C8_FILES = {"workflow.json", "compat.json", "job-timings.json", "smoke/smoke.json"}
BUNDLE_FILES = {"bundle.json", "ed25519.pub", "falcon.pub", "sample-hybrid.pdf"}
ARCHIVE_LIMIT = 2_000_000


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def frozen_json(data):
    return (json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class GitHub:
    def __init__(self, token):
        self.headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2026-03-10"}
        self.opener = build_opener(NoRedirect)

    def get(self, path):
        with self.opener.open(Request(BASE + path, headers=self.headers), timeout=30) as response:
            return json.load(response)

    def zip(self, artifact_id):
        request = Request(BASE + f"/actions/artifacts/{artifact_id}/zip", headers=self.headers)
        try:
            with self.opener.open(request, timeout=30) as response:
                return response.read(ARCHIVE_LIMIT + 1)
        except HTTPError as error:
            if error.code != 302:
                raise
            target = error.headers["Location"]
            error.close()
        need(urlparse(target).scheme == "https", "Artifact redirect must use HTTPS.")
        # The redirect is an artifact-storage URL. Keep the API token on api.github.com.
        with urlopen(target, timeout=30) as response:
            return response.read(ARCHIVE_LIMIT + 1)


def exact_run(api, number, mode):
    path = f"/actions/runs/{number}/attempts/{ATTEMPT}"
    run = api.get(path)
    requirements = dict(id=number, run_attempt=ATTEMPT, event="workflow_dispatch", head_branch="main",
                        status="completed", conclusion="success", workflow_id=PILOT_WORKFLOW,
                        path=".github/workflows/phase5-5a-research.yml", head_sha=PILOT_WORKFLOW_SHA,
                        display_title=f"Phase 5.5A {mode} / {SOURCE}")
    need(all(run.get(k) == v for k, v in requirements.items()), f"Unaccepted run or attempt: {number}.")
    jobs = api.get(path + "/jobs?per_page=100")["jobs"]
    need(len(jobs) == len(RUNNERS) and {j["name"] for j in jobs} == set(RUNNERS)
         and all(j["conclusion"] == "success" for j in jobs), f"Unaccepted jobs: {number}.")
    indexed = api.get(f"/actions/runs/{number}/artifacts?per_page=100")["artifacts"]
    return {artifact["id"]: artifact for artifact in indexed}


def expected_name(number, label, suffix):
    return f"p55a-{SOURCE}-{number}-a{ATTEMPT}-{label}-{suffix}"


def files_from(api, metadata, run, label, suffix, pin, expected):
    number, digest, _ = pin
    artifact = metadata.get(number, {})
    need(artifact.get("name") == expected_name(run, label, suffix) and artifact.get("expired") is False
         and artifact.get("digest") == "sha256:" + digest, f"Unaccepted artifact: {number}.")
    archive = api.zip(number)
    need(len(archive) <= ARCHIVE_LIMIT and sha(archive) == digest, f"ZIP digest mismatch: {number}.")
    with ZipFile(io.BytesIO(archive)) as unpacked:
        members = [member for member in unpacked.infolist() if not member.is_dir()]
        need(len(members) == len(expected) and {m.filename for m in members} == expected
             and sum(m.file_size for m in members) <= ARCHIVE_LIMIT, f"Unexpected archive layout: {number}.")
        return {member.filename: unpacked.read(member) for member in members}


def verify_bundle(files, label):
    metadata = json.loads(files["bundle.json"])
    need(sha(files["bundle.json"]) == PILOT_BUNDLES[label][2] and metadata["source_commit"] == SOURCE
         and metadata["producer"] == label and metadata["run_id"] == str(PILOT)
         and metadata["attempt"] == str(ATTEMPT) and metadata["protocol"] == PROTOCOL,
         f"Bundle provenance mismatch: {label}.")
    checks = metadata["checksums"]
    need(set(checks) == BUNDLE_FILES - {"bundle.json"}
         and all(sha(files[name]) == digest for name, digest in checks.items()), f"Bundle inventory mismatch: {label}.")


def verify_c8(files, label):
    report = json.loads(files["compat.json"])
    verifier = report["verifier"]
    need(sha(files["compat.json"]) == C8_REPORTS[label][2] and report["source_commit"] == SOURCE
         and report["producer_run"] == str(PILOT) and report["producer_attempt"] == str(ATTEMPT)
         and verifier["environment"] == label and verifier["run_id"] == str(C8)
         and verifier["attempt"] == str(ATTEMPT) and report["profile"]["id"] == PROFILE
         and report["profile"]["file_sha256"] == PROFILE_HASH, f"C8 provenance mismatch: {label}.")
    rows = report["observations"]
    need(len(rows) == len(RUNNERS) and {row["producer"] for row in rows} == set(RUNNERS),
         f"C8 coverage mismatch: {label}.")
    for row in rows:
        need(row["status"] == "VALID" and row["valid"] is True and row["source_commit"] == SOURCE
             and row["protocol"] == PROTOCOL and row["run_id"] == str(PILOT)
             and row["attempt"] == str(ATTEMPT)
             and row["bundle_inventory_sha256"] == PILOT_BUNDLES[row["producer"]][2],
             f"C8 result mismatch: {label}/{row['producer']}.")


def verify_pilot(files, label, checkout):
    inventory = files["session/checksums.sha256"]
    need(sha(inventory) == PILOT_SESSIONS[label][2], "Pilot inventory digest mismatch.")
    entries = {}
    for line in inventory.decode("utf-8").splitlines():
        digest, name = line.split("  ", 1)
        need(name in SESSION_FILES and name not in entries, "Unexpected pilot inventory entry.")
        entries[name] = digest
    need(set(entries) == SESSION_FILES and all(sha(files["session/" + name]) == h for name, h in entries.items()),
         "Pilot inventory mismatch.")
    session = json.loads(files["session/session.json"])
    outcome = json.loads(files["session/outcome.json"])
    plan, execution, profile = (session[key] for key in ("configuration", "execution", "profile"))
    need(session["source_commit"] == SOURCE and session["worktree_dirty"] is False
         and plan["mode"] == "pilot" and plan["protocol"] == PROTOCOL and plan["measured_blocks"] == 6
         and outcome["status"] == "complete" and outcome["measured_positive_rows"] == 168
         and profile["id"] == PROFILE and profile["file_sha256"] == PROFILE_HASH and profile["architecture"] == "x64"
         and execution["environment"] == label and execution["runner_label"] == RUNNERS[label]
         and execution["run_id"] == str(PILOT) and execution["attempt"] == str(ATTEMPT),
         "Pilot session identity mismatch.")
    hashes = session["source_sha256"]
    need(session["source_set_sha256"] == SOURCE_SET and sha(frozen_json(hashes)) == SOURCE_SET
         and hashes["research/benchmarks/p55/protocol.py"] == PROTOCOL_HASH
         and hashes["research/benchmarks/p55/wheels.json"] == PROFILE_HASH,
         "Pilot source or profile hash mismatch.")
    for name, digest in hashes.items():
        need(sha((checkout / name).read_bytes()) == digest, f"Frozen checkout differs: {name}.")
    return session["session"]


def git(checkout, *args):
    return subprocess.check_output(["git", "-C", str(checkout), *args], text=True, timeout=15).strip()


def prepare(api, label, slot, checkout, destination, evidence):
    need(label in RUNNERS and slot in (1, 2, 3), "Unexpected environment or slot.")
    need(git(checkout, "rev-parse", "HEAD") == SOURCE and not git(checkout, "status", "--porcelain"),
         "Measurement checkout is not the clean approved commit.")
    repository = api.get("")
    need(repository["visibility"] == "public" and repository["default_branch"] == "main",
         "Expected the public repository and its main default branch.")
    pilot, c8 = exact_run(api, PILOT, "pilot"), exact_run(api, C8, "compat")
    for producer, record in PILOT_BUNDLES.items():
        verify_bundle(files_from(api, pilot, PILOT, producer, "c8", record, BUNDLE_FILES), producer)
    for verifier, record in C8_REPORTS.items():
        verify_c8(files_from(api, c8, C8, verifier, "s1", record, C8_FILES), verifier)
    current = PILOT_SESSIONS[label]
    files = files_from(api, pilot, PILOT, label, "s1", current, PILOT_FILES)
    session = verify_pilot(files, label, checkout)
    need(not destination.resolve().is_relative_to(checkout.resolve()), "Pilot destination must be outside checkout.")
    destination.mkdir()
    for name in {*SESSION_FILES, "checksums.sha256"}:
        with (destination / PurePosixPath(name)).open("xb") as stream:
            stream.write(files["session/" + name])
    with evidence.open("xb") as stream:
        stream.write(frozen_json(dict(environment=label, slot=slot, measurement_source=SOURCE,
                          protocol=PROTOCOL, protocol_sha256=PROTOCOL_HASH, profile=PROFILE,
                          profile_sha256=PROFILE_HASH, source_set_sha256=SOURCE_SET,
                          pilot_run=PILOT, pilot_attempt=ATTEMPT, pilot_artifact=current[0],
                          pilot_zip_sha256=current[1], pilot_inventory_sha256=current[2],
                          pilot_session=session, c8_run=C8, c8_attempt=ATTEMPT, c8_valid_cells=9,
                          c8_verifier_artifacts={name: pin[0] for name, pin in C8_REPORTS.items()})))
    print(f"Accepted {label} slot {slot}: pilot artifact {current[0]}; C8 9/9.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", required=True, choices=RUNNERS)
    parser.add_argument("--slot", required=True, type=int, choices=(1, 2, 3))
    for name in ("checkout", "destination", "evidence"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    prepare(GitHub(os.environ["GH_TOKEN"]), args.environment, args.slot, args.checkout, args.destination, args.evidence)


if __name__ == "__main__":
    main()
