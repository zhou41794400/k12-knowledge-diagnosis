from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树"
UPDATED_DATE = "2026-07-13"

EXPECTED_CARDS = {
    "历史": 34,
    "地理": 26,
    "道德与法治": 58,
    "思想政治": 20,
}

TOPIC_MODES = {
    "历史": {
        "中国古代史": "fact_location",
        "世界古代史": "fact_location",
        "中国近代史": "material_interpretation",
        "中国现代史": "material_interpretation",
        "世界近代史": "material_interpretation",
        "世界现代史": "material_interpretation",
        "中外历史纲要": "spatiotemporal_synthesis",
        "国家制度": "spatiotemporal_synthesis",
        "文化交流": "spatiotemporal_synthesis",
        "经济与社会": "spatiotemporal_synthesis",
    },
    "地理": {
        "地球与地图": "fact_location",
        "中国地理": "fact_location",
        "世界地理": "fact_location",
        "地理信息技术": "material_interpretation",
        "人文地理": "material_interpretation",
        "自然地理": "spatiotemporal_synthesis",
        "区域发展": "spatiotemporal_synthesis",
    },
    "道德与法治": {
        "法治教育": "concept_rule",
        "国情教育": "material_argumentation",
        "社会参与": "material_argumentation",
        "道德教育": "open_value_judgment",
        "传统文化": "open_value_judgment",
        "心理健康": "open_value_judgment",
    },
    "思想政治": {
        "中国特色社会主义": "concept_rule",
        "法律与生活": "concept_rule",
        "逻辑与思维": "concept_rule",
        "经济与社会": "material_argumentation",
        "政治与法治": "material_argumentation",
        "当代国际政治与经济": "material_argumentation",
        "哲学与文化": "open_value_judgment",
    },
}

TOPIC_CUES = {
    "历史": "历史事件与阶段特征",
    "地理": "地理位置与区域特征",
    "道德与法治": "道德法治情境分析",
    "思想政治": "思想政治材料分析",
}

BOUNDARIES = {
    "历史": {
        "fact_location": (
            "年代、人物、事件、制度和史实对应等边界明确的事实定位任务可形成结构化证据；"
            "孤立记忆正确不等同于已经理解历史因果和阶段特征。"
        ),
        "material_interpretation": (
            "史料信息提取与出处判断可记录分步证据；史料立场、因果解释和历史结论必须依据材料逐项评价，"
            "不能只用最终答案更新掌握度。"
        ),
        "spatiotemporal_synthesis": (
            "应同时考查时间顺序、空间联系、阶段特征与历史因果；跨时期比较和综合解释需按证据链评价，"
            "单一史实命中不能替代时空综合能力。"
        ),
    },
    "地理": {
        "fact_location": (
            "地名、位置、分布和地图要素等边界明确的定位任务可形成结构化证据；"
            "名称识记正确不等同于能够解释区域差异。"
        ),
        "material_interpretation": (
            "地图、统计图表、遥感影像和文字材料的信息提取可记录分步证据；"
            "关系解释必须标明材料依据，不能只按结论关键词判定。"
        ),
        "spatiotemporal_synthesis": (
            "应综合位置、尺度、过程、时间变化和人地关系评价推理链；区域比较与成因分析需按步骤取证，"
            "单项数据正确不能直接等同于综合能力达标。"
        ),
    },
    "道德与法治": {
        "concept_rule": (
            "概念含义、法律规范和权利义务边界明确的任务可形成结构化证据；"
            "会复述规则不等同于能够在真实情境中作出合理选择。"
        ),
        "material_argumentation": (
            "必须评价观点、材料依据、规则调用和论证结构，由人工复核后形成证据；"
            "只出现结论关键词或立场正确不能直接判定掌握。"
        ),
        "open_value_judgment": (
            "价值判断应结合具体情境，按立场合理性、理由充分性、责任意识和行动可行性进行开放评价；"
            "必须由人工复核，不得把单一标准表述作为唯一正确答案。"
        ),
    },
    "思想政治": {
        "concept_rule": (
            "核心概念、基本原理和逻辑规则等边界明确的任务可形成结构化证据；"
            "概念复述正确不等同于能够迁移到复杂社会情境。"
        ),
        "material_argumentation": (
            "必须评价观点、材料依据、原理调用和论证结构，由人工复核后形成证据；"
            "只匹配术语或结论方向正确不能直接判定掌握。"
        ),
        "open_value_judgment": (
            "价值判断应结合事实与公共立场，按价值选择、理由充分性、辩证性和实践指向进行开放评价；"
            "必须由人工复核，不得将单一立场标签替代完整论证。"
        ),
    },
}

REVIEW_REQUIRED_MODES = {"material_argumentation", "open_value_judgment"}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def keywords(title: str, subject: str, topic: str) -> list[str]:
    parts = re.split(
        r"(?:与|和|及|、|的|初步|基础|基本|主要|综合|认识|理解|分析|概述|建设|发展|管理)",
        title,
    )
    candidates = [title]
    candidates.extend(part.strip("《》 ") for part in parts if len(part.strip("《》 ")) >= 2)
    candidates.extend((topic, TOPIC_CUES[subject], f"{title}考查"))
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique[:4]


