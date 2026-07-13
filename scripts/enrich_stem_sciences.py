from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树"
SUBJECTS = ("物理", "化学", "生物学")
EXPECTED_COUNTS = {"物理": 31, "化学": 23, "生物学": 30}
EXPECTED_MODE_COUNTS = {
    "物理": {"concept_rule": 8, "quantitative_calculation": 20, "experimental_evidence": 3},
    "化学": {"concept_rule": 13, "quantitative_calculation": 7, "experimental_evidence": 3},
    "生物学": {"concept_rule": 14, "quantitative_calculation": 1, "experimental_evidence": 15},
}

EXPERIMENTAL_CODES = {
    "PHY-JHS-G8-MAT-001",
    "PHY-SHS-G10-EXP-001",
    "PHY-SHS-G12-EXP-001",
    "CHE-JHS-G9-EXP-001",
    "CHE-JHS-G9-EXP-002",
    "CHE-SHS-G12-EXP-001",
}

QUANTITATIVE_CODES = {
    "PHY-JHS-G8-MAT-002",
    "PHY-JHS-G8-MEC-001",
    "PHY-JHS-G8-MEC-003",
    "PHY-JHS-G9-EM-001",
    "PHY-JHS-G9-EM-002",
    "PHY-JHS-G9-ENE-001",
    "PHY-JHS-G9-MEC-001",
    "PHY-JHS-G9-MEC-002",
    "PHY-JHS-G9-MEC-003",
    "PHY-JHS-G9-WAV-002",
    "PHY-SHS-G10-EM-001",
    "PHY-SHS-G10-MEC-001",
    "PHY-SHS-G10-MEC-002",
    "PHY-SHS-G10-MEC-003",
    "PHY-SHS-G11-EM-001",
    "PHY-SHS-G11-MEC-001",
    "PHY-SHS-G11-MEC-002",
    "PHY-SHS-G11-WAV-001",
    "PHY-SHS-G12-EM-001",
    "PHY-SHS-G12-MEC-001",
    "CHE-JHS-G9-CAL-001",
    "CHE-JHS-G9-CAL-002",
    "CHE-SHS-G10-REA-002",
    "CHE-SHS-G11-REA-001",
    "CHE-SHS-G11-REA-002",
    "CHE-SHS-G11-REA-003",
    "CHE-SHS-G12-REA-001",
    "BIO-SHS-G11-GEN-002",
}

MODE_KEYWORDS = {
    "concept_rule": "核心概念与规律辨析",
    "quantitative_calculation": "数量关系与规范计算",
    "experimental_evidence": "实验探究与证据推理",
}

BOUNDARIES = {
    "物理": {
        "concept_rule": (
            "概念定义、规律条件和典型现象判断可形成结构化证据；涉及多过程解释、模型选择或开放论证时，"
            "应结合推理链核验，不能只凭结论对错更新掌握度。"
        ),
        "quantitative_calculation": (
            "应同时核验物理量、公式条件、单位、运算过程和结果合理性；单个最终数值不能独立证明掌握，"
            "复杂情境中的建模过程需单独评价。"
        ),
        "experimental_evidence": (
            "实验设计、仪器操作、变量控制、数据处理、误差分析和结论解释应按证据链评价；"
            "实验探究结论必须经人工复核后形成掌握证据。"
        ),
    },
    "化学": {
        "concept_rule": (
            "概念、符号、物质性质和反应规律等边界明确的任务可形成结构化证据；宏观现象、微观解释与符号表达"
            "应相互印证，开放解释不能只按结论关键词判定。"
        ),
        "quantitative_calculation": (
            "应同时核验化学式或方程式、数量关系、单位、计算步骤和结果合理性；只答对最终数值不足以证明"
            "计算链条已经掌握。"
        ),
        "experimental_evidence": (
            "实验安全、变量控制、操作顺序、现象记录、数据分析和结论推断应整体评价；探究方案与开放证据"
            "必须经人工复核后形成掌握证据。"
        ),
    },
    "生物学": {
        "concept_rule": (
            "结构名称、功能对应、生命过程和基本机制等边界明确的任务可形成结构化证据；跨层级机制解释"
            "不能仅凭术语命中或最终结论更新掌握度。"
        ),
        "quantitative_calculation": (
            "应同时核验遗传关系判断、符号表达、概率模型、计算过程和结果解释；最终比例正确不等于"
            "遗传推理链完整。"
        ),
        "experimental_evidence": (
            "观察或实验中的问题、假设、变量、对照、样本、数据与结论应按完整证据链评价；涉及健康、生态、"
            "进化或工程方案的开放推理必须经人工复核。"
        ),
    },
}


