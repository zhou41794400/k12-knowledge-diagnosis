from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树" / "语文"
EXPECTED_CARDS = 95

OBJECTIVE_TOPICS = {"识字与写字", "语言积累与运用"}
READING_TOPICS = {"阅读与鉴赏"}
RUBRIC_TOPICS = {"表达与交流", "梳理与探究", "整本书阅读"}

TOPIC_CUES = {
    "识字与写字": "字音字形词义",
    "语言积累与运用": "语言文字运用",
    "阅读与鉴赏": "阅读理解与鉴赏",
    "表达与交流": "写作与口语表达",
    "梳理与探究": "信息整理与探究",
    "整本书阅读": "整本书阅读任务",
}

BOUNDARIES = {
    "objective_rule": (
        "字音、字形、词义、语病或规范书写等边界明确的任务可形成结构化证据；"
        "涉及语境效果、书写质量和开放表达时，必须保留人工复核。"
    ),
    "reading_mixed": (
        "信息提取、文意判断等客观任务可作为规则证据；主旨阐释、人物评价和审美鉴赏等开放题"
        "应按题目层级量规评分，不能只用最终对错更新掌握度。"
    ),
    "rubric_human_review": (
        "采用内容、结构、语言、证据和交流效果等维度量规，由人工确认后形成证据；"
        "单次总分不得直接等同于某个知识点已掌握。"
    ),
}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def assessment_mode(topic: str) -> str:
    if topic in OBJECTIVE_TOPICS:
        return "objective_rule"
    if topic in READING_TOPICS:
        return "reading_mixed"
    if topic in RUBRIC_TOPICS:
        return "rubric_human_review"
    raise ValueError(f"未定义语文主题评价方式：{topic}")


def keywords(title: str, topic: str) -> list[str]:
    parts = re.split(
        r"(?:与|和|及|、|的|初步|基础|综合|深度|正确|简单|复杂|能力|技巧|策略|训练|运用|掌握|认识|达标)",
        title,
    )
    candidates = [title]
    candidates.extend(part.strip("《》 ") for part in parts if len(part.strip("《》 ")) >= 2)
    candidates.append(TOPIC_CUES[topic])
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    if len(unique) < 3:
        unique.append(f"{title}评价")
    return unique[:4]


def main() -> None:
    cards: list[Path] = []
    for path in KNOWLEDGE_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if value(text, "mastery_granularity") == "knowledge_point":
            cards.append(path)
    if len(cards) != EXPECTED_CARDS:
        raise SystemExit(f"预期 {EXPECTED_CARDS} 张语文知识卡，实际 {len(cards)} 张")

    changed = 0
    for path in cards:
        text = path.read_text(encoding="utf-8")
        if value(text, "status") != "draft":
            raise SystemExit(f"拒绝修改非草稿知识卡：{path}")
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        if not title_match:
            raise SystemExit(f"缺少正文标题：{path}")
        title = title_match.group(1).strip()
        topic = value(text, "topic")
        mode = assessment_mode(topic)
        has_keywords = "matching_keywords:" in text
        has_mode = "assessment_mode:" in text
        has_boundary = "## 学科评价边界" in text
        if has_keywords and has_mode and has_boundary:
            continue
        if has_keywords or has_mode or has_boundary:
            raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{path}")

        keyword_block = "matching_keywords:\n" + "".join(f"  - {item}\n" for item in keywords(title, topic))
        metadata_block = f"{keyword_block}assessment_mode: {mode}\n"
        text = text.replace("mastery_granularity: knowledge_point\n", f"mastery_granularity: knowledge_point\n{metadata_block}", 1)

        boundary_block = (
            "## 学科评价边界\n\n"
            "> [!important] 证据使用边界\n"
            f"> {BOUNDARIES[mode]}\n\n"
        )
        if "## 追踪说明\n" not in text:
            raise SystemExit(f"缺少追踪说明段落：{path}")
        text = text.replace("## 追踪说明\n", f"{boundary_block}## 追踪说明\n", 1)
        if mode == "rubric_human_review":
            text = re.sub(r"^review_required:\s*false$", "review_required: true", text, count=1, flags=re.MULTILINE)
        text = re.sub(r"^updated:\s*.+$", "updated: 2026-07-13", text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        changed += 1
    print(f"本次补充 {changed} 张；语文目标草稿卡共 {len(cards)} 张")


if __name__ == "__main__":
    main()
