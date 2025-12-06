# tracker_main.py
from flask import Flask
from flask_socketio import SocketIO
from auth_utils import fetch_ca_public_key
from routes import register_http_routes
from socket_events import register_socket_events

def create_app():
    app = Flask(__name__)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")


    register_http_routes(app, socketio)

    register_socket_events(socketio)

    return app, socketio


if __name__ == "__main__":
    print("[TRACKER] Starting SocketIO server on port 5555...")
    fetch_ca_public_key()
    app, socketio = create_app()
    socketio.run(app, host="0.0.0.0", port=5555, debug=True)
