import socket
import threading
import json

BUFFER_SIZE = 4096

def start_server(peer_id, host, port):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((host, port))
    server.listen(5)
    print(f"[+] {peer_id} listening on {host}:{port}")

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

def handle_client(conn, addr):
    try:
        data = conn.recv(BUFFER_SIZE).decode()
        if not data:
            return
        msg = json.loads(data)
        print(f"[{addr}] {msg['from']}: {msg['data']}")
    except Exception as e:
        print(f"[!] Error from {addr}: {e}")
    finally:
        conn.close()