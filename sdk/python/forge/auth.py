import json
from feedback_forge_sdk.exceptions import AuthenticationError

class Authenticator:
    def __init__(self, config):
        self.config = config

    def authenticate(self):
        try:
            json_key_path = self.config.get("GCP_JSON_KEY_PATH")
            if not json_key_path or not os.path.exists(json_key_path):
                raise AuthenticationError(f"GCP JSON key file not found: {json_key_path}")

            with open(json_key_path, 'r') as f:
                return json.load(f)
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError("Authentication failed", e)
