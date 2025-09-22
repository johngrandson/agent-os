"""Crypto helper functions"""

import base64
import json
from typing import Union, Dict, Any
from cryptography.fernet import Fernet
from core.config import config


def _get_cipher():
    """Get cipher for encryption/decryption"""
    if config.ENCRYPTION_KEY:
        # Use key from config
        key = base64.urlsafe_b64decode(config.ENCRYPTION_KEY.encode())
        return Fernet(key)
    else:
        # Generate a consistent key for development (NOT for production!)
        # This ensures data can be decrypted in development environment
        dev_key = base64.urlsafe_b64encode(b"dev-key-32-chars-for-testing-123")
        return Fernet(dev_key)


def encrypt_data(data: Union[str, Dict[str, Any]]) -> str:
    """
    Encrypt data (string or dictionary)

    Args:
        data: String or dictionary to encrypt

    Returns:
        Base64 encoded encrypted string
    """
    cipher = _get_cipher()

    # Convert dict to JSON string if needed
    if isinstance(data, dict):
        data_str = json.dumps(data, sort_keys=True)
    else:
        data_str = str(data)

    encrypted = cipher.encrypt(data_str.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_data(encrypted_data: str) -> str:
    """
    Decrypt data and return as string

    Args:
        encrypted_data: Base64 encoded encrypted string

    Returns:
        Decrypted string
    """
    cipher = _get_cipher()
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
    decrypted = cipher.decrypt(encrypted_bytes)
    return decrypted.decode()


def decrypt_json(encrypted_data: str) -> Dict[str, Any]:
    """
    Decrypt data and return as dictionary

    Args:
        encrypted_data: Base64 encoded encrypted JSON string

    Returns:
        Decrypted dictionary

    Raises:
        json.JSONDecodeError: If decrypted data is not valid JSON
    """
    decrypted_str = decrypt_data(encrypted_data)
    return json.loads(decrypted_str)
