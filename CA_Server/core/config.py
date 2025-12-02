# core/config.py
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORAGE_DIR = os.path.join(BASE_DIR, "storage")
CA_KEY_PATH = os.path.join(STORAGE_DIR, "ca_private_key.pem")
DJANGO_API_URL = "http://127.0.0.1:8000/api"


if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)