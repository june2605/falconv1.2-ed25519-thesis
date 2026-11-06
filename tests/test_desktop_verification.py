"""Test-first native public-only verification on the original managed worker."""
from dataclasses import replace
import json
from threading import Event
import time

import pytest

from conftest import make_pdf
from desktop.verification_bridge import VerificationBridge
from desktop.verification_worker import VerificationWorker
from hybrid_keys import HybridPublicKey
from keygen import generate_hybrid_key_pair
from vault import create_vault
from vault_format import parse_vault, encode_header, HEADER_LENGTH
from test_desktop_signing import Dialogs, data, begin, complete


class VerificationDialogs(Dialogs):
    def choose_verification_pdf(self): return None if self.pdf_cancel else self.output


@pytest.fixture
def verification(tmp_path):
    worker = VerificationWorker()
    worker.start()
    dialogs = VerificationDialogs(tmp_path)
    bridge = VerificationBridge(worker, trusted=lambda: True, dialogs=dialogs)
    data(bridge.create_vault())
    public = data(bridge.unlock_vault())['vault']
    native = bridge, worker, dialogs, public
    begin(native)
    assert complete(bridge)['state'] == 'completed'
    try:
        yield native
    finally:
        deadline = time.monotonic() + 10
        while worker.sign_busy() and time.monotonic() < deadline: time.sleep(.02)
        bridge._close()
        assert worker.shutdown()


def select(native, authenticated=False):
    bridge, _, _, public = native
    doc = data(bridge.choose_verification_pdf())['document']
    source = data(bridge.use_authenticated_vault_keys(public['vaultId'], public['sessionId'])
                  if authenticated else bridge.choose_verification_keys())['keySource']
    return doc, source


def verify(native, authenticated=False, operation='2' * 32):
    doc, source = select(native, authenticated)
    return data(native[0].verify_pdf(doc['documentId'], source['keySourceId'], operation))


def settled(bridge, operation='2' * 32):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        state = data(bridge.get_verification_state(operation))
        if state['state'] not in ('ready', 'queued', 'running'): return state
        time.sleep(.02)
    pytest.fail('Verification did not settle')


@pytest.mark.parametrize('authenticated', [False, True])
def test_actual_valid_pdf_overall_result_and_key_source_provenance(verification, authenticated):
    bridge, _, dialogs, public = verification
    before = {path: path.read_bytes() for path in (dialogs.source, dialogs.output, dialogs.vault)}
    verify(verification, authenticated)
    status = settled(bridge)
    assert status['state'] == 'valid' and status['hybridValid'] is True
    assert status['keySource']['hybridKeyId'] == public['hybridKeyId']
    assert status['keySource']['trust'] == ('vault-authenticated' if authenticated else 'unauthenticated-metadata')
    assert 'ed25519' not in status and 'falcon512' not in status
    assert all(path.read_bytes() == content for path, content in before.items())
    assert str(dialogs.vault.parent) not in json.dumps(status)


@pytest.mark.parametrize('kind', ['tampered', 'unsigned', 'truncated', 'malformed-trailer'])
def test_altered_unsigned_and_malformed_documents_are_never_valid(verification, kind):
    bridge, _, dialogs, _ = verification
    signed = dialogs.output.read_bytes()
    content = {'tampered': signed.replace(b'Native signing test', b'Native changed test'),
               'unsigned': make_pdf('unsigned'), 'truncated': signed[:-30],
               'malformed-trailer': signed.replace(b'ByteRange:', b'BadRanges:', 1)}[kind]
    assert content != signed
    dialogs.output.write_bytes(content)
    verify(verification)
    status = settled(bridge)
    assert status['state'] == 'invalid' and status['hybridValid'] is False


@pytest.mark.parametrize('wrong', ['ed25519', 'falcon', 'both'])
def test_wrong_and_mixed_public_keys_are_invalid_without_private_access(verification, wrong):
    bridge, _, dialogs, _ = verification
    original = parse_vault(dialogs.vault.read_bytes()).metadata.public_keys
    other = generate_hybrid_key_pair()
    path = dialogs.vault.parent / 'other.hvault'
    create_vault(path, other, 'disposable other vault password')
    encrypted = path.read_bytes()
    parsed = parse_vault(encrypted)
    keys = HybridPublicKey(other.public_keys.ed25519_public_key if wrong != 'falcon' else original.ed25519_public_key,
                           other.public_keys.falcon_public_key if wrong != 'ed25519' else original.falcon_public_key)
    path.write_bytes(encode_header(replace(parsed.metadata, public_keys=keys)) + encrypted[HEADER_LENGTH:])
    dialogs.vault = path
    verify(verification)
    assert settled(bridge)['state'] == 'invalid'


