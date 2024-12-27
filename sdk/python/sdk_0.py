import os
import yaml
import logging
import requests
from concurrent.futures import ThreadPoolExecutor
import time
from crontab import CronTab
from typing import List
import unittest

# -----------------------
# Logging Configuration
# -----------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------
# config.py
# -----------------------
def load_config():
    """Load configuration from env.yaml."""
    config_path = os.path.join(os.path.dirname(__file__), 'env.yaml')
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)

config = load_config()

# -----------------------
# auth.py
# -----------------------
def authenticate():
    """Authenticate using GCP JSON key and return necessary credentials."""
    json_key_path = config.get("GCP_JSON_KEY_PATH")
    if not os.path.exists(json_key_path):
        raise FileNotFoundError(f"GCP JSON key file not found: {json_key_path}")
    return json_key_path  # Placeholder for actual GCP auth logic

# -----------------------
# utils.py
# -----------------------
def retry(func, retries=3, delay=2):
    """Retry a function call with exponential backoff."""
    for attempt in range(retries):
        try:
            return func()
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(delay * (2 ** attempt))
    raise Exception(f"All {retries} retries failed.")

def monitor_progress(urls: List[str], completed):
    """Log progress of document processing."""
    total = len(urls)
    while completed.qsize() < total:
        logger.info(f"Progress: {completed.qsize()}/{total} documents processed.")
        time.sleep(1)

# -----------------------
# sdk.py
# -----------------------
def call_process(url: str):
    """Call the /process endpoint with a document URL."""
    endpoint = config.get("API_ENDPOINT")
    if not endpoint:
        raise ValueError("API endpoint is not configured.")

    headers = {"Authorization": f"Bearer {config.get('API_KEY')}"}
    payload = {"url": url}

    def make_request():
        response = requests.post(f"{endpoint}/process", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    return retry(make_request)

def process_documents(urls: List[str]):
    """Process multiple document URLs using the /process endpoint."""
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(call_process, url) for url in urls]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                logger.error(f"Failed to process document: {e}")
    return results

# -----------------------
# cron.py
# -----------------------
def create_cron_job(script_path: str, schedule: str = "0 18 * * *"):
    """Create a cron job to run the script at the specified schedule."""
    cron = CronTab(user=True)
    job = cron.new(command=f"python {script_path}", comment="Process Documents Cron Job")
    job.setall(schedule)
    cron.write()
    logger.info(f"Cron job created: {job}")

# -----------------------
# Unit Tests (tests/test_sdk.py)
# -----------------------
class TestSDK(unittest.TestCase):
    def test_load_config(self):
        config = load_config()
        self.assertIn("API_ENDPOINT", config)
        self.assertIn("API_KEY", config)

    def test_retry_success(self):
        def mock_func():
            return "Success"
        self.assertEqual(retry(mock_func), "Success")

    def test_retry_failure(self):
        def mock_func():
            raise ValueError("Failure")
        with self.assertRaises(Exception):
            retry(mock_func, retries=2)

    def test_call_process_invalid_url(self):
        with self.assertRaises(Exception):
            call_process("invalid_url")

    def test_process_documents(self):
        def mock_call_process(url):
            return {"url": url, "status": "processed"}
        global call_process
        original_call_process = call_process
        call_process = mock_call_process
        urls = ["https://example.com/doc1", "https://example.com/doc2"]
        results = process_documents(urls)
        self.assertEqual(len(results), len(urls))
        call_process = original_call_process

if __name__ == "__main__":
    unittest.main()

# -----------------------
# Example Usage (examples/process_documents.py)
# -----------------------
if __name__ == "__main__":
    from queue import Queue

    test_urls = [
        "https://example.com/document1.pdf",
        "https://example.com/document2.pdf"
    ]

    try:
        creds = authenticate()
        logger.info(f"Authenticated successfully with credentials: {creds}")
        
        completed = Queue()
        monitor_thread = ThreadPoolExecutor().submit(monitor_progress, test_urls, completed)

        results = process_documents(test_urls)
        for _ in test_urls:
            completed.put(1)

        monitor_thread.result()  # Wait for monitoring to complete

        logger.info(f"Processing results: {results}")

        create_cron_job(script_path=__file__)

    except Exception as error:
        logger.error(f"An error occurred: {error}")
