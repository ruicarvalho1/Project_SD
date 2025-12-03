import jwt
import time
import requests
import sys
import os
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, disconnect
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.backends import default_backend
from threading import Lock

# --- CONFIGURAÇÃO ---
app = Flask(__name__)
# 1. Inicializa SocketIO: Permite que o servidor lide com conexões persistentes
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

CA_API_URL = "http://127.0.0.1:8000/api/get_ca_cert/"

# Armazenamento em memória:
PEERS = {}  # Armazena dados do peer (IP, última vez visto - Opcional)
PEER_SIDS = {}  # CRÍTICO: Mapeia peer_id (username) para Socket ID
SID_PEERS = {}  # Mapeia Socket ID para peer_id

TIMEOUT_SECONDS = 30
CA_PUBLIC_KEY_CACHE = None
thread_lock = Lock()


# --- FUNÇÕES DE SEGURANÇA E VALIDAÇÃO (Mantêm-se as mesmas) ---
def fetch_ca_public_key():
    # ... (código igual, apenas para validação JWT) ...
    # Para o propósito desta resposta, assume-se que as funções estão intactas
    global CA_PUBLIC_KEY_CACHE
    if CA_PUBLIC_KEY_CACHE: return CA_PUBLIC_KEY_CACHE
    try:
        response = requests.post(CA_API_URL, json={})
        if response.status_code == 200:
            cert_pem = response.json().get("certificate_pem")
            cert = load_pem_x509_certificate(cert_pem.encode(), default_backend())
            CA_PUBLIC_KEY_CACHE = cert.public_key()
            return CA_PUBLIC_KEY_CACHE
    except:
        return None


def validate_token(token):
    public_key = fetch_ca_public_key()
    if not public_key: return None
    try:
        payload = jwt.decode(token, public_key, algorithms=["RS256"])
        return payload["sub"]
    except:
        return None


# -------------------------------------------------------------
# NOVAS FUNÇÕES: GERENCIAMENTO DE CONEXÃO WEBSOCKET
# -------------------------------------------------------------

@socketio.on('connect')
def handle_connect():
    """
    Novo cliente WebSocket se conectou. Este é o primeiro passo para o login P2P.
    Ainda não sabemos quem é o utilizador.
    """
    print(f" [SOCKETIO] Cliente conectado: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """
    O cliente fechou o browser ou a aplicação. Removemos o peer.
    """
    sid = request.sid
    if sid in SID_PEERS:
        peer_id = SID_PEERS[sid]
        with thread_lock:
            if peer_id in PEERS:
                del PEERS[peer_id]
            del PEER_SIDS[peer_id]
            del SID_PEERS[sid]
        print(f" [SOCKETIO] Peer desconectado e removido: {peer_id}")


@socketio.on('authenticate')
def handle_authentication(data):
    """
    O cliente envia o token JWT para se identificar após a conexão.
    Isto substitui a lógica de registo HTTP.
    """
    token = data.get('token')
    port = data.get('port')  # A porta P2P é opcional agora

    peer_id = validate_token(token)

    if not peer_id:
        # Falha na autenticação - Desliga a conexão
        print(f" [SOCKETIO] Falha na Autenticação (Token Inválido): {request.sid}")
        disconnect()
        return

    # SUCESSO: Associar o ID de Sessão ao utilizador
    sid = request.sid
    client_ip = request.remote_addr

    with thread_lock:
        PEER_SIDS[peer_id] = sid
        SID_PEERS[sid] = peer_id
        PEERS[peer_id] = {
            "host": client_ip,
            "port": port,
            "last_seen": time.time()
        }

    print(f" [SOCKETIO] ✅ Autenticado e registado: {peer_id} @ {client_ip}")
    # Envia de volta uma confirmação
    emit('status', {'message': 'Authenticated', 'user': peer_id})


# -------------------------------------------------------------
# FUNÇÕES DE LÓGICA DE NEGÓCIO (Mantêm-se, mas o Broadcast muda)
# -------------------------------------------------------------

# A rota /register (HTTP) torna-se redundante. O cliente deve usar 'authenticate' (WebSocket)
@app.route("/register", methods=["POST"], strict_slashes=False)
def register_peer_http():
    # Esta rota é um fallback ou pode ser usada para Heartbeat
    token = request.json.get("token")
    peer_id = validate_token(token)
    if not peer_id:
        return jsonify({"error": "Invalid token. Use WebSocket 'authenticate'."}), 403
    return jsonify({"status": "ok", "message": "Use WebSocket para real-time."}), 200


# ROTA PRINCIPAL: BROADCAST (Agora usa SocketIO)
@app.route("/broadcast", methods=["POST"], strict_slashes=False)
def broadcast_message():
    """
    Recebe a mensagem HTTP/POST do cliente e distribui via WebSocket.
    """
    data = request.json
    token = data.get("token")
    payload = data.get("payload")

    sender_id = validate_token(token)
    if not sender_id:
        return jsonify({"error": "Acesso negado."}), 403

    print(f"\n [TRACKER] 📢 A emitir evento de {sender_id} via WebSocket...")

    # 1. Prepara a mensagem
    msg_to_send = {
        "sender": sender_id,
        "type": payload.get("type"),
        "data": payload.get("data")
    }

    # 2. EMISSÃO GERAL (O Cliente vai ouvir o evento 'new_event')
    # include_self=False garante que o emissor não recebe a própria mensagem.
    socketio.emit('new_event', msg_to_send, broadcast=True, include_self=False)

    print(f" [TRACKER] ✅ Evento emitido para todos os clientes conectados.")
    return jsonify({"status": "broadcast_sent", "receivers": len(PEER_SIDS) - 1}), 200


# -------------------------------------------------------------
# FUNÇÕES RESTANTES (Mantêm-se as rotas GET/POST)
# -------------------------------------------------------------

@app.route("/peers", methods=["GET"])
def get_peers():
    # ... (mantém a lógica para retornar a lista de peers) ...
    # No modelo WebSocket, a lista de peers online é simplesmente len(PEER_SIDS)
    now = time.time()
    active = []
    # Usamos os PEER_SIDS para contar os ativos, mas devolvemos a informação completa
    for pid, info in PEERS.items():
        if now - info["last_seen"] < TIMEOUT_SECONDS:  # Isto é opcional no modelo WS
            active.append({"peer_id": pid, "host": info["host"], "port": info["port"]})
    return jsonify(active), 200


@app.route("/heartbeat", methods=["POST"], strict_slashes=False)
def heartbeat():
    # ... (mantém a lógica, mas só atualiza o timestamp em PEERS) ...
    data = request.json
    peer_id = data.get("peer_id")
    if peer_id in PEERS:
        PEERS[peer_id]["last_seen"] = time.time()
        return jsonify({"status": "alive"}), 200
    return jsonify({"error": "Unknown peer"}), 404


if __name__ == "__main__":
    print("[TRACKER] A arrancar servidor SocketIO na porta 5555...")
    fetch_ca_public_key()
    # 3. Usa socketio.run no lugar de app.run
    socketio.run(app, host="0.0.0.0", port=5555, debug=True)