"""Sample Python module for repository testing and CI/CD verification."""

import sys
import unittest


def calculate_summary(numbers: list[float]) -> dict[str, float]:
    """Calculate basic statistical metrics for a list of numbers."""
    if not numbers:
        raise ValueError("List of numbers cannot be empty.")

    total = sum(numbers)
    count = len(numbers)
    return {
        "count": float(count),
        "total": float(total),
        "mean": float(total / count),
        "min": float(min(numbers)),
        "max": float(max(numbers)),
    }


def is_palindrome(text: str) -> bool:
    """Check whether a given string is a palindrome, ignoring non-alphanumeric chars."""
    cleaned = "".join(char.lower() for char in text if char.isalnum())
    return cleaned == cleaned[::-1]


class TestCoreFunctions(unittest.TestCase):
    """Unit test suite for validating core logic."""

    def test_calculate_summary_valid(self):
        data = [10.0, 20.0, 30.0, 40.0]
        result = calculate_summary(data)
        self.assertEqual(result["count"], 4.0)
        self.assertEqual(result["total"], 100.0)
        self.assertEqual(result["mean"], 25.0)
        self.assertEqual(result["min"], 10.0)
        self.assertEqual(result["max"], 40.0)

    def test_calculate_summary_empty(self):
        with self.assertRaises(ValueError):
            calculate_summary([])

    def test_is_palindrome(self):
        self.assertTrue(is_palindrome("A man, a plan, a canal: Panama"))
        self.assertTrue(is_palindrome("racecar"))
        self.assertFalse(is_palindrome("github"))


def main():
    """Run tests or execute sample logic."""
    print("Running embedded test suite...")
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCoreFunctions)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if not result.wasSuccessful():
        print("Tests failed!")
        sys.exit(1)

    print("\nAll unit tests passed successfully!")
    sample_data = [4.5, 9.2, 1.8, 12.0]
    print(f"Sample calculation for {sample_data}:")
    print(calculate_summary(sample_data))


if __name__ == "__main__":
    main()
