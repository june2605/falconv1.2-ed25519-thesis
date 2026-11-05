"""Owner-thread document validation and the single inherited managed signer."""
from pathlib import Path

from signing_io import _fingerprint, validate_signing_paths
from vault_io import check_path, lock_file_path
from vault_signing import sign_vault_document
from verify import verify_bytes
from .pdf_io import locked_pdf, digest, fingerprint, OutputChoice
from .worker import WorkerError


class SigningService:
    def __init__(self):
        self.document = None  # Private checked source metadata/digest; no frontend contents.

    def select(self, path, document_id):
        with locked_pdf(path) as snapshot:
            self.document = (check_path(path), _fingerprint(snapshot.stat_info), digest(snapshot),
                             {'documentId': document_id, 'displayName': snapshot.path.name[:160],
                              'sizeBytes': len(snapshot.data)})
        return dict(self.document[3])

    def require_document(self, document_id):
        if self.document is None or self.document[3]['documentId'] != document_id:
            raise WorkerError('STALE_DOCUMENT')
        checked, expected, checksum, public = self.document
        checked.recheck()
        with locked_pdf(checked.original) as snapshot:
            if _fingerprint(snapshot.stat_info) != expected or digest(snapshot) != checksum:
                raise WorkerError('DOCUMENT_CHANGED')
        return dict(public)

    def run(self, vaults, args, choice, engine_started):
        document_id, vault_id, session_id, _ = args
        handle = vaults.require_session(vault_id, session_id)
        self.require_document(document_id)
        checked, expected, checksum, _ = self.document
        if type(choice) is not OutputChoice: raise WorkerError('INVALID_REQUEST')
        output = check_path(choice.path)
        if output.path.suffix.lower() != '.pdf': raise WorkerError('SIGN_PATH')
        if fingerprint(output.path) != choice.approved_fingerprint: raise WorkerError('SIGN_PATH')
        with locked_pdf(checked.original) as source:
            if _fingerprint(source.stat_info) != expected or digest(source) != checksum:
                raise WorkerError('DOCUMENT_CHANGED')
            validate_signing_paths(source, output.path, protected_paths=(handle.path, lock_file_path(handle.path)))
            if output.path.exists():
                with output.path.open('rb') as existing:
                    if not existing.read(8).startswith(b'%PDF-'): raise WorkerError('SIGN_PATH')
            # Existing core owns captured bytes, stages, capacity checks, final
            # verification, storage guards and atomic replacement. No new engine.
            public = handle.metadata.public_keys
            engine_started()
            result = sign_vault_document(handle, checked.original, output.path)
            if type(result) is not tuple or len(result) != 11 or Path(result[0]) != output.path:
                raise WorkerError('SIGN_UNCERTAIN')
            with locked_pdf(output.path, unsigned=False) as completed:
                if verify_bytes(completed.data, public.ed25519_public_key, public.falcon_public_key)[0] is not True:
                    raise WorkerError('SIGN_UNCERTAIN')
        return output.path.name[:160]
