import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidTag

# Constants
DEFAULT_MASTER_KEY = b"ThisIsA32ByteKeyForDemoOnly!!!!"
SALT = b"bureaucracy-fixed-salt-12345"  # Using a fixed salt for demo/DB persistence matching

def get_encryption_key() -> bytes:
    try:
        master_key_str = os.getenv("BUREAUCRACY_MASTER_KEY")
        if master_key_str:
            master_key = master_key_str.encode('utf-8')
        else:
            master_key = DEFAULT_MASTER_KEY

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=SALT,
            iterations=100000,
        )
        return kdf.derive(master_key)
    except Exception:
        # Fallback in case of catastrophic failure
        return DEFAULT_MASTER_KEY

def encrypt_data(plaintext: bytes) -> bytes:
    try:
        key = get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)
        # aesgcm.encrypt appends the 16-byte tag to the ciphertext automatically
        return nonce + ciphertext
    except Exception as e:
        raise ValueError(f"Encryption failed: {str(e)}")

def decrypt_data(data: bytes) -> bytes:
    try:
        if len(data) < 28: # 12 nonce + 16 tag minimum
            raise ValueError("Data too short")
        key = get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = data[:12]
        ciphertext = data[12:]
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext
    except InvalidTag:
        raise ValueError("Decryption failed: Invalid tag or data corruption")
    except Exception as e:
        raise ValueError(f"Decryption failed: {str(e)}")

def encrypt_string(text: str) -> str:
    try:
        if not text:
            return ""
        encrypted_bytes = encrypt_data(text.encode('utf-8'))
        return base64.b64encode(encrypted_bytes).decode('utf-8')
    except Exception as e:
        raise ValueError(f"String encryption failed: {str(e)}")

def decrypt_string(encrypted: str) -> str:
    try:
        if not encrypted:
            return ""
        encrypted_bytes = base64.b64decode(encrypted.encode('utf-8'))
        decrypted_bytes = decrypt_data(encrypted_bytes)
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        raise ValueError(f"String decryption failed: {str(e)}")
