import requests

TRACKER_URL = "http://127.0.0.1:5001"


def register(peer_id, host, port):
    try:
        r = requests.post(
            f"{TRACKER_URL}/register",
            json={"peer_id": peer_id, "host": host, "port": port}
        )
        return r.status_code == 200
    except:
        return False


def heartbeat(peer_id):
    try:
        requests.post(f"{TRACKER_URL}/heartbeat", json={"peer_id": peer_id})
    except:
        pass


def get_peers():
    try:
        r = requests.get(f"{TRACKER_URL}/peers")
        return r.json()
    except:
        return []