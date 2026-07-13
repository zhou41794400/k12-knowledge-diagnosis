from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树"
UPDATED_DATE = "2026-07-13"


@dataclass(frozen=True)
class SubjectConfig:
    expected_cards: int
    topic_cues: dict[str, str]


SUBJECTS = {
    "体育与健康": SubjectConfig(
        expected_cards=43,
        topic_cues={
            "基本运动技能": "基本运动技能表现",
            "体能发展": "体能发展过程",
            "球类活动": "球类活动表现",
            "体操与技巧": "体操技巧表现",
            "民族传统体育": "民族传统体育表现",
            "球类运动": "球类运动表现",
            "田径类运动": "田径运动表现",
            "体能训练": "体能训练过程",
            "健康知识": "健康知识与行为",
            "健康教育": "健康教育与实践",
        },
    ),
    "艺术": SubjectConfig(
        expected_cards=33,
        topic_cues={
            "音乐感知": "音乐感知与表现",
            "造型·美术": "美术创作作品",
            "艺术欣赏": "艺术欣赏与阐释",
            "舞蹈表现": "舞蹈动作表现",
            "戏剧表演": "戏剧角色表现",
            "影视艺术": "影视作品欣赏",
            "音乐": "音乐实践表现",
            "舞蹈": "舞蹈实践表现",
            "戏剧": "戏剧实践表现",
            "影视": "影视作品鉴赏",
            "音乐鉴赏": "音乐鉴赏阐释",
            "美术鉴赏": "美术鉴赏阐释",
            "艺术展演": "艺术展演过程",
            "艺术创作": "艺术主题创作",
        },
    ),
    "劳动": SubjectConfig(
        expected_cards=33,
        topic_cues={
            "日常生活劳动": "日常劳动实践",
            "生产劳动": "生产劳动实践",
            "服务性劳动": "服务劳动过程",
            "传统工艺": "传统工艺作品",
            "新技术体验": "新技术实践作品",
            "职业启蒙": "职业体验过程",
            "职业体验": "职业体验过程",
            "新技术应用": "新技术应用作品",
        },
    ),
}

PURE_HEALTH_KNOWLEDGE = {"运动与营养", "睡眠与健康", "合理饮食与营养"}
HEALTH_TOPICS = {"健康知识", "健康教育"}
ART_APPRECIATION_TOPICS = {"艺术欣赏", "影视艺术", "影视", "美术鉴赏", "音乐鉴赏"}
ARTWORK_TOPICS = {"造型·美术", "艺术创作"}
LABOR_PRODUCT_TOPICS = {"生产劳动", "传统工艺", "新技术体验", "新技术应用"}

BOUNDARIES = {
    "sport_performance_rubric": (
        "依据动作规范、安全意识、完成质量、体能变化和合作表现等维度量规，结合多次课堂观察形成证据；"
        "单次测试成绩或单题对错不得直接判定动作技能已经掌握。"
    ),
    "health_process_rubric": (
        "健康概念客观题只能证明知识理解；习惯养成、风险处置和健康行为应结合情境任务、行为记录与过程量规，"
        "经人工复核后形成证据。"
    ),
    "health_knowledge_objective": (
        "仅边界明确的健康知识识记、分类和判断题可形成规则证据；涉及行为养成、方案制定或实际处置时，"
        "必须转为过程性评价并人工复核。"
    ),
    "art_performance_rubric": (
        "依据感知理解、技能运用、表现完整性、合作参与和反思改进等维度量规评价，并保留过程记录；"
        "单题对错不得直接判定艺术表现能力已经掌握。"
    ),
    "artwork_rubric": (
        "结合创作过程、材料与技法、主题表达、作品完成度和自评互评等证据进行作品量规评价；"
        "不得仅凭知识题对错或单件作品总分直接判定掌握。"
    ),
    "art_appreciation_rubric": (
        "事实性识别只作为辅助证据，重点依据观察描述、审美阐释、比较分析和证据表达等维度量规；"
        "开放性艺术理解须经人工复核，不能以单题对错判定掌握。"
    ),
    "labor_process_rubric": (
        "依据任务规划、规范操作、安全卫生、协作责任、问题解决和反思改进等过程量规，结合连续观察形成证据；"
        "单题对错不得直接判定劳动实践能力已经掌握。"
    ),
    "labor_product_rubric": (
        "综合评价操作过程、安全规范、工具材料使用、成果质量、实用性和改进说明；"
        "不得仅凭成品外观、一次结果或单题对错直接判定劳动能力已经掌握。"
    ),
}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def assessment(subject: str, topic: str, title: str) -> tuple[str, bool]:
    if subject == "体育与健康":
        if title in PURE_HEALTH_KNOWLEDGE:
            return "health_knowledge_objective", False
        if topic in HEALTH_TOPICS:
            return "health_process_rubric", True
        return "sport_performance_rubric", True
    if subject == "艺术":
        if topic in ART_APPRECIATION_TOPICS:
            return "art_appreciation_rubric", True
        if topic in ARTWORK_TOPICS:
            return "artwork_rubric", True
        return "art_performance_rubric", True
    if subject == "劳动":
        if topic in LABOR_PRODUCT_TOPICS:
            return "labor_product_rubric", True
        return "labor_process_rubric", True
    raise ValueError(f"未定义学科评价方式：{subject}")


