from __future__ import annotations

import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树"
SUBJECT_ROOTS = {
    "科学": KNOWLEDGE_ROOT / "科学",
    "信息科技": KNOWLEDGE_ROOT / "信息科技",
}
EXPECTED_CARDS = {"科学": 38, "信息科技": 51}
EXPECTED_MODES = {
    "科学": Counter(
        {
            "concept_observation": 14,
            "experimental_inquiry": 16,
            "evidence_explanation": 8,
        }
    ),
    "信息科技": Counter(
        {
            "knowledge_rule": 18,
            "operation_task": 25,
            "project_artifact": 8,
        }
    ),
}

SCIENCE_EXPERIMENT_TITLES = {
    "比较与测量",
    "材料与性能",
    "磁铁",
    "植物的生长",
    "设计与制作",
    "物质的三种状态",
    "简单工具的使用",
    "声音的产生与传播",
    "电路基本元件",
    "简单机械设计",
    "光与影子",
    "热传递",
    "简易机械装置",
    "物质的变化",
    "能量转换",
    "工程设计综合",
}
SCIENCE_EXPLANATION_TITLES = {
    "太阳的位置与方向",
    "天气与季节",
    "生物多样性与栖息地",
    "地球的公转与自转",
    "生物的生长与繁殖",
    "太阳系与宇宙探索",
    "生态系统",
    "人体系统的协同",
}

TECHNOLOGY_OPERATION_TITLES = {
    "鼠标操作",
    "信息获取与表达",
    "顺序与步骤",
    "计算机基本操作",
    "文件与文件夹管理",
    "顺序结构初步",
    "文字处理基础",
    "表格初步认识",
    "数据的收集与整理",
    "浏览器基本使用",
    "循环结构初步",
    "分支结构初步",
    "数据的可视化",
    "多条件分支",
    "变量与数据存储",
    "数据处理与分析",
    "函数与模块化",
    "文档与表格高级应用",
    "互联网与信息获取",
    "Python入门",
    "函数与模块化编程",
    "Python程序设计",
    "算法设计与效率",
}

TOPIC_CUES = {
    ("科学", "物质科学"): "物质现象与规律",
    ("科学", "生命科学"): "生命现象与结构",
    ("科学", "地球与宇宙"): "地球宇宙观察",
    ("科学", "技术与工程"): "工程设计与验证",
    ("信息科技", "计算机基础"): "计算机基础知识",
    ("信息科技", "数据与信息"): "数据与信息处理",
    ("信息科技", "信息处理"): "数字工具与信息处理",
    ("信息科技", "网络与安全"): "网络安全与数字责任",
    ("信息科技", "算法与编程"): "算法与编程实践",
    ("信息科技", "数字创作"): "数字作品设计与创作",
    ("信息科技", "人工智能初步"): "人工智能基础与责任",
    ("信息科技", "人工智能"): "人工智能原理与应用",
    ("信息科技", "数据与计算"): "数据计算与程序设计",
    ("信息科技", "信息系统"): "信息系统与安全",
    ("信息科技", "算法与程序设计"): "算法设计与程序实现",
}
MODE_CUES = {
    "concept_observation": "概念辨识与观察记录",
    "experimental_inquiry": "实验探究与过程证据",
    "evidence_explanation": "证据分析与科学解释",
    "knowledge_rule": "知识规则与概念判断",
    "operation_task": "操作过程与任务结果",
    "project_artifact": "项目过程与作品量规",
}
BOUNDARIES = {
    "concept_observation": (
        "概念辨识、特征比较和连续观察记录可形成结构化证据；仅凭一次观察或单道选择题，"
        "不得直接认定学生已能在新情境中稳定运用概念。"
    ),
    "experimental_inquiry": (
        "实验探究须核对问题提出、变量控制、操作过程、数据记录、结论和安全规范；"
        "自动检查只能辅助判断，必须经人工复核后才能更新掌握证据。"
    ),
    "evidence_explanation": (
        "可结构化核对证据是否相关、结论是否有依据；涉及因果链、模型选择或多种合理解释时，"
        "应按证据质量评价，不能只按结论关键词判定。"
    ),
    "knowledge_rule": (
        "术语、规则、结构和安全规范等边界明确的任务可形成结构化证据；"
        "涉及真实情境取舍、数字伦理或综合方案判断时，应保留人工复核。"
    ),
    "operation_task": (
        "操作任务须同时核对步骤、工具使用、过程记录和结果有效性；"
        "仅凭最终文件或单次自动判定不能确认掌握，必须由人工复核。"
    ),
    "project_artifact": (
        "项目作品应按需求理解、方案设计、实现过程、功能效果、表达规范和迭代反思等维度评价；"
        "必须由人工依据量规复核，不得用单一总分替代知识点证据。"
    ),
}
REVIEW_REQUIRED_MODES = {"experimental_inquiry", "operation_task", "project_artifact"}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def mode_for(subject: str, title: str, topic: str) -> str:
    if subject == "科学":
        if title in SCIENCE_EXPERIMENT_TITLES:
            return "experimental_inquiry"
        if title in SCIENCE_EXPLANATION_TITLES:
            return "evidence_explanation"
        return "concept_observation"
    if topic == "数字创作" or "项目" in title:
        return "project_artifact"
    if title in TECHNOLOGY_OPERATION_TITLES:
        return "operation_task"
    return "knowledge_rule"


