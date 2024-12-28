# Feedback Forge SDK

## Overview
The Feedback Forge SDK is a Python library designed for seamless document processing using the Feedback Forge API. It includes features such as concurrent processing, custom job scheduling, and robust error handling.

## Features
- **Configuration Loader:** Supports YAML-based and environment variable configurations.
- **Authentication:** Secure authentication using GCP JSON keys.
- **Concurrent Processing:** Process multiple documents in parallel with progress tracking.
- **Scheduling:** Schedule daily processing jobs with cron integration.
- **Custom Exceptions:** Clear error diagnosis with specific exception classes.

## Installation
Install the SDK via pip:

```bash
pip install feedback-forge-sdk
```

Alternatively, install from source:

```bash
git clone https://github.com/your-repo/feedback-forge-sdk.git
cd feedback-forge-sdk
pip install .
```

## Usage

### Basic Setup
```python
from feedback_forge_sdk import DocumentProcessingSDK

# Initialize the SDK
sdk = DocumentProcessingSDK(config_path="env.yaml")

# Authenticate
sdk.authenticate()
```

### Processing Documents
```python
test_urls = [
    "https://example.com/document1.pdf",
    "https://example.com/document2.pdf"
]

# Process documents
results = sdk.process_documents(urls=test_urls)

# Log results
for result in results:
    print(f"Document {result.url}: {result.status}")
```

### Scheduling Jobs
```python
sdk.schedule_processing(
    script_path="/path/to/your/script.py",
    schedule="0 18 * * *"  # Run daily at 6 PM
)
```

## Configuration
Create an `env.yaml` file with the following structure:

```yaml
API_ENDPOINT: "https://api.feedbackforge.com"
API_KEY: "your_api_key"
GCP_JSON_KEY_PATH: "path/to/gcp_credentials.json"
```

## Testing
Run the tests using:

```bash
python -m unittest discover tests
```

## License
This project is licensed under the MIT License.
