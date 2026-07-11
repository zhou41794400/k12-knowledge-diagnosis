from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Callable, Iterable, Optional


ID_FIELDS = {
    "questions": "question_id",
    "evidence": "event_id",
    "ingest": "ingest_id",
    "audit": "audit_id",
    "mastery": "last_evidence_id",
}
SCHEMA_VERSION = 1


class SQLiteStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as db:
            current_version = int(db.execute("PRAGMA user_version").fetchone()[0])
            if current_version > SCHEMA_VERSION:
                raise RuntimeError(f"数据库版本 {current_version} 高于当前程序支持的 {SCHEMA_VERSION}")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS records (
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    student_id TEXT,
                    question_id TEXT,
                    point_code TEXT,
                    created_at TEXT,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (record_type, record_id)
                );
                CREATE INDEX IF NOT EXISTS idx_records_student ON records(student_id);
                CREATE INDEX IF NOT EXISTS idx_records_question ON records(question_id);
                CREATE INDEX IF NOT EXISTS idx_records_point ON records(point_code);
                CREATE TABLE IF NOT EXISTS mastery_current (
                    student_id TEXT NOT NULL,
                    point_code TEXT NOT NULL,
                    mastery_score REAL NOT NULL,
                    last_updated_at TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (student_id, point_code)
                );
                CREATE TABLE IF NOT EXISTS review_tasks (
                    review_id TEXT PRIMARY KEY,
                    student_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_review_status ON review_tasks(status, student_id);
                CREATE TABLE IF NOT EXISTS outbox (
                    outbox_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    exported_at TEXT,
                    UNIQUE(filename, record_type, record_id)
                );
                """
            )
            if current_version < SCHEMA_VERSION:
                db.execute(f"PRAGMA user_version={SCHEMA_VERSION}")

    def commit_operation(
        self,
        entries: Iterable[tuple[str, dict]],
        *,
        review_task: Optional[dict] = None,
        resolve_review_id: str = "",
        resolved_at: str = "",
    ) -> None:
        with self._connect() as db:
            self._commit_entries(
                db, entries, review_task=review_task, resolve_review_id=resolve_review_id,
                resolved_at=resolved_at,
            )

    def commit_mastery_operation(
        self,
        student_id: str,
        point_code: str,
        build_entries: Callable[[Optional[dict]], Iterable[tuple[str, dict]]],
        *,
        resolve_review_id: str = "",
        resolved_at: str = "",
    ) -> list[tuple[str, dict]]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT payload_json FROM mastery_current WHERE student_id=? AND point_code=?",
                (student_id, point_code),
            ).fetchone()
            previous = json.loads(row[0]) if row else None
            entries = list(build_entries(previous))
            self._commit_entries(
                db, entries, resolve_review_id=resolve_review_id, resolved_at=resolved_at,
            )
            db.commit()
            return entries

    def _commit_entries(
        self,
        db: sqlite3.Connection,
        entries: Iterable[tuple[str, dict]],
        *,
        review_task: Optional[dict] = None,
        resolve_review_id: str = "",
        resolved_at: str = "",
    ) -> None:
        for filename, payload in entries:
            self._write_entry(db, filename, payload)
        if review_task:
            db.execute(
                    """INSERT OR REPLACE INTO review_tasks
                    (review_id, student_id, source_type, target_id, reason, status, created_at, resolved_at, payload_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        review_task["review_id"], review_task["student_id"], review_task["source_type"],
                        review_task["target_id"], review_task["reason"], review_task["status"],
                        review_task["created_at"], review_task.get("resolved_at"),
                        json.dumps(review_task, ensure_ascii=False),
                    ),
                )
        if resolve_review_id:
            row = db.execute(
                    "SELECT payload_json FROM review_tasks WHERE review_id=? AND status='待处理'",
                    (resolve_review_id,),
                ).fetchone()
            if row:
                payload = json.loads(row[0])
                payload["status"] = "已解决"
                payload["resolved_at"] = resolved_at
                db.execute(
                        """UPDATE review_tasks
                        SET status='已解决', resolved_at=?, payload_json=?
                        WHERE review_id=? AND status='待处理'""",
                        (resolved_at, json.dumps(payload, ensure_ascii=False), resolve_review_id),
                )

    def update_review_status(self, review_id: str, status: str, resolved_at: str) -> Optional[dict]:
        if status not in {"已解决", "已放弃"}:
            raise ValueError("复核任务只能更新为已解决或已放弃")
        with self._connect() as db:
            row = db.execute(
                "SELECT payload_json FROM review_tasks WHERE review_id=? AND status='待处理'",
                (review_id,),
            ).fetchone()
            if not row:
                return None
            payload = json.loads(row[0])
            payload["status"] = status
            payload["resolved_at"] = resolved_at
            db.execute(
                "UPDATE review_tasks SET status=?, resolved_at=?, payload_json=? WHERE review_id=?",
                (status, resolved_at, json.dumps(payload, ensure_ascii=False), review_id),
            )
            return payload

    def _write_entry(self, db: sqlite3.Connection, filename: str, payload: dict) -> None:
        record_type = filename.removesuffix(".jsonl")
        id_field = ID_FIELDS.get(record_type)
        record_id = str(payload.get(id_field, "")) if id_field else ""
        if not record_id:
            return
        db.execute(
            """INSERT OR REPLACE INTO records
            (record_type, record_id, student_id, question_id, point_code, created_at, payload_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                record_type, record_id, payload.get("student_id"),
                payload.get("question_id") or payload.get("target_id"), payload.get("point_code"),
                payload.get("created_at") or payload.get("last_updated_at"),
                json.dumps(payload, ensure_ascii=False),
            ),
        )
        if record_type == "mastery":
            db.execute(
                """INSERT INTO mastery_current
                (student_id, point_code, mastery_score, last_updated_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(student_id, point_code) DO UPDATE SET
                    mastery_score=excluded.mastery_score,
                    last_updated_at=excluded.last_updated_at,
                    payload_json=excluded.payload_json""",
                (
                    payload["student_id"], payload["point_code"], payload["mastery_score"],
                    payload["last_updated_at"], json.dumps(payload, ensure_ascii=False),
                ),
            )
        outbox_record_id = record_id
        if record_type == "ingest":
            outbox_record_id = f"{record_id}:{payload.get('status', '')}"
        db.execute(
            """INSERT OR IGNORE INTO outbox(filename, record_type, record_id, payload_json)
            VALUES (?, ?, ?, ?)""",
            (filename, record_type, outbox_record_id, json.dumps(payload, ensure_ascii=False)),
        )

    def flush_outbox(self, log_dir: Path) -> int:
        exported = 0
        with self._connect() as db:
            rows = db.execute(
                "SELECT outbox_id, filename, payload_json FROM outbox WHERE exported_at IS NULL ORDER BY outbox_id"
            ).fetchall()
            for row in rows:
                path = log_dir / row["filename"]
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(row["payload_json"] + "\n")
                db.execute("UPDATE outbox SET exported_at=CURRENT_TIMESTAMP WHERE outbox_id=?", (row["outbox_id"],))
                db.commit()
                exported += 1
        return exported

    def get_mastery(self, student_id: str, point_code: str) -> Optional[dict]:
        with self._connect() as db:
            row = db.execute(
                "SELECT payload_json FROM mastery_current WHERE student_id=? AND point_code=?",
                (student_id, point_code),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def load_records(self, record_type: str, student_id: str = "") -> list[dict]:
        query = "SELECT payload_json FROM records WHERE record_type=?"
        params: list[str] = [record_type]
        if student_id:
            query += " AND student_id=?"
            params.append(student_id)
        query += " ORDER BY created_at, record_id"
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute(query, params).fetchall()]

    def load_current_mastery(self, student_id: str = "") -> list[dict]:
        query = "SELECT payload_json FROM mastery_current"
        params: list[str] = []
        if student_id:
            query += " WHERE student_id=?"
            params.append(student_id)
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute(query, params).fetchall()]

    def load_review_tasks(self, student_id: str = "", status: str = "待处理") -> list[dict]:
        query = "SELECT payload_json FROM review_tasks WHERE status=?"
        params = [status]
        if student_id:
            query += " AND student_id=?"
            params.append(student_id)
        with self._connect() as db:
            return [json.loads(row[0]) for row in db.execute(query, params).fetchall()]

    def get_record(self, record_type: str, record_id: str) -> Optional[dict]:
        with self._connect() as db:
            row = db.execute(
                "SELECT payload_json FROM records WHERE record_type=? AND record_id=?",
                (record_type, record_id),
            ).fetchone()
        return json.loads(row[0]) if row else None

    def schema_version(self) -> int:
        with self._connect() as db:
            return int(db.execute("PRAGMA user_version").fetchone()[0])

    def pending_outbox_count(self) -> int:
        with self._connect() as db:
            return int(db.execute("SELECT COUNT(*) FROM outbox WHERE exported_at IS NULL").fetchone()[0])

    def delete_student(self, student_id: str, question_ids: set[str], ingest_ids: set[str]) -> dict[str, int]:
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            record_count = db.execute("DELETE FROM records WHERE student_id=?", (student_id,)).rowcount
            if question_ids:
                placeholders = ",".join("?" for _ in question_ids)
                record_count += db.execute(
                    f"DELETE FROM records WHERE record_type='evidence' AND question_id IN ({placeholders})",
                    tuple(question_ids),
                ).rowcount
                record_count += db.execute(
                    f"DELETE FROM records WHERE record_type='audit' AND question_id IN ({placeholders})",
                    tuple(question_ids),
                ).rowcount
            mastery_count = db.execute("DELETE FROM mastery_current WHERE student_id=?", (student_id,)).rowcount
            review_count = db.execute("DELETE FROM review_tasks WHERE student_id=?", (student_id,)).rowcount
            outbox_rows = db.execute("SELECT outbox_id, payload_json FROM outbox").fetchall()
            outbox_ids = []
            targets = question_ids | ingest_ids
            for row in outbox_rows:
                payload = json.loads(row["payload_json"])
                if payload.get("student_id") == student_id or str(payload.get("question_id", "")) in question_ids or str(payload.get("target_id", "")) in targets:
                    outbox_ids.append(row["outbox_id"])
            if outbox_ids:
                db.executemany("DELETE FROM outbox WHERE outbox_id=?", [(value,) for value in outbox_ids])
            db.commit()
        return {"records": record_count, "mastery": mastery_count, "reviews": review_count, "outbox": len(outbox_ids)}
