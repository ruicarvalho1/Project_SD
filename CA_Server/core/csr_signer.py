import datetime
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from .ca_state import ca_state
from .django_client import publish_user_cert, check_username_availability


def sign_csr_request(csr_pem):
    """Process and sign a CSR, returning the signed certificate in PEM format."""
    if not ca_state.is_ready():
        raise Exception("CA System not ready")

    csr = x509.load_pem_x509_csr(csr_pem.encode())

    # Validate CSR Signature
    csr.public_key().verify(
        csr.signature,
        csr.tbs_certrequest_bytes,
        padding.PKCS1v15(),
        csr.signature_hash_algorithm,
    )

    # Extract Username
    try:
        username = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)[0].value
    except IndexError:
        raise ValueError("CSR missing COMMON_NAME")

    if not check_username_availability(username):
        raise ValueError(f"Certificate already exists for user: {username}")

    # Create User Certificate
    now = datetime.datetime.utcnow()
    user_cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_state.certificate.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(private_key=ca_state.private_key, algorithm=hashes.SHA256())
    )

    cert_pem = user_cert.public_bytes(serialization.Encoding.PEM).decode()

    # Publish to Django
    r = publish_user_cert(username, cert_pem, str(user_cert.serial_number))
    if r.status_code != 200:
        raise Exception(f"Django rejected storage: {r.text}")

    return cert_pem