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
ERRORS = {"INVALID_REQUEST": "Invalid desktop request.",
          "UNAVAILABLE": "Desktop connection is unavailable.",
          "BUSY": "Desktop worker is busy.",
          "TIMEOUT": "Desktop request timed out.",
          "INTERNAL_ERROR": "Desktop request could not complete."}


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


class SuccessReply(TypedDict):
    ok: Literal[True]
    protocolVersion: Literal[1]
    data: AppInfo | Capabilities


class ErrorReply(TypedDict):
    ok: Literal[False]
    protocolVersion: Literal[1]
    error: PublicError


def success(data: AppInfo | Capabilities) -> SuccessReply:
    return {"ok": True, "protocolVersion": PROTOCOL_VERSION, "data": dict(data)}


def failure(code: str) -> ErrorReply:
    code = code if code in ERRORS else "INTERNAL_ERROR"
    return {"ok": False, "protocolVersion": PROTOCOL_VERSION,
            "error": {"code": code, "message": ERRORS[code]}}
