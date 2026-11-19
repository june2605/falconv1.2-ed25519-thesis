"""Collect separate, sequential Phase 5.2B runs with the unchanged pilot harness."""

import argparse
import ctypes
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from research.benchmarks import phase5_2a as pilot


PILOT_ARTIFACTS = {
    "raw.csv": "7cbdde5a636f57554c555a4c867cb9da0dd55e9f374b2ecd7dfa859242e73b48",
    "experiment.json": "0243e205c5136d99c7a0a5d441f2d3851d4855e6a002fa4b675b3f1f847905c6",
    "summary.json": "56b6f6db7a01f458056b7f2007b7a0609a3f51c92ab5d3e1bbcfea2e43b93347",
    "hybrid-pdf-median.png": "09fa94e6a4ac6ad9f5b5b4680a92e6b9065af2d85a5b4c999227879444024b31",
    "primitive-64b-median.png": "cc55b602bf769ada0e4af0c8001104f1420d365087345355f1f8542c2a395e41",
    "demo.pdf": "2d94ba434bbbfda3ffcd78731f2e94146352e5dc7680dcd566d2ca0614a20639",
    "1-MiB.pdf": "568830f43d6be53c262a29d679ab97bb02afcd44418a839a10d26ece85ca6490",
    "10-MiB.pdf": "34061f01468d32fa023756bfc0b225d703d31c2275a387cf68cc2139ad4cdec5",
}
PILOT_HARNESS_SHA256 = "29a697ca3d4063773e3be9856a9a3e70fba7d4671e37c89613d0fc775a579410"
WARMUPS = 3
REPETITIONS = 30
ADMISSION_S = 300

BOOTSTRAP = """\
import gc
import json
import os
import runpy
import sys
import threading

def record(event):
    context = dict(pid=os.getpid(), gc_enabled=gc.isenabled(),
                   gc_thresholds=gc.get_threshold(), python_threads=threading.active_count(),
                   switch_interval_s=sys.getswitchinterval())
    print(event + '=' + json.dumps(context), flush=True)

record('PROCESS_START')
try:
    runpy.run_module('research.benchmarks.phase5_2a', run_name='__main__', alter_sys=True)
finally:
    record('PROCESS_END')
"""


def file_hash(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def preserve_pilot(source, destination):
    missing = [name for name in PILOT_ARTIFACTS if not (source / name).is_file()]
    if missing:
        raise ValueError("Missing Phase 5.2A artifacts: " + ", ".join(missing))
    for name, digest in PILOT_ARTIFACTS.items():
        if file_hash(source / name) != digest:
            raise ValueError(f"Phase 5.2A hash mismatch: {name}")
    destination.mkdir()
    for name, digest in PILOT_ARTIFACTS.items():
        with (source / name).open("rb") as original, (destination / name).open("xb") as archived:
            shutil.copyfileobj(original, archived)
        if file_hash(destination / name) != digest:
            raise OSError(f"Phase 5.2A copy verification failed: {name}")
    pilot.write_json(destination / "archive-checksums.json", PILOT_ARTIFACTS)


def host_conditions(root):
    """Sample operating conditions outside all timed workload intervals."""
    drive = root.drive.removesuffix(":")
    if len(drive) != 1 or not drive.isascii() or not drive.isalpha():
        raise ValueError("Use a local Windows volume for research data")
    script = f"""
        $ErrorActionPreference='Stop'
        $cpu=Get-CimInstance Win32_Processor
        $os=Get-CimInstance Win32_OperatingSystem
        $fs=Get-Volume -DriveLetter '{drive}'
        @{{
            physical_cores=[int](($cpu | Measure-Object NumberOfCores -Sum).Sum)
            free_ram_bytes=([long]$os.FreePhysicalMemory*1024)
            filesystem=$fs.FileSystem
        }} | ConvertTo-Json -Compress
    """
    record = json.loads(subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        text=True, encoding="utf-8", timeout=30,
    ))
    if record["filesystem"] != "NTFS" or ctypes.windll.kernel32.GetDriveTypeW(str(root.anchor)) != 3:
        raise ValueError("Use a fixed local NTFS volume")
    # SYSTEM_POWER_STATUS has four byte fields and two DWORDs.
    status = (ctypes.c_ubyte * 12)()
    if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
        raise ctypes.WinError()
    record.update(
        ac_line={0: "battery", 1: "AC"}.get(status[0], "unknown"),
        battery_percent=None if status[2] == 255 else int(status[2]),
        power_saving={0: "off", 1: "on"}.get(status[3], "unknown"),
        power_scheme=subprocess.check_output(["powercfg.exe", "/getactivescheme"],
                                             text=True, errors="replace", timeout=10).strip(),
        free_disk_bytes=shutil.disk_usage(root).free,
    )
    return record


