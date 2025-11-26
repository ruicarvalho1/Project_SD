from pathlib import Path

def get_user_folder(username: str) -> Path:
    folder = Path.home() / "Desktop" / "AuctionUsers" / username
    folder.mkdir(parents=True, exist_ok=True)
    return folder
