import unittest
from feedback_forge_sdk.sdk import DocumentProcessingSDK
from feedback_forge_sdk.exceptions import ValidationError

class TestSDK(unittest.TestCase):
    def setUp(self):
        self.sdk = DocumentProcessingSDK(config_path="env.yaml")

    def test_process_documents_success(self):
        test_urls = ["https://example.com/doc1", "https://example.com/doc2"]
        results = self.sdk.process_documents(urls=test_urls)
        self.assertEqual(len(results), len(test_urls))

    def test_process_documents_failure(self):
        with self.assertRaises(ValidationError):
            self.sdk.process_documents(urls=[])

if __name__ == "__main__":
    unittest.main()