def test_locked_vault_and_locking_after_authenticated_selection_do_not_block_public_verification(verification, monkeypatch):
    bridge, _, dialogs, public = verification
    doc, source = select(verification, authenticated=True)
    data(bridge.lock_vault(public['vaultId'], public['sessionId']))
    def no_password(**_): pytest.fail('Public verification must not prompt for password')
    monkeypatch.setattr(dialogs, 'password', no_password)
    data(bridge.verify_pdf(doc['documentId'], source['keySourceId'], '2' * 32))
    assert settled(bridge)['state'] == 'valid'
    verify(verification, operation='3' * 32)
    assert settled(bridge, '3' * 32)['keySource']['trust'] == 'unauthenticated-metadata'
    assert bridge.use_authenticated_vault_keys(public['vaultId'], public['sessionId'])['ok'] is False


@pytest.mark.parametrize('offset', [0, 8, 34, 50, 1068])
def test_invalid_vault_header_or_profile_rejects_without_result(verification, offset):
    bridge, _, dialogs, _ = verification
    raw = bytearray(dialogs.vault.read_bytes())
    raw[offset] ^= 1
    dialogs.vault.write_bytes(raw)
    assert bridge.choose_verification_keys()['ok'] is False
    assert data(bridge.get_verification_state())['state'] == 'idle'


@pytest.mark.parametrize('which', ['pdf', 'keys'])
def test_cancelled_dialog_has_no_result(verification, monkeypatch, which):
    bridge, _, dialogs, _ = verification
    if which == 'pdf': dialogs.pdf_cancel = True
    else: monkeypatch.setattr(dialogs, 'choose_file', lambda **_: None)
    reply = data(bridge.choose_verification_pdf() if which == 'pdf' else bridge.choose_verification_keys())
    assert reply['cancelled'] is True
    assert data(bridge.get_verification_state())['hybridValid'] is None


def test_ids_are_opaque_stale_or_cross_selection_ids_reject(verification):
    bridge = verification[0]
    doc, source = select(verification)
    for args in [('0' * 32, source['keySourceId'], '2' * 32), (doc['documentId'], '0' * 32, '2' * 32),
                 ('C:/private.pdf', source['keySourceId'], '2' * 32)]:
        assert bridge.verify_pdf(*args)['ok'] is False
    assert bridge.get_verification_state('0' * 32)['ok'] is False
    assert bridge.choose_verification_pdf('path')['ok'] is False
    assert bridge.choose_verification_keys({})['ok'] is False


@pytest.mark.parametrize('target', ['pdf-change', 'pdf-replace', 'vault-change', 'vault-replace'])
def test_selection_change_is_failed_not_a_mathematical_result(verification, target):
    bridge, _, dialogs, _ = verification
    doc, source = select(verification)
    path = dialogs.output if target.startswith('pdf') else dialogs.vault
    raw = path.read_bytes()
    if target.endswith('replace'):
        replacement = path.with_suffix('.old')
        path.rename(replacement)
        path.write_bytes(raw)
    else:
        path.write_bytes(raw[:-1] + bytes([raw[-1] ^ 1]))
    data(bridge.verify_pdf(doc['documentId'], source['keySourceId'], '2' * 32))
    status = settled(bridge)
    assert status['state'] == 'failed' and status['hybridValid'] is None


@pytest.mark.parametrize('fault', ['raise', 'false-tuple', 'integer-true', 'short-tuple'])
def test_verifier_exceptions_and_contract_errors_never_claim_valid(verification, monkeypatch, fault):
    import desktop.verification_service as service
    def result(*_):
        if fault == 'raise': raise RuntimeError('secret path private password')
        return {'false-tuple': (False,) + (0,) * 10, 'integer-true': (1,) + (0,) * 10,
                'short-tuple': (True,)}[fault]
    monkeypatch.setattr(service, 'verify_bytes', result)
    verify(verification)
    status = settled(verification[0])
    assert status['state'] == ('invalid' if fault == 'false-tuple' else 'failed')
    assert status['hybridValid'] is (False if fault == 'false-tuple' else None)
    assert 'secret path' not in json.dumps(status)


