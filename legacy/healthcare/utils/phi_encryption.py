"""
HIPAA-compliant PHI encryption utilities.
Provides AES-256-GCM encryption for sensitive health data at rest.
"""

import os
import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480000,
    )
    return kdf.derive(password.encode())


def encrypt_phi(plaintext: str | dict, password: str | None = None) -> dict:
    if isinstance(plaintext, dict):
        plaintext = json.dumps(plaintext)

    encryption_key = password or os.environ.get("PHI_ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("PHI_ENCRYPTION_KEY environment variable must be set")

    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = _derive_key(encryption_key, salt)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)

    return {
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "algorithm": "AES-256-GCM",
    }


def decrypt_phi(encrypted: dict, password: str | None = None) -> str:
    encryption_key = password or os.environ.get("PHI_ENCRYPTION_KEY")
    if not encryption_key:
        raise ValueError("PHI_ENCRYPTION_KEY environment variable must be set")

    salt = base64.b64decode(encrypted["salt"])
    nonce = base64.b64decode(encrypted["nonce"])
    ciphertext = base64.b64decode(encrypted["ciphertext"])
    key = _derive_key(encryption_key, salt)
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()


def redact_phi(data: dict, fields: list[str] | None = None) -> dict:
    """Redact PHI fields from a dict for logging or non-secure storage."""
    if fields is None:
        fields = ["name", "ssn", "date_of_birth", "address", "phone", "email", "mrn"]
    redacted = data.copy()
    for field in fields:
        if field in redacted:
            redacted[field] = "[REDACTED]"
    return redacted
