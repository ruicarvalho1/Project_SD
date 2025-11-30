import base64
import os
from eth_account import Account
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def _derive_key(password: str, salt: bytes) -> bytes:
    """
Derives a secure 32-byte key from the password.
Uses PBKDF2HMAC with 100,000 iterations to resist brute-force attacks.
"""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def create_encrypted_wallet(password: str):
    """
Generates a new Ethereum account and encrypts the private key.
Returns: Address (str) and Encrypted Data (str).
"""

    new_account = Account.create()
    private_key_hex = new_account.key.hex()

    # 2. Generate Salt
    salt = os.urandom(16)

    # 3. Derivate Key and Encrypt Private Key
    key = _derive_key(password, salt)
    f = Fernet(key)
    token = f.encrypt(private_key_hex.encode())

    # 4. Combine Salt and Token
    encrypted_data = base64.urlsafe_b64encode(salt).decode() + "." + token.decode()

    return new_account.address, encrypted_data


def load_wallet(user_folder, password: str):
    """
Loads and decrypts the wallet file to retrieve the Ethereum account.
    """
    file_path = user_folder / "wallet.enc"

    if not file_path.exists():
        raise FileNotFoundError("Ficheiro de carteira não encontrado.")

    data = file_path.read_text().strip()

    try:
        # 1. Separate Salt and Token
        salt_b64, token = data.split(".")
        salt = base64.urlsafe_b64decode(salt_b64)

        # 2. Derive Key
        key = _derive_key(password, salt)
        f = Fernet(key)

        # 3. Decrypt Private Key
        private_key_hex = f.decrypt(token.encode()).decode()

        return Account.from_key(private_key_hex)

    except Exception:

        raise ValueError("Password incorreta ou ficheiro corrompido.")


def save_wallet_file(user_folder, encrypted_data):

    (user_folder / "wallet.enc").write_text(encrypted_data)