def keyword_count(text: str) -> int:
    match = re.search(r"^matching_keywords:\s*\n((?:  - .+\n)+)", text, re.MULTILINE)
    return len(re.findall(r"^  - .+$", match.group(1), re.MULTILINE)) if match else 0


def validate_enriched(text: str, path: Path, expected_mode: str) -> None:
    if value(text, "assessment_mode") != expected_mode:
        raise SystemExit(f"评价方式与主题映射不一致：{path}")
    if keyword_count(text) < 3:
        raise SystemExit(f"matching_keywords 少于 3 个：{path}")
    if expected_mode in REVIEW_REQUIRED_MODES and value(text, "review_required") != "true":
        raise SystemExit(f"材料论证或开放价值评价必须人工复核：{path}")


def enrich(text: str, path: Path, subject: str, mode: str) -> str:
    title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if not title_match:
        raise SystemExit(f"缺少正文标题：{path}")
    title = title_match.group(1).strip()
    topic = value(text, "topic")
    keyword_items = keywords(title, subject, topic)
    if len(keyword_items) < 3:
        raise SystemExit(f"无法生成至少 3 个 matching_keywords：{path}")

    keyword_block = "matching_keywords:\n" + "".join(f"  - {item}\n" for item in keyword_items)
    anchor = "mastery_granularity: knowledge_point\n"
    if anchor not in text:
        raise SystemExit(f"缺少知识点粒度锚点：{path}")
    text = text.replace(anchor, f"{anchor}{keyword_block}assessment_mode: {mode}\n", 1)

    tracking_anchor = "## 追踪说明\n"
    if tracking_anchor not in text:
        raise SystemExit(f"缺少追踪说明段落：{path}")
    boundary_block = (
        "## 学科评价边界\n\n"
        "> [!important] 证据使用边界\n"
        f"> {BOUNDARIES[subject][mode]}\n\n"
    )
    text = text.replace(tracking_anchor, f"{boundary_block}{tracking_anchor}", 1)

    if mode in REVIEW_REQUIRED_MODES:
        if not re.search(r"^review_required:\s*.+$", text, re.MULTILINE):
            raise SystemExit(f"缺少 review_required 字段：{path}")
        text = re.sub(
            r"^review_required:\s*.+$",
            "review_required: true",
            text,
            count=1,
            flags=re.MULTILINE,
        )
    text = re.sub(
        r"^updated:\s*.+$",
        f"updated: {UPDATED_DATE}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    return text


def main() -> None:
    cards_by_subject: dict[str, list[Path]] = {}
    for subject, expected_count in EXPECTED_CARDS.items():
        cards = []
        for path in (KNOWLEDGE_ROOT / subject).rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if value(text, "mastery_granularity") == "knowledge_point":
                cards.append(path)
        cards.sort()
        if len(cards) != expected_count:
            raise SystemExit(f"预期 {expected_count} 张{subject}知识卡，实际 {len(cards)} 张")
        cards_by_subject[subject] = cards

    pending: list[tuple[Path, str]] = []
    mode_counts: Counter[tuple[str, str]] = Counter()
    for subject, cards in cards_by_subject.items():
        for path in cards:
            text = path.read_text(encoding="utf-8")
            if value(text, "status") != "draft":
                raise SystemExit(f"拒绝修改非草稿知识卡：{path}")
            if value(text, "subject") != subject:
                raise SystemExit(f"学科字段与目录不一致：{path}")
            topic = value(text, "topic")
            mode = TOPIC_MODES[subject].get(topic)
            if mode is None:
                raise SystemExit(f"未定义{subject}主题评价方式：{topic}（{path}）")
            mode_counts[(subject, mode)] += 1

            fields = (
                "matching_keywords:" in text,
                "assessment_mode:" in text,
                "## 学科评价边界" in text,
            )
            if all(fields):
                validate_enriched(text, path, mode)
                continue
            if any(fields):
                raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{path}")
            pending.append((path, enrich(text, path, subject, mode)))

    for path, text in pending:
        path.write_text(text, encoding="utf-8")

    labels = {
        "fact_location": "事实定位",
        "material_interpretation": "材料解释",
        "spatiotemporal_synthesis": "时空综合",
        "concept_rule": "概念规则",
        "material_argumentation": "材料论证",
        "open_value_judgment": "开放价值评价",
    }
    for subject in EXPECTED_CARDS:
        summary = "，".join(
            f"{labels[mode]} {count} 张"
            for (item_subject, mode), count in mode_counts.items()
            if item_subject == subject
        )
        print(f"{subject}：{summary}")
    print(f"本次补充 {len(pending)} 张；四科目标草稿卡共 {sum(EXPECTED_CARDS.values())} 张")


if __name__ == "__main__":
    main()
