import os
import datetime
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from .config import CA_KEY_PATH
from .django_client import fetch_ca_cert, publish_ca_cert
from .ca_state import ca_state


def load_or_generate_private_key():
    """Load the CA's private key from disk, or generate a new one if not found."""
    if os.path.exists(CA_KEY_PATH):
        print(" [LOCAL] Private Key found.")
        with open(CA_KEY_PATH, "rb") as f:
            return serialization.load_pem_private_key(f.read(), password=None)

    print(" [LOCAL] Generating NEW Private Key...")
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with open(CA_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    return private_key


def keys_match(private_key, cert):
    """Verify if the private key matches the certificate's public key."""
    try:
        return cert.public_key().public_numbers() == private_key.public_key().public_numbers()
    except Exception:
        return False


def initialize_ca():
    """Logic to initialize the CA: load/generate key, fetch/generate cert."""
    ca_state.private_key = load_or_generate_private_key()

    cert_pem = fetch_ca_cert()
    if cert_pem:
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        if keys_match(ca_state.private_key, cert):
            print(" [OK] DB Certificate matches Local Private Key.")
            ca_state.certificate = cert
            return True
        print(" [CRITICAL] Mismatch or missing cert. Regenerating.")

    # Generate new CA cert
    print(" [GEN] Generating NEW Root CA...")
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "PT"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MyAuctionCA"),
        x509.NameAttribute(NameOID.COMMON_NAME, "myauction.root.ca"),
    ])

    now = datetime.datetime.utcnow()
    new_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_state.private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(ca_state.private_key, hashes.SHA256())
    )

    ca_state.certificate = new_cert

    # Publish to Django
    pem = new_cert.public_bytes(serialization.Encoding.PEM).decode()
    publish_ca_cert(pem, str(new_cert.serial_number))
    return True