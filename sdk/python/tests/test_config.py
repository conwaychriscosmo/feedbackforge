import unittest
from feedback_forge_sdk.config import Config
from feedback_forge_sdk.exceptions import ConfigurationError
import os

class TestConfig(unittest.TestCase):
    def test_load_valid_config(self):
        config = Config(config_path="env.yaml")
        self.assertIsNotNone(config.get("API_ENDPOINT"))
        self.assertIsNotNone(config.get("API_KEY"))

    def test_missing_config(self):
        with self.assertRaises(ConfigurationError):
            Config(config_path="non_existent.yaml")

    def test_missing_required_fields(self):
        os.environ.pop("API_ENDPOINT", None)
        os.environ.pop("API_KEY", None)
        with self.assertRaises(ConfigurationError):
            Config()

if __name__ == "__main__":
    unittest.main()
