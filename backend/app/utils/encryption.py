"""
Encryption Utilities
====================
Fernet encryption for broker credentials and sensitive data.
"""

import os
import base64
from cryptography.fernet import Fernet


_fernet = None


def get_fernet() -> Fernet:
    """Get or create Fernet instance."""
    global _fernet

    if _fernet is None:
        key = os.environ.get('ENCRYPTION_KEY')
        if not key:
            key = base64.urlsafe_b64encode(os.urandom(32)).decode()
            os.environ['ENCRYPTION_KEY'] = key

        _fernet = Fernet(key.encode() if isinstance(key, str) else key)

    return _fernet


def encrypt_value(value: str) -> str:
    """
    Encrypt a string value.

    Args:
        value: Plain text value to encrypt

    Returns:
        Encrypted string
    """
    if not value:
        return ''

    fernet = get_fernet()
    encrypted = fernet.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str) -> str:
    """
    Decrypt an encrypted string.

    Args:
        encrypted_value: Encrypted string to decrypt

    Returns:
        Decrypted plain text
    """
    if not encrypted_value:
        return ''

    try:
        fernet = get_fernet()
        decoded = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = fernet.decrypt(decoded)
        return decrypted.decode()
    except Exception:
        return ''


def encrypt_dict(data: dict) -> dict:
    """
    Encrypt all string values in a dictionary.

    Args:
        data: Dictionary with string values

    Returns:
        Dictionary with encrypted values
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and value:
            result[key] = encrypt_value(value)
        else:
            result[key] = value
    return result


def decrypt_dict(data: dict) -> dict:
    """
    Decrypt all encrypted values in a dictionary.

    Args:
        data: Dictionary with encrypted values

    Returns:
        Dictionary with decrypted values
    """
    result = {}
    for key, value in data.items():
        if isinstance(value, str) and value:
            result[key] = decrypt_value(value)
        else:
            result[key] = value
    return result