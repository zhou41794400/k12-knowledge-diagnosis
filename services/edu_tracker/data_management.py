from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .input_validation import STUDENT_ID_PATTERN
from .reporting import safe_filename_component
from .storage import SQLiteStore


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def export_student(project_root: Path, student_id: str) -> Path:
    if not STUDENT_ID_PATTERN.fullmatch(student_id):
        raise ValueError("学生编号不合法")
    vault = project_root / "教育智能体"
    store = SQLiteStore(vault / "logs" / "edu_tracker.sqlite3")
    questions = store.load_records("questions", student_id)
    question_ids = {row.get("question_id") for row in questions}
    ingest = store.load_records("ingest", student_id)
    payload = {
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "questions": questions,
        "evidence": [row for row in store.load_records("evidence") if row.get("question_id") in question_ids],
        "mastery": store.load_current_mastery(student_id),
        "ingest": ingest,
        "audit": [
            row for row in store.load_records("audit")
            if row.get("target_id") in question_ids or row.get("target_id") in {item.get("ingest_id") for item in ingest}
        ],
        "review_tasks": store.load_review_tasks(student_id, "待处理")
        + store.load_review_tasks(student_id, "已解决")
        + store.load_review_tasks(student_id, "已放弃"),
    }
    output_dir = project_root / "exports"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"学生数据-{safe_filename_component(student_id)}-{_timestamp()}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("学生数据.json", json.dumps(payload, ensure_ascii=False, indent=2))
        for row in ingest:
            image = Path(str(row.get("image_path", "")))
            if image.is_file() and image.is_relative_to(vault):
                archive.write(image, f"图片/{image.name}")
    return path


def delete_student(project_root: Path, student_id: str, confirmation: str) -> dict[str, int]:
    if confirmation != student_id or not STUDENT_ID_PATTERN.fullmatch(student_id):
        raise ValueError("删除确认与学生编号不一致")
    vault = project_root / "教育智能体"
    log_dir = vault / "logs"
    store = SQLiteStore(log_dir / "edu_tracker.sqlite3")
    questions = store.load_records("questions", student_id)
    ingest = store.load_records("ingest", student_id)
    question_ids = {str(row.get("question_id", "")) for row in questions}
    ingest_ids = {str(row.get("ingest_id", "")) for row in ingest}
    deleted = store.delete_student(student_id, question_ids, ingest_ids)

    filters = {
        "questions.jsonl": lambda row: row.get("student_id") != student_id,
        "mastery.jsonl": lambda row: row.get("student_id") != student_id,
        "ingest.jsonl": lambda row: row.get("student_id") != student_id,
        "evidence.jsonl": lambda row: str(row.get("question_id", "")) not in question_ids,
        "audit.jsonl": lambda row: str(row.get("target_id", "")) not in question_ids | ingest_ids,
    }
    for filename, keep in filters.items():
        _rewrite_jsonl(log_dir / filename, keep)
    for row in ingest:
        image = Path(str(row.get("image_path", "")))
        if image.is_file() and image.is_relative_to(log_dir):
            image.unlink()
    report = vault / "05-结果视图" / f"学生端-{safe_filename_component(student_id)}.md"
    report.unlink(missing_ok=True)
    detail_dir = vault / "05-结果视图" / "题目详情"
    for question_id in question_ids:
        (detail_dir / f"{question_id}.md").unlink(missing_ok=True)
    return deleted


def create_backup(project_root: Path) -> Path:
    vault = project_root / "教育智能体"
    output_dir = project_root / "backups"
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"启智知踪备份-{_timestamp()}.zip"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in vault.rglob("*"):
            if file.is_file() and ".obsidian/workspace" not in file.as_posix():
                archive.write(file, file.relative_to(project_root))
    return path


def restore_backup(backup_path: Path, target_dir: Path) -> Path:
    if not backup_path.is_file():
        raise FileNotFoundError(f"备份不存在：{backup_path}")
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir.resolve()
    with zipfile.ZipFile(backup_path) as archive:
        for member in archive.infolist():
            destination = (target / member.filename).resolve()
            if target not in destination.parents and destination != target:
                raise ValueError("备份包包含非法路径")
        archive.extractall(target)
    return target


def health_status(project_root: Path) -> dict[str, object]:
    vault = project_root / "教育智能体"
    store = SQLiteStore(vault / "logs" / "edu_tracker.sqlite3")
    return {
        "status": "正常",
        "schema_version": store.schema_version(),
        "questions": len(store.load_records("questions")),
        "current_mastery": len(store.load_current_mastery()),
        "pending_reviews": len(store.load_review_tasks()),
        "pending_outbox": store.pending_outbox_count(),
    }


def _rewrite_jsonl(path: Path, keep) -> None:
    if not path.exists():
        return
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if keep(row):
            rows.append(json.dumps(row, ensure_ascii=False))
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    temporary.replace(path)
