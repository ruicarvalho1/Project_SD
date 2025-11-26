import requests

AUTH_LOGIN_URL = "http://localhost:6001/login"

def login_with_certificate(cert_pem: str):
    resp = requests.post(AUTH_LOGIN_URL, json={"certificate": cert_pem})
    return resp