@dataclass(frozen=True)
class Card:
    path: Path
    text: str
    subject: str
    title: str
    topic: str
    point_code: str
    tracking_mode: str
    assessment_mode: str


def value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def mode_for(subject: str, point_code: str, tracking_mode: str) -> str:
    if point_code in EXPERIMENTAL_CODES:
        return "experimental_evidence"
    if point_code in QUANTITATIVE_CODES:
        return "quantitative_calculation"
    if subject == "生物学" and tracking_mode == "MIXED":
        return "experimental_evidence"
    return "concept_rule"


def keyword_values(text: str) -> list[str]:
    match = re.search(r"^matching_keywords:\n((?:  - .+\n)+)", text, re.MULTILINE)
    if not match:
        return []
    return re.findall(r"^  -\s*(.+)$", match.group(1), re.MULTILINE)


def keywords(card: Card) -> list[str]:
    candidates = [
        card.title,
        card.topic,
        f"{card.title}核心知识",
        MODE_KEYWORDS[card.assessment_mode],
    ]
    parts = re.split(r"(?:与|和|及|、|的)", card.title)
    candidates.extend(part.strip() for part in parts if len(part.strip()) >= 2)
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    if len(unique) < 3:
        raise ValueError(f"无法生成至少 3 个关键词：{card.path}")
    return unique[:5]


