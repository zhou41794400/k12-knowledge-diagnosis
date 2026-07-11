import json
import tempfile
import unittest
from pathlib import Path

from services.edu_tracker.storage import SQLiteStore


class StorageTests(unittest.TestCase):
    def test_database_schema_version_is_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "edu_tracker.sqlite3"
            SQLiteStore(path)
            import sqlite3
            with sqlite3.connect(path) as db:
                self.assertEqual(db.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_resolved_review_payload_matches_database_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = SQLiteStore(Path(temp_dir) / "edu_tracker.sqlite3")
            review = {
                "review_id": "r_i1", "student_id": "s1", "source_type": "photo",
                "target_id": "i1", "reason": "OCR待确认", "status": "待处理",
                "created_at": "2026-07-11T00:00:00Z",
            }
            store.commit_operation([], review_task=review)
            store.commit_operation([], resolve_review_id="r_i1", resolved_at="2026-07-11T01:00:00Z")

            resolved = store.load_review_tasks(status="已解决")
            self.assertEqual(resolved[0]["status"], "已解决")
            self.assertEqual(resolved[0]["resolved_at"], "2026-07-11T01:00:00Z")

    def test_outbox_recovers_after_jsonl_write_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            log_dir = root / "logs"
            log_dir.mkdir()
            store = SQLiteStore(log_dir / "edu_tracker.sqlite3")
            payload = {"question_id": "q1", "student_id": "s1", "created_at": "2026-07-11T00:00:00Z"}
            store.commit_operation([("questions.jsonl", payload)])

            blocked_path = log_dir / "questions.jsonl"
            blocked_path.mkdir()
            with self.assertRaises(IsADirectoryError):
                store.flush_outbox(log_dir)
            self.assertEqual(store.get_record("questions", "q1"), payload)

            blocked_path.rmdir()
            self.assertEqual(store.flush_outbox(log_dir), 1)
            self.assertEqual(json.loads(blocked_path.read_text(encoding="utf-8")), payload)
            self.assertEqual(store.flush_outbox(log_dir), 0)


if __name__ == "__main__":
    unittest.main()
