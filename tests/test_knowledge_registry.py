import tempfile
import unittest
from pathlib import Path

from services.edu_tracker.knowledge_registry import knowledge_stats, match_question, registry

from tests.helpers import write_point


class KnowledgeRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        write_point(self.root)
        write_point(
            self.root,
            point_code="MATH-PRI-G2-NS-999",
            title="未发布知识点",
            status="draft",
            keywords=("未发布",),
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_registry_only_loads_published_trackable_points(self) -> None:
        points = registry(self.root)
        self.assertEqual([point.point_code for point in points], ["MATH-PRI-G2-NS-003"])

    def test_match_filters_subject_and_grade_before_keywords(self) -> None:
        result = match_question("英语", "八年级", "这道题包含乘法口诀", knowledge_root=self.root)
        self.assertIsNone(result.point)
        self.assertTrue(result.review_required)

    def test_match_returns_none_when_no_keyword_matches(self) -> None:
        result = match_question("数学", "二年级", "认识直角", knowledge_root=self.root)
        self.assertIsNone(result.point)
        self.assertEqual(result.candidates, [])

    def test_match_returns_explainable_candidate(self) -> None:
        result = match_question("数学", "二年级", "用乘法口诀计算", knowledge_root=self.root)
        self.assertEqual(result.point.point_code, "MATH-PRI-G2-NS-003")
        self.assertIn("乘法口诀", result.reason)
        self.assertFalse(result.review_required)

    def test_stats_distinguish_nodes_trackable_and_published(self) -> None:
        stats = knowledge_stats(self.root)
        self.assertEqual(stats["point_nodes"], 2)
        self.assertEqual(stats["trackable_cards"], 2)
        self.assertEqual(stats["published"], 1)


if __name__ == "__main__":
    unittest.main()
