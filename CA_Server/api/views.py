import json
import jwt
import datetime
import base64
import time
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend

from certs.models import UserCertificate
from certs.models import CACertificate
from core.config import CA_KEY_PATH


PENDING_CHALLENGES = {}


# ------------------------------------------------------------------
#  FUNÇÕES AUXILIARES
# ------------------------------------------------------------------

def generate_jwt(username):
    """
    Gera um JWT assinado com a Chave Privada do CA.
    """
    try:
        # DEBUG: Imprimir onde estamos a tentar ler
        print(f"[DEBUG] A tentar ler chave privada em: {CA_KEY_PATH}")

        if not os.path.exists(CA_KEY_PATH):
            print(f"[ERRO CRÍTICO] O ficheiro NÃO existe no caminho indicado!")
            return None

        with open(CA_KEY_PATH, "rb") as f:
            private_key_data = f.read()

        private_key = serialization.load_pem_private_key(
            private_key_data,
            password=None,
            backend=default_backend()
        )

        payload = {
            "sub": username,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=60),
            "iat": datetime.datetime.utcnow(),
            "type": "p2p_access"
        }

        token = jwt.encode(payload, private_key, algorithm="RS256")
        return token
    except Exception as e:
        print(f"[ERRO JWT] Falha ao gerar token: {e}")
        return None


# ------------------------------------------------------------------
#  VIEWS DE CERTIFICADOS (JÁ EXISTENTES)
# ------------------------------------------------------------------

@csrf_exempt
def store_user_certificate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get("username")
        cert_pem = data.get("certificate_pem")
        serial = data.get("serial_number")

        if not cert_pem or not serial:
            return JsonResponse({"error": "Missing fields"}, status=400)

        UserCertificate.objects.create(
            username=username,
            certificate_pem=cert_pem,
            serial_number=serial
        )
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def get_user_certificate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get("username")
        if not username:
            return JsonResponse({"error": "Missing username"}, status=400)
        try:
            user_cert = UserCertificate.objects.get(username=username)
            return JsonResponse({
                "certificate_pem": user_cert.certificate_pem,
                "serial_number": user_cert.serial_number
            })
        except UserCertificate.DoesNotExist:
            return JsonResponse({"error": "User certificate not found"}, status=404)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def store_ca_certificate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    try:
        data = json.loads(request.body)
        ca_cert = data.get("certificate_pem")
        serial = data.get("serial_number")

        if not ca_cert or not serial:
            return JsonResponse({"error": "Missing fields"}, status=400)

        CACertificate.objects.all().delete()
        CACertificate.objects.create(ca_cert=ca_cert, serial_number=serial)
        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def get_ca_certificate(request):
    # Esta view serve tanto para o Login_Client como para o Tracker P2P
    # Aceitamos GET ou POST para facilitar a vida ao Tracker
    if request.method not in ["POST", "GET"]:
        return JsonResponse({"error": "Method not allowed"}, status=405)
    try:
        ca = CACertificate.objects.last()
        if not ca:
            return JsonResponse({"error": "No CA found"}, status=404)
        return JsonResponse({
            "certificate_pem": ca.ca_cert,
            "serial_number": ca.serial_number
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def check_user_exists(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)
    try:
        data = json.loads(request.body)
        username = data.get("username")
        if not username:
            return JsonResponse({"error": "Missing username"}, status=400)
        exists = UserCertificate.objects.filter(username=username).exists()
        return JsonResponse({"exists": exists})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ------------------------------------------------------------------
#  NOVAS VIEWS DE AUTENTICAÇÃO (MIGRADAS DO FLASK)
# ------------------------------------------------------------------

@csrf_exempt
def request_challenge(request):
    """
    Fase 1: Cliente pede um Nonce para assinar.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get("username")

        if not username:
            return JsonResponse({"error": "Username required"}, status=400)

        # Verificar se o user existe na BD do Django
        if not UserCertificate.objects.filter(username=username).exists():
            return JsonResponse({"error": "User not found"}, status=404)

        # 1. Gerar Nonce
        nonce = os.urandom(32)

        # 2. Guardar Sessão (Nonce + Timestamp)
        PENDING_CHALLENGES[username] = {
            'nonce': nonce,
            'timestamp': time.time()
        }

        print(f" [AUTH] Challenge generated for {username}")

        return JsonResponse({
            "nonce": base64.b64encode(nonce).decode()
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def login_secure(request):
    """
    Fase 2: Cliente envia assinatura. Validamos e emitimos JWT.
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

    try:
        data = json.loads(request.body)
        username = data.get("username")
        signature_b64 = data.get("signature")

        if not username or not signature_b64:
            return JsonResponse({"error": "Missing credentials"}, status=400)

        # 1. Validar Sessão
        if username not in PENDING_CHALLENGES:
            return JsonResponse({"error": "Challenge not requested or expired"}, status=400)

        session = PENDING_CHALLENGES.pop(username)

        if time.time() - session['timestamp'] > 120:
            return JsonResponse({"error": "Time limit exceeded"}, status=408)

        try:
            user_entry = UserCertificate.objects.get(username=username)
        except UserCertificate.DoesNotExist:
            return JsonResponse({"error": "User not found"}, status=403)

        try:
            signature = base64.b64decode(signature_b64)

            cert = load_pem_x509_certificate(
                user_entry.certificate_pem.encode(),
                default_backend()
            )
            public_key = cert.public_key()

            public_key.verify(
                signature,
                session['nonce'],
                padding.PKCS1v15(),
                hashes.SHA256()
            )
        except Exception as e:
            print(f" [FAIL] Signature check failed for {username}: {e}")
            return JsonResponse({"error": "Invalid signature"}, status=401)

        token = generate_jwt(username)

        if not token:
            return JsonResponse({"error": "Server error generating token"}, status=500)

        print(f" [SUCCESS] {username} logged in via Django.")
        return JsonResponse({"status": "authenticated", "token": token})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)