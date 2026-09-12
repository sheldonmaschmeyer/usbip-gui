"""Unit tests for crypto.py."""

import base64
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from usbip_gui.common.common import JsonDict
from usbip_gui.common.crypto import (
    DecryptionError,
    MasterKeyManager,
    create_sentinel,
    decrypt_data,
    decrypt_field,
    derive_key,
    encrypt_data,
    encrypt_field,
    is_encrypted_field,
    verify_sentinel,
)


def test_derive_key():
    """Test PBKDF2 key derivation."""
    salt = b"0" * 16
    key1 = derive_key("password123", salt, iterations=1000)
    key2 = derive_key("password123", salt, iterations=1000)
    key3 = derive_key("different", salt, iterations=1000)

    assert len(key1) == 32
    assert key1 == key2
    assert key1 != key3


def test_encrypt_decrypt_data_roundtrip():
    """Test encrypt and decrypt round trip."""
    key = AESGCM.generate_key(bit_length=256)
    plaintext = "super_secret_token_12345"

    payload = encrypt_data(plaintext, key)
    assert payload["enc"] == "v1"
    assert "nonce" in payload
    assert "ciphertext" in payload

    decrypted = decrypt_data(payload, key)
    assert decrypted == plaintext


def test_decrypt_data_invalid_payload():
    """Test decrypting malformed payloads raises DecryptionError."""
    key = AESGCM.generate_key(bit_length=256)

    # Not a dict or wrong version
    with pytest.raises(DecryptionError, match="Invalid encryption payload"):
        decrypt_data("not-a-dict", key)  # type: ignore[arg-type]

    with pytest.raises(DecryptionError, match="Invalid encryption payload"):
        decrypt_data({"enc": "v2"}, key)

    # Missing nonce or ciphertext
    with pytest.raises(DecryptionError, match="Missing nonce or ciphertext"):
        decrypt_data({"enc": "v1", "nonce": ""}, key)

    # Invalid base64
    with pytest.raises(DecryptionError, match="Decryption failed"):
        decrypt_data(
            {"enc": "v1", "nonce": "???", "ciphertext": "???"},
            key,
        )

    # Tampered ciphertext (InvalidTag)
    payload = encrypt_data("valid_data", key)
    payload["ciphertext"] = payload["ciphertext"][:-4] + "AAAA"
    with pytest.raises(DecryptionError, match="Decryption failed"):
        decrypt_data(payload, key)


def test_is_encrypted_field():
    """Test is_encrypted_field detection."""
    assert not is_encrypted_field(None)
    assert not is_encrypted_field("plain_text")
    assert not is_encrypted_field(123)
    assert not is_encrypted_field({"enc": "v2"})
    assert is_encrypted_field({"enc": "v1", "nonce": "abc"})


def test_encrypt_field():
    """Test encrypt_field with empty and non-empty values."""
    key = AESGCM.generate_key(bit_length=256)
    assert encrypt_field("", key) == ""
    enc = encrypt_field("token_abc", key)
    assert isinstance(enc, dict)
    assert enc.get("enc") == "v1"


def test_decrypt_field():
    """Test decrypt_field with various input types."""
    key = AESGCM.generate_key(bit_length=256)
    assert decrypt_field("plain_password", key) == "plain_password"
    assert decrypt_field(12345, key) == ""  # type: ignore[arg-type]

    enc = encrypt_field("secret_password", key)
    assert decrypt_field(enc, key) == "secret_password"


def test_create_and_verify_sentinel():
    """Test sentinel generation and verification."""
    key, sentinel = create_sentinel("mypassword", iterations=1000)
    assert len(key) == 32
    assert sentinel["enc"] == "v1"
    assert sentinel["iterations"] == 1000

    # Correct password
    verified_key = verify_sentinel("mypassword", sentinel)
    assert verified_key == key

    # Incorrect password
    assert verify_sentinel("wrongpassword", sentinel) is None

    # Tampered sentinel
    tampered = dict(sentinel)
    tampered["salt"] = 12345  # Not a string
    assert verify_sentinel("mypassword", tampered) is None

    tampered_bad_b64 = dict(sentinel)
    tampered_bad_b64["salt"] = "invalid-base64???"
    assert verify_sentinel("mypassword", tampered_bad_b64) is None


def test_create_sentinel_with_provided_salt():
    """Test create_sentinel with an explicit salt."""
    salt = b"a" * 16
    key, sentinel = create_sentinel("pw", salt=salt, iterations=1000)
    assert verify_sentinel("pw", sentinel) == key


def test_verify_sentinel_mismatch_plaintext():
    """Test verify_sentinel when decrypted plaintext does not match."""
    key = AESGCM.generate_key(bit_length=256)
    enc_dict = encrypt_data("wrong_plaintext", key)
    sentinel: JsonDict = {
        "salt": base64.b64encode(b"0" * 16).decode("ascii"),
        "iterations": 1000,
        **enc_dict,
    }
    with patch("usbip_gui.common.crypto.derive_key", return_value=key):
        assert verify_sentinel("pwd", sentinel) is None


def test_master_key_manager():
    """Test MasterKeyManager lifecycle and locking."""
    mgr = MasterKeyManager()
    assert not mgr.is_unlocked()
    assert mgr.get_key() is None

    test_key = b"k" * 32
    mgr.set_key(test_key)
    assert mgr.is_unlocked()
    assert mgr.get_key() == test_key

    mgr.clear()
    assert not mgr.is_unlocked()
    assert mgr.get_key() is None
