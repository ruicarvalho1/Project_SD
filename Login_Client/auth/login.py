import requests
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

AUTH_URL = "http://127.0.0.1:6001"


def login_secure(username, private_key_path):

    try:
        r = requests.post(f"{AUTH_URL}/auth/challenge", json={"username": username})
        r.raise_for_status()
        nonce = base64.b64decode(r.json()['nonce'])
    except Exception as e:
        raise Exception(f"Failed to get challenge: {e}")

    try:
        with open(private_key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)

        signature = key.sign(
            nonce,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        sig_b64 = base64.b64encode(signature).decode()
    except Exception as e:
        raise Exception(f"Crypto error: {e}")

    try:
        r = requests.post(f"{AUTH_URL}/auth/login", json={
            "username": username,
            "signature": sig_b64
        })

        if r.status_code == 200:
            return True
        else:
            raise Exception(f"Login denied: {r.text}")

    except Exception as e:
        raise Exception(f"Login request failed: {e}")