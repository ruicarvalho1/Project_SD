import requests
from .config import DJANGO_API_URL
from cryptography import x509

def fetch_ca_cert():
    """Broadcast request to Django to fetch the current CA certificate."""
    try:
        r = requests.get(f"{DJANGO_API_URL}/get_ca_cert/", timeout=2)
        if r.status_code == 200:
            data = r.json()
            return data.get("certificate_pem")
    except Exception as e:
        print(f" [WARN] Could not fetch from Django: {e}")
    return None

def publish_ca_cert(cert_pem, serial):
    """Send the CA certificate to Django for storage/replacement."""
    try:
        requests.post(
            f"{DJANGO_API_URL}/storeca/",
            json={"certificate_pem": cert_pem, "serial_number": serial, "action": "replace"},
            timeout=3
        )
    except Exception as e:
        print(f" [ERROR] Failed to push cert to Django: {e}")

def publish_user_cert(username, cert_pem, serial):
    """Send a user certificate to Django for storage."""
    return requests.post(
        f"{DJANGO_API_URL}/store/",
        json={"username": username, "certificate_pem": cert_pem, "serial_number": serial},
        timeout=3
    )


def check_username_availability(username):
    """
Checks in Django whether the user already exists.
Returns False if the user EXISTS (username is taken).
Returns True if the username is available.
"""
    try:
        r = requests.get(
            f"{DJANGO_API_URL}/check_user/",
            params={"username": username},
            timeout=2
        )

        if r.status_code == 200:
            data = r.json()
            # Se exists for True, user exist
            if data.get('exists') is True:
                return False
            return True

    except Exception as e:
        print(f" [WARN] Failed to check user availability: {e}")
        return False

    return True


def get_trusted_user_cert(username):
    """
Fetches a user's certificate from Django by username.
    """
    try:

        response = requests.get(
            f"{DJANGO_API_URL}/get_user_cert/",
            params={"username": username},
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            cert_pem = data.get("certificate_pem")
            if cert_pem:
                return x509.load_pem_x509_certificate(cert_pem.encode())

    except Exception as e:

        print(f" [ERROR] Failed to contact Django to fetch certificate for {username}: {e}")
    return None
