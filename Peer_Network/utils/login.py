import os
import json
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from web3 import Web3

CA_CERT_PATH = "CA_Server/certs/ca_cert.pem"
PEER_CERT_PATH = "Peer_Network/peers/certs/peer_cert.pem"
PEER_KEY_PATH = "Peer_Network/peers/certs/peer_key.pem"

ABI_PATH = "Blockchain/build/CARegistry.json"
CONTRACT_ADDRESS = "0x0000000000000000000000000000000000000000"  # substitui pelo endereço real

GANACHE_URL = "http://127.0.0.1:7545"
web3 = Web3(Web3.HTTPProvider(GANACHE_URL))


def load_certificates():
    if not os.path.exists(PEER_CERT_PATH):
        raise FileNotFoundError("peer_cert.pem não encontrado!")

    if not os.path.exists(CA_CERT_PATH):
        raise FileNotFoundError("ca_cert.pem não encontrado!")

    peer_cert = x509.load_pem_x509_certificate(open(PEER_CERT_PATH, "rb").read())
    ca_cert = x509.load_pem_x509_certificate(open(CA_CERT_PATH, "rb").read())

    return peer_cert, ca_cert


def validate_certificate(peer_cert, ca_cert):
    try:
        ca_public_key = ca_cert.public_key()

        ca_public_key.verify(
            peer_cert.signature,
            peer_cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            peer_cert.signature_hash_algorithm,
        )
        return True

    except Exception as e:
        print("Erro a validar certificado:", e)
        return False


def load_peer_private_key():
    return serialization.load_pem_private_key(
        open(PEER_KEY_PATH, "rb").read(), password=None
    )


def derive_eth_address(public_key):
    pub_bytes = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    address = Web3.keccak(pub_bytes)[-20:]
    return Web3.to_checksum_address(address.hex())


def blockchain_verify_registration(address):
    abi = json.load(open(ABI_PATH))["abi"]
    contract = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

    return contract.functions.isRegistered(address).call()


def login():
    print("\n=== LOGIN DO PEER ===")

    peer_cert, ca_cert = load_certificates()

    print("[1] Validando certificado...")
    if not validate_certificate(peer_cert, ca_cert):
        print("❌ Certificado inválido!")
        return None

    print("[2] Certificado válido ✔")

    peer_private_key = load_peer_private_key()
    peer_public_key = peer_private_key.public_key()
    eth_address = derive_eth_address(peer_public_key)

    print(f"[3] Endereço Ethereum derivado: {eth_address}")

    print("[4] Verificando registo na blockchain...")
    is_registered = blockchain_verify_registration(eth_address)

    if not is_registered:
        print("❌ Peer NÃO está registado na Blockchain!")
        return None

    print("✔ Peer autenticado com sucesso!")
    return {
        "peer_name": peer_cert.subject.get_attributes_for_oid(
            x509.NameOID.COMMON_NAME
        )[0].value,
        "eth_address": eth_address,
        "public_key": peer_public_key,
    }


if __name__ == "__main__":
    login()
