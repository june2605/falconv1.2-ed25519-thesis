"""Pinned wheels, execution evidence and resource admission for the research harness."""
import ctypes
from datetime import datetime, timezone
from importlib import import_module, metadata
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from urllib.request import urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
LOCK = Path(__file__).with_name("wheels.json")
PROTOCOL = "hybridsign-5.5a-v1"
UNKNOWN = "unknown"
ENVIRONMENTS = {"LOCAL-WIN": "windows", "CI-WIN": "windows", "CI-LINUX": "linux", "CI-MAC": "macos"}
RUNNERS = {"CI-WIN": "windows-2022", "CI-LINUX": "ubuntu-24.04", "CI-MAC": "macos-15-intel"}
MIB = 1024**2
MIN_RAM = max(512 * MIB, 48 * 10 * MIB)
MIN_DISK = 8 * 10 * MIB + 64 * MIB
NATIVES = {"pqcrypto": "pqcrypto._sign.falcon_512", "PyNaCl": "nacl._sodium", "cffi": "_cffi_backend"}


class EnvironmentError(ValueError):
    """Public reason why a research environment was not accepted."""


def utc():
    return datetime.now(timezone.utc).isoformat()


def file_hash(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def write_json(path, value):
    with path.open("xb") as stream:
        stream.write(json_bytes(value))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, timeout=15).strip()


def selected_profile():
    profile = json.loads(LOCK.read_bytes())
    target = {"win32": "windows", "linux": "linux", "darwin": "macos"}.get(sys.platform)
    if (target is None or platform.machine().lower() not in ("amd64", "x86_64")
            or platform.python_implementation() != "CPython" or platform.python_version() != profile["python"]
            or sys.maxsize <= 2**32):
        raise EnvironmentError("profile.unsupported_platform_architecture_or_python")
    return profile, target, profile["wheels"][target]


def install_wheels(wheelhouse):
    _, _, wheels = selected_profile()
    app_venv = ROOT / ".venv"
    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve().is_relative_to(app_venv.resolve()):
        raise EnvironmentError("profile.requires_separate_research_venv")
    wheelhouse = wheelhouse.resolve()
    if wheelhouse.is_relative_to(ROOT):
        raise EnvironmentError("profile.keep_wheels_outside_repository")
    wheelhouse.mkdir(exist_ok=True)
    paths = []
    for entry in wheels.values():
        path = wheelhouse / entry["file"]
        if not path.exists():
            with urlopen(entry["url"], timeout=50) as source:
                data = source.read()
            if hashlib.sha256(data).hexdigest() != entry["sha256"]:
                raise EnvironmentError("profile.distribution_hash_mismatch")
            with path.open("xb") as out:
                out.write(data)
        if file_hash(path) != entry["sha256"]:
            raise EnvironmentError("profile.distribution_hash_mismatch")
        paths.append(str(path))
    subprocess.run([sys.executable, "-m", "pip", "--disable-pip-version-check", "install",
                    "--no-deps", "--no-index", "--only-binary=:all:", *paths], check=True, timeout=180)
    subprocess.run([sys.executable, "-m", "pip", "--disable-pip-version-check", "check"], check=True, timeout=30)


