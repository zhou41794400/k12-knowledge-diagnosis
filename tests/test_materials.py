import tempfile
import unittest
from pathlib import Path

from services.edu_tracker.materials import _numbered_source_line, build_version_note, project_version


class MaterialsTests(unittest.TestCase):
    def test_version_is_read_from_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "pyproject.toml").write_text('[project]\nversion = "2.3.4"\n', encoding="utf-8")
            self.assertEqual(project_version(root), "2.3.4")

    def test_version_note_uses_structured_correctness_and_dynamic_stats(self) -> None:
        questions = [
            {"subject": "数学", "grade": "二年级", "is_correct": True},
            {"subject": "数学", "grade": "二年级", "is_correct": False},
            {"subject": "数学", "grade": "二年级", "is_correct": None},
        ]
        stats = {
            "point_nodes": 10,
            "trackable_cards": 8,
            "published": 3,
            "subjects": 1,
            "index_files": 2,
        }
        note = build_version_note(questions, [], [], "2.3.4", stats)
        self.assertIn("当前版本：v2.3.4", note)
        self.assertIn("正确题数 | 1", note)
        self.assertIn("错题数 | 1", note)
        self.assertIn("待判断题数 | 1", note)
        self.assertIn("可追踪知识点卡 | 8", note)

    def test_version_note_separates_current_and_legacy_evidence(self) -> None:
        stats = {
            "point_nodes": 1,
            "trackable_cards": 1,
            "published": 1,
            "subjects": 1,
            "index_files": 1,
        }
        mastery = [{"last_evidence_id": "current"}, {"last_evidence_id": "legacy"}]
        evidence = [
            {"event_id": "current", "model_version": "rule-v2"},
            {"event_id": "legacy", "model_version": "rule-v1"},
        ]
        note = build_version_note([], mastery, [], "2.3.4", stats, evidence)
        self.assertIn("当前模型有效掌握状态数 | 1", note)
        self.assertIn("当前模型有效证据数 | 1", note)
        self.assertIn("已隔离旧模型证据数 | 1", note)

    def test_numbered_source_blank_line_has_no_trailing_whitespace(self) -> None:
        self.assertEqual(_numbered_source_line(7, ""), "    7|")
        self.assertEqual(_numbered_source_line(8, "value = 1"), "    8| value = 1")


if __name__ == "__main__":
    unittest.main()
