"""Captured inputs, path checks and owned-file signing transactions."""

from dataclasses import dataclass
import os
from pathlib import Path
import stat
import tempfile
from typing import Callable, Iterable


class SigningPathError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class SourceSnapshot:
    path: Path
    data: bytes
    stat_info: os.stat_result


@dataclass(frozen=True)
class SigningProtection:
    """Internal caller-owned storage paths and a preflight/prepublication guard.

    The caller must retain its required locks for the whole signing operation.
    This is not an identity assertion or an independently trusted capability.
    """

    protected_paths: tuple
    check: Callable[[Path], None]


def _fingerprint(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def capture_source(input_path) -> SourceSnapshot:
    """Read one regular-file handle once, rejecting observed concurrent changes."""
    path = Path(input_path).resolve(strict=True)
    if not stat.S_ISREG(path.stat().st_mode):
        raise SigningPathError("source.type", "Source must be a regular file")
    with path.open("rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise SigningPathError("source.type", "Source must be a regular file")
        data = source.read()
        after = os.fstat(source.fileno())
    if _fingerprint(before) != _fingerprint(after) or len(data) != after.st_size:
        raise SigningPathError("source.changed", "Source changed while it was being captured")
    return SourceSnapshot(path, data, after)


def validate_signing_paths(snapshot: SourceSnapshot, output_path, *, protected_paths: Iterable = ()) -> Path:
    """Resolve a destination without writing, protecting source and supplied keys.

    File identity checks catch hard links; resolution catches equivalent paths
    and symlink aliases. These checks are not a filesystem transaction or a
    defense against hostile path replacement after validation.
    """
    raw_output = Path(output_path)
    if os.name == "nt" and (
        raw_output.is_reserved() or ":" in str(raw_output)[len(raw_output.drive):]
    ):
        raise SigningPathError("path.destination", "Windows device and alternate-stream destinations are unsupported")
    output = raw_output.resolve(strict=False)
    try:
        link_info = raw_output.lstat()
    except FileNotFoundError:
        link_info = None
    try:
        output_info = output.stat()
    except FileNotFoundError:
        output_info = None

    source_now = snapshot.path.stat()
    if (os.path.normcase(str(output)) == os.path.normcase(str(snapshot.path))
            or output_info is not None and any(
                os.path.samestat(info, output_info) for info in (snapshot.stat_info, source_now))):
        raise SigningPathError("path.alias", "Destination aliases the captured source")
    for key_path in protected_paths:
        captured_key = key_path if isinstance(key_path, SourceSnapshot) else None
        key = Path(captured_key.path if captured_key else key_path).resolve(strict=True)
        key_info = key.stat()
        if (os.path.normcase(str(output)) == os.path.normcase(str(key))
                or output_info is not None and (
                    os.path.samestat(key_info, output_info)
                    or captured_key is not None and os.path.samestat(captured_key.stat_info, output_info))):
            raise SigningPathError("path.alias", "Destination aliases a supplied key file")

    reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    if link_info is not None and (
        stat.S_ISLNK(link_info.st_mode)
        or getattr(link_info, "st_file_attributes", 0) & reparse_point
    ):
        raise SigningPathError("path.destination_link", "Destination links and reparse points are unsupported")
    if output_info is not None and not stat.S_ISREG(output_info.st_mode):
        raise SigningPathError("path.destination", "Destination must be a regular file")
    parent = output.parent.resolve(strict=True)
    if not parent.is_dir():
        raise SigningPathError("path.destination", "Destination parent must be a directory")
    return parent / output.name


def _optional_fingerprint(path):
    try:
        return _fingerprint(path.stat())
    except FileNotFoundError:
        return None


class SigningTransaction:
    """Own each created artifact explicitly; never recursively delete a directory.

    The candidate is on the destination filesystem. All working files are
    removed before the sole commit operation, os.replace(). Cleanup errors
    before commit abort publication. A primary error keeps its traceback and
    receives a note if cleanup also fails. Process termination cannot run this
    cleanup, and path checks cannot defeat a hostile concurrent filesystem.
    """

    def __init__(self, destination, *, _before_publish=None):
        self.destination = Path(destination)
        self._before_publish = _before_publish
        self.workspace = None
        self.candidate = None
        self._owned = set()
        self._verified = False
        self._published = False
        self._candidate_before = None
        self._destination_before = _optional_fingerprint(self.destination)
        self._parent_identity = self.destination.parent.stat()

    def __enter__(self):
        self.workspace = Path(tempfile.mkdtemp(prefix=self._temp_prefix("work"), dir=self.destination.parent))
        return self

    def _temp_prefix(self, purpose):
        prefix = f".esign-{purpose}-"
        # Random temporary names must never be able to equal the final name,
        # including when that absent destination itself resembles a temp file.
        return ".esign-other-" if os.path.normcase(self.destination.name).startswith(prefix) else prefix

    def write_stage(self, name, data):
        if self.workspace is None or Path(name).name != name or name in ("", ".", ".."):
            raise ValueError("Invalid transaction stage name or state")
        path = self.workspace / name
        with path.open("xb") as handle:
            self._owned.add(path)
            if handle.write(data) != len(data):
                raise OSError("Short write to signing stage")
        return path

    def write_candidate(self, data):
        if self.candidate is not None:
            raise RuntimeError("Candidate has already been created")
        fd, name = tempfile.mkstemp(prefix=self._temp_prefix("candidate"), suffix=".tmp", dir=self.destination.parent)
        self.candidate = Path(name)
        self._owned.add(self.candidate)
        try:
            handle = os.fdopen(fd, "wb")
        except BaseException:
            os.close(fd)
            raise
        with handle:
            if handle.write(data) != len(data):
                raise OSError("Short write to signing candidate")
            handle.flush()
            os.fsync(handle.fileno())
            identity = os.fstat(handle.fileno())
        info = self._candidate_stat()
        if not os.path.samestat(identity, info):
            raise SigningPathError("candidate.changed", "Candidate path changed during writing")
        self._candidate_before = _fingerprint(info)
        return self.candidate

    def _candidate_stat(self):
        try:
            info = self.candidate.lstat()
        except FileNotFoundError as error:
            raise SigningPathError("candidate.changed", "Candidate disappeared") from error
        reparse_point = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
        if (not stat.S_ISREG(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & reparse_point):
            raise SigningPathError("candidate.changed", "Candidate is no longer a regular owned file")
        return info

    def mark_verified(self):
        if self.candidate is None or self._published:
            raise RuntimeError("No unpublished candidate")
        self._verified = True

    def _cleanup(self, *, working_only=False):
        errors = []
        for path in tuple(self._owned):
            if working_only and path == self.candidate:
                continue
            try:
                path.unlink(missing_ok=True)
                self._owned.discard(path)
            except OSError as error:
                errors.append(error)
        if self.workspace is not None:
            try:
                self.workspace.rmdir()  # Refuse to delete unexpected/unowned files.
                self.workspace = None
            except FileNotFoundError:
                self.workspace = None
            except OSError as error:
                errors.append(error)
        if errors:
            error = errors[0]
            for extra in errors[1:]:
                error.add_note(f"Additional signing cleanup failure: {extra}")
            raise error

    def cleanup_working(self):
        self._cleanup(working_only=True)

    def publish(self):
        if not self._verified or self._published or self.workspace is not None:
            raise RuntimeError("Publication requires a verified candidate and cleaned working files")
        if self._before_publish is not None:
            self._before_publish()
        if not os.path.samestat(self._parent_identity, self.destination.parent.stat()):
            raise SigningPathError("path.changed", "Destination directory changed during signing")
        if _optional_fingerprint(self.destination) != self._destination_before:
            raise SigningPathError("path.changed", "Destination changed during signing")
        if _fingerprint(self._candidate_stat()) != self._candidate_before:
            raise SigningPathError("candidate.changed", "Candidate changed after writing or verification")
        os.replace(self.candidate, self.destination)
        self._published = True
        self._owned.discard(self.candidate)

    def __exit__(self, exc_type, error, traceback):
        if not self._published:
            try:
                self._cleanup()
            except OSError as cleanup_error:
                if error is None:
                    raise
                error.add_note(f"Signing temporary-file cleanup failed: {cleanup_error}")
        return False
