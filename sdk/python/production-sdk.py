import os
import yaml
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import time
from crontab import CronTab
from typing import List, Dict, Optional, Union, Callable
from dataclasses import dataclass
from datetime import datetime
import backoff
import json

# -----------------------
# Logging Configuration
# -----------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# -----------------------
# Exceptions
# -----------------------
class SDKException(Exception):
    """Base exception for SDK-related errors."""
    pass

class ConfigurationError(SDKException):
    """Raised when there's an issue with configuration."""
    pass

class AuthenticationError(SDKException):
    """Raised when authentication fails."""
    pass

class APIError(SDKException):
    """Raised when API calls fail."""
    pass

# -----------------------
# Data Models
# -----------------------
@dataclass
class ProcessingResult:
    """Represents the result of document processing."""
    url: str
    status: str
    processed_at: datetime
    metadata: Optional[Dict] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert the result to a dictionary."""
        return {
            'url': self.url,
            'status': self.status,
            'processed_at': self.processed_at.isoformat(),
            'metadata': self.metadata,
            'error': self.error
        }

# -----------------------
# Configuration
# -----------------------
class Config:
    """Configuration manager for the SDK."""
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), 'env.yaml')
        self.config = self._load_config()
        self._validate_config()

    def _load_config(self) -> Dict:
        """Load configuration from file or environment variables."""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as file:
                return yaml.safe_load(file)
        
        # Fallback to environment variables
        return {
            'API_ENDPOINT': os.getenv('API_ENDPOINT'),
            'API_KEY': os.getenv('API_KEY'),
            'GCP_JSON_KEY_PATH': os.getenv('GCP_JSON_KEY_PATH')
        }

    def _validate_config(self):
        """Validate required configuration values."""
        required_fields = ['API_ENDPOINT', 'API_KEY']
        missing_fields = [field for field in required_fields if not self.config.get(field)]
        if missing_fields:
            raise ConfigurationError(f"Missing required configuration: {', '.join(missing_fields)}")

    def get(self, key: str) -> Optional[str]:
        """Get a configuration value."""
        return self.config.get(key)

# -----------------------
# Authentication
# -----------------------
class Authenticator:
    """Handles authentication with GCP."""
    def __init__(self, config: Config):
        self.config = config
        self._credentials = None

    def authenticate(self) -> str:
        """Authenticate and return credentials."""
        json_key_path = self.config.get("GCP_JSON_KEY_PATH")
        if not json_key_path or not os.path.exists(json_key_path):
            raise AuthenticationError(f"GCP JSON key file not found: {json_key_path}")
        
        try:
            # Placeholder for actual GCP auth logic
            with open(json_key_path, 'r') as f:
                self._credentials = json.load(f)
            return json_key_path
        except Exception as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}")

# -----------------------
# API Client
# -----------------------
class DocumentProcessor:
    """Handles document processing API calls."""
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.get('API_KEY')}",
            "Content-Type": "application/json"
        })

    @backoff.on_exception(
        backoff.expo,
        (requests.exceptions.RequestException, APIError),
        max_tries=3,
        max_time=30
    )
    def process_document(self, url: str) -> ProcessingResult:
        """Process a single document."""
        try:
            response = self.session.post(
                f"{self.config.get('API_ENDPOINT')}/process",
                json={"url": url}
            )
            response.raise_for_status()
            data = response.json()
            
            return ProcessingResult(
                url=url,
                status=data.get('status', 'completed'),
                processed_at=datetime.now(),
                metadata=data.get('metadata')
            )
        except requests.exceptions.RequestException as e:
            logger.error(f"API call failed for URL {url}: {str(e)}")
            return ProcessingResult(
                url=url,
                status='failed',
                processed_at=datetime.now(),
                error=str(e)
            )

    def process_batch(
        self,
        urls: List[str],
        max_workers: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessingResult]:
        """Process multiple documents concurrently."""
        results = []
        total = len(urls)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {executor.submit(self.process_document, url): url for url in urls}
            
            for future in as_completed(future_to_url):
                result = future.result()
                results.append(result)
                completed += 1
                
                if progress_callback:
                    progress_callback(completed, total)
                else:
                    logger.info(f"Progress: {completed}/{total} documents processed")

        return results

# -----------------------
# Scheduler
# -----------------------
class DocumentProcessingScheduler:
    """Handles scheduling of document processing jobs."""
    def __init__(self, script_path: str):
        self.script_path = script_path
        self.cron = CronTab(user=True)

    def schedule_job(self, schedule: str = "0 18 * * *", comment: str = "Document Processing Job"):
        """Schedule a document processing job."""
        try:
            # Remove existing jobs with the same comment
            existing_jobs = self.cron.find_comment(comment)
            for job in existing_jobs:
                self.cron.remove(job)

            # Create new job
            job = self.cron.new(command=f"python {self.script_path}", comment=comment)
            job.setall(schedule)
            self.cron.write()
            
            logger.info(f"Scheduled job: {job}")
            return job
        except Exception as e:
            raise SDKException(f"Failed to schedule job: {str(e)}")

# -----------------------
# Main SDK Class
# -----------------------
class DocumentProcessingSDK:
    """Main SDK class that orchestrates all functionality."""
    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self.authenticator = Authenticator(self.config)
        self.processor = DocumentProcessor(self.config)
        
    def authenticate(self) -> str:
        """Authenticate with GCP."""
        return self.authenticator.authenticate()
    
    def process_documents(
        self,
        urls: List[str],
        max_workers: int = 5,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[ProcessingResult]:
        """Process multiple documents."""
        return self.processor.process_batch(urls, max_workers, progress_callback)
    
    def schedule_processing(
        self,
        script_path: str,
        schedule: str = "0 18 * * *",
        comment: str = "Document Processing Job"
    ):
        """Schedule document processing."""
        scheduler = DocumentProcessingScheduler(script_path)
        return scheduler.schedule_job(schedule, comment)

# -----------------------
# Example Usage
# -----------------------
if __name__ == "__main__":
    def progress_callback(completed: int, total: int):
        print(f"Progress: {completed}/{total} documents processed")

    try:
        # Initialize SDK
        sdk = DocumentProcessingSDK()
        
        # Authenticate
        creds = sdk.authenticate()
        logger.info("Authentication successful")
        
        # Process documents
        test_urls = [
            "https://example.com/document1.pdf",
            "https://example.com/document2.pdf"
        ]
        
        results = sdk.process_documents(
            urls=test_urls,
            max_workers=3,
            progress_callback=progress_callback
        )
        
        # Log results
        for result in results:
            logger.info(f"Document {result.url}: {result.status}")
        
        # Schedule daily processing
        sdk.schedule_processing(
            script_path=__file__,
            schedule="0 18 * * *",  # Run at 6 PM daily
            comment="Daily Document Processing"
        )
        
    except SDKException as e:
        logger.error(f"SDK Error: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
