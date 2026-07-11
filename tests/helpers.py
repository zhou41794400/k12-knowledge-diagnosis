from pathlib import Path


def write_point(
    root: Path,
    *,
    point_code: str = "MATH-PRI-G2-NS-003",
    subject: str = "数学",
    subject_code: str = "MATH",
    grade: str = "二年级",
    title: str = "乘法口诀的熟练应用",
    status: str = "published",
    keywords: tuple[str, ...] = ("乘法口诀", "口诀"),
) -> Path:
    path = root / subject / grade / f"{point_code}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    keyword_lines = "\n".join(f"  - {keyword}" for keyword in keywords)
    path.write_text(
        f"""---
title: {title}
tags:
  - knowledge-point
subject: {subject}
subject_code: {subject_code}
stage: 小学
stage_code: PRI
grade: {grade}
topic: 数与代数
topic_code: NS
point_code: {point_code}
standard_version: 2022
tracking_mode: RULE
mastery_granularity: knowledge_point
matching_keywords:
{keyword_lines}
status: {status}
---
# {title}
""",
        encoding="utf-8",
    )
    return path
