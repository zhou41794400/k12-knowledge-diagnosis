from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class KnowledgePoint:
    point_code: str
    subject: str
    subject_code: str
    stage: str
    stage_code: str
    grade: str
    topic: str
    topic_code: str
    standard_version: str
    tracking_mode: str
    title: str = ""
    status: str = "draft"
    matching_keywords: list[str] = field(default_factory=list)
    source_path: str = ""
    prerequisites: list[str] = field(default_factory=list)
    related_points: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuestionRecord:
    question_id: str
    student_id: str
    source_type: str
    subject: str
    subject_code: str
    grade: str
    text: str
    answer: str = ""
    student_answer: str = ""
    is_correct: Optional[bool] = None
    review_required: bool = False
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceEvent:
    event_id: str
    question_id: str
    point_code: str
    evidence_type: str
    evidence_strength: str
    confidence: float
    model_version: str
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MasteryState:
    student_id: str
    point_code: str
    mastery_score: float
    mastery_level: str
    evidence_count: int
    negative_evidence_count: int
    review_required: bool
    last_updated_at: str = field(default_factory=now_iso)
    last_evidence_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AuditEvent:
    audit_id: str
    event_type: str
    actor: str
    target_id: str
    before: Optional[dict[str, Any]]
    after: Optional[dict[str, Any]]
    reason: str
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IngestEvent:
    ingest_id: str
    student_id: str
    source_type: str
    image_path: str
    status: str
    subject: str = ""
    grade: str = ""
    ocr_text: str = ""
    ocr_confidence: float = 0.0
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
