from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = PROJECT_ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树"
REPORT_PATH = PROJECT_ROOT / "教育智能体" / "02-课标与知识体系" / "00-总览" / "全学科内容覆盖与质量审计.md"
GRADE_ORDER = ("一年级", "二年级", "三年级", "四年级", "五年级", "六年级", "七年级", "八年级", "九年级", "高一", "高二", "高三")
REQUIRED_SECTIONS = ("定义", "适用范围", "前置知识", "关键能力表现", "证据规则", "追踪说明", "课标依据")


def read_frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, object] = {}
    current_list = ""
    for line in lines[1:]:
        if line.strip() == "---":
            break
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and current_list:
            values = metadata.setdefault(current_list, [])
            if isinstance(values, list):
                values.append(item.group(1).strip().strip('"').strip("'"))
            continue
        field = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if not field:
            current_list = ""
            continue
        key, value = field.group(1), field.group(2).strip()
        if not value or value == "[]":
            metadata[key] = []
            current_list = key if not value else ""
        else:
            metadata[key] = value.strip('"').strip("'")
            current_list = ""
    return metadata


def audit() -> tuple[list[dict[str, object]], list[str]]:
    cards: list[dict[str, object]] = []
    issues: list[str] = []
    for path in sorted(KNOWLEDGE_ROOT.rglob("*.md")):
        metadata = read_frontmatter(path)
        if metadata.get("mastery_granularity") != "knowledge_point":
            continue
        body = path.read_text(encoding="utf-8")
        keywords = metadata.get("matching_keywords", [])
        if not isinstance(keywords, list):
            keywords = [keywords] if keywords else []
        missing_sections = [section for section in REQUIRED_SECTIONS if f"## {section}" not in body]
        card = {
            "path": path,
            "subject": str(metadata.get("subject", "未标注")),
            "grade": str(metadata.get("grade", "未标注")),
            "status": str(metadata.get("status", "draft")),
            "point_code": str(metadata.get("point_code", "")),
            "keywords": keywords,
            "assessment_mode": str(metadata.get("assessment_mode", "")),
            "has_assessment_boundary": "## 学科评价边界" in body,
            "review_required": str(metadata.get("review_required", "false")).lower() == "true",
            "missing_sections": missing_sections,
        }
        cards.append(card)
        if not card["point_code"]:
            issues.append(f"缺少 point_code：`{path.relative_to(PROJECT_ROOT)}`")
        if missing_sections:
            issues.append(f"缺少正文段落（{'、'.join(missing_sections)}）：`{path.relative_to(PROJECT_ROOT)}`")
    return cards, issues


def render(cards: list[dict[str, object]], issues: list[str]) -> str:
    by_subject: dict[str, Counter[str]] = defaultdict(Counter)
    statuses = Counter(str(card["status"]) for card in cards)
    insufficient_keywords = Counter()
    without_assessment_mode = Counter()
    without_assessment_boundary = Counter()
    review_required = Counter()
    for card in cards:
        subject = str(card["subject"])
        by_subject[subject][str(card["grade"])] += 1
        if len(card["keywords"]) < 3:
            insufficient_keywords[subject] += 1
        if not card["assessment_mode"]:
            without_assessment_mode[subject] += 1
        if not card["has_assessment_boundary"]:
            without_assessment_boundary[subject] += 1
        if card["review_required"]:
            review_required[subject] += 1

    lines = [
        "---",
        "title: 全学科内容覆盖与质量审计",
        "tags:",
        "  - project/k12-tracking",
        "  - knowledge-system/audit",
        "status: active",
        "updated: 2026-07-13",
        "---",
        "",
        "# 全学科内容覆盖与质量审计",
        "",
        "> [!info] 统计口径",
        "> 仅统计 `mastery_granularity: knowledge_point` 的知识卡；主题导航页、INDEX 和总览页不计入知识点。运行 `make knowledge-audit` 可重新生成本页。",
        "",
        "## 当前总量",
        "",
        f"- 可追踪知识卡：**{len(cards)}** 张",
        f"- 草稿：**{statuses.get('draft', 0)}** 张",
        f"- 已发布：**{statuses.get('published', 0)}** 张",
        f"- 其他状态：**{len(cards) - statuses.get('draft', 0) - statuses.get('published', 0)}** 张",
        f"- 题目匹配关键词少于 3 个：**{sum(insufficient_keywords.values())}** 张",
        f"- 缺少学科评价方式：**{sum(without_assessment_mode.values())}** 张",
        f"- 缺少学科评价边界：**{sum(without_assessment_boundary.values())}** 张",
        f"- 结构问题：**{len(issues)}** 项",
        "",
        "## 学科与年级覆盖",
        "",
        "| 学科 | 知识卡 | 已覆盖年级 | 关键词不足 3 个 | 缺评价方式 | 缺评价边界 | 强制复核 |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for subject in sorted(by_subject):
        counts = by_subject[subject]
        grades = "、".join(f"{grade}（{counts[grade]}）" for grade in GRADE_ORDER if counts.get(grade))
        lines.append(
            f"| {subject} | {sum(counts.values())} | {grades} | {insufficient_keywords[subject]} | "
            f"{without_assessment_mode[subject]} | {without_assessment_boundary[subject]} | {review_required[subject]} |"
        )

    lines.extend([
        "",
        "## 发布边界",
        "",
        "> [!warning] 不等于全部可用",
        "> 目录存在或知识卡已写入，不代表已通过课标逐条校核、题目映射验收和真实试卷验证。当前只有 [[小学二至三年级数学发布清单]] 中的 9 张数学卡允许进入运行时。",
        "",
        "## 待完善批次",
        "",
        "1. 数学：逐卡校核 2022 版课标依据与冀教版适配内容，按年级建设计算、推理、数据和建模验收题。",
        "2. 语文与英语：逐卡校核课标依据，分别建设客观任务、阅读混合任务和表现性任务验收集。",
        "3. 理化生、史地政法：逐卡校核课标依据，建设计算实验、概念解释、材料分析和论证评价验收集。",
        "4. 科学、信息科技、体育与健康、艺术、劳动：逐卡校核课标依据，建设过程性、操作性、作品性和表现性任务验收集。",
        "5. 所有学科完成真实题盲测、人工复核与版本留痕后，再按批次将知识卡从 `draft` 改为 `published`。",
        "",
        "## 结构问题",
        "",
    ])
    if issues:
        lines.extend(f"- {issue}" for issue in issues)
    else:
        lines.append("- 未发现缺少核心正文段落或知识点编码的问题。")
    lines.extend(["", "## 关联入口", "", "- [[课标与知识体系总览]]", "- [[知识点卡片模板]]", "- [[下一批知识点建设清单]]", "- [[项目首页]]", ""])
    return "\n".join(lines)


def main() -> None:
    cards, issues = audit()
    REPORT_PATH.write_text(render(cards, issues), encoding="utf-8")
    print(f"已生成：{REPORT_PATH}")
    print(f"知识卡={len(cards)}，结构问题={len(issues)}")


if __name__ == "__main__":
    main()
