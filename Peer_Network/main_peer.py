from network.server import start_server
from network.client import send_message
from network.peerlist import load_peers
import threading
import time
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python main_peer.py <PeerID>")
        sys.exit(1)

    peer_id = sys.argv[1]
    peers = load_peers()

    me = next((p for p in peers if p["id"] == peer_id), None)
    if not me:
        print(f"[!] Peer {peer_id} not found in peers.json")
        sys.exit(1)


    threading.Thread(target=start_server, args=(peer_id, me["host"], me["port"]), daemon=True).start()
    time.sleep(1)

    print(f"\n[{peer_id}] ready! Type messages below.\n")


    while True:
        text = input("> ")
        if text.lower() in ["exit", "quit"]:
            break

        for peer in peers:
            if peer["id"] != peer_id:
                msg = {"from": peer_id, "data": text}
                send_message(peer, msg)

if __name__ == "__main__":
    main()
