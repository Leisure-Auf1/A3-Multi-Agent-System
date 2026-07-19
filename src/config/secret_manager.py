"""
Phase 4.0 — Secret Manager (local API key encryption)

Simple local encryption for API keys stored in llm.json.
Uses a machine-local secret key to prevent plaintext API key storage.

Design:
  - Generates a random 32-byte key on first use at ~/.a3-agent/config/.secret_key
  - Uses XOR + base64 encoding (simple, local, no external deps)
  - Not production-grade, but API key is not stored as plaintext

Usage:
    from src.config.secret_manager import encrypt_api_key, decrypt_api_key

    encrypted = encrypt_api_key("sk-abc123")
    decrypted = decrypt_api_key(encrypted)  # "sk-abc123"
"""

from __future__ import annotations

import base64
import os
import secrets
import sys


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
    """Load existing key or generate a new random one."""
    path = _key_path()
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    key = secrets.token_bytes(32)
    with open(path, "wb") as f:
        f.write(key)
    # Restrict permissions on key file
    os.chmod(path, 0o600)
    return key


def _xor_bytes(data: bytes, key: bytes) -> bytes:
    """XOR each byte of data with cycling key bytes."""
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def encrypt_api_key(plaintext: str) -> str:
    """
    Encrypt an API key for storage in llm.json.

    Returns a base64-encoded string that can be safely stored.
    Returns empty string for empty input.
    """
    if not plaintext:
        return ""
    key = _get_or_create_key()
    plain_bytes = plaintext.encode("utf-8")
    encrypted = _xor_bytes(plain_bytes, key)
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_api_key(ciphertext: str) -> str:
    """
    Decrypt an API key previously encrypted with encrypt_api_key().

    Returns the original plaintext string.
    Returns empty string for empty input.
    """
    if not ciphertext:
        return ""
    key = _get_or_create_key()
    encrypted = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
    decrypted = _xor_bytes(encrypted, key)
    return decrypted.decode("utf-8")
