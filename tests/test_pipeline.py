import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from services.edu_tracker.pipeline import LocalPipeline
from services.edu_tracker.ocr import OCRResult

from tests.helpers import write_point


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp_dir.name)
        self.knowledge_root = self.vault / "02-课标与知识体系" / "02-国家课标知识树"
        write_point(self.knowledge_root)
        self.pipeline = LocalPipeline(self.vault)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_mastery_accumulates_for_confirmed_evidence(self) -> None:
        first = self.pipeline.process_manual_question(
            student_id="s1",
            subject="数学",
            grade="二年级",
            text="乘法口诀练习",
            answer="6",
            student_answer="6",
        )
        second = self.pipeline.process_manual_question(
            student_id="s1",
            subject="数学",
            grade="二年级",
            text="乘法口诀口算",
            answer="8",
            student_answer="8",
        )
        self.assertGreater(second["mastery"]["mastery_score"], first["mastery"]["mastery_score"])
        self.assertEqual(second["mastery"]["evidence_count"], 2)
        with sqlite3.connect(self.vault / "logs" / "edu_tracker.sqlite3") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM records WHERE record_type='questions'").fetchone()[0], 2)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM mastery_current").fetchone()[0], 1)

    def test_concurrent_mastery_updates_do_not_lose_evidence(self) -> None:
        def submit(_: int) -> None:
            LocalPipeline(self.vault).process_manual_question(
                student_id="parallel", subject="数学", grade="二年级",
                text="乘法口诀练习", answer="6", student_answer="6",
            )

        with ThreadPoolExecutor(max_workers=6) as executor:
            list(executor.map(submit, range(20)))

        mastery = self.pipeline.store.get_mastery("parallel", "MATH-PRI-G2-NS-003")
        self.assertEqual(mastery["evidence_count"], 20)

    def test_unmatched_question_does_not_create_evidence_or_mastery(self) -> None:
        result = self.pipeline.process_manual_question(
            student_id="s1",
            subject="物理",
            grade="八年级",
            text="测量物体速度",
            answer="1",
            student_answer="1",
        )
        self.assertIsNone(result["evidence"])
        self.assertIsNone(result["mastery"])
        self.assertFalse((self.vault / "logs" / "evidence.jsonl").exists())
        self.assertFalse((self.vault / "logs" / "mastery.jsonl").exists())
        question = json.loads((self.vault / "logs" / "questions.jsonl").read_text(encoding="utf-8"))
        self.assertTrue(question["review_required"])

    def test_ambiguous_match_does_not_create_evidence_or_mastery(self) -> None:
        write_point(
            self.knowledge_root,
            point_code="MATH-PRI-G2-NS-004",
            title="乘法与口诀综合",
            keywords=("乘法口诀",),
        )
        result = self.pipeline.process_manual_question(
            student_id="s1",
            subject="数学",
            grade="二年级",
            text="乘法口诀练习",
            answer="6",
            student_answer="6",
        )
        self.assertTrue(result["match"]["review_required"])
        self.assertIsNone(result["evidence"])
        self.assertIsNone(result["mastery"])

    def test_pending_answer_does_not_reduce_mastery(self) -> None:
        result = self.pipeline.process_manual_question(
            student_id="s1",
            subject="数学",
            grade="二年级",
            text="乘法口诀练习",
        )
        self.assertIsNone(result["mastery"])
        self.assertIsNone(result["evidence"])
        self.assertTrue(result["question"]["review_required"])

    def test_low_confidence_source_does_not_create_evidence(self) -> None:
        result = self.pipeline._process_question(
            source_type="photo", student_id="s1", subject="数学", grade="二年级",
            text="乘法口诀练习", answer="6", student_answer="6", image_path="paper.png",
            ocr_confidence=0.5,
        )
        self.assertIsNone(result["evidence"])
        self.assertIsNone(result["mastery"])
        self.assertTrue(result["question"]["review_required"])

    def test_rule_v2_does_not_inherit_legacy_mastery(self) -> None:
        logs = self.vault / "logs"
        logs.mkdir(exist_ok=True)
        (logs / "evidence.jsonl").write_text(
            json.dumps({"event_id": "legacy-e1", "model_version": "rule-v1"}) + "\n",
            encoding="utf-8",
        )
        (logs / "mastery.jsonl").write_text(
            json.dumps(
                {
                    "student_id": "s1",
                    "point_code": "MATH-PRI-G2-NS-003",
                    "mastery_score": 0.9,
                    "mastery_level": "熟练掌握",
                    "evidence_count": 9,
                    "negative_evidence_count": 0,
                    "review_required": False,
                    "last_updated_at": "2026-06-10T00:00:00+00:00",
                    "last_evidence_id": "legacy-e1",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        result = self.pipeline.process_manual_question(
            student_id="s1",
            subject="数学",
            grade="二年级",
            text="乘法口诀练习",
            answer="6",
            student_answer="6",
        )
        self.assertEqual(result["mastery"]["mastery_score"], 0.2)
        self.assertEqual(result["mastery"]["evidence_count"], 1)

    def test_ocr_requires_ingest_id_and_resolves_pending_task(self) -> None:
        image = self.vault / "paper.png"
        image.write_bytes(b"image")
        with patch(
            "services.edu_tracker.pipeline.recognize_image",
            return_value=OCRResult("乘法口诀练习", 0.7, "test-ocr"),
        ):
            pending = self.pipeline.process_photo(
                student_id="s1", subject="数学", grade="二年级", image_path=str(image)
            )
        ingest_id = pending["ingest"]["ingest_id"]
        confirmed = self.pipeline.process_photo(
            student_id="s1", subject="数学", grade="二年级", image_path=str(image),
            ingest_id=ingest_id, ocr_text="乘法口诀练习", answer="6", student_answer="6",
        )
        self.assertIsNotNone(confirmed["evidence"])
        self.assertEqual(self.pipeline.store.load_review_tasks(), [])
        self.assertEqual(self.pipeline.store.get_record("ingest", ingest_id)["status"], "已解析")

    def test_ocr_failure_is_audited_and_reviewable(self) -> None:
        result = self.pipeline.process_photo(
            student_id="s1", subject="数学", grade="二年级", image_path=str(self.vault / "missing.png")
        )
        self.assertEqual(result["status"], "OCR失败")
        self.assertEqual(len(self.pipeline.store.load_records("audit")), 1)
        self.assertEqual(len(self.pipeline.store.load_review_tasks()), 1)

    def test_review_decision_creates_evidence_and_resolves_task(self) -> None:
        pending = self.pipeline.process_manual_question(
            student_id="s1", subject="数学", grade="二年级",
            text="这是一道无法自动命中的题", answer="6", student_answer="6",
        )
        review_id = f"r_{pending['question']['question_id']}"
        result = self.pipeline.apply_review_decision(
            review_id, point_code="MATH-PRI-G2-NS-003", is_correct=True,
        )
        self.assertEqual(result["status"], "已解决")
        self.assertEqual(result["mastery"]["evidence_count"], 1)
        self.assertEqual(self.pipeline.list_review_tasks(), [])
        self.assertEqual(self.pipeline.list_review_tasks(status="已解决")[0]["status"], "已解决")

    def test_review_task_can_be_abandoned(self) -> None:
        pending = self.pipeline.process_manual_question(
            student_id="s1", subject="数学", grade="二年级", text="未知题目",
        )
        review_id = f"r_{pending['question']['question_id']}"
        result = self.pipeline.close_review_task(review_id, abandon=True)
        self.assertEqual(result["status"], "已放弃")
        self.assertEqual(self.pipeline.list_review_tasks(), [])


if __name__ == "__main__":
    unittest.main()