def runtime_profile(environment, wheelhouse):
    profile, target, wheels = selected_profile()
    if ENVIRONMENTS[environment] != target:
        raise EnvironmentError("profile.environment_os_mismatch")
    if (environment.startswith("CI-") != (os.environ.get("GITHUB_ACTIONS") == "true")
            or environment.startswith("CI-") and any(not os.environ.get(k) for k in
                ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_JOB", "RUNNER_NAME", "ImageOS", "ImageVersion"))):
        raise EnvironmentError("profile.missing_or_incorrect_execution_context")
    if sys.prefix == sys.base_prefix or Path(sys.prefix).resolve().is_relative_to((ROOT / ".venv").resolve()):
        raise EnvironmentError("profile.requires_separate_research_venv")
    installed = {}
    for name, entry in wheels.items():
        # Wheel metadata's first two filenames fields are normalized name and version.
        expected_version = entry["file"].split("-")[1]
        seen = metadata.version(name)
        if seen != expected_version or file_hash(wheelhouse / entry["file"]) != entry["sha256"]:
            raise EnvironmentError("profile.installed_version_or_wheel_hash_mismatch")
        installed[name] = {**entry, "version": seen, "platform_tag": entry["file"][:-4].split("-")[-1]}
        if name in NATIVES:
            loaded = Path(import_module(NATIVES[name]).__file__)
            actual = file_hash(loaded)
            if loaded.name != Path(entry["native_member"]).name or actual != entry["native_sha256"]:
                raise EnvironmentError("profile.loaded_native_hash_mismatch")
            installed[name]["loaded_native_sha256"] = actual
    return dict(id=profile["id"], file_sha256=file_hash(LOCK), python=platform.python_version(),
                architecture="x64", falcon_lineage=profile["falcon_lineage"],
                build_reproducibility=UNKNOWN, packages=installed)


def _command(*args):
    try:
        return subprocess.check_output(args, encoding="utf-8", errors="replace",
                                       stderr=subprocess.DEVNULL, timeout=25).strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return ""


def windows_state(root):
    drive = root.drive.removesuffix(":")
    if not re.fullmatch("[A-Za-z]", drive):
        return {}
    cmd = (
        "$ErrorActionPreference='Stop';"
        "$cpu=Get-CimInstance Win32_Processor;"
        "$o=Get-CimInstance Win32_OperatingSystem;"
        f"$v=Get-Volume -DriveLetter '{drive}';"
        "@{cpu=@($cpu | ForEach-Object {$_.Name});"
        "cores=[int](($cpu | Measure-Object NumberOfCores -Sum).Sum);"
        "total=([long]$o.TotalVisibleMemorySize*1024);"
        "available=([long]$o.FreePhysicalMemory*1024);"
        "fs=$v.FileSystem; build=($o.BuildNumber+' '+$o.Version); os=$o.Caption"
        "}|ConvertTo-Json -Compress"
    )
    line = _command("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd)
    data = json.loads(line) if line else {}
    state = (ctypes.c_ubyte * 12)()
    on_ac = ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(state))
    data.update(local_volume=ctypes.windll.kernel32.GetDriveTypeW(str(root.anchor)) == 3,
                power=("AC" if state[0] == 1 else "battery" if state[0] == 0 else UNKNOWN) if on_ac else UNKNOWN,
                power_saver={0: "off", 1: "on"}.get(state[3], UNKNOWN) if on_ac else UNKNOWN,
                power_policy=_command("powercfg.exe", "/getactivescheme") or UNKNOWN)
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
            patch = winreg.QueryValueEx(key, "UBR")[0]
        if data.get("build"):
            data["build"] += f".{patch}"
    except OSError:
        pass
    return data


def linux_state(root):
    ram = {k: int(v) * 1024 for k, v in re.findall(r"^(MemTotal|MemAvailable):\s+(\d+) kB",
                                                Path("/proc/meminfo").read_text(), re.MULTILINE)}
    cpuinfo = Path("/proc/cpuinfo").read_text()
    model = re.findall(r"^model name\s*:\s*(.+)$", cpuinfo, re.MULTILINE)
    topology = [dict(re.findall(r"^(physical id|core id)\s*:\s*(\d+)$", block, re.MULTILINE))
                for block in cpuinfo.split("\n\n")]
    cores = {(part["physical id"], part["core id"]) for part in topology if len(part) == 2}
    fs = _command("findmnt", "-n", "-T", str(root), "-o", "FSTYPE")
    distro = platform.freedesktop_os_release()
    return dict(cpu=sorted(set(model)) or UNKNOWN, cores=len(cores) or UNKNOWN, total=ram.get("MemTotal"),
                available=ram.get("MemAvailable"), fs=fs, local_volume=fs in {"ext4", "xfs", "btrfs"},
                os=distro.get("PRETTY_NAME"), build=platform.release())


def macos_state(root):
    stats = _command("/usr/bin/vm_stat")
    pg = re.search(r"page size of (\d+) bytes", stats)
    pages = re.findall(r"^Pages (?:free|inactive|speculative):\s+(\d+)\.", stats, re.MULTILINE)
    free = int(pg[1]) * sum(map(int, pages)) if pg and len(pages) == 3 else None
    df = _command("/bin/df", "-P", str(root)).splitlines()
    device = df[-1].split()[0] if len(df) > 1 else ""
    raw = _command("/usr/sbin/diskutil", "info", "-plist", device) if device.startswith("/dev/") else ""
    volume = plistlib.loads(raw.encode()) if raw else {}
    fs = volume.get("FilesystemType")
    return dict(cpu=_command("/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"),
                cores=int(_command("/usr/sbin/sysctl", "-n", "hw.physicalcpu") or 0),
                total=int(_command("/usr/sbin/sysctl", "-n", "hw.memsize") or 0),
                available=free, fs=fs, local_volume=fs in {"apfs", "hfs"},
                os=_command("/usr/bin/sw_vers", "-productVersion"), build=_command("/usr/bin/sw_vers", "-buildVersion"))


def host_state(target, root):
    raw = {"windows": windows_state, "linux": linux_state, "macos": macos_state}[target](root)
    result = {key: raw.get(key) or UNKNOWN for key in
              ("cpu", "cores", "total", "available", "fs", "os", "build", "power", "power_saver", "power_policy")}
    result.update(local_volume=raw.get("local_volume", False), free_disk=shutil.disk_usage(root).free,
                  kernel=platform.release(), logical_cores=os.cpu_count(), machine=platform.machine(),
                  affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else UNKNOWN,
                  thread_policy="sequential; no affinity, thread or system power settings changed",
                  python_threads=threading.active_count(), gc_enabled=gc.isenabled(),
                  gc_thresholds=gc.get_threshold(), switch_interval_s=sys.getswitchinterval(),
                  clock_resolution_ns=round(time.get_clock_info("perf_counter").resolution * 10**9))
    return result


def execution(environment):
    ci = environment.startswith("CI-")
    return dict(environment=environment, execution_kind="ci" if ci else "local",
                physical_host_id=UNKNOWN if ci else "local-win-01", physical_parent_id=UNKNOWN,
                run_id=os.environ.get("GITHUB_RUN_ID", UNKNOWN) if ci else UNKNOWN,
                job=os.environ.get("GITHUB_JOB", UNKNOWN) if ci else UNKNOWN,
                attempt=os.environ.get("GITHUB_RUN_ATTEMPT", UNKNOWN) if ci else UNKNOWN,
                runner_label=RUNNERS.get(environment, UNKNOWN),
                runner_image=os.environ.get("ImageOS", UNKNOWN) if ci else UNKNOWN,
                runner_image_version=os.environ.get("ImageVersion", UNKNOWN) if ci else UNKNOWN,
                runner_instance_id=uuid4().hex, process_id=os.getpid())


def safe_output(path, *, local):
    parent = path.parent.resolve(strict=True)
    if not parent.is_dir() or parent.is_relative_to(ROOT) or path.name in {"", ".", ".."}:
        raise EnvironmentError("output.keep_research_evidence_outside_repository")
    if local:
        locations = (tempfile.gettempdir(), os.environ.get("OneDrive"), os.environ.get("OneDriveConsumer"),
                     os.environ.get("OneDriveCommercial"))
        if any(value and parent.is_relative_to(Path(value).resolve()) for value in locations):
            raise EnvironmentError("output.temp_or_sync_folder")
    return parent / path.name


def check_idle():
    """Detect competing known Windows project automation at local pilot entry."""
    filter_text = r"playwright|pytest|desktop\.launcher|research\.benchmarks\.(phase5_2[ab]|p55)"
    script = (
        f"$skip=@({os.getpid()},{os.getppid()});"
        "($null -ne (Get-CimInstance Win32_Process | Where-Object { "
        "($_.ProcessId -notin $skip) -and ($_.Name -eq 'HybridSign.exe' -or "
        f"($_.Name -match '^(python|node).*' -and $_.CommandLine -match '{filter_text}')) }} "
        "| Select-Object -First 1)).ToString()"
    )
    idle = _command("powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script)
    if idle != "False":
        raise EnvironmentError("preflight.competing_automation_or_check_unavailable")


def preflight(state):
    if not state["local_volume"] or state["fs"] not in {"NTFS", "ext4", "xfs", "btrfs", "apfs", "hfs"}:
        raise EnvironmentError("preflight.local_filesystem_required")
    if type(state["available"]) is not int or state["available"] < MIN_RAM:
        raise EnvironmentError("preflight.available_ram")
    if state["free_disk"] < MIN_DISK:
        raise EnvironmentError("preflight.available_disk")
