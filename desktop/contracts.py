"""Versioned public JSON contract; never return exception text or native objects."""
from typing import Literal, TypedDict

PROTOCOL_VERSION = 1
APP_NAME = "HybridSign"
APP_VERSION = "0.1.0"
APP_INFO = {"applicationName": APP_NAME, "applicationVersion": APP_VERSION,
            "runtime": "pywebview-edgechromium", "desktopStatus": "connected"}
CAPABILITIES = {"nativeShell": True, "vaultOperations": False, "pdfSigning": False,
                "pdfVerification": False, "accountRegistry": False}
METHODS = frozenset({"get_app_info", "get_capabilities"})
VAULT_METHODS = frozenset({"get_vault_state", "create_vault", "unlock_vault", "lock_vault"})
METHODS = METHODS | VAULT_METHODS
METHODS = METHODS | frozenset({'choose_pdf', 'sign_pdf', 'get_signing_state'})
VAULT_CAPABILITIES = {**CAPABILITIES, "vaultOperations": True, "vaultCreate": True,
                      "vaultUnlock": True, "vaultLock": True, "vaultPasswordChange": False,
                      "vaultBackupRestore": False}
SIGNING_CAPABILITIES = {**VAULT_CAPABILITIES, 'pdfSigning': True}
VERIFICATION_CAPABILITIES = {**SIGNING_CAPABILITIES, 'pdfVerification': True}
METHODS = METHODS | frozenset({'choose_verification_pdf', 'choose_verification_keys',
    'use_authenticated_vault_keys', 'verify_pdf', 'get_verification_state'})
ERRORS = {"INVALID_REQUEST": "Invalid desktop request.",
          "UNAVAILABLE": "Desktop connection is unavailable.",
          "BUSY": "Wait for the current operation to finish.",
          "TIMEOUT": "Desktop request timed out.",
          "INTERNAL_ERROR": "Desktop request could not complete."}
ERRORS.update({"CANCELLED": "Operation cancelled.", "STALE_SESSION": "Vault session is no longer valid.",
               "STALE_SELECTION": "Selected vault is no longer available. Select it again.",
               "VAULT_ACTIVE": "Lock the current vault before opening or creating another.",
               "vault.unlock": "Incorrect password or damaged vault.",
               "vault.password": "Use 15 or more characters for a new password, at most 1024 UTF-8 bytes.",
               "vault.format": "The selected file is not a supported encrypted vault.",
               "vault.profile": "The selected vault profile is not supported.",
               "vault.key_material": "Vault key validation failed.",
               "vault.backend": "The required cryptographic backend is unavailable.",
               "vault.busy": "Another vault encryption operation is running.",
               "vault.exists": "Destination already exists. Choose a new filename.",
               "vault.path": "Select a safe local vault path without links or aliases.",
               "vault.security": "Vault requires a fixed local NTFS drive and the approved Windows permissions.",
               "vault.permission": "Windows denied vault access. Permissions were not changed.",
               "vault.io": "Vault operation failed. Inspect the selected location before retrying; publication or cleanup may have completed.",
               "vault.file_locked": "Another operation is using the vault. Wait for it to finish.",
               "vault.conflict": "The vault changed and was locked. Select it again to unlock it.",
               "vault.verification": "Encrypted vault validation failed.",
               "vault.locked": "Vault is locked.", "vault.handle": "Vault session is not valid."})
ERRORS.update({'PDF_INVALID': 'Choose a PDF of 50 MiB or less that HybridSign can read.',
               'STALE_DOCUMENT': 'Select the PDF again.', 'DOCUMENT_CHANGED': 'Selected PDF changed. Select it again.',
               'STALE_OPERATION': 'This signing job is unavailable in the current session.',
               'SIGN_PATH': 'The selected save location is unsafe or has changed. Choose another location.',
               'SIGN_FAILED': 'Signing did not complete. No new signed output was confirmed.',
               'SIGN_UNCERTAIN': 'A signed PDF may already exist. Check the selected save location before trying again.'})
ERRORS.update({'STALE_KEY_SOURCE': 'Choose the public-key source again.',
               'VERIFY_FAILED': 'Verification could not complete. There is no signature result.',
               'VERIFY_IO': 'The selected verification file could not be read safely. Check access and select it again.',
               'VERIFY_UNCERTAIN': 'Check the verification status before submitting another request.'})


class PublicError(TypedDict):
    code: str
    message: str


