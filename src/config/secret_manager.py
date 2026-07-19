"""
Phase 6.0 — Secret Manager (API key encryption with system keyring)

Multi-backend API key storage. Attempts system credential store first,
falls back to local XOR encryption when keyring is unavailable.

Backends (priority order):
  1. System keyring (Windows Credential Manager / Linux Secret Service / macOS Keychain)
  2. Local XOR encryption (~/.a3-agent/config/.secret_key)

Storage format in llm.json:
  - Keyring:  "api_key": "keyring://deepseek"  (marker, actual key in system store)
  - Local:    "api_key": "base64_encrypted..." (XOR-encrypted value)

Usage:
    from src.config.secret_manager import encrypt_api_key, decrypt_api_key

    # Store API key (prefers keyring)
    encrypt_api_key("sk-abc123", provider="deepseek")

    # Retrieve API key (tries keyring first, falls back to XOR decrypt)
    key = decrypt_api_key(ciphertext, provider="deepseek")

    # Delete from keyring
    delete_api_key("deepseek")
"""

from __future__ import annotations

import base64
import logging
import os
import secrets
import sys
from typing import Optional

logger = logging.getLogger(__name__)

# ── Keyring constants ──────────────────────

_KEYRING_SERVICE = "A3-Agent"
_KEYRING_MARKER = "keyring://"


# ── Keyring backend detection ──────────────

def _keyring_available() -> bool:
    """
    Check if the system keyring is available.

    Returns True if keyring can store/retrieve credentials.
    Returns False on headless Linux, missing dbus, or import failure.
    """
    try:
        import keyring

        # Quick smoke test — try listing backends
        backends = keyring.backend.get_all_keyring()
        if not backends:
            logger.debug("keyring: no backends available, falling back to local encryption")
            return False

        # On Linux, check if Secret Service is reachable
        if sys.platform == "linux":
            try:
                # Test a harmless operation
                keyring.get_credential(_KEYRING_SERVICE, "__a3_probe__")
            except keyring.errors.KeyringError as e:
                if "dbus" in str(e).lower() or "secret service" in str(e).lower():
                    logger.debug("keyring: Secret Service unavailable (%s), falling back", e)
                    return False
                # Other errors (e.g., key not found) are fine — the backend works

        logger.debug("keyring: available with %d backends", len(backends))
        return True

    except ImportError:
        logger.debug("keyring: not installed, falling back to local encryption")
        return False
    except Exception as e:
        logger.debug("keyring: unexpected error (%s), falling back", e)
        return False


# ── Local XOR backend (fallback) ──────────

def _config_dir() -> str:
    """Platform-appropriate config directory."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        return os.path.join(base, "A3-Agent", "config")
    else:
        return os.path.expanduser("~/.a3-agent/config")


def _key_path() -> str:
    return os.path.join(_config_dir(), ".secret_key")


def _get_or_create_key() -> bytes:
    """Load existing local key or generate a new random one."""
    path = _key_path()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    key = secrets.token_bytes(32)
    with open(path, "wb") as f:
        f.write(key)
    os.chmod(path, 0o600)
    return key


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR each byte of data with cycling key bytes."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def _local_encrypt(plaintext: str) -> str:
    """Encrypt with XOR + base64 (fallback)."""
    if not plaintext:
        return ""
    key = _get_or_create_key()
    plain_bytes = plaintext.encode("utf-8")
    encrypted = _xor_bytes(plain_bytes, key)
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def _local_decrypt(ciphertext: str) -> str:
    """Decrypt XOR + base64 (fallback)."""
    if not ciphertext:
        return ""
    key = _get_or_create_key()
    encrypted = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
    decrypted = _xor_bytes(encrypted, key)
    return decrypted.decode("utf-8")


# ── Public API ─────────────────────────────

def encrypt_api_key(plaintext: str, provider: str = "") -> str:
    """
    Encrypt/store an API key.

    Priority:
      1. System keyring (if available and provider is given)
      2. Local XOR encryption (always works)

    Returns a string suitable for storage in llm.json:
      - "keyring://deepseek"  when stored in system keyring
      - base64-encoded XOR string when stored locally

    Args:
        plaintext: The API key to encrypt.
        provider: Provider name (e.g., "deepseek"). Required for keyring storage.
    """
    if not plaintext:
        return ""

    # Attempt system keyring storage
    if provider and _keyring_available():
        try:
            import keyring
            keyring.set_password(_KEYRING_SERVICE, provider, plaintext)
            logger.info("Stored API key for '%s' in system keyring", provider)
            return _KEYRING_MARKER + provider
        except Exception as e:
            logger.warning("keyring store failed for '%s': %s — falling back to local encryption", provider, e)

    # Fallback: local XOR encryption
    return _local_encrypt(plaintext)


def decrypt_api_key(ciphertext: str, provider: str = "") -> str:
    """
    Decrypt/retrieve an API key.

    Detection:
      - If ciphertext starts with "keyring://" → retrieve from system keyring
      - Otherwise → XOR decrypt from local storage

    Args:
        ciphertext: The stored value from llm.json.
        provider: Provider name (used as fallback if ciphertext is a marker).

    Returns:
        Decrypted API key string, or empty string.
    """
    if not ciphertext:
        return ""

    # ── Keyring marker ──
    if ciphertext.startswith(_KEYRING_MARKER):
        provider_name = ciphertext[len(_KEYRING_MARKER):] or provider
        if _keyring_available():
            try:
                import keyring
                key = keyring.get_password(_KEYRING_SERVICE, provider_name)
                if key:
                    return key
                logger.warning("keyring: no credential for '%s'", provider_name)
            except Exception as e:
                logger.warning("keyring retrieve failed for '%s': %s", provider_name, e)
        return ""  # Keyring unavailable or key not found

    # ── Legacy: local XOR decryption ──
    return _local_decrypt(ciphertext)


def delete_api_key(provider: str) -> bool:
    """
    Delete a stored API key from all backends.

    Args:
        provider: Provider name (must match the one used during encrypt).

    Returns:
        True if the key was deleted from at least one backend.
    """
    deleted = False

    # System keyring
    if _keyring_available():
        try:
            import keyring
            keyring.delete_password(_KEYRING_SERVICE, provider)
            deleted = True
            logger.info("Deleted API key for '%s' from system keyring", provider)
        except keyring.errors.PasswordDeleteError:
            logger.debug("keyring: no credential to delete for '%s'", provider)
        except Exception as e:
            logger.warning("keyring delete failed for '%s': %s", provider, e)

    # Local: delete the .secret_key file (forces re-encryption on next save)
    local_key_path = _key_path()
    if os.path.exists(local_key_path):
        try:
            os.remove(local_key_path)
            deleted = True
            logger.debug("Deleted local secret key")
        except OSError:
            pass

    return deleted


def get_storage_backend() -> str:
    """
    Return the active storage backend name.

    Returns:
        "keyring" if system keyring is in use,
        "local" if using local XOR encryption.
    """
    if _keyring_available():
        return "keyring"
    return "local"
