from __future__ import annotations

import json
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Tuple

from .knowledge_registry import registry
from .storage import SQLiteStore


CURRENT_MODEL_VERSION = "rule-v2"


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


def build_point_note_index(vault_root: Path) -> Dict[str, dict]:
    tree_root = vault_root / "02-课标与知识体系" / "02-国家课标知识树"
    index: Dict[str, dict] = {}
    if not tree_root.exists():
        return index
    for path in tree_root.rglob("*.md"):
        meta = read_frontmatter(path)
        point_code = meta.get("point_code")
        if not point_code:
            continue
        title = extract_first_heading(path) or str(meta.get("title") or path.stem)
        index[point_code] = {
            "path": path.relative_to(vault_root).as_posix(),
            "abs_path": path,
            "title": title,
        }
    return index


def read_frontmatter(path: Path) -> Dict[str, str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    meta: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip().strip('"').strip("'")
        meta[key] = value
    return meta


def extract_first_heading(path: Path) -> Optional[str]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    in_frontmatter = False
    for line in lines:
        if line.strip() == "---":
            in_frontmatter = not in_frontmatter
            continue
        if in_frontmatter:
            continue
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def wikilink(path: str, alias: Optional[str] = None) -> str:
    return f"[[{path}|{alias}]]" if alias else f"[[{path}]]"


def question_detail_relative_path(question_id: str) -> str:
    return f"05-结果视图/题目详情/{question_id}.md"


def student_report_relative_path(student_id: str) -> str:
    return f"05-结果视图/学生端-{safe_filename_component(student_id)}.md"


def safe_filename_component(value: str) -> str:
    normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "-", value.strip()).strip("-._")
    if normalized == value and normalized:
        return normalized
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:8]
    return f"{normalized or '学生'}-{digest}"


def yaml_string(value: object) -> str:
    return json.dumps(str(value), ensure_ascii=False)


