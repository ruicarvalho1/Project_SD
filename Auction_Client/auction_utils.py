NEEDS_REFRESH = False


def signal_refresh():
    global NEEDS_REFRESH
    NEEDS_REFRESH = True


try:
    from p2p_ws_client import broadcast_to_peers
except ImportError:
    def broadcast_to_peers(*args, **kwargs):
        print(" [WARNING] P2P module not found. Notifications will not be broadcast.")
