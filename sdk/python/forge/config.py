import os
import yaml
from feedback_forge_sdk.exceptions import ConfigurationError

class Config:
    def __init__(self, config_path=None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'env.yaml')
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    return yaml.safe_load(file)
            return {
                'API_ENDPOINT': os.getenv('API_ENDPOINT'),
                'API_KEY': os.getenv('API_KEY'),
                'GCP_JSON_KEY_PATH': os.getenv('GCP_JSON_KEY_PATH')
            }
        except Exception as e:
            raise ConfigurationError("Failed to load configuration", e)

    def _validate_config(self):
        required_fields = ['API_ENDPOINT', 'API_KEY']
        missing_fields = [field for field in required_fields if not self.config.get(field)]
        if missing_fields:
            raise ConfigurationError(f"Missing required configuration: {', '.join(missing_fields)}")

    def get(self, key):
        return self.config.get(key)