def load_cards() -> list[Card]:
    cards: list[Card] = []
    subject_counts: Counter[str] = Counter()
    for subject in SUBJECTS:
        for path in sorted((KNOWLEDGE_ROOT / subject).rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            if value(text, "mastery_granularity") != "knowledge_point":
                continue
            title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            if not title_match:
                raise SystemExit(f"缺少正文标题：{path}")
            actual_subject = value(text, "subject")
            if actual_subject != subject:
                raise SystemExit(f"学科字段与目录不一致：{path}")
            point_code = value(text, "point_code")
            tracking_mode = value(text, "tracking_mode")
            cards.append(
                Card(
                    path=path,
                    text=text,
                    subject=subject,
                    title=title_match.group(1).strip(),
                    topic=value(text, "topic"),
                    point_code=point_code,
                    tracking_mode=tracking_mode,
                    assessment_mode=mode_for(subject, point_code, tracking_mode),
                )
            )
            subject_counts[subject] += 1

    if dict(subject_counts) != EXPECTED_COUNTS:
        raise SystemExit(f"知识卡总数保护失败：预期 {EXPECTED_COUNTS}，实际 {dict(subject_counts)}")

    actual_modes = {
        subject: dict(Counter(card.assessment_mode for card in cards if card.subject == subject))
        for subject in SUBJECTS
    }
    if actual_modes != EXPECTED_MODE_COUNTS:
        raise SystemExit(f"评价分类总数保护失败：预期 {EXPECTED_MODE_COUNTS}，实际 {actual_modes}")
    return cards


def enrichment_state(card: Card) -> str:
    has_keywords = bool(re.search(r"^matching_keywords:", card.text, re.MULTILINE))
    has_mode = bool(re.search(r"^assessment_mode:", card.text, re.MULTILINE))
    has_boundary = "## 学科评价边界" in card.text
    if has_keywords and has_mode and has_boundary:
        return "complete"
    if has_keywords or has_mode or has_boundary:
        return "partial"
    return "missing"


def validate_card(card: Card, require_enriched: bool) -> str:
    if value(card.text, "status") != "draft":
        raise SystemExit(f"拒绝处理非草稿知识卡：{card.path}")
    state = enrichment_state(card)
    if state == "partial":
        raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{card.path}")
    if require_enriched and state != "complete":
        raise SystemExit(f"知识卡尚未完成补充：{card.path}")
    if state != "complete":
        return state

    if value(card.text, "assessment_mode") != card.assessment_mode:
        raise SystemExit(f"评价方式与分类规则不一致：{card.path}")
    if len(keyword_values(card.text)) < 3:
        raise SystemExit(f"matching_keywords 少于 3 个：{card.path}")
    if BOUNDARIES[card.subject][card.assessment_mode] not in card.text:
        raise SystemExit(f"学科评价边界内容不完整：{card.path}")
    if card.assessment_mode == "experimental_evidence" and value(card.text, "review_required") != "true":
        raise SystemExit(f"实验探究或开放证据卡未要求人工复核：{card.path}")
    return state


def enrich(card: Card) -> str:
    keyword_block = "matching_keywords:\n" + "".join(f"  - {item}\n" for item in keywords(card))
    metadata_block = f"{keyword_block}assessment_mode: {card.assessment_mode}\n"
    text = card.text.replace(
        "mastery_granularity: knowledge_point\n",
        f"mastery_granularity: knowledge_point\n{metadata_block}",
        1,
    )
    if text == card.text:
        raise SystemExit(f"无法插入评价元数据：{card.path}")

    boundary_block = (
        "## 学科评价边界\n\n"
        "> [!important] 证据使用边界\n"
        f"> {BOUNDARIES[card.subject][card.assessment_mode]}\n\n"
    )
    if "## 追踪说明\n" not in text:
        raise SystemExit(f"缺少追踪说明段落：{card.path}")
    text = text.replace("## 追踪说明\n", f"{boundary_block}## 追踪说明\n", 1)
    if card.assessment_mode == "experimental_evidence":
        updated_text = re.sub(
            r"^review_required:\s*false$",
            "review_required: true",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if updated_text == text:
            raise SystemExit(f"无法启用人工复核：{card.path}")
        text = updated_text
    text = re.sub(r"^updated:\s*.+$", "updated: 2026-07-13", text, count=1, flags=re.MULTILINE)
    return text


def print_summary(cards: list[Card], changed: int, pending: int, label: str) -> None:
    print(f"{label}：共 {len(cards)} 张，待补充 {pending} 张，本次写入 {changed} 张")
    for subject in SUBJECTS:
        counts = Counter(card.assessment_mode for card in cards if card.subject == subject)
        print(
            f"{subject} {EXPECTED_COUNTS[subject]} 张："
            f"概念规则 {counts['concept_rule']}，"
            f"定量计算 {counts['quantitative_calculation']}，"
            f"实验探究/证据推理 {counts['experimental_evidence']}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="补充物理、化学、生物学知识卡的关键词与评价边界")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--dry-run", action="store_true", help="只做写入前检查并输出计划统计")
    group.add_argument("--check", action="store_true", help="只检查全部知识卡是否符合增强规则")
    args = parser.parse_args()

    cards = load_cards()
    states = [validate_card(card, require_enriched=args.check) for card in cards]
    pending = states.count("missing")
    if args.dry_run or args.check:
        print_summary(cards, changed=0, pending=pending, label="专项检查通过" if args.check else "预检通过")
        return

    updates = [(card.path, enrich(card)) for card, state in zip(cards, states) if state == "missing"]
    for path, text in updates:
        path.write_text(text, encoding="utf-8")

    verified_cards = load_cards()
    for card in verified_cards:
        validate_card(card, require_enriched=True)
    print_summary(verified_cards, changed=len(updates), pending=0, label="增强并复核通过")


if __name__ == "__main__":
    main()
