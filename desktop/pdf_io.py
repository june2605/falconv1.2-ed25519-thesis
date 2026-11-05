"""Bounded PDF selection and Windows read sharing; no keys or HTTP content API."""
from contextlib import contextmanager
import ctypes as ct
from dataclasses import dataclass, field
import hashlib
import os
from pathlib import Path
import re

from signing_io import SourceSnapshot, _fingerprint
from utils import validate_unsigned_input
from vault_io import check_path, _native
from .worker import WorkerError

MAX_PDF_BYTES = 50 * 1024 * 1024


def fingerprint(path):
    try: return _fingerprint(Path(path).lstat())
    except FileNotFoundError: return None


@dataclass(frozen=True, repr=False)
class OutputChoice:
    path: object = field(repr=False)
    approved_fingerprint: tuple | None = field(repr=False)


def output_choice(path):
    """Called by native FileOk after overwrite approval, never by JavaScript."""
    return OutputChoice(path, fingerprint(path))


@contextmanager
def locked_pdf(path, *, unsigned=True):
    checked = check_path(path)  # Same conservative local NTFS/link/namespace policy.
    if checked.path.suffix.lower() != '.pdf': raise WorkerError('PDF_INVALID')
    native = _native()
    handle = native.kernel.CreateFileW(native.long_path(checked.path), 0x80000000,
                                      1, None, 3, 0x200080, None)  # Read, SHARE_READ, non-following.
    if handle == ct.c_void_p(-1).value: raise ct.WinError(ct.get_last_error())
    try:
        native.info(handle)  # Disk regular file, no reparse point, exactly one link.
        import msvcrt
        fd = msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
    except BaseException:
        native.close(handle)
        raise
    try: stream = os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise
    with stream:
        before = os.fstat(stream.fileno())
        limit = MAX_PDF_BYTES if unsigned else MAX_PDF_BYTES + 65536
        if not 0 < before.st_size <= limit: raise WorkerError('PDF_INVALID')
        content = stream.read(limit + 1)
        if len(content) > limit or _fingerprint(before) != _fingerprint(os.fstat(stream.fileno())):
            raise WorkerError('DOCUMENT_CHANGED')
        checked.recheck()
        if _fingerprint(before) != fingerprint(checked.path): raise WorkerError('DOCUMENT_CHANGED')
        if not re.match(rb'%PDF-(?:1\.[0-7]|2\.0)(?:\r|\n)', content): raise WorkerError('PDF_INVALID')
        if unsigned:
            if not content.rstrip().endswith(b'%%EOF') or not re.search(rb'startxref\s+[0-9]+\s+%%EOF\s*$', content):
                raise WorkerError('PDF_INVALID')
            try: validate_unsigned_input(content)
            except ValueError: raise WorkerError('PDF_INVALID') from None
        yield SourceSnapshot(checked.path, content, before)


def digest(snapshot):
    return hashlib.sha256(snapshot.data).hexdigest()
