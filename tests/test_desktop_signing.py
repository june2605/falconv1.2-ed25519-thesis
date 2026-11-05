"""Actual native orchestration, one owner thread and transactional PDF core."""
import json
from pathlib import Path
from threading import Event, current_thread
import time

import pytest

from conftest import make_pdf
from desktop.signing_bridge import SigningBridge
from desktop.signing_worker import SigningWorker
from desktop.pdf_io import output_choice
from desktop.worker import WorkerError
from verify import verify_file_with_public_keys


class Dialogs:
    def __init__(self, root):
        self.vault = root / 'local.hvault'
        self.source = root / 'original.pdf'
        self.source.write_bytes(make_pdf('Native signing test'))
        self.output = root / 'signed.pdf'
        self.pdf_cancel = self.output_cancel = False
        self.saves = 0
    def choose_file(self, *, creating): return self.vault
    def password(self, *, creating): return 'disposable native signing password'
    def choose_pdf(self): return None if self.pdf_cancel else self.source
    def choose_pdf_output(self, suggested_name):
        self.saves += 1
        return None if self.output_cancel else output_choice(self.output)
    def close(self): pass


def data(reply):
    assert reply['ok'] is True, reply
    return reply['data']


@pytest.fixture
def native(tmp_path):
    worker = SigningWorker()
    worker.start()
    dialogs = Dialogs(tmp_path)
    bridge = SigningBridge(worker, trusted=lambda: True, dialogs=dialogs)
    data(bridge.create_vault())
    public = data(bridge.unlock_vault())['vault']
    try:
        yield bridge, worker, dialogs, public
    finally:
        deadline = time.monotonic() + 10
        while worker.sign_busy() and time.monotonic() < deadline: time.sleep(.02)
        bridge._close()
        assert worker.shutdown()


def begin(native, operation='1' * 32):
    bridge, _, _, public = native
    document = data(bridge.choose_pdf())['document']
    return data(bridge.sign_pdf(document['documentId'], public['vaultId'], public['sessionId'], operation))


def complete(bridge, operation='1' * 32):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        status = data(bridge.get_signing_state(operation))
        if status['state'] not in ('ready', 'queued', 'running'): return status
        time.sleep(.02)
    pytest.fail('Native signing did not settle')


def test_real_signing_verification_original_keys_and_unchanged_sources(native):
    bridge, _, dialogs, public = native
    source, vault = dialogs.source.read_bytes(), dialogs.vault.read_bytes()
    begin(native)
    status = complete(bridge)
    assert status['state'] == 'completed' and status['selfVerified'] is True
    assert status['hybridKeyId'] == public['hybridKeyId']
    assert status['outputName'] == 'signed.pdf'
    assert verify_file_with_public_keys(dialogs.output, bytes.fromhex(public['ed25519PublicKey']),
                                        bytes.fromhex(public['falconPublicKey']))[0] is True
    assert dialogs.source.read_bytes() == source and dialogs.vault.read_bytes() == vault
    assert dialogs.vault.stat().st_size == 2416
    encoded = json.dumps(status)
    assert str(dialogs.output.parent) not in encoded and 'password' not in encoded and 'private' not in encoded


@pytest.mark.parametrize('locked', [True, False])
def test_locked_or_stale_session_rejected_without_output(native, locked):
    bridge, _, dialogs, public = native
    document = data(bridge.choose_pdf())['document']
    if locked: data(bridge.lock_vault(public['vaultId'], public['sessionId']))
    session = public['sessionId'] if locked else '0' * 32
    reply = bridge.sign_pdf(document['documentId'], public['vaultId'], session, '1' * 32)
    assert reply['ok'] is False
    assert not dialogs.output.exists() and dialogs.saves == 0


def test_wrong_document_or_operation_ids_are_not_paths(native):
    bridge, _, dialogs, public = native
    assert bridge.sign_pdf('0' * 32, public['vaultId'], public['sessionId'], '1' * 32)['ok'] is False
    for args in [(str(dialogs.source),), ({'path': str(dialogs.source)},), ('bad-id',)]:
        assert bridge.get_signing_state(*args)['error']['code'] == 'INVALID_REQUEST'
    assert bridge.choose_pdf(str(dialogs.source))['error']['code'] == 'INVALID_REQUEST'
    assert not dialogs.output.exists()


