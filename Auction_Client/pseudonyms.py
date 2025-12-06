# pseudonyms.py
import uuid, json, base64, datetime
from cryptography.hazmat.primitives.asymmetric import ed25519,padding
from cryptography.hazmat.primitives import serialization, hashes

def generate_pseudonym():
    return uuid.uuid4().hex

def generate_pseudonym_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    priv_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()
    )
    pub_pem = pub.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return priv, priv_pem, pub_pem

def build_pseudonym_token(user_private_key, user_cert_serial, auction_id, pseudonym_id, pseudonym_pubkey_pem):
    now = datetime.datetime.now(datetime.timezone.utc)
    token = {
        "auction_id": auction_id,
        "pseudonym_id": pseudonym_id,
        "pseudonym_pubkey": base64.b64encode(pseudonym_pubkey_pem).decode(),
        "user_cert_serial": str(user_cert_serial),
        "not_before": now.isoformat() + "Z",
        "not_after": (now + datetime.timedelta(minutes=60)).isoformat() + "Z"
    }
    # sign with user’s long-term RSA private key
    msg = json.dumps(token, sort_keys=True).encode()
    sig = user_private_key.sign(msg, padding.PKCS1v15(), hashes.SHA256())
    token["signature"] = base64.b64encode(sig).decode()
    return token