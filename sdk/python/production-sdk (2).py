import os
import yaml
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from crontab import CronTab
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
    """Base exception for all SDK-related errors."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.original_error = original_error

class ConfigurationError(SDKException):
    """Raised when there are issues with SDK configuration."""
    pass

class AuthenticationError(SDKException):
    """Raised when authentication fails."""
    pass

class APIError(SDKException):
    """Raised when API calls fail."""
    pass

class SchedulingError(SDKException):
    """Raised when job scheduling fails."""
    pass

class ValidationError(SDKException):
    """Raised when input validation fails."""
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
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as file:
                    return yaml.safe_load(file)
            
            # Fallback to environment variables
            return {
                'API_ENDPOINT': os.getenv('API_ENDPOINT'),
                'API_KEY': os.getenv('API_KEY'),
                'GCP_JSON_KEY_PATH': os.getenv('GCP_JSON_KEY_PATH')
            }
        except Exception as e:
            raise ConfigurationError("Failed to load configuration", e)

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
        try:
            json_key_path = self.config.get("GCP_JSON_KEY_PATH")
            if not json_key_path or not os.path.exists(json_key_path):
                raise AuthenticationError(f"GCP JSON key file not found: {json_key_path}")
            
            with open(json_key_path, 'r') as f:
                self._credentials = json.load(f)
            return json_key_path
        except AuthenticationError:
            raise
        except Exception as e:
            raise AuthenticationError("Authentication failed", e)

# -----------------------
# API Client
# -----------------------
class APIClient:
    """Handles API communications."""
    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.get('API_KEY')}",
            "Content-Type": "application/json"
        })

    def post(self, endpoint: str, data: Dict) -> Dict:
        """Make a POST request to the API."""
        try:
            url = f"{self.config.get('API_ENDPOINT')}{endpoint}"
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"API request failed: {str(e)}", e)

# -----------------------
# Document Processor
# -----------------------
class DocumentProcessor:
    """Handles document processing operations."""
    def __init__(self, api_client: APIClient):
        self.api_client = api_client

    def process_document(self, url: str) -> ProcessingResult:
        """Process a single document."""
        try:
            data = self.api_client.post("/process", {"url": url})
            return ProcessingResult(
                url=url,
                status=data.get('status', 'completed'),
                processed_at=datetime.now(),
                metadata=data.get('metadata')
            )
        except APIError as e:
            logger.error(f"Failed to process document {url}: {str(e)}")
            raise

    def process_batch(
        self,
        urls: List[str],
        max_workers: int = 5
    ) -> List[ProcessingResult]:
        """Process multiple documents concurrently."""
        if not urls:
            raise ValidationError("No URLs provided for processing")

        results = []
        total = len(urls)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.process_document, url): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append(ProcessingResult(
                        url=url,
                        status='failed',
                        processed_at=datetime.now(),
                        error=str(e)
                    ))
                completed += 1
                logger.info(f"Progress: {completed}/{total} documents processed")

        return results

# -----------------------
# Scheduler
# -----------------------
class DocumentProcessingScheduler:
    """Handles scheduling of document processing jobs."""
    def __init__(self, script_path: str):
        self.script_path = script_path
        try:
            self.cron = CronTab(user=True)
        except Exception as e:
            raise SchedulingError("Failed to initialize scheduler", e)

    def schedule_job(self, schedule: str = "0 18 * * *", comment: str = "Document Processing Job"):
        """Schedule a document processing job."""
        try:
            # Remove existing jobs with the same comment
            existing_jobs = list(self.cron.find_comment(comment))
            if existing_jobs:
                logger.info(f"Removing {len(existing_jobs)} existing jobs")
                for job in existing_jobs:
                    self.cron.remove(job)

            # Create new job
            job = self.cron.new(command=f"python {self.script_path}", comment=comment)
            job.setall(schedule)
            self.cron.write()
            
            logger.info(f"Scheduled job: {job}")
            return job
        except Exception as e:
            raise SchedulingError(f"Failed to schedule job: {str(e)}", e)

# -----------------------
# Main SDK Class
# -----------------------
class DocumentProcessingSDK:
    """Main SDK class that orchestrates all functionality."""
    def __init__(self, config_path: Optional[str] = None):
        self.config = Config(config_path)
        self.authenticator = Authenticator(self.config)
        self.api_client = APIClient(self.config)
        self.processor = DocumentProcessor(self.api_client)
        
    def authenticate(self) -> str:
        """Authenticate with GCP."""
        return self.authenticator.authenticate()
    
    def process_documents(
        self,
        urls: List[str],
        max_workers: int = 5
    ) -> List[ProcessingResult]:
        """Process multiple documents."""
        return self.processor.process_batch(urls, max_workers)
    
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
        
        results = sdk.process_documents(urls=test_urls, max_workers=3)
        
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
        if e.original_error:
            logger.error(f"Original error: {str(e.original_error)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
