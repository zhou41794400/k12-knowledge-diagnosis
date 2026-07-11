from __future__ import annotations

import re


STUDENT_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{1,64}$")
SUPPORTED_SUBJECTS = {"数学", "语文", "英语", "科学", "物理", "化学", "生物学", "历史", "地理", "道德与法治", "思想政治", "信息科技", "体育与健康", "艺术", "劳动"}


def validate_context(student_id: str, subject: str, grade: str) -> None:
    if not STUDENT_ID_PATTERN.fullmatch(student_id):
        raise ValueError("学生编号仅能包含字母、数字、下划线和连字符，长度 1 至 64 位")
    if subject not in SUPPORTED_SUBJECTS:
        raise ValueError("不支持的学科")
    if not grade.strip() or len(grade) > 16 or any(ord(char) < 32 for char in grade):
        raise ValueError("年级不合法")


def validate_question_text(text: str) -> None:
    if not text.strip():
        raise ValueError("题干不能为空")
    if len(text) > 10000:
        raise ValueError("题干不能超过 10000 个字符")


def validate_answer(value: str, field_name: str) -> None:
    if len(value) > 2000:
        raise ValueError(f"{field_name}不能超过 2000 个字符")
