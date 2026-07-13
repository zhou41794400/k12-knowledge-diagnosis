from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树" / "英语"
EXPECTED_CARDS = 68

FORM_TOPICS = {"词汇", "语法", "语音", "词汇与语法"}
READING_TOPICS = {"阅读", "阅读理解"}
PERFORMANCE_TOPICS = {"写作", "写作表达", "听说能力"}

TOPIC_CUES = {
    "词汇": "英语词汇识别与运用",
    "语法": "英语语法结构",
    "语音": "英语语音与拼读",
    "词汇与语法": "词汇语法综合运用",
    "阅读": "英语阅读理解",
    "阅读理解": "英语篇章理解",
    "写作": "英语写作表达",
    "写作表达": "英语写作任务",
    "听说能力": "英语听说交互",
}

BOUNDARIES = {
    "language_form_rule": (
        "词形、词义、拼读和语法结构等答案边界明确的任务可形成结构化证据；"
        "真实语境中的得体性、流利度和综合表达仍需单独评价。"
    ),
    "reading_mixed": (
        "事实信息定位和明确推断可形成规则证据；篇章结构、作者意图和开放回应应按题目层级评价，"
        "不能只用整篇阅读总分更新单个知识点。"
    ),
    "performance_rubric": (
        "写作与听说任务按内容完成度、语言准确性、连贯性、得体性及语音流利度等维度评分，"
        "由人工确认后形成证据。"
    ),
}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def mode_for(topic: str) -> str:
    if topic in FORM_TOPICS:
        return "language_form_rule"
    if topic in READING_TOPICS:
        return "reading_mixed"
    if topic in PERFORMANCE_TOPICS:
        return "performance_rubric"
    raise ValueError(f"未定义英语主题评价方式：{topic}")


def keywords(title: str, topic: str) -> list[str]:
    parts = re.split(
        r"(?:与|和|及|、|的|初步|基础|基本|综合|日常|常用|核心|简单|复杂|能力|技巧|策略|表达|运用|理解|识别)",
        title,
    )
    candidates = [title]
    candidates.extend(part.strip() for part in parts if len(part.strip()) >= 2)
    candidates.append(TOPIC_CUES[topic])
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    if len(unique) < 3:
        unique.append(f"{title}题型")
    return unique[:4]


def main() -> None:
    cards: list[Path] = []
    for path in KNOWLEDGE_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if value(text, "mastery_granularity") == "knowledge_point":
            cards.append(path)
    if len(cards) != EXPECTED_CARDS:
        raise SystemExit(f"预期 {EXPECTED_CARDS} 张英语知识卡，实际 {len(cards)} 张")

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
        mode = mode_for(topic)
        has_keywords = "matching_keywords:" in text
        has_mode = "assessment_mode:" in text
        has_boundary = "## 学科评价边界" in text
        if has_keywords and has_mode and has_boundary:
            continue
        if has_keywords or has_mode or has_boundary:
            raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{path}")

        keyword_block = "matching_keywords:\n" + "".join(f"  - {item}\n" for item in keywords(title, topic))
        text = text.replace(
            "mastery_granularity: knowledge_point\n",
            f"mastery_granularity: knowledge_point\n{keyword_block}assessment_mode: {mode}\n",
            1,
        )
        boundary_block = (
            "## 学科评价边界\n\n"
            "> [!important] 证据使用边界\n"
            f"> {BOUNDARIES[mode]}\n\n"
        )
        if "## 追踪说明\n" not in text:
            raise SystemExit(f"缺少追踪说明段落：{path}")
        text = text.replace("## 追踪说明\n", f"{boundary_block}## 追踪说明\n", 1)
        if mode == "performance_rubric":
            text = re.sub(r"^review_required:\s*false$", "review_required: true", text, count=1, flags=re.MULTILINE)
        text = re.sub(r"^updated:\s*.+$", "updated: 2026-07-13", text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        changed += 1
    print(f"本次补充 {changed} 张；英语目标草稿卡共 {len(cards)} 张")


if __name__ == "__main__":
    main()
