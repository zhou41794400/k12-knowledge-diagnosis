import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from services.edu_tracker.data_management import (
    create_backup,
    delete_student,
    export_student,
    health_status,
    restore_backup,
)
from services.edu_tracker.pipeline import LocalPipeline
from tests.helpers import write_point


class DataManagementTests(unittest.TestCase):
    def test_export_delete_and_health(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            vault = project / "教育智能体"
            write_point(vault / "02-课标与知识体系" / "02-国家课标知识树")
            pipeline = LocalPipeline(vault)
            pipeline.process_manual_question(
                student_id="keep", subject="数学", grade="二年级",
                text="乘法口诀练习", answer="6", student_answer="6",
            )
            pipeline.process_manual_question(
                student_id="remove", subject="数学", grade="二年级",
                text="乘法口诀练习", answer="6", student_answer="5",
            )

            exported = export_student(project, "remove")
            with zipfile.ZipFile(exported) as archive:
                payload = json.loads(archive.read("学生数据.json"))
            self.assertEqual(payload["student_id"], "remove")
            self.assertEqual(len(payload["questions"]), 1)

            deleted = delete_student(project, "remove", "remove")
            self.assertGreater(deleted["records"], 0)
            self.assertEqual(pipeline.store.load_records("questions", "remove"), [])
            self.assertEqual(len(pipeline.store.load_records("questions", "keep")), 1)
            self.assertEqual(health_status(project)["questions"], 1)

    def test_backup_restores_to_new_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir) / "project"
            note = project / "教育智能体" / "note.md"
            note.parent.mkdir(parents=True)
            note.write_text("备份验证", encoding="utf-8")
            backup = create_backup(project)
            restored = restore_backup(backup, Path(temp_dir) / "restored")
            self.assertEqual((restored / "教育智能体" / "note.md").read_text(encoding="utf-8"), "备份验证")

    def test_delete_requires_exact_confirmation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                delete_student(Path(temp_dir), "s1", "wrong")


if __name__ == "__main__":
    unittest.main()
