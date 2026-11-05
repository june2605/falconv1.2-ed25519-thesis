"""Interactive local harness. No password/key argument or environment mode."""

import getpass
import sys
import warnings

from vault import unlock_vault
from vault_io import VaultIOError, VaultVerificationError
from vault_signing import sign_vault_document
from verify import verify_file_with_public_keys


def _prompt_password():
    if not sys.stdin.isatty():
        raise VaultIOError()
    with warnings.catch_warnings():
        # getpass otherwise falls back to potentially echoed stdin input.
        warnings.simplefilter("error", getpass.GetPassWarning)
        return getpass.getpass("Vault password: ")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        if argv in (["--help"], ["-h"]):
            print("Local vault signing harness. Run without arguments; all paths and the password are prompted interactively.")
            return 0
        print("This harness accepts interactive input only; no argument values are processed.", file=sys.stderr)
        return 2
    try:
        path = input("Encrypted vault path: ")
        password = _prompt_password()
        with unlock_vault(path, password) as handle:
            del password  # Drop this reference; no zeroization guarantee.
            source = input("Unsigned PDF path: ")
            destination = input("Signed PDF output path: ")
            sign_vault_document(handle, source, destination)
            public = handle.metadata.public_keys
            verified = verify_file_with_public_keys(destination, public.ed25519_public_key,
                                                   public.falcon_public_key)
            if verified[0] is not True:
                raise VaultVerificationError()
        print("Signed PDF verified with both Ed25519 and Falcon-512.")
        return 0
    except KeyboardInterrupt:
        print("Cancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        print("Vault signing failed or completed output could not be confirmed. Inspect the destination before retrying.",
              file=sys.stderr)
        if any("cleanup" in note.lower() for note in getattr(error, "__notes__", ())):
            print("Temporary artifact cleanup failed; manual review may be required.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
