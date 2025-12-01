import requests
from cryptography import x509
from .config import DJANGO_API_URL


def fetch_ca_cert():
    """
    Fetches the CA certificate from Django.
    Uses POST to match the privacy-focused architecture (even with empty body).
    """
    try:

        r = requests.post(f"{DJANGO_API_URL}/get_ca_cert/", json={}, timeout=2)

        if r.status_code == 200:
            data = r.json()
            return data.get("certificate_pem")

    except Exception as e:
        print(f" [WARN] Could not fetch from Django: {e}")
    return None


def publish_ca_cert(cert_pem, serial):
    """
    Uploads the new CA certificate to Django.
    """
    try:
        requests.post(
            f"{DJANGO_API_URL}/storeca/",
            json={
                "certificate_pem": cert_pem,
                "serial_number": serial,
                "action": "replace"
            },
            timeout=3
        )
    except Exception as e:
        print(f" [ERROR] Failed to push cert to Django: {e}")


def publish_user_cert(username, cert_pem, serial):
    """
    Uploads the signed user certificate to Django.
    """
    return requests.post(
        f"{DJANGO_API_URL}/store/",
        json={
            "username": username,
            "certificate_pem": cert_pem,
            "serial_number": serial
        },
        timeout=3
    )


def check_username_availability(username):
    """
    Checks if the user already exists.
    PRIVACY NOTE: Uses POST to avoid leaking the username in server logs/URL.
    """
    try:
        r = requests.post(
            f"{DJANGO_API_URL}/check_user/",
            json={"username": username},
            timeout=2
        )

        if r.status_code == 200:
            data = r.json()
            if data.get('exists') is True:
                return False
            return True

    except Exception as e:
        print(f" [WARN] Failed to check user availability: {e}")
        return False

    return True


def get_trusted_user_cert(username):
    """
    Fetches the official trusted public certificate from Django.
    Used during login verification to ensure the user is legitimate.
    """
    try:
        response = requests.post(
            f"{DJANGO_API_URL}/get_user_cert/",
            json={"username": username},
            timeout=3
        )

        if response.status_code == 200:
            data = response.json()
            cert_pem = data.get("certificate_pem")
            if cert_pem:
                return x509.load_pem_x509_certificate(cert_pem.encode())

    except Exception as e:
        print(f" [ERROR] Failed to contact Django for cert of {username}: {e}")

    return None