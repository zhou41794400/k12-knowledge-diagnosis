from __future__ import annotations

from dataclasses import dataclass

from .models import KnowledgePoint


@dataclass
class MatchResult:
    point: KnowledgePoint
    confidence: float
    reason: str


def registry() -> list[KnowledgePoint]:
    return [
        KnowledgePoint(
            point_code="MATH-PRI-G2-NS-001",
            subject="数学",
            subject_code="MATH",
            stage="小学",
            stage_code="PRI",
            grade="二年级",
            topic="数与代数",
            topic_code="NS",
            standard_version="2022",
            tracking_mode="BKT",
        ),
        KnowledgePoint(
            point_code="MATH-PRI-G2-NS-002",
            subject="数学",
            subject_code="MATH",
            stage="小学",
            stage_code="PRI",
            grade="二年级",
            topic="数与代数",
            topic_code="NS",
            standard_version="2022",
            tracking_mode="BKT",
        ),
        KnowledgePoint(
            point_code="MATH-PRI-G2-NS-003",
            subject="数学",
            subject_code="MATH",
            stage="小学",
            stage_code="PRI",
            grade="二年级",
            topic="数与代数",
            topic_code="NS",
            standard_version="2022",
            tracking_mode="BKT",
        ),
        KnowledgePoint(
            point_code="ENG-JHS-G8-GRM-001",
            subject="英语",
            subject_code="ENG",
            stage="初中",
            stage_code="JHS",
            grade="八年级",
            topic="语法",
            topic_code="GRM",
            standard_version="2022",
            tracking_mode="MIXED",
        ),
        KnowledgePoint(
            point_code="CHN-PRI-G2-READ-001",
            subject="语文",
            subject_code="CHN",
            stage="小学",
            stage_code="PRI",
            grade="二年级",
            topic="阅读与鉴赏",
            topic_code="READ",
            standard_version="2022",
            tracking_mode="MIXED",
        ),
    ]


def match_question(subject: str, grade: str, text: str) -> MatchResult:
    candidates = registry()
    normalized = f"{subject} {grade} {text}"

    if "乘法口诀" in normalized or "乘法" in normalized:
        point = next(p for p in candidates if p.point_code == "MATH-PRI-G2-NS-003")
        return MatchResult(point=point, confidence=0.94, reason="命中乘法关键词")
    if "阅读" in normalized or "短文" in normalized:
        point = next(p for p in candidates if p.point_code == "CHN-PRI-G2-READ-001")
        return MatchResult(point=point, confidence=0.72, reason="命中阅读关键词")
    if "过去时" in normalized or "比较级" in normalized:
        point = next(p for p in candidates if p.point_code == "ENG-JHS-G8-GRM-001")
        return MatchResult(point=point, confidence=0.81, reason="命中英语语法关键词")

    point = candidates[0]
    return MatchResult(point=point, confidence=0.35, reason="未命中规则，使用默认候选")