def check_idle():
    """Detect competing project automation before launching each child."""
    script = """
        $matches=Get-CimInstance Win32_Process | Where-Object {
            $_.Name -eq 'HybridSign.exe' -or
            ($_.Name -match '^(python|node).*' -and
             $_.CommandLine -match '(playwright|pytest|research\\.benchmarks\\.phase5_2a|desktop\\.launcher)')
        } | Select-Object -ExpandProperty ProcessId
        if ($matches) { $matches -join ',' }
    """
    busy = subprocess.check_output(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        text=True, timeout=30,
    ).strip()
    if busy:
        raise RuntimeError(f"Competing project processes detected: {busy}")


def run_session(campaign, label, kind, sizes, warmups, repetitions, budget):
    check_idle()
    before = host_conditions(campaign)
    directory = campaign / label
    directory.mkdir()
    argv = ["--output-root", str(directory), "--pdf-mib", *map(str, sizes),
            "--warmups", str(warmups), "--repetitions", str(repetitions), "--budget-seconds", str(budget)]
    context = {"label": label, "kind": kind, "planned_warmups": warmups,
               "planned_repetitions": repetitions, "pdf_mib": sizes, "budget_s": budget,
               "source_commit": subprocess.check_output(
                   ["git", "rev-parse", "HEAD"], cwd=pilot.ROOT, text=True, timeout=10).strip(),
               "utc_launch": utc_now(), "before": before, "status": "running"}
    metadata = directory / "session.json"
    pilot.write_json(metadata, context)
    started = time.perf_counter_ns()
    print(f"Starting {label}", flush=True)
    try:
        with (directory / "process.log").open("xb") as log:
            with subprocess.Popen([sys.executable, "-B", "-c", BOOTSTRAP, *argv],
                                  cwd=pilot.ROOT, stdout=log, stderr=subprocess.STDOUT) as process:
                context["launcher_pid"] = process.pid
                try:
                    context["exit_code"] = process.wait(timeout=budget + 150)
                except (subprocess.TimeoutExpired, KeyboardInterrupt):
                    subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                    process.wait(timeout=15)
                    context["exit_code"] = process.returncode
                    raise
        context["utc_exit"] = utc_now()
        context["process_wall_ns"] = time.perf_counter_ns() - started
        events = {}
        for line in (directory / "process.log").read_text(encoding="utf-8", errors="replace").splitlines():
            event, _, payload = line.partition("=")
            if event in {"PROCESS_START", "PROCESS_END"}:
                events[event] = json.loads(payload)
        context["python_process_context"] = events
        children = [path for path in directory.iterdir() if path.is_dir() and path.name.startswith("hybridsign-phase5-2a-")]
        if len(children) == 1:
            context["data_path"] = children[0].relative_to(campaign).as_posix()
        if context["exit_code"] or len(children) != 1:
            raise RuntimeError(f"{label} failed. Review its independent process record.")
        observed = json.loads((children[0] / "experiment.json").read_bytes())
        if (observed["status"] != "complete" or set(events) != {"PROCESS_START", "PROCESS_END"}
                or events["PROCESS_START"]["pid"] != events["PROCESS_END"]["pid"]
                or observed["commit"] != context["source_commit"]
                or observed["harness_sha256"] != PILOT_HARNESS_SHA256):
            raise RuntimeError(f"Session evidence mismatch in {label}")
        context["pid"] = events["PROCESS_START"]["pid"]
        context["experiment_id"] = observed["experiment_id"]
        context["after"] = host_conditions(campaign)
        context["status"] = "complete"
        print(f"Completed {label}, PID {context['pid']}", flush=True)
        return context
    except BaseException as error:
        context.update(status="failed", failure_type=type(error).__name__)
        raise
    finally:
        context.setdefault("utc_exit", utc_now())
        context.setdefault("process_wall_ns", time.perf_counter_ns() - started)
        pilot.write_json(metadata, context)


