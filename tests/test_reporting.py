import json
import tempfile
import unittest
from pathlib import Path

from services.edu_tracker.pipeline import LocalPipeline
from services.edu_tracker.reporting import generate_reports, markdown_inline, safe_filename_component, yaml_string

from tests.helpers import write_point


class ReportingTests(unittest.TestCase):
    def test_safe_filename_component_blocks_path_traversal(self) -> None:
        component = safe_filename_component("../../学生/A")
        self.assertNotIn("/", component)
        self.assertNotIn("..", component)
        self.assertEqual(yaml_string("a\nstatus: hacked"), '"a\\nstatus: hacked"')
        self.assertEqual(markdown_inline("a|b\nc"), "a\\|b c")

    def test_ocr_only_student_is_visible_in_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            vault = project_root / "教育智能体"
            pipeline = LocalPipeline(vault)
            pipeline.process_photo(
                student_id="ocr-only", subject="数学", grade="二年级",
                image_path=str(vault / "missing.png"),
            )

            generate_reports(project_root)

            report = vault / "05-结果视图" / "学生端-ocr-only.md"
            overview = (vault / "05-结果视图" / "家长端总览.md").read_text(encoding="utf-8")
            self.assertTrue(report.exists())
            self.assertIn("待处理复核任务数：1", overview)
            self.assertIn("## 本周复习任务", report.read_text(encoding="utf-8"))
            self.assertIn("ocr-only 周报", overview)

    def test_single_student_overview_uses_filtered_question_count(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            vault = project_root / "教育智能体"
            knowledge_root = vault / "02-课标与知识体系" / "02-国家课标知识树"
            write_point(knowledge_root)
            pipeline = LocalPipeline(vault)
            for student_id in ("a", "b"):
                pipeline.process_manual_question(
                    student_id=student_id,
                    subject="数学",
                    grade="二年级",
                    text="乘法口诀练习",
                    answer="6",
                    student_answer="6",
                )
            generate_reports(project_root, "a")
            overview = (vault / "05-结果视图" / "家长端总览.md").read_text(encoding="utf-8")
            self.assertIn("覆盖学生数：1", overview)
            self.assertIn("已记录题目数：1", overview)

    def test_legacy_evidence_is_excluded_from_current_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            vault = project_root / "教育智能体"
            knowledge_root = vault / "02-课标与知识体系" / "02-国家课标知识树"
            write_point(knowledge_root)
            logs = vault / "logs"
            logs.mkdir(parents=True)
            question = {
                "question_id": "q-old",
                "student_id": "a",
                "subject": "英语",
                "grade": "三年级",
                "text": "What color is the sky?",
                "is_correct": True,
            }
            evidence = {
                "event_id": "e-old",
                "question_id": "q-old",
                "point_code": "MATH-PRI-G2-NS-003",
                "model_version": "rule-v1",
            }
            mastery = {
                "student_id": "a",
                "point_code": "MATH-PRI-G2-NS-003",
                "mastery_score": 0.9,
                "last_evidence_id": "e-old",
            }
            for name, row in (("questions.jsonl", question), ("evidence.jsonl", evidence), ("mastery.jsonl", mastery)):
                (logs / name).write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            generate_reports(project_root)
            report = (vault / "05-结果视图" / "学生端-a.md").read_text(encoding="utf-8")
            detail = (vault / "05-结果视图" / "题目详情" / "q-old.md").read_text(encoding="utf-8")
            self.assertIn("当前模型有效证据数：0", report)
            self.assertIn("历史样例，待重新分析", report)
            self.assertNotIn("MATH-PRI-G2-NS-003", report)
            self.assertIn("旧知识点映射和掌握度已从当前报告隔离", detail)
            self.assertIn("point_code: ", detail)

    def test_pending_question_is_counted_as_review_task(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            vault = project_root / "教育智能体"
            write_point(vault / "02-课标与知识体系" / "02-国家课标知识树")
            pipeline = LocalPipeline(vault)
            pipeline.process_manual_question(
                student_id="a", subject="数学", grade="二年级", text="乘法口诀练习"
            )
            generate_reports(project_root)
            report = (vault / "05-结果视图" / "学生端-a.md").read_text(encoding="utf-8")
            overview = (vault / "05-结果视图" / "家长端总览.md").read_text(encoding="utf-8")
            self.assertIn("需要复核的记录数：1", report)
            self.assertIn("待处理复核任务数：1", overview)


if __name__ == "__main__":
    unittest.main()
