"""Lightweight URL health checker and validation utility for repository testing."""

import json
import logging
import sys
import unittest
from dataclasses import asdict, dataclass
from typing import Optional
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
)


@dataclass
class HealthCheckResult:
    url: str
    is_valid_format: bool
    scheme: Optional[str]
    host: Optional[str]
    status: str


class URLValidator:
    """Validates and processes URL configurations."""

    @staticmethod
    def validate(url: str) -> HealthCheckResult:
        if not url or not isinstance(url, str):
            return HealthCheckResult(
                url=str(url),
                is_valid_format=False,
                scheme=None,
                host=None,
                status="INVALID_INPUT",
            )

        parsed = urlparse(url.strip())
        is_valid = bool(parsed.scheme in ("http", "https") and parsed.netloc)

        return HealthCheckResult(
            url=url,
            is_valid_format=is_valid,
            scheme=parsed.scheme if is_valid else None,
            host=parsed.netloc if is_valid else None,
            status="READY" if is_valid else "INVALID_URL",
        )

    @classmethod
    def batch_validate(cls, urls: list[str]) -> list[HealthCheckResult]:
        return [cls.validate(u) for u in urls]


class TestURLValidator(unittest.TestCase):
    """Test suite covering edge cases and URL parsing rules."""

    def test_valid_https_url(self):
        res = URLValidator.validate("https://api.github.com/events")
        self.assertTrue(res.is_valid_format)
        self.assertEqual(res.scheme, "https")
        self.assertEqual(res.host, "api.github.com")
        self.assertEqual(res.status, "READY")

    def test_missing_scheme(self):
        res = URLValidator.validate("github.com/features")
        self.assertFalse(res.is_valid_format)
        self.assertEqual(res.status, "INVALID_URL")

    def test_empty_input(self):
        res = URLValidator.validate("")
        self.assertFalse(res.is_valid_format)
        self.assertEqual(res.status, "INVALID_INPUT")

    def test_batch_validation(self):
        targets = [
            "https://httpbin.org/get",
            "invalid-url",
            "http://localhost:8000/health",
        ]
        results = URLValidator.batch_validate(targets)
        self.assertEqual(len(results), 3)
        self.assertTrue(results[0].is_valid_format)
        self.assertFalse(results[1].is_valid_format)
        self.assertTrue(results[2].is_valid_format)


def run_pipeline() -> int:
    """Execute test verification and sample batch processing."""
    logging.info("Executing automated test suite...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestURLValidator)
    runner = unittest.TextTestRunner(verbosity=2)
    test_result = runner.run(suite)

    if not test_result.wasSuccessful():
        logging.error("One or more tests failed.")
        return 1

    logging.info("All tests passed! Running demo execution...")
    sample_urls = [
        "https://api.github.com",
        "https://raw.githubusercontent.com",
        "ftp://invalid-target.internal",
        "https://google.com/search?q=test",
    ]

    processed = URLValidator.batch_validate(sample_urls)
    output = [asdict(r) for r in processed]
    print("\nBatch Verification Output:")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(run_pipeline())
