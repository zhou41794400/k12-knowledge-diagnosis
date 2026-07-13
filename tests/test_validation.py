import json
import tempfile
import unittest
from pathlib import Path

from services.edu_tracker.validation import load_cases, validate_mapping

from tests.helpers import write_point


class ValidationTests(unittest.TestCase):
    def test_validate_mapping_reports_match_and_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            knowledge_root = root / "knowledge"
            write_point(knowledge_root)
            dataset = root / "cases.jsonl"
            cases = [
                {
                    "case_id": "hit",
                    "subject": "数学",
                    "grade": "二年级",
                    "text": "乘法口诀练习",
                    "expected_point_code": "MATH-PRI-G2-NS-003",
                    "expected_review_required": False,
                },
                {
                    "case_id": "reject",
                    "subject": "英语",
                    "grade": "二年级",
                    "text": "乘法口诀练习",
                    "expected_point_code": "",
                    "expected_review_required": True,
                },
            ]
            dataset.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in cases) + "\n", encoding="utf-8")
            result = validate_mapping(dataset, knowledge_root)
            self.assertEqual(result["total"], 2)
            self.assertEqual(result["failed"], 0)
            self.assertEqual(result["pass_rate"], 1.0)

    def test_load_cases_rejects_missing_required_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cases.jsonl"
            path.write_text('{"case_id": "broken"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "缺少字段"):
                load_cases(path)


if __name__ == "__main__":
    unittest.main()