def test_duplicate_job_conflicts_readonly_snapshot_and_shutdown(verification, monkeypatch):
    import desktop.verification_service as service
    bridge, worker, dialogs, public = verification
    real = service.verify_bytes
    entered, release = Event(), Event()
    calls = []
    def blocked(*args):
        calls.append(1)
        with pytest.raises(PermissionError): dialogs.output.write_bytes(b'changed')
        with pytest.raises(PermissionError): dialogs.output.unlink()
        entered.set()
        assert release.wait(9)
        return real(*args)
    monkeypatch.setattr(service, 'verify_bytes', blocked)
    job = verify(verification)
    try:
        assert entered.wait(2)
        args = (job['document']['documentId'], job['keySource']['keySourceId'], '2' * 32)
        assert data(bridge.verify_pdf(*args))['operationId'] == '2' * 32
        assert bridge.verify_pdf(*args[:2], '3' * 32)['error']['code'] == 'BUSY'
        assert bridge.choose_pdf()['error']['code'] == 'BUSY'
        assert bridge.choose_verification_keys()['error']['code'] == 'BUSY'
        assert bridge.lock_vault(public['vaultId'], public['sessionId'])['error']['code'] == 'BUSY'
        assert worker.shutdown(timeout=.01) is False
    finally: release.set()
    assert settled(bridge)['state'] == 'valid' and calls == [1]


def test_long_verification_survives_five_second_request_deadline(verification, monkeypatch):
    import desktop.verification_service as service
    real = service.verify_bytes
    def slow(*args):
        time.sleep(5.2)
        return real(*args)
    monkeypatch.setattr(service, 'verify_bytes', slow)
    verify(verification)  # Ignore admission reply; reconcile without resubmission.
    assert settled(verification[0])['state'] == 'valid'


def test_public_only_does_not_authenticate_ciphertext_or_invoke_unlock(verification, monkeypatch):
    import vault_crypto
    bridge, _, dialogs, public = verification
    data(bridge.lock_vault(public['vaultId'], public['sessionId']))
    raw = bytearray(dialogs.vault.read_bytes())
    raw[-1] ^= 1  # Public header remains structurally sound, AEAD tag is damaged.
    dialogs.vault.write_bytes(raw)
    def forbidden(*args, **kwargs): pytest.fail('Public metadata must never unseal private keys')
    monkeypatch.setattr(vault_crypto, 'unseal_key_pair', forbidden)
    verify(verification)
    status = settled(bridge)
    assert status['state'] == 'valid'
    assert status['keySource']['trust'] == 'unauthenticated-metadata'


@pytest.mark.parametrize('kind', ['bad-header', 'oversized', 'hardlink'])
def test_invalid_or_unsafe_pdf_selection_produces_no_result(verification, kind):
    bridge, _, dialogs, _ = verification
    if kind == 'bad-header': dialogs.output.write_bytes(b'not a PDF')
    if kind == 'oversized':
        with dialogs.output.open('r+b') as stream: stream.truncate(50 * 1024 * 1024 + 65537)
    if kind == 'hardlink': (dialogs.output.parent / 'alias.pdf').hardlink_to(dialogs.output)
    assert bridge.choose_verification_pdf()['ok'] is False
    assert data(bridge.get_verification_state())['hybridValid'] is None


def test_lost_admission_reply_reconciles_one_readonly_job(verification, monkeypatch):
    bridge, worker, _, _ = verification
    doc, source = select(verification)
    enqueue = worker.enqueue_verification
    def lost(*args):
        enqueue(*args)
        raise OSError('private transport diagnostics')
    monkeypatch.setattr(worker, 'enqueue_verification', lost)
    assert bridge.verify_pdf(doc['documentId'], source['keySourceId'], '2' * 32)['ok'] is False
    assert settled(bridge)['state'] == 'valid'


def test_active_signing_blocks_verification_admission(verification, monkeypatch):
    import desktop.signing_service as service
    bridge, _, _, _ = verification
    original = service.sign_vault_document
    entered, release = Event(), Event()
    def blocked(*args):
        entered.set()
        assert release.wait(8)
        return original(*args)
    monkeypatch.setattr(service, 'sign_vault_document', blocked)
    begin(verification, operation='4' * 32)
    try:
        assert entered.wait(2)
        assert bridge.choose_verification_pdf()['error']['code'] == 'BUSY'
        assert bridge.verify_pdf('d' * 32, 'e' * 32, '5' * 32)['error']['code'] == 'BUSY'
    finally: release.set()
    assert complete(bridge, '4' * 32)['state'] == 'completed'
