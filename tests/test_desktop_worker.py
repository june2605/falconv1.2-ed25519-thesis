"""Non-sensitive worker lifecycle; no vault or cryptographic imports."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread
import time

import pytest

from desktop.worker import Command, Worker, WorkerError, WorkerState


def test_lifecycle_and_single_owned_thread(monkeypatch):
    worker = Worker()
    assert worker.state is WorkerState.NEW
    seen = []
    original = worker._handle
    def record(command, sequence):
        seen.append(current_thread())
        return original(command, sequence)
    monkeypatch.setattr(worker, "_handle", record)
    worker.start()
    try:
        worker.start()  # Idempotent while running, never a second owner.
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(lambda _: worker.request(Command.STATUS), range(8)))
        assert sorted(r["sequence"] for r in results) == list(range(1, 9))
        assert len(set(seen)) == 1 and seen[0] is not current_thread()
    finally:
        assert worker.shutdown()
    assert worker.state is WorkerState.STOPPED
    assert not seen[0].is_alive()
    assert worker.shutdown()
    with pytest.raises(WorkerError):
        worker.start()


@pytest.mark.parametrize("command", ["status", "unlock", "__class__", lambda: None, {}, None, True])
def test_no_generic_worker_dispatch(command):
    worker = Worker()
    worker.start()
    try:
        with pytest.raises(WorkerError, match="INVALID_REQUEST"):
            worker.request(command)
    finally:
        worker.shutdown()


@pytest.mark.parametrize("timeout", [0, -1, True, float("nan"), float("inf"), 99, "1"])
def test_request_timeouts_are_bounded(timeout):
    worker = Worker()
    worker.start()
    try:
        with pytest.raises(WorkerError, match="INVALID_REQUEST"):
            worker.request(Command.STATUS, timeout=timeout)
    finally:
        worker.shutdown()


def test_requests_before_start_and_after_shutdown_rejected():
    worker = Worker()
    for _ in range(2):
        with pytest.raises(WorkerError, match="UNAVAILABLE"):
            worker.request(Command.STATUS)
        worker.shutdown()


def test_faults_are_sanitized_and_worker_remains_usable(monkeypatch):
    worker = Worker()
    worker.start()
    original = worker._handle
    def fail(*_):
        raise OSError("C:/private/password-secret.key")
    try:
        monkeypatch.setattr(worker, "_handle", fail)
        with pytest.raises(WorkerError, match="INTERNAL_ERROR") as caught:
            worker.request(Command.STATUS)
        assert "private" not in str(caught.value)
        monkeypatch.setattr(worker, "_handle", original)
        assert worker.request(Command.STATUS)["state"] == "running"
    finally:
        worker.shutdown()


def test_queue_order_expiry_and_shutdown_bound(monkeypatch):
    worker = Worker(capacity=1)
    entered, release = Event(), Event()
    original = worker._handle
    def block(command, sequence):
        entered.set()
        release.wait(3)
        return original(command, sequence)
    monkeypatch.setattr(worker, "_handle", block)
    worker.start()
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(worker.request, Command.STATUS)
        assert entered.wait(1)
        second = pool.submit(worker.request, Command.STATUS, timeout=0.05)
        deadline = time.monotonic() + 1
        while worker._queue.empty() and time.monotonic() < deadline:
            time.sleep(0.001)
        with pytest.raises(WorkerError, match="BUSY"):
            worker.request(Command.STATUS)
        with pytest.raises(WorkerError, match="TIMEOUT"):
            second.result()
        assert not worker.shutdown(timeout=0.01)
        assert worker.state is WorkerState.STOPPING
        release.set()
        assert first.result()["sequence"] == 1
    assert worker.shutdown()


def test_fifo_requests_and_startup_failure(monkeypatch):
    worker = Worker()
    worker.start()
    try:
        assert [worker.request(Command.STATUS)["sequence"] for _ in range(5)] == list(range(1, 6))
    finally:
        worker.shutdown()
    broken = Worker()
    monkeypatch.setattr(broken, "_run", lambda: None)
    with pytest.raises(WorkerError, match="TIMEOUT"):
        broken.start(timeout=0.02)
    assert broken.shutdown()
