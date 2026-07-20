"""
Phase 9.6-B — API Key Management

Secure API key lifecycle: create, revoke, rotate, validate.
Keys are stored as SHA-256 hashes — plaintext is never persisted.

Format (returned to user once): a3_<32-hex-chars>
Format (stored): sha256(full_key)

Architecture: does NOT modify Veritas-Core or src/core/.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ── Constants ────────────────────────────────

KEY_PREFIX = "a3_"
KEY_TOKEN_LENGTH = 32          # hex chars after prefix
DEFAULT_KEY_EXPIRY_DAYS = 90


def _get_keys_dir() -> Path:
    base = Path(os.path.expanduser("~/.a3-agent/workspace"))
    return base / ".api_keys"


def _get_keys_file() -> Path:
    return _get_keys_dir() / "api_keys.json"


def _ensure_keys_dir() -> Path:
    d = _get_keys_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


# ── Data Models ──────────────────────────────

@dataclass
class ApiKeyRecord:
    """Stored API key metadata. Plaintext key is NEVER stored."""
    key_id: str                     # unique ID for this key
    key_hash: str                   # SHA-256 of full key string
    key_prefix: str                 # first 8 chars for display (a3_xxxx...)
    user_id: str                    # owning user
    name: str                       # human label (e.g. "CLI tool")
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    last_used_at: float = 0.0
    is_active: bool = True
    scopes: List[str] = field(default_factory=list)  # e.g. ["read", "generate"]

    def __post_init__(self):
        if self.expires_at <= 0:
            self.expires_at = self.created_at + DEFAULT_KEY_EXPIRY_DAYS * 86400

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key_id": self.key_id,
            "key_hash": self.key_hash,
            "key_prefix": self.key_prefix,
            "user_id": self.user_id,
            "name": self.name,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_used_at": self.last_used_at,
            "is_active": self.is_active,
            "scopes": self.scopes,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ApiKeyRecord":
        return cls(
            key_id=d.get("key_id", ""),
            key_hash=d.get("key_hash", ""),
            key_prefix=d.get("key_prefix", ""),
            user_id=d.get("user_id", ""),
            name=d.get("name", ""),
            created_at=d.get("created_at", 0.0),
            expires_at=d.get("expires_at", 0.0),
            last_used_at=d.get("last_used_at", 0.0),
            is_active=d.get("is_active", True),
            scopes=d.get("scopes", []),
        )


# ── Key Manager ──────────────────────────────

class ApiKeyManager:
    """Secure API key lifecycle manager.

    Usage:
        mgr = ApiKeyManager()
        key_str, record = mgr.create_api_key("usr_1", "My CLI", scopes=["read"])
        user = mgr.validate_api_key(key_str)    # → user_id or None
        mgr.revoke_api_key(record.key_id)
        new_key = mgr.rotate_api_key(record.key_id)
    """

    # ── Storage ───────────────────────────

    @staticmethod
    def _load_all() -> Dict[str, Dict[str, Any]]:
        f = _get_keys_file()
        if not f.exists():
            return {}
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            return {}

    @staticmethod
    def _save_all(data: Dict[str, Dict[str, Any]]) -> None:
        _ensure_keys_dir()
        _get_keys_file().write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── Create ────────────────────────────

    def create_api_key(
        self,
        user_id: str,
        name: str = "",
        scopes: Optional[List[str]] = None,
        expiry_days: int = 0,
    ) -> tuple[str, ApiKeyRecord]:
        """Create a new API key. Returns (plaintext_key, record).

        The plaintext key is ONLY returned here — it is never stored.
        """
        # Generate key
        token = secrets.token_hex(KEY_TOKEN_LENGTH)
        full_key = f"{KEY_PREFIX}{token}"
        key_hash = hashlib.sha256(full_key.encode("utf-8")).hexdigest()
        key_id = f"apikey_{secrets.token_hex(8)}"

        record = ApiKeyRecord(
            key_id=key_id,
            key_hash=key_hash,
            key_prefix=full_key[:12],
            user_id=user_id,
            name=name or f"API Key {key_id[-8:]}",
            scopes=scopes or ["read"],
        )
        if expiry_days > 0:
            record.expires_at = record.created_at + expiry_days * 86400

        # Persist
        data = self._load_all()
        data[key_id] = record.to_dict()
        self._save_all(data)

        return full_key, record

    # ── Validate ──────────────────────────

    def validate_api_key(self, key_str: str) -> Optional[str]:
        """Validate an API key. Returns user_id if valid, None otherwise."""
        if not key_str or not key_str.startswith(KEY_PREFIX):
            return None

        key_hash = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        data = self._load_all()

        for kid, kd in data.items():
            if not kd.get("is_active", True):
                continue
            stored_hash = kd.get("key_hash", "")
            if not hmac.compare_digest(key_hash, stored_hash):
                continue
            # Check expiry
            expires = kd.get("expires_at", 0)
            if expires > 0 and time.time() > expires:
                continue
            # Update last_used
            kd["last_used_at"] = time.time()
            self._save_all(data)
            return kd.get("user_id", "")
        return None

    # ── Revoke ────────────────────────────

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke an API key (soft delete)."""
        data = self._load_all()
        if key_id not in data:
            return False
        data[key_id]["is_active"] = False
        self._save_all(data)
        return True

    def hard_delete_api_key(self, key_id: str) -> bool:
        """Permanently delete an API key."""
        data = self._load_all()
        if key_id not in data:
            return False
        del data[key_id]
        self._save_all(data)
        return True

    # ── Rotate ────────────────────────────

    def rotate_api_key(
        self,
        key_id: str,
        retain_scopes: bool = True,
    ) -> Optional[tuple[str, ApiKeyRecord]]:
        """Rotate an API key: revoke old, create new with same metadata.

        Returns (new_plaintext_key, new_record) or None if key_id not found.
        """
        data = self._load_all()
        if key_id not in data:
            return None
        old = data[key_id]
        if not old.get("is_active", True):
            return None

        # Revoke old key
        old["is_active"] = False
        self._save_all(data)

        # Create new with same metadata
        return self.create_api_key(
            user_id=old["user_id"],
            name=f"{old.get('name', 'Rotated')} (rotated)",
            scopes=list(old.get("scopes", ["read"])) if retain_scopes else ["read"],
        )

    # ── List ──────────────────────────────

    def list_api_keys(
        self,
        user_id: str = "",
        active_only: bool = True,
    ) -> List[ApiKeyRecord]:
        """List API keys, optionally filtered by user."""
        data = self._load_all()
        records = []
        for kid, kd in data.items():
            record = ApiKeyRecord.from_dict(kd)
            if not active_only and not record.is_active:
                continue
            if active_only and (not record.is_active or record.is_expired()):
                continue
            if user_id and record.user_id != user_id:
                continue
            records.append(record)
        return sorted(records, key=lambda r: r.created_at, reverse=True)

    def get_api_key(self, key_id: str) -> Optional[ApiKeyRecord]:
        """Get a single API key record by ID."""
        data = self._load_all()
        kd = data.get(key_id)
        if kd is None:
            return None
        return ApiKeyRecord.from_dict(kd)

    def count_active_keys(self, user_id: str = "") -> int:
        """Count active (non-expired) API keys."""
        return len(self.list_api_keys(user_id=user_id, active_only=True))
