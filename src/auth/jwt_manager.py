"""
Phase 9.6-A — JWT Token Manager

Minimal JWT (JSON Web Token) implementation using HMAC-SHA256.
Zero external dependencies — pure stdlib (base64, json, hashlib, hmac).

Architecture: does NOT modify Veritas-Core or src/core/.

Token format:
    base64url(header).base64url(payload).signature

Usage:
    from src.auth.jwt_manager import JWTManager

    mgr = JWTManager(secret="my-secret-key")
    token = mgr.create_token(user_id="usr_abc", role="pro")
    payload = mgr.verify_token(token)  # → UserToken or None
    refreshed = mgr.refresh_token(token)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# ── Constants ────────────────────────────────

DEFAULT_EXPIRY_SECONDS = 3600          # 1 hour
REFRESH_WINDOW_SECONDS = 86400 * 7     # 7 days (can refresh within this window)
DEFAULT_SECRET = "a3-agent-default-secret-change-me"


def _b64url_encode(data: bytes) -> str:
    """Base64url encode (no padding)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    """Base64url decode (add padding back)."""
    # Add padding
    rem = len(s) % 4
    if rem:
        s += "=" * (4 - rem)
    return base64.urlsafe_b64decode(s)


# ── Data Model ───────────────────────────────

@dataclass
class UserToken:
    """Decoded JWT payload with user identity and role."""
    user_id: str
    role: str = "free"
    username: str = ""
    email: str = ""
    issued_at: float = field(default_factory=time.time)
    expire_at: float = 0.0

    def __post_init__(self):
        if self.expire_at <= 0:
            self.expire_at = self.issued_at + DEFAULT_EXPIRY_SECONDS

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expire_at

    @property
    def ttl_seconds(self) -> float:
        """Remaining seconds until expiry."""
        return max(0.0, self.expire_at - time.time())

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "username": self.username,
            "email": self.email,
            "issued_at": self.issued_at,
            "expire_at": self.expire_at,
        }

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> "UserToken":
        return cls(
            user_id=payload.get("user_id", ""),
            role=payload.get("role", "free"),
            username=payload.get("username", ""),
            email=payload.get("email", ""),
            issued_at=payload.get("iat", 0.0),
            expire_at=payload.get("exp", 0.0),
        )


# ── JWT Manager ──────────────────────────────

class JWTManager:
    """HMAC-SHA256 JWT token manager.

    Usage:
        mgr = JWTManager(secret="my-secret-key")

        # Create token
        token = mgr.create_token(
            user_id="usr_abc",
            role="pro",
            username="alice",
            email="alice@test.com",
            expiry_seconds=3600,
        )

        # Verify token
        payload = mgr.verify_token(token)
        if payload:
            print(f"User: {payload.user_id}, Role: {payload.role}")

        # Refresh token
        new_token = mgr.refresh_token(token)
    """

    def __init__(self, secret: str = ""):
        self._secret = secret or DEFAULT_SECRET

    # ── Token Creation ───────────────────────

    def create_token(
        self,
        user_id: str,
        role: str = "free",
        username: str = "",
        email: str = "",
        expiry_seconds: int = 0,
        extra_claims: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a signed JWT token.

        Args:
            user_id: User identifier
            role: User role (free/student/pro/teacher/admin)
            username: Optional username
            email: Optional email
            expiry_seconds: Token TTL in seconds. 0 = use default (3600).
                            Negative = past (already expired, for testing).
            extra_claims: Extra claims to include in payload

        Returns:
            Signed JWT token string: header.payload.signature
        """
        now = time.time()
        # expiry_seconds=0 means default; negative means past (testing)
        if expiry_seconds == 0:
            ttl = DEFAULT_EXPIRY_SECONDS
        else:
            ttl = expiry_seconds

        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "user_id": user_id,
            "role": role,
            "username": username,
            "email": email,
            "iat": now,
            "exp": now + ttl,
        }
        if extra_claims:
            payload.update(extra_claims)

        return self._sign(header, payload)

    def _sign(self, header: dict, payload: dict) -> str:
        """Sign header + payload with HMAC-SHA256."""
        header_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
        message = f"{header_b64}.{payload_b64}"

        sig = hmac.new(
            self._secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        sig_b64 = _b64url_encode(sig)

        return f"{message}.{sig_b64}"

    # ── Token Verification ───────────────────

    def verify_token(self, token: str) -> Optional[UserToken]:
        """Verify a JWT token and return decoded UserToken.

        Returns None if token is invalid, tampered, or expired.
        """
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, sig_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                self._secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            actual_sig = _b64url_decode(sig_b64)

            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            # Decode payload
            payload_bytes = _b64url_decode(payload_b64)
            payload = json.loads(payload_bytes)

            # Check expiration
            if time.time() > payload.get("exp", 0):
                return None

            # Check not-before
            nbf = payload.get("nbf", 0)
            if nbf > 0 and time.time() < nbf:
                return None

            return UserToken.from_payload(payload)

        except (json.JSONDecodeError, ValueError, KeyError):
            return None

    def decode_unsafe(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode token WITHOUT signature verification (debug only)."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            payload_bytes = _b64url_decode(parts[1])
            return json.loads(payload_bytes)
        except (json.JSONDecodeError, ValueError):
            return None

    # ── Token Refresh ────────────────────────

    def refresh_token(
        self,
        token: str,
        new_expiry_seconds: int = 0,
    ) -> Optional[str]:
        """Refresh an existing token if within the refresh window.

        Tokens can be refreshed if they haven't expired, OR if they're
        within the refresh window after expiry.

        Returns new token string or None if refresh not allowed.
        """
        # Try verification first (handles non-expired tokens)
        payload = self.verify_token(token)

        if payload is not None:
            # Token still valid — issue new one
            return self.create_token(
                user_id=payload.user_id,
                role=payload.role,
                username=payload.username,
                email=payload.email,
                expiry_seconds=new_expiry_seconds,
            )

        # Token may be expired — check if within refresh window
        decoded = self.decode_unsafe(token)
        if decoded is None:
            return None

        exp = decoded.get("exp", 0)
        if exp <= 0:
            return None

        # Allow refresh within REFRESH_WINDOW_SECONDS after expiry
        if time.time() - exp > REFRESH_WINDOW_SECONDS:
            return None

        # Verify signature even for refresh (tampered tokens rejected)
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            message = f"{parts[0]}.{parts[1]}"
            expected_sig = hmac.new(
                self._secret.encode("utf-8"),
                message.encode("utf-8"),
                hashlib.sha256,
            ).digest()
            actual_sig = _b64url_decode(parts[2])
            if not hmac.compare_digest(expected_sig, actual_sig):
                return None
        except Exception:
            return None

        return self.create_token(
            user_id=decoded.get("user_id", ""),
            role=decoded.get("role", "free"),
            username=decoded.get("username", ""),
            email=decoded.get("email", ""),
            expiry_seconds=new_expiry_seconds,
        )

    # ── Utility ──────────────────────────────

    def get_remaining_seconds(self, token: str) -> float:
        """Get remaining TTL in seconds. Returns 0 for invalid/expired."""
        decoded = self.decode_unsafe(token)
        if decoded is None:
            return 0.0
        return max(0.0, decoded.get("exp", 0) - time.time())
