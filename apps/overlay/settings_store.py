"""User-scoped settings storage with Windows DPAPI protection for API keys."""

from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Protocol


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


class SecretProtector(Protocol):
    def protect(self, cleartext: bytes) -> bytes: ...
    def unprotect(self, ciphertext: bytes) -> bytes: ...


class SettingsStoreError(RuntimeError):
    """Raised when settings cannot be securely read or written."""


class WindowsDpapiProtector:
    """Encrypt and decrypt user secrets with Windows Data Protection API."""

    _CRYPTPROTECT_UI_FORBIDDEN = 0x1

    @staticmethod
    def _blob(data: bytes) -> tuple[ctypes.Array, _DataBlob]:
        buffer = ctypes.create_string_buffer(data)
        blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
        return buffer, blob

    @staticmethod
    def _free_blob(kernel32: ctypes.WinDLL, blob: _DataBlob) -> None:
        kernel32.LocalFree(ctypes.cast(blob.pbData, ctypes.c_void_p))

    def protect(self, cleartext: bytes) -> bytes:
        if os.name != "nt":
            raise SettingsStoreError("Encrypted API-key storage requires Windows DPAPI")
        crypt32 = ctypes.WinDLL("Crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
        crypt32.CryptProtectData.argtypes = [
            ctypes.POINTER(_DataBlob), wintypes.LPCWSTR, ctypes.POINTER(_DataBlob),
            wintypes.LPVOID, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        crypt32.CryptProtectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        source_buffer, source = self._blob(cleartext)
        destination = _DataBlob()
        if not crypt32.CryptProtectData(
            ctypes.byref(source), "Bloodborne Copilot API key", None, None, None,
            self._CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(destination),
        ):
            raise OSError(ctypes.get_last_error(), "Windows could not encrypt the API key")
        try:
            return ctypes.string_at(destination.pbData, destination.cbData)
        finally:
            self._free_blob(kernel32, destination)
            del source_buffer

    def unprotect(self, ciphertext: bytes) -> bytes:
        if os.name != "nt":
            raise SettingsStoreError("Encrypted API-key storage requires Windows DPAPI")
        crypt32 = ctypes.WinDLL("Crypt32", use_last_error=True)
        kernel32 = ctypes.WinDLL("Kernel32", use_last_error=True)
        crypt32.CryptUnprotectData.argtypes = [
            ctypes.POINTER(_DataBlob), ctypes.POINTER(wintypes.LPWSTR),
            ctypes.POINTER(_DataBlob), wintypes.LPVOID, wintypes.LPVOID,
            wintypes.DWORD, ctypes.POINTER(_DataBlob),
        ]
        crypt32.CryptUnprotectData.restype = wintypes.BOOL
        kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        kernel32.LocalFree.restype = ctypes.c_void_p
        source_buffer, source = self._blob(ciphertext)
        destination = _DataBlob()
        if not crypt32.CryptUnprotectData(
            ctypes.byref(source), None, None, None, None,
            self._CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(destination),
        ):
            raise OSError(ctypes.get_last_error(), "Windows could not decrypt the saved API key")
        try:
            return ctypes.string_at(destination.pbData, destination.cbData)
        finally:
            self._free_blob(kernel32, destination)
            del source_buffer


def default_settings_path() -> Path:
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "BloodborneCopilot" / "settings.json"
    return Path.home() / "AppData" / "Local" / "BloodborneCopilot" / "settings.json"


class SettingsStore:
    """Persist provider settings while encrypting the API key at rest."""

    def __init__(
        self,
        path: Path | None = None,
        protector: SecretProtector | None = None,
    ) -> None:
        self.path = path or default_settings_path()
        self.protector = protector or WindowsDpapiProtector()

    def load(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
            encrypted_text = document.get("api_key_protected", "")
            encrypted_key = base64.b64decode(encrypted_text, validate=True) if encrypted_text else b""
            api_key = self.protector.unprotect(encrypted_key).decode("utf-8") if encrypted_key else ""
            return {
                "provider": str(document.get("provider", "openai")),
                "base_url": str(document.get("base_url", "")),
                "model": str(document.get("model", "")),
                "api_key": api_key,
            }
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SettingsStoreError(
                "Saved provider settings could not be read or decrypted"
            ) from exc

    def save(self, settings: dict[str, str]) -> None:
        api_key = settings.get("api_key", "")
        try:
            encrypted_key = self.protector.protect(api_key.encode("utf-8")) if api_key else b""
            document = {
                "provider": settings.get("provider", "openai"),
                "base_url": settings.get("base_url", ""),
                "model": settings.get("model", ""),
                "api_key_protected": base64.b64encode(encrypted_key).decode("ascii"),
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
            temporary_path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary_path, self.path)
        except (OSError, UnicodeError, ValueError) as exc:
            raise SettingsStoreError("Provider settings could not be saved securely") from exc
