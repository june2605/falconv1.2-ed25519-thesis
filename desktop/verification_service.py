"""Read-only public-key snapshots; the inherited verifier is the sole engine."""
import secrets

from signing_io import _fingerprint
from vault_format import parse_vault
from vault_io import check_path, recheck_snapshot
from verify import verify_bytes
from .pdf_io import locked_pdf, digest
from .worker import WorkerError


class VerificationService:
    def __init__(self):
        self.document = None
        self.source = None

    def select_pdf(self, path):
        with locked_pdf(path, unsigned=False) as snapshot:
            public = {'documentId': secrets.token_hex(16), 'displayName': snapshot.path.name[:160],
                      'sizeBytes': len(snapshot.data)}
            self.document = (check_path(path), _fingerprint(snapshot.stat_info), digest(snapshot), public)
        return dict(public)

    def select_keys(self, snapshot, *, authenticated=False):
        # Structural profile, encodings/sizes and hybrid-v1 ID are checked by the
        # existing codec. Only managed authentication establishes header origin.
        public = parse_vault(snapshot.data).metadata.public_keys
        metadata = {'keySourceId': secrets.token_hex(16), 'displayName': snapshot.path.stem[:80],
                    'hybridKeyId': public.key_id,
                    'trust': 'vault-authenticated' if authenticated else 'unauthenticated-metadata'}
        self.source = snapshot, public, metadata
        return dict(metadata)

    def check_ids(self, document_id, key_id):
        if self.document is None or self.document[3]['documentId'] != document_id:
            raise WorkerError('STALE_DOCUMENT')
        if self.source is None or self.source[2]['keySourceId'] != key_id:
            raise WorkerError('STALE_KEY_SOURCE')
        return dict(self.document[3]), dict(self.source[2])

    def run(self, document_id, key_id):
        self.check_ids(document_id, key_id)
        checked, expected, checksum, _ = self.document
        vault_snapshot, public, _ = self.source
        recheck_snapshot(vault_snapshot)
        checked.recheck()
        with locked_pdf(checked.original, unsigned=False) as snapshot:
            if expected != _fingerprint(snapshot.stat_info) or checksum != digest(snapshot):
                raise WorkerError('DOCUMENT_CHANGED')
            result = verify_bytes(snapshot.data, public.ed25519_public_key, public.falcon_public_key)
            # Timing slots are not independent algorithm results. Never infer
            # success from tuple truthiness, an integer or a malformed response.
            if type(result) is not tuple or len(result) != 11 or type(result[0]) is not bool:
                raise WorkerError('VERIFY_FAILED')
            recheck_snapshot(vault_snapshot)
            checked.recheck()
            return result[0]
