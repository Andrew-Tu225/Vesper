"""AES-256-GCM encryption for OAuth tokens stored in the database.

Each encrypted value is stored as three separate columns:
  encrypted_token  — ciphertext
  nonce            — 12-byte GCM nonce (unique per row, enforced by DB constraint)
  tag              — 16-byte GCM authentication tag

Key: APP_SECRET_KEY must be exactly 64 hex characters (32 random bytes).
Generate with: openssl rand -hex 32
"""

import os
from base64 import b64decode, b64encode
from typing import NamedTuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_NONCE_SIZE = 12  # bytes — GCM standard
_TAG_SIZE = 16  # bytes — GCM auth tag appended by cryptography library


class TokenDecryptionError(Exception):
    """Raised when AES-GCM authentication fails.

    Causes: wrong key, tampered ciphertext, or mismatched nonce/tag bytes.
    Never expose the underlying cryptographic exception to callers.
    """


class EncryptedToken(NamedTuple):
    """Named container for the three AES-GCM components stored per DB row."""

    ciphertext: bytes
    nonce: bytes  # 12 bytes
    tag: bytes  # 16 bytes


def _get_key() -> bytes:
    from app.config import settings  # avoid circular import at module load time

    return bytes.fromhex(settings.app_secret_key)


def encrypt(plaintext: str) -> EncryptedToken:
    """Encrypt plaintext and return an EncryptedToken.

    The cryptography library appends the 16-byte auth tag to the ciphertext;
    we split it off to store the three fields separately for schema clarity.
    """
    key = _get_key()
    nonce = os.urandom(_NONCE_SIZE)
    aesgcm = AESGCM(key)
    ct_and_tag = aesgcm.encrypt(nonce, plaintext.encode(), None)
    ciphertext = ct_and_tag[:-_TAG_SIZE]
    tag = ct_and_tag[-_TAG_SIZE:]
    return EncryptedToken(ciphertext=ciphertext, nonce=nonce, tag=tag)


def decrypt(token: EncryptedToken) -> str:
    """Decrypt and return the original plaintext string.

    Raises TokenDecryptionError if the authentication tag does not verify.
    """
    key = _get_key()
    aesgcm = AESGCM(key)
    ct_and_tag = token.ciphertext + token.tag
    try:
        plaintext = aesgcm.decrypt(token.nonce, ct_and_tag, None)
    except InvalidTag as exc:
        raise TokenDecryptionError(
            "Token authentication failed — key mismatch or data corruption"
        ) from exc
    return plaintext.decode()


# ── Base64 helpers for transporting tokens across API boundaries ───────────────

def token_to_b64(token: EncryptedToken) -> str:
    """Pack an EncryptedToken into a single base64 string (nonce ‖ tag ‖ ciphertext)."""
    return b64encode(token.nonce + token.tag + token.ciphertext).decode()


def b64_to_token(packed: str) -> EncryptedToken:
    """Unpack a base64 string produced by token_to_b64 into an EncryptedToken."""
    raw = b64decode(packed)
    nonce = raw[:_NONCE_SIZE]
    tag = raw[_NONCE_SIZE: _NONCE_SIZE + _TAG_SIZE]
    ciphertext = raw[_NONCE_SIZE + _TAG_SIZE:]
    return EncryptedToken(ciphertext=ciphertext, nonce=nonce, tag=tag)
