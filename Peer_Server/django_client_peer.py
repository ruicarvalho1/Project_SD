import requests

DJANGO_API_URL="http://127.0.0.1:9000/api"

def publish_peer(peer_id,host,port,last_seen):
    """
    Uploads the peer to Django.
    """
    return requests.post(
        f"{DJANGO_API_URL}/store/",
        json={
            "peer_id":peer_id,
            "host": host,
            "port": port,
            "last_seen": last_seen
        },
        timeout=3
    )