import pytest

from desktop.dialogs import NativeDialogs, validate_password
from vault_format import VaultPasswordError


@pytest.mark.parametrize("password", ["", "short", "\ud800", "a" * 1025, "界" * 342])
def test_native_creation_reuses_exact_password_policy(password):
    with pytest.raises(VaultPasswordError):
        validate_password(password, password, creating=True)


def test_native_password_confirmation_and_unlock_compatibility():
    with pytest.raises(VaultPasswordError):
        validate_password("valid vault password 123", "different password", creating=True)
    assert validate_password("valid vault password 123", "valid vault password 123", creating=True) is None
    assert validate_password("x", None, creating=False) is None


def test_closed_dialog_provider_never_schedules_gui_calls():
    class Window:
        @property
        def native(self):
            pytest.fail("closed provider accessed GUI")
    dialogs = NativeDialogs(Window())
    # Closing may attempt a nonblocking native cancellation; subsequent calls
    # must not touch the disposed window at all.
    dialogs._closed.set()
    assert dialogs.choose_file(creating=True) is None
    assert dialogs.password(creating=False) is None

