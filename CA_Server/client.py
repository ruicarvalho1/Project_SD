# client_request_cert.py (clean version - identity certificate only)
import requests
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID

CA_SIGN_URL = "http://localhost:5000/sign_csr"
CA_CERT_URL = "http://localhost:5000/ca_cert"

# 1) Generate keypair
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

with open("client_private_key.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ))


# 2) Build CSR (simple identity)
csr_builder = x509.CertificateSigningRequestBuilder()
csr_builder = csr_builder.subject_name(x509.Name([
    x509.NameAttribute(NameOID.COUNTRY_NAME, "PT"),
    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "AuctionUser"),
    x509.NameAttribute(NameOID.COMMON_NAME, "user123"),   # change dynamically later
]))

# 3) Optional: add KeyUsage + EKU (CA will include CLIENT_AUTH anyway)
csr = csr_builder.sign(key, hashes.SHA256())

csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()

with open("client.csr.pem", "w") as f:
    f.write(csr_pem)

# 4) Send CSR to CA
resp = requests.post(CA_SIGN_URL, json={"csr": csr_pem})
if resp.status_code != 200:
    print("CA ERROR:", resp.text)
    exit(1)

# 5) Save certificate
cert_pem = resp.text
with open("client_cert.pem", "w") as f:
    f.write(cert_pem)

# 6) Save CA cert
resp_ca = requests.get(CA_CERT_URL)
with open("ca_cert.pem", "w") as f:
    f.write(resp_ca.text)

print("Client certificate and CA certificate saved.")