@pytest.mark.parametrize('content', [b'not pdf', b'%PDF-1.4\ntruncated', b'%PDF-9.9\n%%EOF\n'])
def test_invalid_pdf_rejected(native, content):
    bridge, _, dialogs, _ = native
    dialogs.source.write_bytes(content)
    assert bridge.choose_pdf()['ok'] is False
    assert not dialogs.output.exists()


def test_already_signed_input_and_changed_selection_reject(native):
    bridge, _, dialogs, public = native
    begin(native)
    assert complete(bridge)['state'] == 'completed'
    dialogs.source = dialogs.output
    assert bridge.choose_pdf()['ok'] is False
    dialogs.source = dialogs.output.parent / 'fresh.pdf'
    dialogs.source.write_bytes(make_pdf('first'))
    document = data(bridge.choose_pdf())['document']
    dialogs.source.write_bytes(make_pdf('changed'))
    assert bridge.sign_pdf(document['documentId'], public['vaultId'], public['sessionId'], '2' * 32)['ok'] is False


@pytest.mark.parametrize('which', ['pdf', 'output'])
def test_cancelled_native_dialog_has_no_signing_effect(native, which):
    bridge, _, dialogs, _ = native
    setattr(dialogs, which + '_cancel', True)
    reply = data(bridge.choose_pdf()) if which == 'pdf' else begin(native)
    assert reply.get('cancelled') is True or reply.get('state') == 'cancelled'
    assert not dialogs.output.exists()


@pytest.mark.parametrize('target', ['source', 'vault', 'sidecar', 'other-vault'])
def test_protected_destinations_preserved(native, target):
    from vault_io import lock_file_path
    bridge, _, dialogs, _ = native
    paths = {'source': dialogs.source, 'vault': dialogs.vault, 'sidecar': lock_file_path(dialogs.vault)}
    if target == 'other-vault':
        other = dialogs.vault.parent / 'other.pdf'
        other.write_bytes(dialogs.vault.read_bytes())
        paths[target] = other
    dialogs.output = paths[target]
    before = dialogs.output.read_bytes()
    begin(native)
    assert complete(bridge)['state'] == 'failed'
    assert dialogs.output.read_bytes() == before


def test_existing_pdf_is_replaced_only_after_native_approval(native):
    bridge, _, dialogs, public = native
    dialogs.output.write_bytes(make_pdf('old destination'))
    begin(native)
    assert complete(bridge)['state'] == 'completed'
    assert verify_file_with_public_keys(dialogs.output, bytes.fromhex(public['ed25519PublicKey']),
                                        bytes.fromhex(public['falconPublicKey']))[0] is True


def test_core_failure_never_reports_success_and_preserves_destination(native, monkeypatch):
    import desktop.signing_service as service
    bridge, _, dialogs, _ = native
    dialogs.output.write_bytes(make_pdf('preserve'))
    before = dialogs.output.read_bytes()
    def fail(*_): raise OSError('secret path and credential diagnostics')
    monkeypatch.setattr(service, 'sign_vault_document', fail)
    begin(native)
    status = complete(bridge)
    assert status['state'] == 'outcome-uncertain' and not status['selfVerified']
    assert dialogs.output.read_bytes() == before
    assert 'secret' not in json.dumps(status)


def test_duplicate_jobs_conflicts_owner_thread_and_shutdown(native, monkeypatch):
    import desktop.signing_service as service
    bridge, worker, dialogs, public = native
    entered, release = Event(), Event()
    original, owners = service.sign_vault_document, []
    def blocking(*args):
        owners.append(current_thread())
        entered.set()
        assert release.wait(8)
        return original(*args)
    monkeypatch.setattr(service, 'sign_vault_document', blocking)
    job = begin(native)
    assert entered.wait(1)
    assert data(bridge.sign_pdf(job['document']['documentId'], public['vaultId'], public['sessionId'], '1' * 32))['operationId'] == '1' * 32
    assert bridge.lock_vault(public['vaultId'], public['sessionId'])['error']['code'] == 'BUSY'
    assert bridge.choose_pdf()['error']['code'] == 'BUSY'
    assert worker.shutdown(timeout=.01) is False
    assert worker.sign_busy() and dialogs.saves == 1
    release.set()
    assert complete(bridge)['state'] == 'completed'
    assert owners == [worker._thread]


