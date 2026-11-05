"""Windows/NTFS encrypted-only vault I/O. No cryptographic or key operations.

Fail closed on unsupported platforms, paths or security descriptors. Persistent
empty sidecars coordinate cooperating processes; they are deliberately not
unlinked on unlock. Rechecks are not an atomic CAS against hostile filesystem
actors. Publication visibility is not a power-loss durability guarantee.
"""

from contextlib import contextmanager
import ctypes as ct
from ctypes import wintypes as wt
from dataclasses import dataclass, field
from functools import lru_cache
import hashlib
import os
from pathlib import Path
import secrets
import stat
import struct

from vault_format import VAULT_LENGTH, VaultError, VaultFormatError, parse_vault


class VaultIOError(VaultError):
    code = "vault.io"
    message = "Vault filesystem operation failed"


class VaultPathError(VaultIOError):
    code = "vault.path"
    message = "Unsupported or aliased vault path"


class VaultSecurityError(VaultIOError):
    code = "vault.security"
    message = "Required Windows file security could not be established"


class VaultExistsError(VaultIOError):
    code = "vault.exists"
    message = "Destination already exists"


class VaultPermissionError(VaultIOError):
    code = "vault.permission"
    message = "Vault access or publication denied"


class VaultLockError(VaultIOError):
    code = "vault.file_locked"
    message = "Vault is in use by another operation"


class VaultConflictError(VaultIOError):
    code = "vault.conflict"
    message = "Vault path, identity or revision changed"


class VaultVerificationError(VaultIOError):
    code = "vault.verification"
    message = "Staged vault did not recover the expected material"


_PREFIX = ".hybrid-vault-"
_REPARSE = 0x400
_FILE_ALL_ACCESS = 0x1F01FF


class _SecurityAttributes(ct.Structure):
    _fields_ = [("length", wt.DWORD), ("descriptor", ct.c_void_p), ("inherit", wt.BOOL)]


class _FileInfo(ct.Structure):
    _fields_ = [("attributes", wt.DWORD), ("created", wt.FILETIME),
                ("accessed", wt.FILETIME), ("written", wt.FILETIME),
                ("volume", wt.DWORD), ("size_high", wt.DWORD), ("size_low", wt.DWORD),
                ("links", wt.DWORD), ("index_high", wt.DWORD), ("index_low", wt.DWORD)]


class _Overlapped(ct.Structure):
    _fields_ = [("internal", ct.c_size_t), ("internal_high", ct.c_size_t),
                ("offset", wt.DWORD), ("offset_high", wt.DWORD), ("event", wt.HANDLE)]


class _Acl(ct.Structure):
    _fields_ = [("revision", ct.c_ubyte), ("reserved", ct.c_ubyte),
                ("size", wt.WORD), ("count", wt.WORD), ("reserved2", wt.WORD)]


