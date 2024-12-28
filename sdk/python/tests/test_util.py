import unittest
from feedback_forge_sdk.utils import retry

class TestUtils(unittest.TestCase):
    def test_retry_success(self):
        def mock_func():
            return "Success"
        result = retry(mock_func, retries=3)
        self.assertEqual(result, "Success")

    def test_retry_failure(self):
        def mock_func():
            raise ValueError("Failure")
        with self.assertRaises(ValueError):
            retry(mock_func, retries=2)

if __name__ == "__main__":
    unittest.main()
