class CAState:
    _instance = None

    def __init__(self):
        self.private_key = None
        self.certificate = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = CAState()
        return cls._instance

    def is_ready(self):
        return self.private_key is not None and self.certificate is not None

ca_state = CAState.get_instance()