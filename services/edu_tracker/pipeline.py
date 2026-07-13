from __future__ import annotations

import json
import subprocess
from pathlib import Path
from uuid import uuid4
from typing import Optional

from .knowledge_registry import match_question, registry
from .models import AuditEvent, EvidenceEvent, IngestEvent, MasteryState, QuestionRecord, now_iso
from .ocr import recognize_image
from .storage import SQLiteStore
from .input_validation import validate_answer, validate_context, validate_question_text


CURRENT_MODEL_VERSION = "rule-v2"


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
        self.store = SQLiteStore(self.log_dir / "edu_tracker.sqlite3")
        self.last_export_error = ""

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
        validate_context(student_id, subject, grade)
        validate_question_text(text)
        validate_answer(answer, "标准答案")
        validate_answer(student_answer, "学生作答")
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

    def list_review_tasks(self, student_id: str = "", status: str = "待处理") -> list[dict]:
        return self.store.load_review_tasks(student_id=student_id, status=status)

    def close_review_task(self, review_id: str, *, abandon: bool = False) -> dict:
        status = "已放弃" if abandon else "已解决"
        task = self.store.update_review_status(review_id, status, now_iso())
        if task is None:
            return {"status": "操作失败", "reason": "未找到待处理复核任务", "review_id": review_id}
        return {"status": status, "review": task}

    def apply_review_decision(self, review_id: str, *, point_code: str, is_correct: bool) -> dict:
        tasks = [task for task in self.store.load_review_tasks() if task.get("review_id") == review_id]
        if not tasks:
            return {"status": "操作失败", "reason": "未找到待处理复核任务", "review_id": review_id}
        task = tasks[0]
        question = self.store.get_record("questions", str(task.get("target_id", "")))
        if question is None:
            return {"status": "操作失败", "reason": "该任务不是可写入证据的题目复核", "review_id": review_id}
        knowledge_root = self.workspace_root / "02-课标与知识体系" / "02-国家课标知识树"
        points = {point.point_code: point for point in registry(knowledge_root)}
        point = points.get(point_code)
        if point is None:
            return {"status": "操作失败", "reason": "知识点不存在或尚未发布", "review_id": review_id}
        if point.subject != question.get("subject") or point.grade != question.get("grade"):
            return {"status": "操作失败", "reason": "知识点与题目学科或年级不一致", "review_id": review_id}

        question["is_correct"] = is_correct
        question["review_required"] = False
        event = EvidenceEvent(
            event_id=f"e_{uuid4().hex[:12]}", question_id=question["question_id"],
            point_code=point_code, evidence_type="manual_review", evidence_strength="强",
            confidence=1.0, model_version=CURRENT_MODEL_VERSION,
        )
        result: dict[str, object] = {}

        def build_entries(previous_payload: Optional[dict]) -> list[tuple[str, dict]]:
            previous = self._mastery_from_payload(question["student_id"], point_code, previous_payload)
            reviewed_question = QuestionRecord(**{
                key: question[key] for key in QuestionRecord.__dataclass_fields__ if key in question
            })
            updated = self._update_mastery(previous, reviewed_question, event)
            audit = AuditEvent(
                audit_id=f"a_{uuid4().hex[:12]}", event_type="manual_review_applied",
                actor="guardian", target_id=question["question_id"], before=previous.to_dict(),
                after=updated.to_dict(), reason=f"review_id={review_id}; point_code={point_code}; is_correct={is_correct}",
            )
            result["mastery"] = updated.to_dict()
            result["audit"] = audit.to_dict()
            return [
                ("questions.jsonl", question), ("evidence.jsonl", event.to_dict()),
                ("mastery.jsonl", updated.to_dict()), ("audit.jsonl", audit.to_dict()),
            ]

        self.store.commit_mastery_operation(
            question["student_id"], point_code, build_entries,
            resolve_review_id=review_id, resolved_at=now_iso(),
        )
        self._flush_outbox()
        return {
            "status": "已解决", "review_id": review_id, "question": question,
            "evidence": event.to_dict(), "mastery": result["mastery"], "audit": result["audit"],
        }

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
        ingest_id: str = "",
    ) -> dict:
        validate_context(student_id, subject, grade)
        validate_answer(answer, "标准答案")
        validate_answer(student_answer, "学生作答")
        if ingest_id:
            pending = self.store.get_record("ingest", ingest_id)
            if not pending or pending.get("student_id") != student_id or pending.get("status") != "待确认":
                return {"status": "确认失败", "reason": "未找到该学生的待确认 OCR 记录", "ingest_id": ingest_id}
            text = ocr_text.strip() or str(pending.get("ocr_text", "")).strip()
            if not text:
                return {"status": "确认失败", "reason": "确认文本不能为空", "ingest_id": ingest_id}
            validate_question_text(text)
            return self._process_question(
                source_type="photo", student_id=student_id, subject=subject, grade=grade, text=text,
                answer=answer, student_answer=student_answer, image_path=str(pending.get("image_path", image_path)),
                ocr_confidence=1.0, confirmed_ingest_id=ingest_id,
            )
        if not ocr_text.strip() and self._find_sidecar_text(image_path) is None:
            try:
                recognized = recognize_image(Path(image_path))
            except (FileNotFoundError, RuntimeError, subprocess.SubprocessError) as exc:
                ingest = IngestEvent(
                    ingest_id=f"i_{uuid4().hex[:12]}", student_id=student_id, source_type="photo",
                    image_path=image_path, status="OCR失败", subject=subject, grade=grade,
                    ocr_text="", ocr_confidence=0.0,
                )
                audit = AuditEvent(
                    audit_id=f"a_{uuid4().hex[:12]}", event_type="photo_ocr_failed", actor="pipeline",
                    target_id=ingest.ingest_id, before=None, after=ingest.to_dict(), reason=str(exc),
                )
                review = self._review_task(student_id, "photo", ingest.ingest_id, f"OCR失败：{exc}")
                self._persist([("ingest.jsonl", ingest.to_dict()), ("audit.jsonl", audit.to_dict())], review_task=review)
                return {"ingest": ingest.to_dict(), "audit": audit.to_dict(), "status": "OCR失败", "reason": str(exc)}
            ingest = IngestEvent(
                ingest_id=f"i_{uuid4().hex[:12]}",
                student_id=student_id,
                source_type="photo",
                image_path=image_path,
                status="待确认",
                subject=subject,
                grade=grade,
                ocr_text=recognized.text,
                ocr_confidence=recognized.confidence,
            )
            review = self._review_task(student_id, "photo", ingest.ingest_id, "OCR文本待人工确认")
            self._persist([("ingest.jsonl", ingest.to_dict())], review_task=review)
            return {
                "ingest": ingest.to_dict(),
                "status": "待确认",
                "reason": "请人工核对 OCR 文本，修正后通过 --ocr-text 再次提交",
                "ocr": {"text": recognized.text, "confidence": recognized.confidence, "engine": recognized.engine},
            }
        text, ingest = self._prepare_photo_text(
            student_id=student_id, subject=subject, grade=grade,
            image_path=image_path, ocr_text=ocr_text,
        )
        if not text:
            review = self._review_task(student_id, "photo", ingest.ingest_id, "未识别到可确认文本")
            self._persist([("ingest.jsonl", ingest.to_dict())], review_task=review)
            return {
                "ingest": ingest.to_dict(),
                "status": "待解析",
                "reason": "未提供 OCR 文本，也未找到同名旁路文本文件",
            }

        validate_question_text(text)

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
            confirmed_ingest_id="",
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
        confirmed_ingest_id: str = "",
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

        knowledge_root = self.workspace_root / "02-课标与知识体系" / "02-国家课标知识树"
        match = match_question(subject, grade, text, knowledge_root=knowledge_root)
        is_correct = self._derive_correctness(answer, student_answer)
        question.is_correct = is_correct
        question.review_required = match.review_required or ocr_confidence < 0.6 or is_correct is None

        if match.point is None or question.review_required or is_correct is None:
            if match.point is None:
                event_type = f"{source_type}_unmatched"
            elif is_correct is None:
                event_type = f"{source_type}_pending_answer"
            else:
                event_type = f"{source_type}_review_required"
            audit = AuditEvent(
                audit_id=f"a_{uuid4().hex[:12]}",
                event_type=event_type,
                actor="pipeline",
                target_id=question.question_id,
                before=None,
                after=question.to_dict(),
                reason=f"{match.reason}; correctness={is_correct}; review_required={question.review_required}; ocr_confidence={ocr_confidence:.2f}",
            )
            entries: list[tuple[str, dict]] = []
            if source_type == "photo":
                ingest = IngestEvent(
                    ingest_id=confirmed_ingest_id or f"i_{uuid4().hex[:12]}",
                    student_id=student_id,
                    source_type=source_type,
                    image_path=image_path,
                    status="待复核",
                    subject=subject,
                    grade=grade,
                    ocr_text=text,
                    ocr_confidence=ocr_confidence,
                )
                entries.append(("ingest.jsonl", ingest.to_dict()))
            entries.extend([("questions.jsonl", question.to_dict()), ("audit.jsonl", audit.to_dict())])
            review = self._review_task(student_id, source_type, question.question_id, audit.reason)
            self._persist(
                entries,
                review_task=review,
                resolve_review_id=f"r_{confirmed_ingest_id}" if confirmed_ingest_id else "",
            )
            return {
                "question": question.to_dict(),
                "match": self._match_payload(match),
                "ocr": {"confidence": ocr_confidence, "source_type": source_type},
                "evidence": None,
                "mastery": None,
                "audit": audit.to_dict(),
            }

        point = match.point

        event = EvidenceEvent(
            event_id=f"e_{uuid4().hex[:12]}",
            question_id=question.question_id,
            point_code=point.point_code,
            evidence_type=f"{source_type}_question",
            evidence_strength=evidence_strength(min(match.confidence, ocr_confidence)),
            confidence=min(match.confidence, ocr_confidence),
            model_version=CURRENT_MODEL_VERSION,
        )

        fixed_entries = []
        if source_type == "photo":
            ingest = IngestEvent(
                ingest_id=confirmed_ingest_id or f"i_{uuid4().hex[:12]}",
                student_id=student_id,
                source_type=source_type,
                image_path=image_path,
                status="已解析",
                subject=subject,
                grade=grade,
                ocr_text=text,
                ocr_confidence=ocr_confidence,
            )
            fixed_entries.append(("ingest.jsonl", ingest.to_dict()))

        result: dict[str, object] = {}

        def build_entries(previous_payload: Optional[dict]) -> list[tuple[str, dict]]:
            previous = self._mastery_from_payload(student_id, point.point_code, previous_payload)
            updated = self._update_mastery(previous, question, event)
            audit = AuditEvent(
                audit_id=f"a_{uuid4().hex[:12]}", event_type=f"{source_type}_pipeline",
                actor="pipeline", target_id=question.question_id, before=previous.to_dict(),
                after=updated.to_dict(),
                reason=f"match={match.reason}; confidence={match.confidence:.2f}; ocr_confidence={ocr_confidence:.2f}",
            )
            result["mastery"] = updated
            result["audit"] = audit
            return fixed_entries + [
                ("questions.jsonl", question.to_dict()), ("evidence.jsonl", event.to_dict()),
                ("mastery.jsonl", updated.to_dict()), ("audit.jsonl", audit.to_dict()),
            ]

        self.store.commit_mastery_operation(
            student_id, point.point_code, build_entries,
            resolve_review_id=f"r_{confirmed_ingest_id}" if confirmed_ingest_id else "",
            resolved_at=now_iso(),
        )
        self._flush_outbox()
        updated = result["mastery"]
        audit = result["audit"]

        return {
            "question": question.to_dict(),
            "match": self._match_payload(match),
            "ocr": {
                "confidence": ocr_confidence,
                "source_type": source_type,
            },
            "evidence": event.to_dict(),
            "mastery": updated.to_dict(),  # type: ignore[union-attr]
            "audit": audit.to_dict(),  # type: ignore[union-attr]
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

    def _match_payload(self, match) -> dict:
        point = match.point
        return {
            "point_code": point.point_code if point else "",
            "subject": point.subject if point else "",
            "grade": point.grade if point else "",
            "topic": point.topic if point else "",
            "confidence": match.confidence,
            "reason": match.reason,
            "review_required": match.review_required,
            "candidates": [
                {
                    "point_code": candidate.point.point_code,
                    "title": candidate.point.title,
                    "confidence": candidate.confidence,
                    "matched_terms": candidate.matched_terms,
                }
                for candidate in match.candidates
            ],
        }

    def _latest_mastery_state(self, student_id: str, point_code: str) -> MasteryState:
        latest = self.store.get_mastery(student_id, point_code)
        return self._mastery_from_payload(student_id, point_code, latest)

    def _mastery_from_payload(
        self, student_id: str, point_code: str, latest: Optional[dict],
    ) -> MasteryState:
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

    def _persist(
        self,
        entries: list[tuple[str, dict]],
        *,
        review_task: Optional[dict] = None,
        resolve_review_id: str = "",
    ) -> None:
        self.store.commit_operation(
            entries, review_task=review_task, resolve_review_id=resolve_review_id, resolved_at=now_iso()
        )
        self._flush_outbox()

    def _flush_outbox(self) -> None:
        try:
            self.store.flush_outbox(self.log_dir)
            self.last_export_error = ""
        except OSError as exc:
            self.last_export_error = str(exc)

    def _review_task(self, student_id: str, source_type: str, target_id: str, reason: str) -> dict:
        return {
            "review_id": f"r_{target_id}", "student_id": student_id, "source_type": source_type,
            "target_id": target_id, "reason": reason, "status": "待处理", "created_at": now_iso(),
        }

    def _subject_code(self, subject: str) -> str:
        return {"数学": "MATH", "语文": "CHN", "英语": "ENG"}.get(subject, "UNK")

    def _derive_correctness(self, answer: str, student_answer: str) -> Optional[bool]:
        if not answer and not student_answer:
            return None
        if not answer:
            return None
        return answer.strip() == student_answer.strip()

    def _prepare_photo_text(
        self, *, student_id: str, subject: str, grade: str, image_path: str, ocr_text: str,
    ) -> tuple[str, IngestEvent]:
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
            subject=subject,
            grade=grade,
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
