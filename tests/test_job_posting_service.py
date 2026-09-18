import unittest
from unittest.mock import patch

from app.services.job_posting_service import (
    JobPostingIdentity,
    extract_job_posting,
)


class JobPostingServiceTests(unittest.TestCase):
    @patch("app.services.job_posting_service.parse")
    def test_preserves_original_posting_without_model_repeating_it(self, parse):
        parse.return_value = JobPostingIdentity(
            company="Optum Tech",
            title="Software Engineer",
        )
        raw_posting = "Optum Tech\nSoftware Engineer\nBuild reliable systems."

        result = extract_job_posting(raw_posting)

        self.assertEqual(result.company, "Optum Tech")
        self.assertEqual(result.title, "Software Engineer")
        self.assertEqual(result.description, raw_posting)
        self.assertIs(
            parse.call_args.kwargs["response_model"],
            JobPostingIdentity,
        )
        self.assertNotIn("Job description", parse.call_args.kwargs["prompt"])
        self.assertIn(
            "dominant responsibilities and seniority",
            parse.call_args.kwargs["prompt"],
        )
        self.assertIn("Never return placeholders", parse.call_args.kwargs["prompt"])

    def test_rejects_missing_role_placeholders(self):
        with self.assertRaisesRegex(ValueError, "usable company and role title"):
            JobPostingIdentity(company="Armanino", title="Not stated")

    @patch("app.services.job_posting_service.parse")
    def test_rejects_empty_posting_without_api_call(self, parse):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            extract_job_posting("   ")

        parse.assert_not_called()


if __name__ == "__main__":
    unittest.main()