def test_long_running_job_survives_metadata_deadline_and_communication_loss(native, monkeypatch):
    import desktop.signing_service as service
    bridge, _, dialogs, _ = native
    original = service.sign_vault_document
    def slow(*args):
        time.sleep(5.2)
        return original(*args)
    monkeypatch.setattr(service, 'sign_vault_document', slow)
    begin(native)  # Ignore this response as if the caller lost it.
    time.sleep(.1)
    assert data(bridge.get_signing_state())['state'] in ('queued', 'running')
    assert complete(bridge)['state'] == 'completed' and dialogs.output.exists()


@pytest.mark.parametrize('fault', ['fsync', 'verification', 'replace'])
def test_transaction_faults_preserve_destination_and_clean_owned_stages(native, monkeypatch, fault):
    import sign
    import signing_io
    bridge, _, dialogs, _ = native
    dialogs.output.write_bytes(make_pdf('preserved destination'))
    before = dialogs.output.read_bytes()
    def denied(*args): raise PermissionError('private filesystem diagnostic')
    if fault == 'verification':
        monkeypatch.setattr(sign, 'verify_file_with_public_keys', lambda *_: (False,) + (0,) * 10)
    else:
        monkeypatch.setattr(signing_io.os, fault, denied)
    begin(native)
    status = complete(bridge)
    assert status['state'] == 'outcome-uncertain' and status['selfVerified'] is False
    assert dialogs.output.read_bytes() == before
    assert not list(dialogs.output.parent.glob('.esign-*'))
    assert 'private filesystem' not in json.dumps(status)


def test_postpublication_verifier_failure_never_claims_completed(native, monkeypatch):
    import desktop.signing_service as service
    bridge, _, dialogs, _ = native
    monkeypatch.setattr(service, 'verify_bytes', lambda *_: (False,) + (0,) * 10)
    begin(native)
    status = complete(bridge)
    assert status['state'] == 'outcome-uncertain' and status['selfVerified'] is False
    assert dialogs.output.exists()  # Publication may have succeeded; no false cancellation.


def test_native_approval_revision_change_is_rejected(native, monkeypatch):
    bridge, _, dialogs, _ = native
    dialogs.output.write_bytes(make_pdf('approved'))
    def choose(_):
        approved = output_choice(dialogs.output)
        dialogs.output.write_bytes(make_pdf('changed since approval'))
        return approved
    monkeypatch.setattr(dialogs, 'choose_pdf_output', choose)
    begin(native)
    assert complete(bridge)['state'] == 'failed'
    assert dialogs.output.read_bytes() == make_pdf('changed since approval')


def test_source_is_held_against_windows_write_or_delete_during_sign(native, monkeypatch):
    import desktop.signing_service as service
    bridge, _, dialogs, _ = native
    original = service.sign_vault_document
    def checked(*args):
        with pytest.raises(PermissionError): dialogs.source.write_bytes(b'overwrite')
        with pytest.raises(PermissionError): dialogs.source.unlink()
        return original(*args)
    monkeypatch.setattr(service, 'sign_vault_document', checked)
    begin(native)
    assert complete(bridge)['state'] == 'completed'


def test_hardlink_output_alias_rejected_without_source_changes(native):
    bridge, _, dialogs, public = native
    document = data(bridge.choose_pdf())['document']
    dialogs.output.hardlink_to(dialogs.source)
    before = dialogs.source.read_bytes()
    reply = bridge.sign_pdf(document['documentId'], public['vaultId'], public['sessionId'], '1' * 32)
    assert reply['ok'] is False and dialogs.saves == 0
    assert dialogs.source.read_bytes() == before == dialogs.output.read_bytes()


def test_reply_failure_after_enqueue_does_not_cancel_or_duplicate_job(native, monkeypatch):
    bridge, worker, dialogs, _ = native
    original = worker.enqueue
    def lost(choice):
        original(choice)
        raise RuntimeError('transport failed after admission')
    monkeypatch.setattr(worker, 'enqueue', lost)
    document = data(bridge.choose_pdf())['document']
    public = native[3]
    reply = bridge.sign_pdf(document['documentId'], public['vaultId'], public['sessionId'], '1' * 32)
    assert reply['ok'] is False
    assert complete(bridge)['state'] == 'completed'
    assert dialogs.output.exists() and dialogs.saves == 1

