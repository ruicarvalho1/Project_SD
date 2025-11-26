from pathlib import Path
import os
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

def identity_exists(folder: Path) -> bool:
    return (
        (folder / "client_private_key.pem").exists() and
        (folder / "client_cert.pem").exists() and
        (folder / "ca_cert.pem").exists()
    )


def generate_keypair():
    return rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048
    )


def save_private_key(private_key, path: Path):
    path.write_bytes(
        private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()
        )
    )


def generate_csr(private_key, username: str) -> str:
    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(
            x509.Name([
                x509.NameAttribute(NameOID.COUNTRY_NAME, "PT"),
                x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AuctionUser"),
                x509.NameAttribute(NameOID.COMMON_NAME, username),
            ])
        )
        .sign(private_key, hashes.SHA256())
    )

    return csr.public_bytes(serialization.Encoding.PEM).decode()
