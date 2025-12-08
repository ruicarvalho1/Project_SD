import requests
import base64
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

AUTH_URL = "http://127.0.0.1:8000/api"


def login_secure(username, private_key_path):
    """
    Performs the Secure Challenge-Response Authentication Protocol.
    """
    print(f" [AUTH] Initiating secure handshake for user: '{username}'...")

    # --- PHASE 1: REQUEST CHALLENGE ---
    try:
        print(" [AUTH] Step 1: Requesting challenge...")
        r = requests.post(f"{AUTH_URL}/challenge", json={"username": username})
        r.raise_for_status()

        nonce = base64.b64decode(r.json()['nonce'])
        print(" [AUTH] >> Challenge received.")

    except Exception as e:
        print(f" [AUTH ERROR] Failed to get challenge.")
        raise Exception(f"Connection failed: {e}")

    # --- PHASE 2: SIGN CHALLENGE ---
    try:
        print(" [AUTH] Step 2: Signing nonce with Private Key...")

        with open(private_key_path, "rb") as f:
            key = serialization.load_pem_private_key(f.read(), password=None)

        signature = key.sign(
            nonce,
            padding.PKCS1v15(),
            hashes.SHA256()
        )

        sig_b64 = base64.b64encode(signature).decode()
        print(" [AUTH] >> Nonce signed locally.")

    except Exception as e:
        print(f" [AUTH ERROR] Crypto operation failed.")
        raise Exception(f"Signing failed: {e}")

    # --- PHASE 3: VERIFY & LOGIN ---
    try:
        print(" [AUTH] Step 3: Sending proof to server...")

        r = requests.post(f"{AUTH_URL}/login_secure", json={
            "username": username,
            "signature": sig_b64
        })

        if r.status_code == 200:
            print(" [SUCCESS] Signature verified. Access Granted!")

            data = r.json()
            token = data.get("token")

            if not token:
                raise Exception("Login OK but no Token received!")

            print("-" * 50)
            print(f" [TOKEN] JWT RECEIVED FROM CA SERVER:")
            print(f" {token}")
            print("-" * 50)

            return token
        else:
            error_msg = r.json().get('error', r.text)
            print(f" [FAILURE] Access Denied: {error_msg}")
            raise Exception(f"Login denied: {error_msg}")

    except Exception as e:
        if "Login denied" in str(e): raise e
        raise Exception(f"Login request failed: {e}")