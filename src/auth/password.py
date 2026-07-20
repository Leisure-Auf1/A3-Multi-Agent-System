"""
Phase 9.6-A — Password Management

Secure password hashing using PBKDF2-HMAC-SHA256.
Zero external dependencies — pure stdlib.

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import hashlib
import os
import secrets


SALT_BYTES = 16
HASH_ITERATIONS = 200_000  # OWASP 2023 recommendation
KEY_LENGTH = 32             # SHA-256 output in bytes
ALGORITHM = "sha256"


def generate_salt() -> str:
    """Generate a cryptographically secure random salt."""
    return secrets.token_hex(SALT_BYTES)


def hash_password(password: str, salt: str = "") -> tuple[str, str]:
    """
    Hash a password using PBKDF2-HMAC-SHA256.

    Args:
        password: Plain-text password
        salt: Optional existing salt (hex string). If empty, generates new.

    Returns:
        (hash_hex, salt_hex) tuple
    """
    if not salt:
        salt = generate_salt()
    if not password:
        return ("", salt)

    key = hashlib.pbkdf2_hmac(
        ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
        dklen=KEY_LENGTH,
    )
    return key.hex(), salt


def make_password_hash(password: str) -> str:
    """
    One-shot: generate salt and hash, return combined string.

    Format: "salt$iterations$hash_hex"

    Returns:
        Storable password string for database persistence.
    """
    if not password:
        return ""
    salt = generate_salt()
    h, _ = hash_password(password, salt)
    return f"{salt}${HASH_ITERATIONS}${h}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a password against a stored hash string.

    Args:
        password: Plain-text password to check
        stored_hash: Combined hash string in "salt$iterations$hash_hex" format

    Returns:
        True if password matches, False otherwise.
    """
    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")
        if len(parts) < 3:
            # Legacy format: "salt:hash" (backward compat with Phase 9.1)
            return _verify_legacy(password, stored_hash)
        salt, iterations_str, expected_hex = parts[0], parts[1], parts[2]
        iterations = int(iterations_str)
    except (ValueError, IndexError):
        return False

    try:
        key = hashlib.pbkdf2_hmac(
            ALGORITHM,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
            dklen=KEY_LENGTH,
        )
        return secrets.compare_digest(key.hex(), expected_hex)
    except Exception:
        return False


def _verify_legacy(password: str, stored: str) -> bool:
    """Verify Phase 9.1 format: salt:hash (pbkdf2, sha256, 100k iterations)."""
    try:
        salt, expected_hash = stored.split(":", 1)
        actual_hash, _ = _hash_legacy(password, salt)
        return secrets.compare_digest(actual_hash, expected_hash)
    except (ValueError, AttributeError):
        return False


def _hash_legacy(password: str, salt: str) -> tuple[str, str]:
    """Legacy hash for backward compat: 100k iterations."""
    if not salt:
        salt = os.urandom(SALT_BYTES).hex()
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000)
    return h.hex(), salt


def is_legacy_hash(stored_hash: str) -> bool:
    """Check if stored hash uses the legacy format."""
    return ":" in stored_hash and "$" not in stored_hash


def upgrade_hash_if_needed(password: str, stored_hash: str) -> str | None:
    """
    If password is stored in legacy format, return upgraded hash.
    Otherwise return None (no upgrade needed).
    """
    if is_legacy_hash(stored_hash) and verify_password(password, stored_hash):
        return make_password_hash(password)
    return None
