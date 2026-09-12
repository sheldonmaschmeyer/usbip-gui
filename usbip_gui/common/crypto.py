"""Cryptographic utilities for master password credential encryption."""

import base64
import os
import threading
from typing import Dict, Optional, Tuple

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .common import JsonDict, JsonValue

SECRET_FIELDS: Tuple[str, ...] = (
    "password",
    "cloudflared_token",
    "cloudflared_token_secret",
    "cloudflared_token_id",
)
SENTINEL_CONFIG_KEY = "master_password_sentinel"
SENTINEL_PLAINTEXT = "usbip-gui-sentinel-v1"
PBKDF2_ITERATIONS = 600_000


class DecryptionError(Exception):
    """Raised when decryption fails due to invalid key or tampered data."""


def derive_key(
    password: str, salt: bytes, iterations: int = PBKDF2_ITERATIONS
) -> bytes:
    """
    Derive a 256-bit encryption key from password and salt using PBKDF2-HMAC.

    Args:
        password: Plain text password string.
        salt: Cryptographic salt bytes (at least 16 bytes).
        iterations: Number of PBKDF2 iterations (default: 600,000).

    Returns:
        bytes: 32-byte (256-bit) encryption key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(password.encode("utf-8"))


def encrypt_data(plaintext: str, key: bytes) -> Dict[str, str]:
    """
    Encrypt a plaintext string using AES-256-GCM.

    Args:
        plaintext: The secret string to encrypt.
        key: 32-byte AES key.

    Returns:
        Dict[str, str]: Payload with version, nonce, and ciphertext (B64).
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return {
        "enc": "v1",
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
    }


def decrypt_data(payload: Dict[str, str], key: bytes) -> str:
    """
    Decrypt an AES-256-GCM payload dictionary.

    Args:
        payload: Dict with 'enc', 'nonce', and 'ciphertext' fields.
        key: 32-byte AES key.

    Returns:
        str: Decrypted plaintext string.

    Raises:
        DecryptionError: If payload format or tag verification fails.
    """
    is_dict = isinstance(  # pyright: ignore[reportUnnecessaryIsInstance]
        payload, dict
    )
    if not is_dict or payload.get("enc") != "v1":
        raise DecryptionError("Invalid encryption payload format")

    nonce_b64 = payload.get("nonce")
    ct_b64 = payload.get("ciphertext")
    if not nonce_b64 or not ct_b64:
        raise DecryptionError("Missing nonce or ciphertext in payload")

    try:
        nonce = base64.b64decode(nonce_b64.encode("ascii"))
        ciphertext = base64.b64decode(ct_b64.encode("ascii"))
        aesgcm = AESGCM(key)
        plaintext_bytes = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext_bytes.decode("utf-8")
    except (InvalidTag, ValueError, UnicodeDecodeError) as exc:
        raise DecryptionError("Decryption failed") from exc


def is_encrypted_field(value: JsonValue) -> bool:
    """Return True if value represents an encrypted dictionary payload."""
    return isinstance(value, dict) and value.get("enc") == "v1"


def encrypt_field(value: str, key: bytes) -> JsonValue:
    """
    Encrypt a secret string if non-empty, otherwise return empty string.

    Args:
        value: Secret string.
        key: 32-byte encryption key.

    Returns:
        JsonValue: Encrypted dictionary payload or empty string.
    """
    if not value:
        return ""
    result: Dict[str, JsonValue] = dict(encrypt_data(value, key))
    return result


def decrypt_field(value: JsonValue, key: bytes) -> str:
    """
    Decrypt an encrypted payload dictionary or return unencrypted string.

    Args:
        value: Encrypted dict or plain string.
        key: 32-byte encryption key.

    Returns:
        str: Decrypted string or plain string.
    """
    if is_encrypted_field(value) and isinstance(value, dict):
        str_dict: Dict[str, str] = {
            str(k): str(v) for k, v in value.items() if isinstance(v, str)
        }
        return decrypt_data(str_dict, key)
    if isinstance(value, str):
        return value
    return ""


def create_sentinel(
    password: str,
    salt: Optional[bytes] = None,
    iterations: int = PBKDF2_ITERATIONS,
) -> Tuple[bytes, JsonDict]:
    """
    Generate master password key and verification sentinel payload.

    Args:
        password: User master password.
        salt: Optional 16-byte salt (generated if None).
        iterations: Number of PBKDF2 iterations.

    Returns:
        Tuple[bytes, JsonDict]: Derived key and sentinel dictionary.
    """
    if salt is None:
        salt = os.urandom(16)
    key = derive_key(password, salt, iterations)
    enc_dict = encrypt_data(SENTINEL_PLAINTEXT, key)
    sentinel: JsonDict = {
        "salt": base64.b64encode(salt).decode("ascii"),
        "iterations": iterations,
        "enc": enc_dict["enc"],
        "nonce": enc_dict["nonce"],
        "ciphertext": enc_dict["ciphertext"],
    }
    return key, sentinel


def verify_sentinel(password: str, sentinel: JsonDict) -> Optional[bytes]:
    """
    Verify master password against stored sentinel dictionary.

    Args:
        password: User-entered master password.
        sentinel: Sentinel dictionary loaded from settings.json.

    Returns:
        Optional[bytes]: Derived 32-byte key if valid, or None if invalid.
    """
    try:
        salt_val = sentinel.get("salt")
        if not isinstance(salt_val, str):
            return None
        salt = base64.b64decode(salt_val.encode("ascii"))
        raw_iter = sentinel.get("iterations", PBKDF2_ITERATIONS)
        iterations = (
            int(raw_iter)
            if isinstance(raw_iter, (int, str))
            else (PBKDF2_ITERATIONS)
        )
        key = derive_key(password, salt, iterations)
        payload: Dict[str, str] = {
            "enc": str(sentinel.get("enc", "")),
            "nonce": str(sentinel.get("nonce", "")),
            "ciphertext": str(sentinel.get("ciphertext", "")),
        }
        decrypted = decrypt_data(payload, key)
        if decrypted == SENTINEL_PLAINTEXT:
            return key
    except Exception:  # pylint: disable=broad-exception-caught
        return None
    return None


class MasterKeyManager:
    """Thread-safe session key cache."""

    def __init__(self) -> None:
        """Initialize empty session key cache."""
        self._lock = threading.Lock()
        self._key: Optional[bytes] = None

    def set_key(self, key: bytes) -> None:
        """Store the derived key for the current session."""
        with self._lock:
            self._key = key

    def get_key(self) -> Optional[bytes]:
        """Retrieve the current session key, or None if locked."""
        with self._lock:
            return self._key

    def clear(self) -> None:
        """Clear the session key, locking credential access."""
        with self._lock:
            self._key = None

    def is_unlocked(self) -> bool:
        """Check whether the session key is present."""
        with self._lock:
            return self._key is not None


master_key_manager = MasterKeyManager()
