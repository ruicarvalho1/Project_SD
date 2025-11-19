from flask import Flask, render_template, request
import sys
import os

# Caminhos para aceder ao login.py
sys.path.append(os.path.abspath("../Peer_Network/utils"))
from login import login as peer_login   # importa função login()

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_route():
    # NÃO precisamos de username/password,
    # o login é feito com certificados
    result, eth_address = peer_login()

    if result:
        return render_template("dashboard.html", address=eth_address)
    else:
        return render_template("login.html", error="Falha no login. Certificado inválido ou peer não registado.")

if __name__ == "__main__":
    app.run(debug=True)