class _Windows:
    def __init__(self):
        self.kernel = ct.WinDLL("kernel32", use_last_error=True)
        self.security = ct.WinDLL("advapi32", use_last_error=True)
        void, dword, handle = ct.c_void_p, wt.DWORD, wt.HANDLE
        pvoid = ct.POINTER(void)
        definitions = (
            (self.kernel, "GetCurrentProcess", [], handle),
            (self.kernel, "CloseHandle", [handle], wt.BOOL),
            (self.kernel, "LocalFree", [void], void),
            (self.kernel, "CreateFileW", [wt.LPCWSTR, dword, dword, void, dword, dword, handle], handle),
            (self.kernel, "GetFileInformationByHandle", [handle, ct.POINTER(_FileInfo)], wt.BOOL),
            (self.kernel, "GetFileType", [handle], dword),
            (self.kernel, "GetDriveTypeW", [wt.LPCWSTR], wt.UINT),
            (self.kernel, "GetVolumeInformationW", [wt.LPCWSTR, wt.LPWSTR, dword, void, void,
                                                     ct.POINTER(dword), wt.LPWSTR, dword], wt.BOOL),
            (self.kernel, "LockFileEx", [handle, dword, dword, dword, dword, ct.POINTER(_Overlapped)], wt.BOOL),
            (self.kernel, "MoveFileExW", [wt.LPCWSTR, wt.LPCWSTR, dword], wt.BOOL),
            (self.kernel, "SetFileInformationByHandle", [handle, ct.c_int, void, dword], wt.BOOL),
            (self.security, "OpenProcessToken", [handle, dword, ct.POINTER(handle)], wt.BOOL),
            (self.security, "GetTokenInformation", [handle, ct.c_int, void, dword, ct.POINTER(dword)], wt.BOOL),
            (self.security, "ConvertSidToStringSidW", [void, pvoid], wt.BOOL),
            (self.security, "ConvertStringSecurityDescriptorToSecurityDescriptorW",
             [wt.LPCWSTR, dword, pvoid, void], wt.BOOL),
            (self.security, "GetSecurityInfo", [handle, ct.c_int, dword, pvoid, pvoid, pvoid, pvoid, pvoid], dword),
            (self.security, "GetSecurityDescriptorControl", [void, ct.POINTER(wt.WORD), ct.POINTER(dword)], wt.BOOL),
            (self.security, "GetAce", [void, dword, pvoid], wt.BOOL),
        )
        for library, name, arguments, result in definitions:
            function = getattr(library, name)
            function.argtypes, function.restype = arguments, result
        self.user_sid = self._current_sid()

    def _ok(self, result):
        if not result:
            raise ct.WinError(ct.get_last_error())

    def close(self, handle):
        self._ok(self.kernel.CloseHandle(handle))

    def _sid_text(self, sid):
        text = ct.c_void_p()
        self._ok(self.security.ConvertSidToStringSidW(sid, ct.byref(text)))
        try:
            return ct.wstring_at(text)
        finally:
            self.kernel.LocalFree(text)

    def _current_sid(self):
        token, needed = wt.HANDLE(), wt.DWORD()
        self._ok(self.security.OpenProcessToken(self.kernel.GetCurrentProcess(), 8, ct.byref(token)))
        try:
            self.security.GetTokenInformation(token, 1, None, 0, ct.byref(needed))
            if not needed.value:
                raise VaultSecurityError()
            buffer = ct.create_string_buffer(needed.value)
            self._ok(self.security.GetTokenInformation(token, 1, buffer, needed, ct.byref(needed)))
            return self._sid_text(ct.cast(buffer, ct.POINTER(ct.c_void_p))[0])
        finally:
            self.close(token)

    def validate_volume(self, path):
        root = path.anchor
        flags, name = wt.DWORD(), ct.create_unicode_buffer(256)
        if self.kernel.GetDriveTypeW(root) != 3:
            raise VaultSecurityError()
        self._ok(self.kernel.GetVolumeInformationW(root, None, 0, None, None, ct.byref(flags), name, 256))
        if name.value != "NTFS" or not flags.value & 8:  # FILE_PERSISTENT_ACLS
            raise VaultSecurityError()

    def info(self, handle):
        info = _FileInfo()
        self._ok(self.kernel.GetFileInformationByHandle(handle, ct.byref(info)))
        if (self.kernel.GetFileType(handle) != 1 or info.attributes & (0x10 | _REPARSE)
                or info.links != 1):
            raise VaultPathError()
        return info

    def identity(self, handle):
        info = self.info(handle)
        return info.volume, (info.index_high << 32) | info.index_low

    def validate_security(self, handle):
        owner, dacl, descriptor = ct.c_void_p(), ct.c_void_p(), ct.c_void_p()
        status = self.security.GetSecurityInfo(handle, 1, 5, ct.byref(owner), None,
                                               ct.byref(dacl), None, ct.byref(descriptor))
        if status:
            raise VaultSecurityError()
        try:
            control, revision = wt.WORD(), wt.DWORD()
            self._ok(self.security.GetSecurityDescriptorControl(descriptor, ct.byref(control), ct.byref(revision)))
            if not control.value & 0x1000 or not dacl.value or self._sid_text(owner) != self.user_sid:
                raise VaultSecurityError()
            acl = ct.cast(dacl, ct.POINTER(_Acl)).contents
            if acl.count != 2:
                raise VaultSecurityError()
            trustees = []
            for index in range(acl.count):
                ace = ct.c_void_p()
                self._ok(self.security.GetAce(dacl, index, ct.byref(ace)))
                kind, flags, size, mask = struct.unpack("<BBHI", ct.string_at(ace, 8))
                if kind != 0 or flags != 0 or size < 12 or mask != _FILE_ALL_ACCESS:
                    raise VaultSecurityError()
                trustees.append(self._sid_text(ace.value + 8))
            if sorted(trustees) != sorted([self.user_sid, "S-1-5-18"]):
                raise VaultSecurityError()
        finally:
            self.kernel.LocalFree(descriptor)

    @staticmethod
    def long_path(path):
        return "\\\\?\\" + str(path)

    def mark_delete(self, handle):
        disposition = ct.c_ubyte(1)  # FILE_DISPOSITION_INFO uses BOOLEAN, not BOOL.
        self._ok(self.kernel.SetFileInformationByHandle(handle, 4, ct.byref(disposition), ct.sizeof(disposition)))

    def open(self, path, *, create=False, lock=False, delete=False):
        descriptor = ct.c_void_p()
        attributes = None
        if create:
            sddl = f"O:{self.user_sid}D:P(A;;FA;;;{self.user_sid})(A;;FA;;;SY)"
            self._ok(self.security.ConvertStringSecurityDescriptorToSecurityDescriptorW(
                sddl, 1, ct.byref(descriptor), None))
            attributes = _SecurityAttributes(ct.sizeof(_SecurityAttributes), descriptor, False)
        access = 0x80000000 | 0x20000  # GENERIC_READ | READ_CONTROL
        if create or lock:
            access |= 0x40000000
        if create or delete:
            access |= 0x10000  # DELETE, for handle-based owned cleanup.
        try:
            handle = self.kernel.CreateFileW(self.long_path(path), access,
                3 if lock else (0 if create or delete else 1),
                ct.byref(attributes) if attributes else None,
                1 if create else 3, 0x80 | 0x200000, None)
            open_error = ct.get_last_error()
        finally:
            if descriptor:
                self.kernel.LocalFree(descriptor)
        if handle == ct.c_void_p(-1).value:
            raise ct.WinError(open_error)
        try:
            self.info(handle)
            self.validate_security(handle)
        except BaseException as error:
            if create:
                try:
                    self.mark_delete(handle)
                except OSError:
                    error.add_note("Owned encrypted/empty artifact cleanup failed")
            self.close(handle)
            raise
        return handle

    def fd(self, handle):
        """Transfer ownership only on success; a failure leaves the caller owner."""
        import msvcrt
        return msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY | os.O_NOINHERIT)

    def acquire_lock(self, path):
        try:
            handle = self.open(path, create=True, lock=True)
        except FileExistsError:
            handle = self.open(path, lock=True)
        try:
            info = self.info(handle)
            if info.size_high or info.size_low:
                raise VaultSecurityError()
            if not self.kernel.LockFileEx(handle, 3, 0, 1, 0, ct.byref(_Overlapped())):
                raise VaultLockError()
        except BaseException:
            self.close(handle)
            raise
        return handle


