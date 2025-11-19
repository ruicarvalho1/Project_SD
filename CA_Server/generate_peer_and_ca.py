import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from datetime import datetime, timedelta

BASE_CA_PATH = "CA_Server/certs"
BASE_PEER_PATH = "Peer_Network/peers/certs"

os.makedirs(BASE_CA_PATH, exist_ok=True)
os.makedirs(BASE_PEER_PATH, exist_ok=True)

def generate_ca():
    ca_key = rsa.generate_private_key(key_size=2048, public_exponent=65537)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "My Root CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Project_SD"),
    ])

    ca_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(private_key=ca_key, algorithm=hashes.SHA256())
    )

    with open(f"{BASE_CA_PATH}/ca_key.pem", "wb") as f:
        f.write(
            ca_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )

    with open(f"{BASE_CA_PATH}/ca_cert.pem", "wb") as f:
        f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

    print("[+] Certification Authority criada com sucesso!")
    return ca_key, ca_cert


def generate_peer_certificate(ca_key, ca_cert, peer_common_name):
    peer_key = rsa.generate_private_key(key_size=2048, public_exponent=65537)

    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, peer_common_name),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Project_SD Peer"),
    ])

    peer_cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(peer_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .sign(private_key=ca_key, algorithm=hashes.SHA256())
    )

    with open(f"{BASE_PEER_PATH}/peer_key.pem", "wb") as f:
        f.write(
            peer_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption(),
            )
        )

    with open(f"{BASE_PEER_PATH}/peer_cert.pem", "wb") as f:
        f.write(peer_cert.public_bytes(serialization.Encoding.PEM))

    print(f"[+] Certificado do peer '{peer_common_name}' criado com sucesso!")


if __name__ == "__main__":
    ca_key, ca_cert = generate_ca()
    generate_peer_certificate(ca_key, ca_cert, peer_common_name="peer1")
