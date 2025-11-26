from login_menu import login
from auction_menu import handle_bid
from identity.paths import get_user_folder

def main():
    username=login()

    user_folder = get_user_folder(username)

    handle_bid(user_folder)
    if not identity_exists(user_folder):
        print("No identity found. Creating new one...")

        private_key = generate_keypair()
        save_private_key(private_key, user_folder / "client_private_key.pem")

        csr_pem = generate_csr(private_key, username)

        # Fetch CA cert (TOFU)
        ca_pem = fetch_ca_certificate()
        (user_folder / "ca_cert.pem").write_text(ca_pem)
        ca_cert = load_ca_cert(user_folder / "ca_cert.pem")

        # Request certificate
        client_cert_pem = request_certificate(csr_pem)

        # Validate BEFORE saving
        if not validate_cert_with_ca(client_cert_pem, ca_cert):
            print("FATAL: Certificate returned by CA is invalid. Aborting.")
            return

        # Save certificate
        (user_folder / "client_cert.pem").write_text(client_cert_pem)

        print("Identity created successfully.")

    else:
        print("Identity already exists.")

    cert_pem = (user_folder / "client_cert.pem").read_text()

    resp = login_with_certificate(cert_pem)
    print("Login response:", resp.json())




if __name__ == "__main__":
    main()
