import unittest
from feedback_forge_sdk.auth import Authenticator
from feedback_forge_sdk.config import Config
from feedback_forge_sdk.exceptions import AuthenticationError

class TestAuthenticator(unittest.TestCase):
    def setUp(self):
        self.config = Config(config_path="env.yaml")
        self.authenticator = Authenticator(self.config)

    def test_authenticate_success(self):
        creds = self.authenticator.authenticate()
        self.assertIsInstance(creds, dict)

    def test_authenticate_failure(self):
        self.config.config["GCP_JSON_KEY_PATH"] = "invalid_path.json"
        with self.assertRaises(AuthenticationError):
            self.authenticator.authenticate()

if __name__ == "__main__":
    unittest.main()
