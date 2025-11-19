import json

def load_peers(filename="peers.json"):
    with open(filename, "r") as f:
        return json.load(f)
