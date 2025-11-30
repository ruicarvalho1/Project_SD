from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json, time
from .models import Peer

@csrf_exempt
def register_peer(request):
    data = json.loads(request.body)
    peer_id = data["peer_id"]

    Peer.objects.update_or_create(
        peer_id=peer_id,
        defaults={
            "host": data["host"],
            "port": data["port"],
            "last_seen": time.time()
        }
    )

    return JsonResponse({"status": "ok"})

@csrf_exempt
def heartbeat(request):
    data = json.loads(request.body)
    peer_id = data["peer_id"]

    Peer.objects.filter(peer_id=peer_id).update(last_seen=time.time())
    return JsonResponse({"status": "alive"})

def list_peers(request):
    now = time.time()
    active = Peer.objects.filter(last_seen__gte=now - 30)

    return JsonResponse(
        [
            {"peer_id": p.peer_id, "host": p.host, "port": p.port}
            for p in active
        ],
        safe=False
    )