def keywords(subject: str, title: str, topic: str, mode: str) -> list[str]:
    parts = re.split(
        r"(?:与|和|及|、|的|基本|基础|初步|简单|综合|高级|进阶|认识|实践|设计|制作|应用|使用)",
        title,
    )
    candidates = [title]
    candidates.extend(part.strip() for part in parts if len(part.strip()) >= 2)
    try:
        candidates.extend((TOPIC_CUES[(subject, topic)], MODE_CUES[mode]))
    except KeyError as exc:
        raise ValueError(f"未定义主题关键词：{subject}/{topic}") from exc
    unique: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    if len(unique) < 3:
        raise ValueError(f"关键词不足 3 个：{subject}/{title}")
    return unique[:4]


def existing_keyword_count(text: str) -> int:
    match = re.search(r"^matching_keywords:\n((?:  - .+\n)+)", text, re.MULTILINE)
    return len(re.findall(r"^  - .+$", match.group(1), re.MULTILINE)) if match else 0


def enriched_text(text: str, subject: str, title: str, topic: str, mode: str, path: Path) -> str:
    keyword_block = "matching_keywords:\n" + "".join(
        f"  - {item}\n" for item in keywords(subject, title, topic, mode)
    )
    metadata_anchor = "mastery_granularity: knowledge_point\n"
    if text.count(metadata_anchor) != 1:
        raise ValueError(f"知识粒度锚点异常：{path}")
    text = text.replace(
        metadata_anchor,
        f"{metadata_anchor}{keyword_block}assessment_mode: {mode}\n",
        1,
    )

    boundary_anchor = "## 追踪说明\n"
    if text.count(boundary_anchor) != 1:
        raise ValueError(f"追踪说明锚点异常：{path}")
    boundary_block = (
        "## 学科评价边界\n\n"
        "> [!important] 证据使用边界\n"
        f"> {BOUNDARIES[mode]}\n\n"
    )
    text = text.replace(boundary_anchor, f"{boundary_block}{boundary_anchor}", 1)

    if mode in REVIEW_REQUIRED_MODES:
        text, replacements = re.subn(
            r"^review_required:\s*false$",
            "review_required: true",
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if replacements != 1:
            raise ValueError(f"无法启用人工复核：{path}")
    text, replacements = re.subn(
        r"^updated:\s*.+$",
        "updated: 2026-07-13",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise ValueError(f"缺少更新时间：{path}")
    return text


def main() -> None:
    plans: list[tuple[Path, str]] = []
    mode_counts: dict[str, Counter[str]] = {}

    for subject, subject_root in SUBJECT_ROOTS.items():
        cards = []
        for path in sorted(subject_root.rglob("*.md")):
            text = path.read_text(encoding="utf-8")
            if value(text, "mastery_granularity") == "knowledge_point":
                cards.append((path, text))
        if len(cards) != EXPECTED_CARDS[subject]:
            raise SystemExit(
                f"预期 {EXPECTED_CARDS[subject]} 张{subject}知识卡，实际 {len(cards)} 张"
            )

        subject_modes: Counter[str] = Counter()
        subject_plans: list[tuple[Path, str]] = []
        for path, text in cards:
            if value(text, "status") != "draft":
                raise SystemExit(f"拒绝修改非草稿知识卡：{path}")
            title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
            if not title_match:
                raise SystemExit(f"缺少正文标题：{path}")
            title = title_match.group(1).strip()
            topic = value(text, "topic")
            mode = mode_for(subject, title, topic)
            keywords(subject, title, topic, mode)
            subject_modes[mode] += 1

            markers = (
                bool(re.search(r"^matching_keywords:$", text, re.MULTILINE)),
                bool(re.search(r"^assessment_mode:\s*.+$", text, re.MULTILINE)),
                "## 学科评价边界" in text,
            )
            if any(markers) and not all(markers):
                raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{path}")
            if all(markers):
                if value(text, "assessment_mode") != mode:
                    raise SystemExit(f"评价分类与规则不一致：{path}")
                if existing_keyword_count(text) < 3:
                    raise SystemExit(f"matching_keywords 少于 3 个：{path}")
                if mode in REVIEW_REQUIRED_MODES and value(text, "review_required") != "true":
                    raise SystemExit(f"强制人工复核未启用：{path}")
                continue
            try:
                new_text = enriched_text(text, subject, title, topic, mode, path)
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc
            subject_plans.append((path, new_text))

        if subject_modes != EXPECTED_MODES[subject]:
            raise SystemExit(
                f"{subject}分类数量异常：预期 {dict(EXPECTED_MODES[subject])}，"
                f"实际 {dict(subject_modes)}"
            )
        mode_counts[subject] = subject_modes
        plans.extend(subject_plans)

    for path, text in plans:
        path.write_text(text, encoding="utf-8")

    for subject in SUBJECT_ROOTS:
        changed = sum(1 for path, _ in plans if SUBJECT_ROOTS[subject] in path.parents)
        print(
            f"{subject}：本次补充 {changed} 张，共 {EXPECTED_CARDS[subject]} 张；"
            f"分类 {dict(mode_counts[subject])}"
        )


if __name__ == "__main__":
    main()
