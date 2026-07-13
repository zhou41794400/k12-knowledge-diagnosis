from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from .models import KnowledgePoint


DEFAULT_KNOWLEDGE_ROOT = (
    Path(__file__).resolve().parents[2]
    / "教育智能体"
    / "02-课标与知识体系"
    / "02-国家课标知识树"
)


@dataclass
class MatchCandidate:
    point: KnowledgePoint
    confidence: float
    matched_terms: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    point: Optional[KnowledgePoint]
    confidence: float
    reason: str
    candidates: list[MatchCandidate] = field(default_factory=list)
    review_required: bool = True


def registry(
    knowledge_root: Optional[Path] = None,
    *,
    statuses: Iterable[str] = ("published",),
) -> list[KnowledgePoint]:
    root = Path(knowledge_root) if knowledge_root is not None else DEFAULT_KNOWLEDGE_ROOT
    allowed_statuses = set(statuses)
    points: list[KnowledgePoint] = []
    if not root.exists():
        return points

    for path in root.rglob("*.md"):
        metadata = _read_frontmatter(path)
        if metadata.get("mastery_granularity") != "knowledge_point":
            continue
        if metadata.get("status", "draft") not in allowed_statuses:
            continue
        required = (
            "subject",
            "subject_code",
            "stage",
            "stage_code",
            "grade",
            "topic",
            "topic_code",
            "point_code",
            "standard_version",
            "tracking_mode",
        )
        if any(not metadata.get(key) for key in required):
            continue
        points.append(
            KnowledgePoint(
                point_code=str(metadata["point_code"]),
                subject=str(metadata["subject"]),
                subject_code=str(metadata["subject_code"]),
                stage=str(metadata["stage"]),
                stage_code=str(metadata["stage_code"]),
                grade=str(metadata["grade"]),
                topic=str(metadata["topic"]),
                topic_code=str(metadata["topic_code"]),
                standard_version=str(metadata["standard_version"]),
                tracking_mode=str(metadata["tracking_mode"]),
                title=_first_heading(path) or str(metadata.get("title") or path.stem),
                status=str(metadata.get("status", "draft")),
                matching_keywords=_as_list(metadata.get("matching_keywords", [])),
                source_path=path.as_posix(),
                prerequisites=_as_list(metadata.get("prerequisites", [])),
                related_points=_as_list(metadata.get("related_points", [])),
            )
        )
    return sorted(points, key=lambda point: point.point_code)


def knowledge_stats(knowledge_root: Optional[Path] = None) -> dict[str, int]:
    root = Path(knowledge_root) if knowledge_root is not None else DEFAULT_KNOWLEDGE_ROOT
    point_codes: set[str] = set()
    trackable_codes: set[str] = set()
    subjects: set[str] = set()
    published = 0
    index_files = 0
    if not root.exists():
        return {
            "point_nodes": 0,
            "trackable_cards": 0,
            "subjects": 0,
            "published": 0,
            "index_files": 0,
        }
    for path in root.rglob("*.md"):
        if path.name == "INDEX.md":
            index_files += 1
        metadata = _read_frontmatter(path)
        point_code = str(metadata.get("point_code", "")).strip()
        if not point_code:
            continue
        point_codes.add(point_code)
        subject = str(metadata.get("subject", "")).strip()
        if subject:
            subjects.add(subject)
        if metadata.get("mastery_granularity") == "knowledge_point":
            trackable_codes.add(point_code)
        if metadata.get("status") == "published" and metadata.get("mastery_granularity") == "knowledge_point":
            published += 1
    return {
        "point_nodes": len(point_codes),
        "trackable_cards": len(trackable_codes),
        "subjects": len(subjects),
        "published": published,
        "index_files": index_files,
    }


def match_question(
    subject: str,
    grade: str,
    text: str,
    *,
    knowledge_root: Optional[Path] = None,
) -> MatchResult:
    candidates = [
        point
        for point in registry(knowledge_root)
        if point.subject == subject and point.grade == grade
    ]
    if not candidates:
        return MatchResult(
            point=None,
            confidence=0.0,
            reason=f"没有已发布的{subject}{grade}知识点",
            candidates=[],
            review_required=True,
        )

    normalized_text = _normalize(text)
    ranked: list[MatchCandidate] = []
    for point in candidates:
        terms = [term for term in point.matching_keywords if _normalize(term) in normalized_text]
        title_match = bool(point.title and _normalize(point.title) in normalized_text)
        if not terms and not title_match:
            continue
        confidence = 0.95 if title_match else min(0.92, 0.72 + 0.06 * (len(terms) - 1))
        ranked.append(MatchCandidate(point=point, confidence=confidence, matched_terms=terms))

    ranked.sort(key=lambda item: (-item.confidence, -max((len(term) for term in item.matched_terms), default=0), item.point.point_code))
    if not ranked:
        return MatchResult(
            point=None,
            confidence=0.0,
            reason="未命中已发布知识点的匹配关键词",
            candidates=[],
            review_required=True,
        )

    best = ranked[0]
    ambiguous = len(ranked) > 1 and best.confidence - ranked[1].confidence < 0.1
    terms = "、".join(best.matched_terms) if best.matched_terms else best.point.title
    return MatchResult(
        point=best.point,
        confidence=best.confidence,
        reason=f"命中关键词：{terms}",
        candidates=ranked[:5],
        review_required=ambiguous,
    )


def _read_frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, object] = {}
    current_list: Optional[str] = None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        list_item = re.match(r"^\s+-\s+(.*)$", line)
        if list_item and current_list:
            value = _clean_value(list_item.group(1))
            items = metadata.setdefault(current_list, [])
            if isinstance(items, list):
                items.append(value)
            continue
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not match:
            current_list = None
            continue
        key, raw_value = match.group(1), match.group(2).strip()
        if not raw_value:
            metadata[key] = []
            current_list = key
        elif raw_value == "[]":
            metadata[key] = []
            current_list = None
        else:
            metadata[key] = _clean_value(raw_value)
            current_list = None
    return metadata


def _clean_value(value: str) -> str:
    return value.strip().strip('"').strip("'")


def _as_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if not value:
        return []
    return [str(value)]


def _first_heading(path: Path) -> str:
    in_frontmatter = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if not in_frontmatter and line.startswith("# "):
            return line[2:].strip()
    return ""


def _normalize(value: str) -> str:
    return re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "", value).lower()