def matching_keywords(title: str, topic: str, cue: str) -> list[str]:
    parts = re.split(
        r"(?:与|和|及|、|·|的|基本|基础|简单|综合|初步|实践|体验|能力|技能|技巧|活动|训练|学习|制作|表现)",
        title,
    )
    candidates = [title]
    candidates.extend(part.strip() for part in parts if len(part.strip()) >= 2)
    candidates.extend((cue, f"{topic}评价", f"{title}任务"))
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    if len(unique) < 3:
        raise ValueError(f"无法为“{title}”生成至少 3 个匹配关键词")
    return unique[:4]


def title_of(text: str, path: Path) -> str:
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if not match:
        raise SystemExit(f"缺少正文标题：{path}")
    return match.group(1).strip()


def keyword_count(text: str) -> int:
    match = re.search(r"^matching_keywords:\s*\n((?:\s+- .+\n)+)", text, re.MULTILINE)
    if not match:
        return 0
    return len(re.findall(r"^\s+- .+$", match.group(1), re.MULTILINE))


def collect_cards(subject: str, config: SubjectConfig) -> list[Path]:
    cards = []
    for path in (KNOWLEDGE_ROOT / subject).rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if value(text, "mastery_granularity") == "knowledge_point":
            cards.append(path)
    cards.sort()
    if len(cards) != config.expected_cards:
        raise SystemExit(f"预期 {config.expected_cards} 张{subject}知识卡，实际 {len(cards)} 张")
    return cards


def validate_card(subject: str, path: Path, text: str) -> None:
    title = title_of(text, path)
    topic = value(text, "topic")
    expected_mode, expected_review = assessment(subject, topic, title)
    if value(text, "status") != "draft":
        raise SystemExit(f"专项校验失败，卡片未保持草稿：{path}")
    if keyword_count(text) < 3:
        raise SystemExit(f"专项校验失败，matching_keywords 少于 3 个：{path}")
    if value(text, "assessment_mode") != expected_mode:
        raise SystemExit(f"专项校验失败，assessment_mode 不符合预期：{path}")
    if "## 学科评价边界" not in text or BOUNDARIES[expected_mode] not in text:
        raise SystemExit(f"专项校验失败，缺少学科评价边界：{path}")
    if value(text, "review_required") != str(expected_review).lower():
        raise SystemExit(f"专项校验失败，review_required 不符合预期：{path}")


def preflight(subject: str, config: SubjectConfig, cards: list[Path]) -> None:
    for path in cards:
        text = path.read_text(encoding="utf-8")
        if value(text, "status") != "draft":
            raise SystemExit(f"拒绝修改非草稿知识卡：{path}")
        title = title_of(text, path)
        topic = value(text, "topic")
        if topic not in config.topic_cues:
            raise SystemExit(f"未定义{subject}主题评价方式：{topic}（{path}）")
        assessment(subject, topic, title)
        markers = (
            "matching_keywords:" in text,
            "assessment_mode:" in text,
            "## 学科评价边界" in text,
        )
        if any(markers) and not all(markers):
            raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{path}")
        if all(markers):
            validate_card(subject, path, text)
        else:
            if "## 追踪说明\n" not in text:
                raise SystemExit(f"缺少追踪说明段落：{path}")
            if not re.search(r"^review_required:\s*(?:true|false)$", text, re.MULTILINE):
                raise SystemExit(f"缺少有效 review_required 字段：{path}")
            if not re.search(r"^updated:\s*.+$", text, re.MULTILINE):
                raise SystemExit(f"缺少 updated 字段：{path}")


def enrich(subject: str, config: SubjectConfig, cards: list[Path]) -> tuple[int, Counter[str]]:
    changed = 0
    modes: Counter[str] = Counter()
    for path in cards:
        text = path.read_text(encoding="utf-8")
        title = title_of(text, path)
        topic = value(text, "topic")
        mode, review_required = assessment(subject, topic, title)
        modes[mode] += 1
        if "matching_keywords:" in text:
            continue

        keywords = matching_keywords(title, topic, config.topic_cues[topic])
        keyword_block = "matching_keywords:\n" + "".join(f"  - {item}\n" for item in keywords)
        metadata_block = f"{keyword_block}assessment_mode: {mode}\n"
        text = text.replace(
            "mastery_granularity: knowledge_point\n",
            f"mastery_granularity: knowledge_point\n{metadata_block}",
            1,
        )
        boundary_block = (
            "## 学科评价边界\n\n"
            "> [!important] 证据使用边界\n"
            f"> {BOUNDARIES[mode]}\n\n"
        )
        text = text.replace("## 追踪说明\n", f"{boundary_block}## 追踪说明\n", 1)
        text = re.sub(
            r"^review_required:\s*(?:true|false)$",
            f"review_required: {str(review_required).lower()}",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        text = re.sub(r"^updated:\s*.+$", f"updated: {UPDATED_DATE}", text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        changed += 1
    return changed, modes


def validate(subject: str, cards: list[Path]) -> None:
    for path in cards:
        text = path.read_text(encoding="utf-8")
        validate_card(subject, path, text)


def main() -> None:
    batches = {subject: collect_cards(subject, config) for subject, config in SUBJECTS.items()}
    for subject, config in SUBJECTS.items():
        preflight(subject, config, batches[subject])

    for subject, config in SUBJECTS.items():
        cards = batches[subject]
        changed, modes = enrich(subject, config, cards)
        validate(subject, cards)
        mode_summary = "，".join(f"{mode}={count}" for mode, count in sorted(modes.items()))
        print(f"{subject}：本次补充 {changed} 张，共校验 {len(cards)} 张；{mode_summary}")


if __name__ == "__main__":
    main()
