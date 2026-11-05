"""CLI secret-channel tests plus real vault/sign/verify operations with prompt doubles."""

import getpass
import importlib
import subprocess
import sys
from types import SimpleNamespace

import pytest

import keygen
import vault
from verify import verify_bytes


PASSWORD = "disposable local CLI password only"


@pytest.fixture
def cli():
    return importlib.import_module("vault_signing_cli")


@pytest.fixture
def saved(tmp_path):
    pair = keygen.generate_hybrid_key_pair()
    path = tmp_path / "cli.hvault"
    vault.create_vault(path, pair, PASSWORD)
    return SimpleNamespace(pair=pair, path=path)


def prompts(cli, saved, pdf_path, output, monkeypatch, *, password=PASSWORD):
    inputs = iter([str(saved.path), str(pdf_path), str(output)])
    handles = []
    unlock = cli.unlock_vault

    def unlocked(*args):
        handle = unlock(*args)
        handles.append(handle)
        return handle

    monkeypatch.setattr("builtins.input", lambda *a: next(inputs))
    monkeypatch.setattr(cli, "_prompt_password", lambda: password)
    monkeypatch.setattr(cli, "unlock_vault", unlocked)
    return handles


def test_cli_real_valid_flow_locks_handle(cli, saved, pdf_path, tmp_path, monkeypatch, capsys):
    output = tmp_path / "cli-signed.pdf"
    handles = prompts(cli, saved, pdf_path, output, monkeypatch)
    assert cli.main([]) == 0
    assert len(handles) == 1 and handles[0].is_locked
    public = saved.pair.public_keys
    assert verify_bytes(output.read_bytes(), public.ed25519_public_key, public.falcon_public_key)[0] is True
    captured = capsys.readouterr()
    assert "verified" in captured.out.lower()
    assert PASSWORD not in captured.out + captured.err
    assert not list(tmp_path.glob(".esign-*"))


@pytest.mark.parametrize("fault", ["wrong_password", "signing", "verification", "verification_exception", "input", "success_output"])
def test_cli_failures_are_sanitized_and_lock_handles(cli, saved, pdf_path, tmp_path, monkeypatch, capsys, fault):
    output = tmp_path / "preserved.pdf"
    output.write_bytes(b"existing destination")
    handles = prompts(cli, saved, pdf_path, output, monkeypatch,
                      password="wrong password" if fault == "wrong_password" else PASSWORD)

    def fail(*a, **kw):
        raise RuntimeError("SENSITIVE-CLI-INTERNAL")

    if fault == "signing":
        monkeypatch.setattr(cli, "sign_vault_document", fail)
    elif fault == "verification":
        monkeypatch.setattr(cli, "verify_file_with_public_keys", lambda *a: (False,) + (0,) * 10)
    elif fault == "verification_exception":
        monkeypatch.setattr(cli, "verify_file_with_public_keys", fail)
    elif fault == "input":
        def missing(*a):
            if handles:
                raise EOFError()
            return str(saved.path)
        monkeypatch.setattr("builtins.input", missing)
    elif fault == "success_output":
        real_print = print

        def output_failure(*a, **kw):
            if "verified" in str(a).lower():
                fail()
            return real_print(*a, **kw)
        monkeypatch.setattr("builtins.print", output_failure)
    assert cli.main([]) != 0
    assert all(handle.is_locked for handle in handles)
    if fault in ("wrong_password", "signing", "input"):
        assert output.read_bytes() == b"existing destination"
    captured = capsys.readouterr()
    assert PASSWORD not in captured.out + captured.err
    assert "SENSITIVE-CLI-INTERNAL" not in captured.out + captured.err
    assert "verified" not in captured.out.lower()
    assert not list(tmp_path.glob(".esign-*"))


def test_cli_rejects_all_secret_arguments_without_echo(cli, monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda *a: pytest.fail("Argument mode requested input"))
    assert cli.main(["--password", "PRIVATE-ARGUMENT-MARKER"]) != 0
    captured = capsys.readouterr()
    assert "PRIVATE-ARGUMENT-MARKER" not in captured.out + captured.err


def test_password_prompt_uses_getpass_without_echo(cli, monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))

    def secret_prompt(prompt):
        calls.append(prompt)
        return PASSWORD

    monkeypatch.setattr(cli.getpass, "getpass", secret_prompt)
    assert cli._prompt_password() == PASSWORD
    assert len(calls) == 1
    assert capsys.readouterr() == ("", "")


def test_password_prompt_rejects_getpass_echo_fallback(cli, monkeypatch):
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: True))
    monkeypatch.setattr(cli.getpass, "getpass", getpass.fallback_getpass)
    monkeypatch.setattr(cli.getpass, "_raw_input", lambda *a, **kw: pytest.fail("Echo-capable input was read"))
    with pytest.raises(getpass.GetPassWarning):
        cli._prompt_password()


def test_cli_noninteractive_password_input_fails_closed(cli, saved, tmp_path):
    result = subprocess.run([sys.executable, "-B", "-m", "vault_signing_cli"],
                            input=str(saved.path) + "\n", text=True, capture_output=True, timeout=15)
    assert result.returncode != 0
    assert "verified" not in result.stdout.lower()
    assert PASSWORD not in result.stdout + result.stderr
