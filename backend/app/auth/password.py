"""
Password Utilities
==================
Password hashing and verification using bcrypt.
"""

import bcrypt
from typing import Optional


def hash_password(password: str, rounds: int = 12) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password
        rounds: Number of bcrypt rounds (default 12)

    Returns:
        Hashed password as string
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=rounds)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.

    Args:
        password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def generate_password_hash(password: str) -> str:
    """
    Generate password hash (alias for hash_password).

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return hash_password(password)


def check_password_hash(password: str, hash: str) -> bool:
    """
    Check password hash (alias for verify_password).

    Args:
        password: Plain text password
        hash: Hashed password

    Returns:
        True if password matches
    """
    return verify_password(password, hash)