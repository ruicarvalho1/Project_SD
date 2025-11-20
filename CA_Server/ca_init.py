import os
import datetime
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes

os.makedirs("CA_Server/storage/issued", exist_ok=True)

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

with open("CA_Server/storage/ca_private_key.pem", "wb") as f:
    f.write(private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
))
    
subject = issuer = x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, u"PT"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"MyAuctionCA"),
    x509.NameAttribute(NameOID.COMMON_NAME, u"myauction.root.ca"),
])

ca_cert = (
    x509.CertificateBuilder()
    .subject_name(subject)
    .issuer_name(issuer)             # self-signed
    .public_key(private_key.public_key())
    .serial_number(x509.random_serial_number())
    .not_valid_before(datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1))
    .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
    .add_extension(
        x509.BasicConstraints(ca=True, path_length=None),
        critical=True
    )
    .sign(private_key, hashes.SHA256())
)

# Save CA certificate
with open("CA_Server/storage/ca_cert.pem", "wb") as f:
    f.write(ca_cert.public_bytes(serialization.Encoding.PEM))

print("✔ CA initialized successfully!")
print("   Generated: storage/ca_private_key.pem, storage/ca_cert.pem")