class AppInfo(TypedDict):
    applicationName: Literal["HybridSign"]
    applicationVersion: Literal["0.1.0"]
    runtime: Literal["pywebview-edgechromium"]
    desktopStatus: Literal["connected"]


class Capabilities(TypedDict):
    nativeShell: Literal[True]
    vaultOperations: Literal[False]
    pdfSigning: Literal[False]
    pdfVerification: Literal[False]
    accountRegistry: Literal[False]


class VaultCapabilities(TypedDict):
    nativeShell: Literal[True]
    vaultOperations: Literal[True]
    vaultCreate: Literal[True]
    vaultUnlock: Literal[True]
    vaultLock: Literal[True]
    vaultPasswordChange: Literal[False]
    vaultBackupRestore: Literal[False]
    pdfSigning: Literal[False]
    pdfVerification: Literal[False]
    accountRegistry: Literal[False]


class PublicAlgorithms(TypedDict):
    ed25519: Literal["Ed25519"]
    falcon512: Literal["Falcon-512"]


class PublicVault(TypedDict):
    vaultId: str
    sessionId: str | None
    displayName: str
    state: Literal["locked", "unlocked"]
    hybridKeyId: str
    ed25519PublicKey: str
    falconPublicKey: str
    formatVersion: Literal[1]
    algorithms: PublicAlgorithms


class VaultResult(TypedDict):
    vault: PublicVault | None
    cancelled: bool
    selectionId: str | None
    operation: Literal["idle", "reading-state", "selecting-file", "waiting-password", "unlocking", "creating", "locking"]


class SigningCapabilities(TypedDict):
    nativeShell: Literal[True]
    vaultOperations: Literal[True]
    vaultCreate: Literal[True]
    vaultUnlock: Literal[True]
    vaultLock: Literal[True]
    vaultPasswordChange: Literal[False]
    vaultBackupRestore: Literal[False]
    pdfSigning: Literal[True]
    pdfVerification: Literal[False]
    accountRegistry: Literal[False]


class PublicDocument(TypedDict):
    documentId: str
    displayName: str
    sizeBytes: int


class VerificationCapabilities(TypedDict):
    nativeShell: Literal[True]
    vaultOperations: Literal[True]
    vaultCreate: Literal[True]
    vaultUnlock: Literal[True]
    vaultLock: Literal[True]
    vaultPasswordChange: Literal[False]
    vaultBackupRestore: Literal[False]
    pdfSigning: Literal[True]
    pdfVerification: Literal[True]
    accountRegistry: Literal[False]


class PublicKeySource(TypedDict):
    keySourceId: str
    displayName: str
    hybridKeyId: str
    trust: Literal['vault-authenticated', 'unauthenticated-metadata']


class KeySourceSelection(TypedDict):
    keySource: PublicKeySource | None
    cancelled: bool


class VerificationResult(TypedDict):
    operationId: str | None
    state: Literal['idle', 'ready', 'queued', 'running', 'valid', 'invalid', 'failed']
    document: PublicDocument | None
    keySource: PublicKeySource | None
    hybridValid: bool | None
    errorCode: str | None


class PdfSelection(TypedDict):
    document: PublicDocument | None
    cancelled: bool


class SigningResult(TypedDict):
    operationId: str | None
    state: Literal['idle', 'ready', 'queued', 'running', 'completed', 'failed', 'outcome-uncertain', 'cancelled']
    document: PublicDocument | None
    outputName: str | None
    hybridKeyId: str | None
    selfVerified: bool
    errorCode: str | None


PublicData = AppInfo | Capabilities | VaultCapabilities | SigningCapabilities | VerificationCapabilities | VaultResult | PdfSelection | SigningResult | KeySourceSelection | VerificationResult


class SuccessReply(TypedDict):
    ok: Literal[True]
    protocolVersion: Literal[1]
    data: PublicData


class ErrorReply(TypedDict):
    ok: Literal[False]
    protocolVersion: Literal[1]
    error: PublicError


def success(data: PublicData) -> SuccessReply:
    return {"ok": True, "protocolVersion": PROTOCOL_VERSION, "data": dict(data)}


def failure(code: str) -> ErrorReply:
    code = code if code in ERRORS else "INTERNAL_ERROR"
    return {"ok": False, "protocolVersion": PROTOCOL_VERSION,
            "error": {"code": code, "message": ERRORS[code]}}
