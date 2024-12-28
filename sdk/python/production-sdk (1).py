import os
import yaml
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import unittest
from unittest.mock import patch, MagicMock

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

# -----------------------
# Document Processor
# -----------------------
class DocumentProcessor:
    """Handles document processing API calls."""
    def __init__(self, api_endpoint: str, api_key: str):
        """
        Initialize the document processor.
        
        Args:
            api_endpoint: Base URL for the API
            api_key: Authentication key for API access
        """
        self.api_endpoint = api_endpoint
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })

    def process_document(self, url: str) -> ProcessingResult:
        """
        Process a single document.
        
        Args:
            url: URL of the document to process
            
        Returns:
            ProcessingResult object containing the processing status
            
        Raises:
            APIError: If the API call fails
        """
        try:
            response = self.session.post(
                f"{self.api_endpoint}/process",
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
            raise APIError(f"Failed to process document: {str(e)}")

    def process_batch(
        self,
        urls: List[str],
        max_workers: int = 5
    ) -> List[ProcessingResult]:
        """
        Process multiple documents concurrently.
        
        Args:
            urls: List of document URLs to process
            max_workers: Maximum number of concurrent workers
            
        Returns:
            List of ProcessingResult objects
        """
        results = []
        total = len(urls)
        completed = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(self.process_document, url): url 
                for url in urls
            }
            
            for future in as_completed(future_to_url):
                try:
                    result = future.result()
                    results.append(result)
                    completed += 1
                    logger.info(f"Progress: {completed}/{total} documents processed")
                except APIError as e:
                    url = future_to_url[future]
                    logger.error(f"Failed to process {url}: {str(e)}")
                    results.append(ProcessingResult(
                        url=url,
                        status='failed',
                        processed_at=datetime.now(),
                        error=str(e)
                    ))

        return results

# -----------------------
# Tests
# -----------------------
class TestDocumentProcessor(unittest.TestCase):
    """Test cases for the DocumentProcessor class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.api_endpoint = "https://api.example.com"
        self.api_key = "test_key"
        self.processor = DocumentProcessor(self.api_endpoint, self.api_key)
        
    def test_process_document_success(self):
        """Test successful document processing."""
        with patch('requests.Session.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "completed",
                "metadata": {"pages": 5}
            }
            mock_post.return_value = mock_response
            
            result = self.processor.process_document("https://example.com/doc1.pdf")
            
            self.assertEqual(result.status, "completed")
            self.assertEqual(result.metadata, {"pages": 5})
            mock_post.assert_called_once()

    def test_process_document_api_error(self):
        """Test handling of API errors."""
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.exceptions.RequestException("API Error")
            
            with self.assertRaises(APIError):
                self.processor.process_document("https://example.com/doc1.pdf")

    def test_process_batch(self):
        """Test batch processing of documents."""
        test_urls = [
            "https://example.com/doc1.pdf",
            "https://example.com/doc2.pdf"
        ]
        
        with patch('requests.Session.post') as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "status": "completed",
                "metadata": {"pages": 5}
            }
            mock_post.return_value = mock_response
            
            results = self.processor.process_batch(test_urls, max_workers=2)
            
            self.assertEqual(len(results), 2)
            self.assertTrue(all(r.status == "completed" for r in results))
            self.assertEqual(mock_post.call_count, 2)

    def test_process_batch_with_failures(self):
        """Test batch processing with some failures."""
        test_urls = [
            "https://example.com/doc1.pdf",
            "https://example.com/doc2.pdf"
        ]
        
        def mock_post(*args, **kwargs):
            if "doc1" in kwargs['json']['url']:
                return MagicMock(json=lambda: {"status": "completed"})
            raise requests.exceptions.RequestException("API Error")

        with patch('requests.Session.post', side_effect=mock_post):
            results = self.processor.process_batch(test_urls, max_workers=2)
            
            self.assertEqual(len(results), 2)
            success_results = [r for r in results if r.status == "completed"]
            failed_results = [r for r in results if r.status == "failed"]
            self.assertEqual(len(success_results), 1)
            self.assertEqual(len(failed_results), 1)

if __name__ == "__main__":
    unittest.main()
