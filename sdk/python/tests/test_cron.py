import unittest
from feedback_forge_sdk.cron import DocumentProcessingScheduler
from feedback_forge_sdk.exceptions import SchedulingError

class TestCron(unittest.TestCase):
    def setUp(self):
        self.scheduler = DocumentProcessingScheduler(script_path="dummy_script.py")

    def test_schedule_job(self):
        job = self.scheduler.schedule_job(schedule="0 18 * * *")
        self.assertIsNotNone(job)

    def test_schedule_job_failure(self):
        with self.assertRaises(SchedulingError):
            self.scheduler.schedule_job(schedule="invalid_schedule")

if __name__ == "__main__":
    unittest.main()