def markdown_inline(value: object) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|")


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
    evidence_rows: List[dict],
    mastery_rows: List[dict],
    mastery_history: List[dict],
    ingest_rows: List[dict],
    point_index: Dict[str, dict],
    legacy_question_ids: set[str],
    review_tasks: List[dict],
) -> str:
    catalog = point_catalog()
    student_questions = [row for row in questions if row.get("student_id") == student_id]
    student_mastery = [row for row in mastery_rows if row.get("student_id") == student_id]
    student_history = [row for row in mastery_history if row.get("student_id") == student_id]
    student_ingest = [row for row in ingest_rows if row.get("student_id") == student_id]
    student_reviews = [row for row in review_tasks if row.get("student_id") == student_id]
    question_to_point = {
        row.get("question_id", ""): row.get("point_code", "")
        for row in evidence_rows
        if row.get("question_id") and row.get("point_code")
    }
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
    lines.append(f"title: {yaml_string(f'学生端周报-{student_id}')}")
    lines.append(f"tags:")
    lines.append(f"  - project/k12-tracking")
    lines.append(f"  - result-view/student")
    lines.append(f"student_id: {yaml_string(student_id)}")
    lines.append(f"updated: {now_date()}")
    lines.append(f"---")
    lines.append("")

    lines.append(f"# 学生端周报 - {markdown_inline(student_id)}")
    lines.append("")
    lines.append("## 总览")
    lines.append("")
    lines.append(f"- 累计录入题目数：{len(student_questions)}")
    lines.append(f"- 当前模型有效证据数：{sum(1 for row in evidence_rows if row.get('question_id') in {q.get('question_id') for q in student_questions})}")
    lines.append(f"- 待重新分析的历史样例数：{sum(1 for row in student_questions if row.get('question_id') in legacy_question_ids)}")
    lines.append(f"- 累计覆盖学科数：{len(subject_counter)}")
    lines.append(f"- 累计照片导入数：{len(student_ingest)}")
    lines.append(f"- 需要复核的记录数：{len(student_reviews)}")
    lines.append("")
    lines.append("## 掌握度变化")
    lines.append("")
    history_by_point: Dict[str, List[dict]] = defaultdict(list)
    for row in student_history:
        history_by_point[str(row.get("point_code", ""))].append(row)
    trend_rows = []
    for point_code, rows in history_by_point.items():
        ordered = sorted(rows, key=lambda row: row.get("last_updated_at", ""))
        if len(ordered) < 2:
            continue
        change = round(float(ordered[-1].get("mastery_score", 0)) - float(ordered[-2].get("mastery_score", 0)), 3)
        trend_rows.append((point_code, change, ordered[-1]))
    if trend_rows:
        lines.append("| 知识点 | 上次 | 当前 | 变化 |")
        lines.append("| --- | --- | --- | --- |")
        for point_code, change, current in sorted(trend_rows, key=lambda item: item[1])[:5]:
            rows = sorted(history_by_point[point_code], key=lambda row: row.get("last_updated_at", ""))
            point_meta = point_index.get(point_code, {})
            name = point_meta.get("title") or catalog.get(point_code, {}).get("topic") or point_code
            direction = f"+{change}" if change > 0 else str(change)
            lines.append(f"| {name} | {rows[-2].get('mastery_score', 0)} | {current.get('mastery_score', 0)} | {direction} |")
    else:
        lines.append("- 需要至少两次有效证据后才能展示变化。")
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
        lines.append("| 知识点代码 | 知识点名称 | 知识点页面 | 掌握度 | 等级 | 证据数 | 复核 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in shortboards[:5]:
            point_code = row.get("point_code", "")
            point = catalog.get(point_code, {})
            point_meta = point_index.get(point_code, {})
            point_title = point_meta.get("title") or point.get("topic", point_code)
            point_link = wikilink(point_meta["path"], point_meta["title"]) if point_meta else point_code
            lines.append(
                f"| {point_code} | {point_title} | {point_link} | {row.get('mastery_score', 0.0)} | "
                f"{row.get('mastery_level', '')} | {row.get('evidence_count', 0)} | {('是' if row.get('review_required') else '否')} |"
            )
    else:
        lines.append("- 当前没有明显短板。")
    lines.append("")

    lines.append("## 本周复习任务")
    lines.append("")
    if shortboards:
        for index, row in enumerate(shortboards[:3], start=1):
            point_code = row.get("point_code", "")
            point_meta = point_index.get(point_code, {})
            point_name = point_meta.get("title") or catalog.get(point_code, {}).get("topic") or point_code
            lines.append(f"- [ ] 任务 {index}：围绕 {point_name} 完成 3 至 5 道基础或变式题。")
    else:
        lines.append("- [ ] 本周保持正常复习节奏。")
    lines.append("")

    linked_point_codes = []
    seen_points = set()
    for row in student_questions:
        point_code = question_to_point.get(row.get("question_id", ""), "")
        if not point_code or point_code in seen_points:
            continue
        seen_points.add(point_code)
        linked_point_codes.append(point_code)
    if linked_point_codes:
        lines.append("## 关联知识点")
        lines.append("")
        for point_code in linked_point_codes:
            point_meta = point_index.get(point_code, {})
            if point_meta:
                lines.append(f"- {wikilink(point_meta['path'], point_meta['title'])} `({point_code})`")
            else:
                lines.append(f"- `{point_code}`")
        lines.append("")

    lines.append("## 最近题目")
    lines.append("")
    if recent_questions:
        lines.append("| 时间 | 学科 | 年级 | 内容 | 关联知识点 | 题目详情 | 结果 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- |")
        for row in recent_questions:
            is_legacy = row.get("question_id") in legacy_question_ids
            result = "历史样例，待重新分析" if is_legacy else "正确" if row.get("is_correct") is True else "错误" if row.get("is_correct") is False else "待判断"
            point_code = question_to_point.get(row.get("question_id", ""), "")
            point_meta = point_index.get(point_code, {})
            point_link = wikilink(point_meta["path"], point_meta["title"]) if point_meta else point_code
            detail_link = wikilink(question_detail_relative_path(row.get("question_id", "")), "查看")
            lines.append(
                f"| {markdown_inline(row.get('created_at', ''))} | {markdown_inline(row.get('subject', ''))} | "
                f"{markdown_inline(row.get('grade', ''))} | {markdown_inline(row.get('text', ''))} | "
                f"{point_link} | {detail_link} | {result} |"
            )
    else:
        lines.append("- 暂无最近题目。")
    lines.append("")
    lines.append("## 当前提醒")
    lines.append("")
    if student_reviews or review_counter.get("待解析", 0) or review_counter.get("待复核", 0) or review_counter.get("待确认", 0) or review_counter.get("OCR失败", 0):
        lines.append("- 有待处理的导入或复核记录，建议先清理。")
    if shortboards:
        lines.append("- 优先复习短板清单中的前 3 个知识点。")
    if not shortboards and not recent_questions:
        lines.append("- 当前暂无可展示的学习记录。")
    return "\n".join(lines).rstrip() + "\n"


def render_parent_overview(
    student_reports: List[Tuple[str, str]],
    total_questions: int,
    total_students: int,
    current_evidence_count: int,
    legacy_question_count: int,
    pending_review_count: int,
) -> str:
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
    lines.append(f"- 当前模型有效证据数：{current_evidence_count}")
    lines.append(f"- 待重新分析的历史样例数：{legacy_question_count}")
    lines.append(f"- 待处理复核任务数：{pending_review_count}")
    lines.append("")
    lines.append("## 学生周报")
    lines.append("")
    if student_reports:
        for student_id, relative_path in student_reports:
            lines.append(f"- [[{relative_path}|{markdown_inline(student_id).replace(']', '')} 周报]]")
    else:
        lines.append("- 暂无学生周报。")
    lines.append("")
    lines.append("## 使用建议")
    lines.append("")
    lines.append("- 优先查看短板清单前 3 项。")
    lines.append("- 关注带有复核标记的记录，避免直接下结论。")
    lines.append("- 结果页只展示中文摘要和必要证据，不展开内部实现细节。")
    return "\n".join(lines).rstrip() + "\n"


def generate_reports(project_root: Path, student_id: Optional[str] = None) -> List[Path]:
    vault_root = project_root / "教育智能体"
    log_dir = vault_root / "logs"
    output_dir = vault_root / "05-结果视图"
    detail_dir = output_dir / "题目详情"
    output_dir.mkdir(parents=True, exist_ok=True)
    detail_dir.mkdir(parents=True, exist_ok=True)
    point_index = build_point_note_index(vault_root)

    store = SQLiteStore(log_dir / "edu_tracker.sqlite3")
    questions = _merge_records(store.load_records("questions"), load_jsonl(log_dir / "questions.jsonl"), "question_id")
    all_evidence_rows = _merge_records(store.load_records("evidence"), load_jsonl(log_dir / "evidence.jsonl"), "event_id")
    evidence_rows = [row for row in all_evidence_rows if row.get("model_version") == CURRENT_MODEL_VERSION]
    legacy_question_ids = {
        str(row.get("question_id"))
        for row in all_evidence_rows
        if row.get("question_id") and row.get("model_version") != CURRENT_MODEL_VERSION
    }
    mastery_rows = store.load_current_mastery()
    mastery_history = store.load_records("mastery")
    audit_rows = _merge_records(store.load_records("audit"), load_jsonl(log_dir / "audit.jsonl"), "audit_id")
    ingest_rows = _merge_records(store.load_records("ingest"), load_jsonl(log_dir / "ingest.jsonl"), "ingest_id")
    review_tasks = store.load_review_tasks()
    evidence_by_question = {row.get("question_id", ""): row for row in evidence_rows if row.get("question_id")}
    current_evidence_ids = {row.get("event_id") for row in evidence_rows if row.get("event_id")}
    mastery_rows = [row for row in mastery_rows if row.get("last_evidence_id") in current_evidence_ids]
    audit_by_question = {row.get("target_id", ""): row for row in audit_rows if row.get("target_id")}
    latest_mastery_by_point = latest_mastery(mastery_rows)

    if student_id:
        student_ids = [student_id]
    else:
        student_ids = sorted(
            {
                str(row.get("student_id", ""))
                for rows in (questions, mastery_rows, ingest_rows, review_tasks)
                for row in rows
                if row.get("student_id")
            }
        )

    generated: List[Path] = []
    student_refs: List[Tuple[str, str]] = []
    for sid in student_ids:
        student_questions = [row for row in questions if row.get("student_id") == sid]
        for row in student_questions:
            question_id = row.get("question_id", "")
            point_code = evidence_by_question.get(question_id, {}).get("point_code", "")
            point_meta = point_index.get(point_code, {})
            mastery_snapshot = latest_mastery_by_point.get((sid, point_code), {})
            detail_text = render_question_detail(
                question=row,
                point_code=point_code,
                point_meta=point_meta,
                point_index=point_index,
                evidence_row=evidence_by_question.get(question_id, {}),
                mastery_row=mastery_snapshot,
                audit_row=audit_by_question.get(question_id, {}),
                student_report_path=student_report_relative_path(sid),
                legacy_evidence=question_id in legacy_question_ids,
            )
            detail_path = detail_dir / f"{question_id}.md"
            detail_path.write_text(detail_text, encoding="utf-8")
            generated.append(detail_path)
        report_text = render_student_report(
            student_id=sid,
            questions=questions,
            evidence_rows=evidence_rows,
            mastery_rows=mastery_rows,
            mastery_history=mastery_history,
            ingest_rows=ingest_rows,
            point_index=point_index,
            legacy_question_ids=legacy_question_ids,
            review_tasks=review_tasks,
        )
        relative_name = student_report_relative_path(sid)
        report_path = vault_root / relative_name
        report_path.write_text(report_text, encoding="utf-8")
        generated.append(report_path)
        student_refs.append((sid, relative_name))

    selected_questions = [row for row in questions if row.get("student_id") in student_ids]
    parent_path = output_dir / "家长端总览.md"
    selected_question_ids = {row.get("question_id") for row in selected_questions}
    parent_text = render_parent_overview(
        student_refs,
        len(selected_questions),
        len(student_ids),
        sum(1 for row in evidence_rows if row.get("question_id") in selected_question_ids),
        sum(1 for question_id in legacy_question_ids if question_id in selected_question_ids),
        sum(1 for row in review_tasks if row.get("student_id") in student_ids),
    )
    parent_path.write_text(parent_text, encoding="utf-8")
    generated.insert(0, parent_path)
    return generated


def _merge_records(current: List[dict], legacy: List[dict], id_field: str) -> List[dict]:
    merged = {str(row.get(id_field)): row for row in legacy if row.get(id_field)}
    merged.update({str(row.get(id_field)): row for row in current if row.get(id_field)})
    return sorted(merged.values(), key=lambda row: (row.get("created_at", ""), str(row.get(id_field, ""))))


def render_question_detail(
    *,
    question: dict,
    point_code: str,
    point_meta: Dict[str, dict],
    point_index: Dict[str, dict],
    evidence_row: dict,
    mastery_row: dict,
    audit_row: dict,
    student_report_path: str,
    legacy_evidence: bool,
) -> str:
    catalog = point_catalog()
    point_data = catalog.get(point_code, {})
    question_id = question.get("question_id", "")
    point_link = ""
    if legacy_evidence:
        point_link = "未识别（旧模型映射已隔离）"
    elif point_meta:
        point_link = wikilink(point_meta["path"], point_meta["title"])
    elif point_code:
        point_link = point_code
    else:
        point_link = "未识别"
    answer = question.get("answer", "")
    student_answer = question.get("student_answer", "")
    result = "正确" if question.get("is_correct") is True else "错误" if question.get("is_correct") is False else "待判断"
    review_required = "是" if legacy_evidence or question.get("review_required") else "否"
    error_reason = infer_error_reason(question, point_data, evidence_row)
    recommendation = build_recommendation(point_data, point_meta, question, evidence_row, mastery_row)
    result_is_correct = question.get("is_correct") is True
    result_is_wrong = question.get("is_correct") is False

    lines: List[str] = []
    lines.append("---")
    lines.append(f"title: 题目详情-{question_id}")
    lines.append("tags:")
    lines.append("  - project/k12-tracking")
    lines.append("  - result-view/question")
    lines.append(f"question_id: {question_id}")
    lines.append(f"student_id: {yaml_string(question.get('student_id', ''))}")
    lines.append(f'point_code: "{point_code}"')
    lines.append(f"updated: {now_date()}")
    lines.append("---")
    lines.append("")
    lines.append(f"# 题目详情 - {question_id}")
    lines.append("")
    if legacy_evidence:
        lines.append("> [!warning] 历史样例，待重新分析")
        lines.append("> 本题原由 `rule-v1` 处理，旧知识点映射和掌握度已从当前报告隔离。原题与作答仅用于审计回溯，不能作为当前诊断结论。")
        lines.append("")
    lines.append("## 基本信息")
    lines.append("")
    lines.append(f"- 学生：{question.get('student_id', '')}")
    lines.append(f"- 学科：{question.get('subject', '')}")
    lines.append(f"- 年级：{question.get('grade', '')}")
    lines.append(f"- 来源：{question.get('source_type', '')}")
    lines.append(f"- 结果：{result}")
    lines.append(f"- 复核：{review_required}")
    lines.append(f"- 回到周报：[[{student_report_path}|学生周报]]")
    lines.append("")
    lines.append("## 原题")
    lines.append("")
    lines.append(question.get("text", "") or "无")
    lines.append("")
    lines.append("## 作答信息")
    lines.append("")
    lines.append(f"- 标准答案：{answer or '无'}")
    lines.append(f"- 学生作答：{student_answer or '无'}")
    lines.append(f"- 关联知识点：{point_link}")
    lines.append("")
    lines.append("## 证据与掌握")
    lines.append("")
    lines.append(f"- 证据强度：{evidence_row.get('evidence_strength', '未知')}")
    lines.append(f"- 置信度：{evidence_row.get('confidence', '')}")
    lines.append(f"- 掌握度：{mastery_row.get('mastery_score', '')}")
    lines.append(f"- 掌握等级：{mastery_row.get('mastery_level', '')}")
    lines.append(f"- 最近证据：{mastery_row.get('last_evidence_id', '')}")
    lines.append(f"- 复核建议：{('需要' if legacy_evidence or mastery_row.get('review_required') else '不需要')}")
    lines.append(f"- 错因判断：{('旧模型结果已隔离，待重新分析。' if legacy_evidence else error_reason)}")
    lines.append("")
    if legacy_evidence:
        lines.append("## 本题结论")
        lines.append("")
        lines.append("- 本题尚未经过当前模型重新分析。")
        lines.append("- 不生成知识点、掌握度或复习建议。")
        lines.append("")
    elif result_is_correct:
        lines.append("## 本题结论")
        lines.append("")
        lines.append("- 本题作答正确。")
        lines.append("- 这类题可作为正向证据，但仍要结合整体掌握度判断是否继续巩固。")
        lines.append("")
    elif result_is_wrong:
        lines.append("## 错题分析")
        lines.append("")
        lines.append("- 本题作答错误。")
        lines.append(f"- 主要错因：{error_reason}")
        lines.append("")
        lines.append("## 纠错重点")
        lines.append("")
        lines.append("- 先复核题干、标准答案和学生作答。")
        lines.append("- 再回到对应知识点的前置知识与基础题重新练习。")
        lines.append("")
        lines.append("## 下次复习")
        lines.append("")
        lines.append(f"- {recommendation}")
        lines.append("")
    else:
        lines.append("## 本题结论")
        lines.append("")
        lines.append("- 当前无法明确判断对错。")
        lines.append(f"- 建议：{recommendation}")
        lines.append("")
    lines.append("## 前置知识")
    lines.append("")
    prerequisites = [] if legacy_evidence else extract_section_bullets(
        Path(point_meta["abs_path"]) if point_meta and point_meta.get("abs_path") else None,
        "## 前置知识",
    )
    if not prerequisites:
        prerequisites = point_data.get("prerequisites", []) or []
    if prerequisites:
        for item in prerequisites:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无前置知识记录。")
    lines.append("")
    lines.append("## 复习建议")
    lines.append("")
    if legacy_evidence:
        lines.append("- 待当前模型重新分析后再生成建议。")
    elif result_is_wrong:
        lines.append("- 错题优先补基础，再做同类变式题。")
    elif result_is_correct:
        lines.append("- 正确题可做少量同类巩固题，保持熟练度。")
    else:
        lines.append(f"- {recommendation}")
    lines.append("")
    lines.append("## 审计记录")
    lines.append("")
    if audit_row:
        lines.append(f"- 审计类型：{audit_row.get('event_type', '')}")
        lines.append(f"- 审计原因：{audit_row.get('reason', '')}")
    else:
        lines.append("- 暂无审计记录。")
    lines.append("")
    lines.append("## 关联知识点")
    lines.append("")
    if legacy_evidence:
        lines.append("- 旧模型关联已隔离，当前无有效知识点。")
    elif point_code and point_meta:
        lines.append(f"- {wikilink(point_meta['path'], point_meta['title'])}")
        lines.append(f"- 关联知识点代码：`{point_code}`")
    elif point_code:
        lines.append(f"- `{point_code}`")
    else:
        lines.append("- 暂未识别出知识点。")
    lines.append("")
    lines.append("## 反向追踪")
    lines.append("")
    lines.append("- 题目详情页可通过知识点页的反向链接被检索到。")
    lines.append("- 周报页也会链接到本页，便于在 Obsidian 中往返查看。")
    return "\n".join(lines).rstrip() + "\n"


def infer_error_reason(question: dict, point_data: dict, evidence_row: dict) -> str:
    if question.get("is_correct") is True:
        return "本题作答正确，暂未发现明显错因。"
    if question.get("is_correct") is None:
        return "答案信息不足，暂无法判断错因。"
    if evidence_row.get("evidence_strength") == "弱":
        return "证据较弱，建议先复核题干与答案，再判断是否为知识点错误。"
    topic = str(point_data.get("topic", ""))
    topic_code = str(point_data.get("topic_code", ""))
    if topic_code == "NS" or "数与代数" in topic:
        return "更像是计算步骤或口诀调用不稳定。"
    if topic_code == "READ" or "阅读" in topic:
        return "更像是关键信息提取或理解偏差。"
    if topic_code == "GRM" or "语法" in topic:
        return "更像是规则应用不稳定或句型转换失误。"
    return "更像是知识点理解不足或题目迁移能力不足。"


def build_recommendation(
    point_data: dict,
    point_meta: dict,
    question: dict,
    evidence_row: dict,
    mastery_row: dict,
) -> str:
    point_code = str(point_data.get("point_code", ""))
    topic = str(point_meta.get("title") or point_data.get("topic", ""))
    if question.get("review_required") or evidence_row.get("evidence_strength") == "弱":
        return "先人工复核题目与答案，再重新判断是否需要更新掌握度。"
    if mastery_row.get("mastery_score", 0.0) < 0.45:
        return f"优先回到 {topic or point_code} 的基础练习题，做 3 到 5 道同类题巩固。"
    if mastery_row.get("mastery_score", 0.0) < 0.75:
        return f"继续做 {topic or point_code} 的变式题，重点检查步骤是否稳定。"
    return f"保持复习节奏，围绕 {topic or point_code} 做少量巩固题即可。"


def extract_section_bullets(path: Optional[Path], heading: str) -> List[str]:
    if path is None or not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    target_index: Optional[int] = None
    for i, line in enumerate(lines):
        if line.strip() == heading:
            target_index = i
            break
    if target_index is None:
        return []
    bullets: List[str] = []
    for line in lines[target_index + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if stripped.startswith("- "):
            bullets.append(stripped[2:].strip())
    return bullets