def preflight_40(campaign):
    size = 40 * pilot.MIB
    state = host_conditions(campaign)
    required_ram = max(512 * pilot.MIB, 48 * size)
    required_disk = 10 * size + size + 64 * pilot.MIB
    result = {
        "condition": "optional-40-MiB", "input_bytes": size, "desktop_limit_bytes": pilot.MAX_PDF_BYTES,
        "ram_reserve_bytes": required_ram, "disk_reserve_bytes": required_disk,
        "observed": state, "max_intermediate_disk_copies": 10, "status": "not_run",
        "checked_at_utc": utc_now(),
    }
    if size <= pilot.MAX_PDF_BYTES and state["free_ram_bytes"] >= required_ram and state["free_disk_bytes"] >= required_disk:
        data = pilot.extend_pdf(pilot.SAMPLE.read_bytes(), size)
        pilot.validate_pdf(data, size)
        result.update(status="preflight_passed", public_input_sha256=pilot.sha256(data))
    pilot.write_json(campaign / "optional-40-preflight.json", result)
    return result


def collect(output_root, pilot_source, include_40):
    root = pilot.output_parent(output_root)
    if file_hash(Path(pilot.__file__)) != PILOT_HARNESS_SHA256:
        raise ValueError("The Phase 5.2A harness bytes differ from the validated pilot")
    campaign = Path(tempfile.mkdtemp(prefix="campaign-", dir=root))
    print(f"Research data directory: {campaign}", flush=True)
    run_book = {"status": "running", "utc_start": utc_now(), "sessions": [],
                "collector_sha256": file_hash(Path(__file__))}
    record_path = campaign / "collection.json"
    pilot.write_json(record_path, run_book)
    try:
        preserve_pilot(pilot_source, campaign / "phase5-2a-preserved")
        for index in range(1, 4):
            session = run_session(campaign, f"matched-{index:02}", "matched", [1, 10], WARMUPS, REPETITIONS, ADMISSION_S)
            run_book["sessions"].append(session["label"])
            pilot.write_json(record_path, run_book)
        run_book["optional_40"] = "not_requested"
        if include_40:
            optional = preflight_40(campaign)
            run_book["optional_40"] = optional["status"]
            if optional["status"] == "preflight_passed":
                check = run_session(campaign, "optional-40-feasibility", "feasibility", [40], 1, 1, ADMISSION_S)
                run_book["sessions"].append(check["label"])
                projected = check["process_wall_ns"] / 1e9 * (WARMUPS + REPETITIONS)
                optional["projected_conservative_seconds"] = projected
                run_book["optional_40"] = "not_run_after_feasibility"
                if projected <= ADMISSION_S and preflight_40(campaign)["status"] == "preflight_passed":
                    full = run_session(campaign, "optional-40-measured", "optional", [40], WARMUPS, REPETITIONS, ADMISSION_S)
                    run_book["sessions"].append(full["label"])
                    run_book["optional_40"] = "complete"
                optional["status"] = run_book["optional_40"]
                pilot.write_json(campaign / "optional-40-preflight.json", optional)
        run_book["status"] = "complete"
    except BaseException as error:
        run_book.update(status="failed", failure_type=type(error).__name__)
        raise
    finally:
        run_book["utc_end"] = utc_now()
        pilot.write_json(record_path, run_book)


def main():
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--output-root", required=True, type=Path)
    args.add_argument("--pilot-source", required=True, type=Path)
    args.add_argument("--include-40", action="store_true")
    options = args.parse_args()
    collect(options.output_root, options.pilot_source, options.include_40)


if __name__ == "__main__":
    main()
