from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from certs.models import UserCertificate


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