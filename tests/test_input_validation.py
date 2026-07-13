import unittest

from services.edu_tracker.input_validation import validate_context, validate_question_text


class InputValidationTests(unittest.TestCase):
    def test_rejects_path_like_student_id(self) -> None:
        with self.assertRaises(ValueError):
            validate_context("../../student", "数学", "二年级")

    def test_rejects_empty_or_oversized_question(self) -> None:
        with self.assertRaises(ValueError):
            validate_question_text("  ")
        with self.assertRaises(ValueError):
            validate_question_text("x" * 10001)


if __name__ == "__main__":
    unittest.main()
