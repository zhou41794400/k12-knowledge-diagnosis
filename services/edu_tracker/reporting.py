from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .knowledge_registry import registry


def now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def point_catalog() -> Dict[str, dict]:
    catalog: Dict[str, dict] = {}
    for point in registry():
        catalog[point.point_code] = point.to_dict()
    return catalog


def latest_mastery(rows: Iterable[dict]) -> Dict[Tuple[str, str], dict]:
    latest: Dict[Tuple[str, str], dict] = {}
    for row in rows:
        key = (row.get("student_id", ""), row.get("point_code", ""))
        previous = latest.get(key)
        if previous is None or row.get("last_updated_at", "") >= previous.get("last_updated_at", ""):
            latest[key] = row
    return latest


def render_student_report(
    *,
    student_id: str,
    questions: List[dict],
    mastery_rows: List[dict],
    ingest_rows: List[dict],
) -> str:
    catalog = point_catalog()
    student_questions = [row for row in questions if row.get("student_id") == student_id]
    student_mastery = [row for row in mastery_rows if row.get("student_id") == student_id]
    student_ingest = [row for row in ingest_rows if row.get("student_id") == student_id]
    latest = latest_mastery(student_mastery)

    mastery_list = sorted(
        latest.values(),
        key=lambda row: (row.get("mastery_score", 0.0), row.get("negative_evidence_count", 0), row.get("point_code", "")),
    )
    shortboards = [row for row in mastery_list if row.get("mastery_score", 0.0) < 0.75 or row.get("review_required")]
    recent_questions = student_questions[-5:]

    subject_counter = Counter(row.get("subject", "未知") for row in student_questions)
    review_counter = Counter(row.get("status", "") for row in student_ingest)

    lines: List[str] = []
    lines.append(f"---")
    lines.append(f"title: 学生端周报-{student_id}")
    lines.append(f"tags:")
    lines.append(f"  - project/k12-tracking")
    lines.append(f"  - result-view/student")
    lines.append(f"student_id: {student_id}")
    lines.append(f"updated: {now_date()}")
    lines.append(f"---")
    lines.append("")
    lines.append(f"# 学生端周报 - {student_id}")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 本周录入题目数：{len(student_questions)}")
    lines.append(f"- 本周覆盖学科数：{len(subject_counter)}")
    lines.append(f"- 本周照片导入数：{len(student_ingest)}")
    lines.append(f"- 需要复核的记录数：{sum(1 for row in mastery_list if row.get('review_required'))}")
    lines.append("")
    lines.append("## 学科分布")
    lines.append("")
    if subject_counter:
        lines.append("| 学科 | 题目数 |")
        lines.append("| --- | --- |")
        for subject, count in subject_counter.most_common():
            lines.append(f"| {subject} | {count} |")
    else:
        lines.append("- 暂无录入记录。")
    lines.append("")
    lines.append("## 短板清单")
    lines.append("")
    if shortboards:
        lines.append("| 知识点 | 知识点名称 | 掌握度 | 等级 | 证据数 | 复核 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for row in shortboards[:5]:
            point_code = row.get("point_code", "")
            point = catalog.get(point_code, {})
            lines.append(
                f"| {point_code} | {point.get('topic', point_code)} | {row.get('mastery_score', 0.0)} | "
                f"{row.get('mastery_level', '')} | {row.get('evidence_count', 0)} | {('是' if row.get('review_required') else '否')} |"
            )
    else:
        lines.append("- 当前没有明显短板。")
    lines.append("")
    lines.append("## 最近题目")
    lines.append("")
    if recent_questions:
        lines.append("| 时间 | 学科 | 年级 | 内容 | 结果 |")
        lines.append("| --- | --- | --- | --- | --- |")
        for row in recent_questions:
            result = "正确" if row.get("is_correct") is True else "错误" if row.get("is_correct") is False else "待判断"
            lines.append(
                f"| {row.get('created_at', '')} | {row.get('subject', '')} | {row.get('grade', '')} | "
                f"{row.get('text', '')} | {result} |"
            )
    else:
        lines.append("- 暂无最近题目。")
    lines.append("")
    lines.append("## 本周提醒")
    lines.append("")
    if review_counter.get("待解析", 0) or review_counter.get("待复核", 0):
        lines.append("- 有待处理的导入或复核记录，建议先清理。")
    if shortboards:
        lines.append("- 优先复习短板清单中的前 3 个知识点。")
    if not shortboards and not recent_questions:
        lines.append("- 当前暂无可展示的学习记录。")
    return "\n".join(lines) + "\n"


def render_parent_overview(student_reports: List[Tuple[str, str]], total_questions: int, total_students: int) -> str:
    lines: List[str] = []
    lines.append("---")
    lines.append("title: 家长端总览")
    lines.append("tags:")
    lines.append("  - project/k12-tracking")
    lines.append("  - result-view/parent")
    lines.append(f"updated: {now_date()}")
    lines.append("---")
    lines.append("")
    lines.append("# 家长端总览")
    lines.append("")
    lines.append("## 总体情况")
    lines.append("")
    lines.append(f"- 覆盖学生数：{total_students}")
    lines.append(f"- 已记录题目数：{total_questions}")
    lines.append("")
    lines.append("## 学生周报")
    lines.append("")
    if student_reports:
        for student_id, relative_path in student_reports:
            lines.append(f"- [[{relative_path}|{student_id} 周报]]")
    else:
        lines.append("- 暂无学生周报。")
    lines.append("")
    lines.append("## 使用建议")
    lines.append("")
    lines.append("- 优先查看短板清单前 3 项。")
    lines.append("- 关注带有复核标记的记录，避免直接下结论。")
    lines.append("- 结果页只展示中文摘要和必要证据，不展开内部实现细节。")
    return "\n".join(lines) + "\n"


def generate_reports(project_root: Path, student_id: Optional[str] = None) -> List[Path]:
    vault_root = project_root / "教育智能体"
    log_dir = vault_root / "logs"
    output_dir = vault_root / "05-结果视图"
    output_dir.mkdir(parents=True, exist_ok=True)

    questions = load_jsonl(log_dir / "questions.jsonl")
    mastery_rows = load_jsonl(log_dir / "mastery.jsonl")
    ingest_rows = load_jsonl(log_dir / "ingest.jsonl")

    if student_id:
        student_ids = [student_id]
    else:
        student_ids = sorted({row.get("student_id", "") for row in questions if row.get("student_id")})

    generated: List[Path] = []
    student_refs: List[Tuple[str, str]] = []
    for sid in student_ids:
        report_text = render_student_report(
            student_id=sid,
            questions=questions,
            mastery_rows=mastery_rows,
            ingest_rows=ingest_rows,
        )
        relative_name = f"05-结果视图/学生端-{sid}.md"
        report_path = output_dir / f"学生端-{sid}.md"
        report_path.write_text(report_text, encoding="utf-8")
        generated.append(report_path)
        student_refs.append((sid, relative_name))

    parent_path = output_dir / "家长端总览.md"
    parent_text = render_parent_overview(student_refs, len(questions), len(student_ids))
    parent_path.write_text(parent_text, encoding="utf-8")
    generated.insert(0, parent_path)
    return generated
