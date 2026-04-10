"""Unit tests for AES-256-GCM token encryption helpers."""

import pytest

from app.crypto import (
    EncryptedToken,
    TokenDecryptionError,
    b64_to_token,
    decrypt,
    encrypt,
    token_to_b64,
)


# ── encrypt ───────────────────────────────────────────────────────────────────


def test_encrypt_returns_encrypted_token():
    token = encrypt("hello world")

    assert isinstance(token, EncryptedToken)
    assert len(token.nonce) == 12
    assert len(token.tag) == 16
    assert isinstance(token.ciphertext, bytes)


def test_encrypt_ciphertext_differs_from_plaintext():
    token = encrypt("plaintext secret")

    assert token.ciphertext != b"plaintext secret"


def test_encrypt_produces_unique_nonce_each_call():
    t1 = encrypt("same plaintext")
    t2 = encrypt("same plaintext")

    # Two encryptions of the same value must produce different nonces (random IV)
    assert t1.nonce != t2.nonce
    assert t1.ciphertext != t2.ciphertext


# ── decrypt ───────────────────────────────────────────────────────────────────


def test_decrypt_roundtrip():
    plaintext = "xoxb-slack-bot-token-1234567890"
    token = encrypt(plaintext)

    assert decrypt(token) == plaintext


def test_decrypt_empty_string():
    assert decrypt(encrypt("")) == ""


def test_decrypt_unicode():
    plaintext = "token-with-unicode-安全"
    assert decrypt(encrypt(plaintext)) == plaintext


def test_decrypt_tampered_ciphertext_raises():
    token = encrypt("secret")
    tampered = EncryptedToken(
        ciphertext=bytes(b ^ 0xFF for b in token.ciphertext),
        nonce=token.nonce,
        tag=token.tag,
    )

    with pytest.raises(TokenDecryptionError):
        decrypt(tampered)


def test_decrypt_tampered_tag_raises():
    token = encrypt("secret")
    tampered = EncryptedToken(
        ciphertext=token.ciphertext,
        nonce=token.nonce,
        tag=b"\xff" * 16,
    )

    with pytest.raises(TokenDecryptionError):
        decrypt(tampered)


def test_decrypt_wrong_nonce_raises():
    token = encrypt("secret")
    tampered = EncryptedToken(
        ciphertext=token.ciphertext,
        nonce=b"\x00" * 12,
        tag=token.tag,
    )

    with pytest.raises(TokenDecryptionError):
        decrypt(tampered)


# ── base64 transport helpers ──────────────────────────────────────────────────


def test_token_to_b64_returns_string():
    token = encrypt("pack me")
    packed = token_to_b64(token)

    assert isinstance(packed, str)


def test_b64_roundtrip_preserves_components():
    token = encrypt("roundtrip")
    unpacked = b64_to_token(token_to_b64(token))

    assert unpacked.nonce == token.nonce
    assert unpacked.tag == token.tag
    assert unpacked.ciphertext == token.ciphertext


def test_b64_packed_token_decrypts_correctly():
    plaintext = "linkedin-access-token-abc123"
    recovered = decrypt(b64_to_token(token_to_b64(encrypt(plaintext))))

    assert recovered == plaintext
