"""User-scoped settings storage with Windows DPAPI protection for API keys."""

from __future__ import annotations

import base64
import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path
from typing import Any, Protocol


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

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            document = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(document, dict):
                raise ValueError("Settings document must be an object")
            provider = str(document.get("provider", "openai"))
            protected_keys = document.get("api_keys_protected", {})
            if not isinstance(protected_keys, dict):
                raise ValueError("Protected API keys must be an object")
            api_keys = {
                str(provider_id): self.protector.unprotect(
                    base64.b64decode(encrypted_text, validate=True)
                ).decode("utf-8")
                for provider_id, encrypted_text in protected_keys.items()
                if isinstance(encrypted_text, str) and encrypted_text
            }
            legacy_key = document.get("api_key_protected", "")
            if legacy_key and provider not in api_keys:
                encrypted_key = base64.b64decode(legacy_key, validate=True)
                api_keys[provider] = self.protector.unprotect(encrypted_key).decode("utf-8")
            return {
                "provider": provider,
                "base_url": str(document.get("base_url", "")),
                "model": str(document.get("model", "")),
                "api_key": api_keys.get(provider, ""),
                "api_keys": api_keys,
            }
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise SettingsStoreError(
                "Saved provider settings could not be read or decrypted"
            ) from exc

    def save(self, settings: dict[str, Any]) -> None:
        provider = str(settings.get("provider", "openai"))
        api_key = str(settings.get("api_key", ""))
        try:
            existing = self.load()
            api_keys: dict[str, str] = dict(existing.get("api_keys", {}))
            requested_keys = settings.get("api_keys", {})
            if isinstance(requested_keys, dict):
                for provider_id, key in requested_keys.items():
                    if not isinstance(provider_id, str) or not isinstance(key, str):
                        continue
                    if key:
                        api_keys[provider_id] = key
                    else:
                        api_keys.pop(provider_id, None)
            if api_key:
                api_keys[provider] = api_key
            else:
                api_keys.pop(provider, None)
            protected_keys = {
                provider_id: base64.b64encode(
                    self.protector.protect(key.encode("utf-8"))
                ).decode("ascii")
                for provider_id, key in api_keys.items()
                if key
            }
            document = {
                "provider": provider,
                "base_url": settings.get("base_url", ""),
                "model": settings.get("model", ""),
                "api_keys_protected": protected_keys,
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
