"""Read-only source capture and path checks; atomic publication is a later step."""

from dataclasses import dataclass
import os
from pathlib import Path
import stat
from typing import Iterable


class SigningPathError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


@dataclass(frozen=True)
class SourceSnapshot:
    path: Path
    data: bytes
    stat_info: os.stat_result


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

    if (os.path.normcase(str(output)) == os.path.normcase(str(snapshot.path))
            or output_info is not None and os.path.samestat(snapshot.stat_info, output_info)):
        raise SigningPathError("path.alias", "Destination aliases the captured source")
    for key_path in protected_paths:
        key = Path(key_path).resolve(strict=True)
        key_info = key.stat()
        if (os.path.normcase(str(output)) == os.path.normcase(str(key))
                or output_info is not None and os.path.samestat(key_info, output_info)):
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
