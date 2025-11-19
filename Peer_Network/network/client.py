import socket
import json

def send_message(peer, message):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((peer["host"], peer["port"]))
        s.send(json.dumps(message).encode())
        s.close()
    except Exception as e:
        print(f"[!] Error sending to {peer['id']}: {e}")
