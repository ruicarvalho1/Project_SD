from cryptography import x509
from cryptography.hazmat.primitives import serialization

# Change this path to your certificate file
CERT_PATH = "client_cert.pem"

with open(CERT_PATH, "rb") as f:
    cert = x509.load_pem_x509_certificate(f.read())

print("=== Certificate Metadata ===")
print("Subject:", cert.subject)
print("Issuer:", cert.issuer)
print("Serial Number:", cert.serial_number)
print("Valid From:", cert.not_valid_before)
print("Valid Until:", cert.not_valid_after)
print("Signature Algorithm:", cert.signature_algorithm_oid)

print("\n=== Extensions ===")
for ext in cert.extensions:
    print(f"- {ext.oid._name}: {ext.value}")
