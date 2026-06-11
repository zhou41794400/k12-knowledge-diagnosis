from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4
from typing import Optional

from .knowledge_registry import match_question
from .models import AuditEvent, EvidenceEvent, IngestEvent, MasteryState, QuestionRecord


def mastery_level(score: float) -> str:
    if score < 0.2:
        return "未接触"
    if score < 0.45:
        return "初步掌握"
    if score < 0.75:
        return "基本掌握"
    return "熟练掌握"


def evidence_strength(confidence: float) -> str:
    if confidence >= 0.85:
        return "强"
    if confidence >= 0.6:
        return "中"
    return "弱"


class LocalPipeline:
    def __init__(self, workspace_root):
        self.workspace_root = Path(workspace_root)
        self.log_dir = self.workspace_root / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def process_manual_question(
        self,
        *,
        student_id: str,
        subject: str,
        grade: str,
        text: str,
        answer: str = "",
        student_answer: str = "",
    ) -> dict:
        return self._process_question(
            source_type="manual",
            student_id=student_id,
            subject=subject,
            grade=grade,
            text=text,
            answer=answer,
            student_answer=student_answer,
            image_path="",
            ocr_confidence=1.0,
        )

    def process_photo(
        self,
        *,
        student_id: str,
        subject: str,
        grade: str,
        image_path: str,
        answer: str = "",
        student_answer: str = "",
        ocr_text: str = "",
    ) -> dict:
        text, ingest = self._prepare_photo_text(student_id=student_id, image_path=image_path, ocr_text=ocr_text)
        if not text:
            self._append_jsonl("ingest.jsonl", ingest.to_dict())
            return {
                "ingest": ingest.to_dict(),
                "status": "待解析",
                "reason": "未提供 OCR 文本，也未找到同名旁路文本文件",
            }

        result = self._process_question(
            source_type="photo",
            student_id=student_id,
            subject=subject,
            grade=grade,
            text=text,
            answer=answer,
            student_answer=student_answer,
            image_path=image_path,
            ocr_confidence=ingest.ocr_confidence,
        )
        result["ingest"] = ingest.to_dict()
        return result

    def _process_question(
        self,
        *,
        source_type: str,
        student_id: str,
        subject: str,
        grade: str,
        text: str,
        answer: str,
        student_answer: str,
        image_path: str,
        ocr_confidence: float,
    ) -> dict:
        question = QuestionRecord(
            question_id=f"q_{uuid4().hex[:12]}",
            student_id=student_id,
            source_type=source_type,
            subject=subject,
            subject_code=self._subject_code(subject),
            grade=grade,
            text=text,
            answer=answer,
            student_answer=student_answer,
        )

        match = match_question(subject, grade, text)
        is_correct = self._derive_correctness(answer, student_answer)
        question.is_correct = is_correct
        question.review_required = match.confidence < 0.6 or ocr_confidence < 0.6 or is_correct is None

        event = EvidenceEvent(
            event_id=f"e_{uuid4().hex[:12]}",
            question_id=question.question_id,
            point_code=match.point.point_code,
            evidence_type=f"{source_type}_question",
            evidence_strength=evidence_strength(min(match.confidence, ocr_confidence)),
            confidence=min(match.confidence, ocr_confidence),
            model_version="rule-v1",
        )

        previous = self._latest_mastery_state(student_id, match.point.point_code)
        updated = self._update_mastery(previous, question, event)
        audit = AuditEvent(
            audit_id=f"a_{uuid4().hex[:12]}",
            event_type=f"{source_type}_pipeline",
            actor="pipeline",
            target_id=question.question_id,
            before=previous.to_dict(),
            after=updated.to_dict(),
            reason=f"match={match.reason}; confidence={match.confidence:.2f}; ocr_confidence={ocr_confidence:.2f}",
        )

        if source_type == "photo":
            ingest = IngestEvent(
                ingest_id=f"i_{uuid4().hex[:12]}",
                student_id=student_id,
                source_type=source_type,
                image_path=image_path,
                status="已解析",
                ocr_text=text,
                ocr_confidence=ocr_confidence,
            )
            self._append_jsonl("ingest.jsonl", ingest.to_dict())

        self._append_jsonl("questions.jsonl", question.to_dict())
        self._append_jsonl("evidence.jsonl", event.to_dict())
        self._append_jsonl("mastery.jsonl", updated.to_dict())
        self._append_jsonl("audit.jsonl", audit.to_dict())

        return {
            "question": question.to_dict(),
            "match": {
                "point_code": match.point.point_code,
                "subject": match.point.subject,
                "grade": match.point.grade,
                "topic": match.point.topic,
                "confidence": match.confidence,
                "reason": match.reason,
            },
            "ocr": {
                "confidence": ocr_confidence,
                "source_type": source_type,
            },
            "evidence": event.to_dict(),
            "mastery": updated.to_dict(),
            "audit": audit.to_dict(),
        }

    def _update_mastery(
        self,
        previous: MasteryState,
        question: QuestionRecord,
        event: EvidenceEvent,
    ) -> MasteryState:
        score = previous.mastery_score
        if question.is_correct is True:
            if event.evidence_strength == "强":
                score += 0.35
            elif event.evidence_strength == "中":
                score += 0.2
            else:
                score += 0.05
        elif question.is_correct is False:
            if event.evidence_strength == "强":
                score -= 0.25
            elif event.evidence_strength == "中":
                score -= 0.15
            else:
                score -= 0.05

        score = max(0.0, min(1.0, score))
        return MasteryState(
            student_id=previous.student_id,
            point_code=previous.point_code,
            mastery_score=round(score, 3),
            mastery_level=mastery_level(score),
            evidence_count=previous.evidence_count + 1,
            negative_evidence_count=previous.negative_evidence_count + (1 if question.is_correct is False else 0),
            review_required=previous.review_required or event.evidence_strength == "弱" or question.review_required,
            last_evidence_id=event.event_id,
        )

    def _latest_mastery_state(self, student_id: str, point_code: str) -> MasteryState:
        latest: Optional[dict] = None
        path = self.log_dir / "mastery.jsonl"
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if row.get("student_id") != student_id or row.get("point_code") != point_code:
                        continue
                    if latest is None or row.get("last_updated_at", "") >= latest.get("last_updated_at", ""):
                        latest = row
        if latest is None:
            return MasteryState(
                student_id=student_id,
                point_code=point_code,
                mastery_score=0.0,
                mastery_level="未接触",
                evidence_count=0,
                negative_evidence_count=0,
                review_required=False,
            )
        return MasteryState(
            student_id=student_id,
            point_code=point_code,
            mastery_score=float(latest.get("mastery_score", 0.0)),
            mastery_level=str(latest.get("mastery_level", "未接触")),
            evidence_count=int(latest.get("evidence_count", 0)),
            negative_evidence_count=int(latest.get("negative_evidence_count", 0)),
            review_required=bool(latest.get("review_required", False)),
            last_updated_at=str(latest.get("last_updated_at", "")),
            last_evidence_id=str(latest.get("last_evidence_id", "")),
        )

    def _append_jsonl(self, filename: str, payload: dict) -> None:
        path = self.log_dir / filename
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _subject_code(self, subject: str) -> str:
        return {"数学": "MATH", "语文": "CHN", "英语": "ENG"}.get(subject, "UNK")

    def _derive_correctness(self, answer: str, student_answer: str) -> Optional[bool]:
        if not answer and not student_answer:
            return None
        if not answer:
            return None
        return answer.strip() == student_answer.strip()

    def _prepare_photo_text(self, *, student_id: str, image_path: str, ocr_text: str) -> tuple[str, IngestEvent]:
        candidate_text = ocr_text.strip()
        sidecar = self._find_sidecar_text(image_path)
        if not candidate_text and sidecar is not None:
            candidate_text = sidecar.read_text(encoding="utf-8").strip()
        ingest = IngestEvent(
            ingest_id=f"i_{uuid4().hex[:12]}",
            student_id=student_id,
            source_type="photo",
            image_path=image_path,
            status="已解析" if candidate_text else "待解析",
            ocr_text=candidate_text,
            ocr_confidence=0.78 if candidate_text else 0.0,
        )
        return candidate_text, ingest

    def _find_sidecar_text(self, image_path: str):
        image = Path(image_path)
        candidates = [
            image.with_suffix(".txt"),
            image.parent / f"{image.stem}.txt",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None
