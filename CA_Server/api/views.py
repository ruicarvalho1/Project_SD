from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from certs.models import UserCertificate
from certs.models import CACertificate


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
        return JsonResponse({"error": "Only POST allowed for privacy"}, status=405)

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


# -----------------------------------------


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

        # Garante que só existe 1 CA ativa
        CACertificate.objects.all().delete()

        CACertificate.objects.create(
            ca_cert=ca_cert,
            serial_number=serial
        )

        return JsonResponse({"status": "ok"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
def get_ca_certificate(request):
    if request.method != "POST":
        return JsonResponse({"error": "Only POST allowed"}, status=405)

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


# -----------------------------------------


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