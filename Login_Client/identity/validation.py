from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from pathlib import Path

def load_ca_cert(path: Path):
    return x509.load_pem_x509_certificate(path.read_bytes())

def validate_cert_with_ca(client_cert_pem: str, ca_cert) -> bool:
    cert = x509.load_pem_x509_certificate(client_cert_pem.encode())

    try:
        ca_cert.public_key().verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
        return True

    except Exception as e:
        print("Certificate validation failed:", e)
        return False