@lru_cache(maxsize=1)
def _native():
    if os.name != "nt":
        raise VaultSecurityError()
    try:
        return _Windows()
    except Exception:
        raise VaultSecurityError() from None


def _identity(info):
    return info.st_dev, info.st_ino


def _fingerprint(info):
    return (*_identity(info), info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _regular(info):
    if (not stat.S_ISREG(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE
            or info.st_nlink != 1):
        raise VaultPathError()


@dataclass(frozen=True)
class CheckedPath:
    original: Path
    path: Path
    parents: tuple
    internal: bool = False

    def recheck(self):
        current = check_path(self.original, internal=self.internal)
        if current.path != self.path or current.parents != self.parents:
            raise VaultConflictError()


def check_path(path, *, internal=False):
    if type(path) is CheckedPath:
        path.recheck()
        return path
    try:
        value = os.fspath(path)
        if type(value) is not str or not value or any(ord(c) < 32 for c in value):
            raise VaultPathError()
        raw = Path(value)
        if (value.startswith("\\\\") or raw.drive and not raw.root
                or ":" in value[len(raw.drive):]):
            raise VaultPathError()
        for part in raw.parts[1:] if raw.anchor else raw.parts:
            if part in (".", ".."):
                continue
            if (part.endswith((".", " ")) or Path(part).is_reserved()
                    or any(c in '<>"|?*' for c in part)):
                raise VaultPathError()
        original = Path(os.path.abspath(value))
        if not internal and original.name.lower().startswith(_PREFIX):
            raise VaultPathError()
        native = _native()
        native.validate_volume(original)
        parents = []
        for parent in reversed(original.parents):
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & _REPARSE:
                raise VaultPathError()
            parents.append((str(parent), _identity(info)))
        try:
            info = original.lstat()
        except FileNotFoundError:
            resolved = original.parent.resolve(strict=True) / original.name
        else:
            _regular(info)
            resolved = original.resolve(strict=True)
        return CheckedPath(original, resolved, tuple(parents), internal)
    except VaultError:
        raise
    except (TypeError, ValueError, UnicodeError):
        raise VaultPathError() from None


@dataclass(frozen=True)
class VaultSnapshot:
    checked: CheckedPath
    data: bytes = field(repr=False)
    revision: str
    fingerprint: tuple

    @property
    def path(self):
        return self.checked.path


def capture_vault(path, *, internal=False):
    checked = check_path(path, internal=internal)
    native = _native()
    handle = native.open(checked.path)
    try:
        fd = native.fd(handle)
    except BaseException:
        native.close(handle)
        raise
    try:
        stream = os.fdopen(fd, "rb")
    except BaseException:
        os.close(fd)
        raise
    with stream:
        before = os.fstat(stream.fileno())
        _regular(before)
        if before.st_size != VAULT_LENGTH:
            raise VaultFormatError()
        data = stream.read(VAULT_LENGTH + 1)
        after = os.fstat(stream.fileno())
    if _fingerprint(before) != _fingerprint(after) or len(data) != VAULT_LENGTH:
        raise VaultConflictError()
    checked.recheck()
    if _fingerprint(checked.path.lstat()) != _fingerprint(after):
        raise VaultConflictError()
    parse_vault(data)  # Public structure checked before a caller's KDF.
    return VaultSnapshot(checked, data, hashlib.sha256(data).hexdigest(), _fingerprint(after))


def recheck_snapshot(snapshot):
    try:
        current = capture_vault(snapshot.checked)
        if current.fingerprint != snapshot.fingerprint or current.revision != snapshot.revision:
            raise VaultConflictError()
    except (OSError, VaultError):
        raise VaultConflictError() from None


def require_absent(checked):
    checked.recheck()
    try:
        checked.path.lstat()
    except FileNotFoundError:
        return
    raise VaultExistsError()


@contextmanager
def cooperative_locks(paths):
    checked = tuple(check_path(path) for path in paths)
    canonical = {os.path.normcase(str(item.path)): item for item in checked}
    handles, error = [], None
    native = _native()
    try:
        for name, item in sorted(canonical.items()):
            digest = hashlib.sha256(name.encode("utf-8", errors="strict")).hexdigest()
            lock_path = item.path.parent / f"{_PREFIX}lock-{digest}.lck"
            # Lock sidecars are persistent. Native open validates existing ACL,
            # link count, reparse attributes and file type through the handle.
            handles.append(native.acquire_lock(lock_path))
        for item in checked:
            item.recheck()
        yield checked
    except BaseException as caught:
        error = caught
        raise
    finally:
        failed = False
        for handle in reversed(handles):
            try:
                native.close(handle)  # Closing releases LockFileEx locks.
            except OSError:
                failed = True
        if failed:
            if error is not None:
                error.add_note("Vault lock release failed")
            else:
                failure = VaultIOError()
                failure.add_note("Lock release failed; publication may have completed; inspect the destination before retrying")
                raise failure


def _create_candidate(destination):
    native = _native()
    for _ in range(8):
        candidate = destination.parent / f"{_PREFIX}candidate-{secrets.token_hex(16)}.tmp"
        try:
            handle = native.open(candidate, create=True)
        except FileExistsError:
            continue
        try:
            identity = native.identity(handle)
            fd = native.fd(handle)
        except BaseException as error:
            # The exclusive raw handle still belongs to us, even when identity
            # lookup or CRT descriptor conversion failed. Delete by that handle.
            try:
                native.mark_delete(handle)
            except OSError:
                error.add_note("Owned encrypted/empty artifact cleanup failed")
            finally:
                native.close(handle)
            raise
        return fd, candidate, identity
    raise VaultIOError()


def _open_candidate_fd(fd):
    return os.fdopen(fd, "wb")


def _write_candidate_bytes(stream, data):
    return stream.write(data)


def _flush_candidate(stream):
    stream.flush()


def _remove_owned(path, identity):
    native = _native()
    try:
        handle = native.open(path, delete=True)
    except FileNotFoundError:
        return
    try:
        if native.identity(handle) != identity:
            raise VaultConflictError()
        native.mark_delete(handle)  # Handle-based delete; never unlink a replaced path.
    finally:
        native.close(handle)


def _publish_atomic(candidate, destination, *, replace):
    native = _native()
    native._ok(native.kernel.MoveFileExW(native.long_path(candidate), native.long_path(destination),
                                        1 if replace else 0))  # No COPY_ALLOWED fallback.
    return True


class VaultTransaction:
    """One encrypted candidate, authenticated after close, then one native rename."""

    def __init__(self, destination, *, previous=None, protected=()):
        self.destination = check_path(destination)
        self.previous = previous
        self.protected = tuple(protected)
        self.candidate = None
        self._owned_identity = None
        self._written = None
        self._verified = None
        self._published = False

    def __enter__(self):
        return self

    def write_candidate(self, data):
        # Shape validation is not proof of encryption. The lifecycle caller
        # supplies only codec-sealed or captured encrypted vault bytes.
        parse_vault(data)
        if self.candidate is not None:
            raise VaultIOError()
        fd, self.candidate, self._owned_identity = _create_candidate(self.destination.path)
        try:
            stream = _open_candidate_fd(fd)
        except BaseException:
            os.close(fd)
            raise
        with stream:
            if _write_candidate_bytes(stream, data) != len(data):
                raise VaultIOError()
            _flush_candidate(stream)
            os.fsync(stream.fileno())
            self._written = _fingerprint(os.fstat(stream.fileno()))

    def verify(self, validator):
        if self.candidate is None or self._published:
            raise VaultIOError()
        candidate = capture_vault(self.candidate, internal=True)
        if candidate.fingerprint != self._written or validator(candidate.data) is not True:
            raise VaultVerificationError()
        self._verified = candidate

    def publish(self):
        if self._verified is None or self._published:
            raise VaultVerificationError()
        self.destination.recheck()
        for snapshot in self.protected:
            recheck_snapshot(snapshot)
        if self.previous is None:
            require_absent(self.destination)
        else:
            if self.previous.path != self.destination.path:
                raise VaultPathError()
            recheck_snapshot(self.previous)
        recheck_snapshot(self._verified)
        if _publish_atomic(self.candidate, self.destination.path, replace=self.previous is not None) is not True:
            raise VaultIOError()
        self._published = True

    def __exit__(self, exc_type, error, traceback):
        if self.candidate is not None and not self._published:
            try:
                _remove_owned(self.candidate, self._owned_identity)
            except (OSError, VaultError):
                if error is None:
                    failure = VaultIOError()
                    failure.add_note("Vault candidate cleanup failed; encrypted artifact retained")
                    raise failure from None
                error.add_note("Vault candidate cleanup failed; encrypted artifact retained")
        return False
