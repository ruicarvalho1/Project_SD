import jwt
import requests
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

CA_API_URL = "http://127.0.0.1:8000/api/get_ca_cert/"
CA_PUBLIC_KEY_CACHE = None

def fetch_ca_public_key():
    global CA_PUBLIC_KEY_CACHE
    if CA_PUBLIC_KEY_CACHE:
        return CA_PUBLIC_KEY_CACHE
    try:
        response = requests.post(CA_API_URL, json={})
        if response.status_code == 200:
            cert_pem = response.json().get("certificate_pem")
            cert = load_pem_x509_certificate(cert_pem.encode(), default_backend())
            CA_PUBLIC_KEY_CACHE = cert.public_key()
            return CA_PUBLIC_KEY_CACHE
    except:
        return None

def validate_token(token):
    public_key = fetch_ca_public_key()
    if not public_key:
        return None
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return payload["sub"]
    except:
        return None
