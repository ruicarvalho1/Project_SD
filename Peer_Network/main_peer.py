from network.server import start_server
from network.client import send_message
from network.tracker_client import register, get_peers, heartbeat
from utils.login import login

import threading
import time
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python main_peer.py <PeerID>")
        sys.exit(1)

    peer_id = sys.argv[1]

    # ===============================
    # 1) LOGIN via CA + Blockchain
    # ===============================
    auth = login()
    if not auth:
        print("❌ Peer não autenticado — encerrado.")
        sys.exit(1)

    # ===============================
    # 2) Carregar info local do peer (peers.json ainda contém o NOSSO peer)
    # ===============================
    import json
    me = next(p for p in json.load(open("Peer_Network/peers.json")) if p["id"] == peer_id)

    host = me["host"]
    port = me["port"]

    # ===============================
    # 3) REGISTAR NO TRACKER
    # ===============================
    ok = register(peer_id, host, port)
    if not ok:
        print("❌ Erro ao comunicar com tracker!")
        sys.exit(1)

    print(f"[+] Peer {peer_id} registado no tracker.")

    # ===============================
    # 4) Iniciar servidor P2P
    # ===============================
    threading.Thread(
        target=start_server,
        args=(peer_id, host, port),
        daemon=True
    ).start()

    time.sleep(1)

    print(f"[{peer_id}] READY — podes enviar mensagens.\n")

    # =======================================
    # 5) Thread para enviar heartbeat ao tracker
    # =======================================
    def heartbeat_loop():
        while True:
            heartbeat(peer_id)
            time.sleep(5)

    threading.Thread(target=heartbeat_loop, daemon=True).start()

    # ===============================
    # 6) Loop de input
    # ===============================
    while True:
        text = input("> ")
        if text.lower() in ["exit", "quit"]:
            break

        # obter lista de peers ATUALIZADA
        peers = get_peers()

        for p in peers:
            if p["id"] != peer_id:
                send_message(p, {"from": peer_id, "data": text})


if __name__ == "__main__":
    main()
