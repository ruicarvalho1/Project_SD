import requests

CA_SIGN_URL = "http://127.0.0.1:5000/sign_csr"
CA_CERT_URL = "http://127.0.0.1:5000/ca_cert"

def request_certificate(csr_pem: str) -> str:
    resp = requests.post(CA_SIGN_URL, json={"csr": csr_pem})
    if resp.status_code != 200:
        raise Exception("CA Error: " + resp.text)
    return resp.text

def fetch_ca_certificate() -> str:
    resp = requests.get(CA_CERT_URL)
    if resp.status_code != 200:
        raise Exception("Could not fetch CA certificate")
    return resp.text
