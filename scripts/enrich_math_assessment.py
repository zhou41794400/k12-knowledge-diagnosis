from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_ROOT = ROOT / "教育智能体" / "02-课标与知识体系" / "02-国家课标知识树" / "数学"
EXPECTED_CARDS = 103

MODES = {
    "NS": "calculation_rule",
    "PRE": "calculation_rule",
    "GG": "reasoning_mixed",
    "GEO": "reasoning_mixed",
    "FNC": "reasoning_mixed",
    "STP": "data_reasoning_mixed",
    "PRS": "data_reasoning_mixed",
    "PRA": "modeling_rubric",
    "MOD": "modeling_rubric",
}

BOUNDARIES = {
    "calculation_rule": "计算结果、步骤和概念辨析可形成结构化证据；开放解释、方法比较和真实建模不能只按最终答案判定。",
    "reasoning_mixed": "基础识图与结论判断可形成规则证据；推理、证明、参数讨论和多步综合必须按过程分层评价。",
    "data_reasoning_mixed": "读图、计算和明确概率结论可形成规则证据；抽样合理性、统计解释和决策建议必须保留推断过程。",
    "modeling_rubric": "按问题理解、变量假设、模型建立、求解检验和结果解释等维度评价，由人工确认后形成证据。",
}


def value(text: str, key: str) -> str:
    match = re.search(rf"^{key}:\s*(.+)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def main() -> None:
    cards = []
    for path in KNOWLEDGE_ROOT.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        if value(text, "mastery_granularity") == "knowledge_point":
            cards.append(path)
    if len(cards) != EXPECTED_CARDS:
        raise SystemExit(f"预期 {EXPECTED_CARDS} 张数学知识卡，实际 {len(cards)} 张")

    changed = 0
    for path in cards:
        text = path.read_text(encoding="utf-8")
        status = value(text, "status")
        if status not in {"draft", "published"}:
            raise SystemExit(f"不支持的知识卡状态：{path}={status}")
        topic_code = value(text, "topic_code")
        mode = MODES.get(topic_code)
        if not mode:
            raise SystemExit(f"未定义数学主题评价方式：{path}={topic_code}")
        has_mode = "assessment_mode:" in text
        has_boundary = "## 学科评价边界" in text
        if has_mode and has_boundary:
            continue
        if has_mode or has_boundary:
            raise SystemExit(f"知识卡仅完成部分补充，请人工检查：{path}")
        text = text.replace(
            "mastery_granularity: knowledge_point\n",
            f"mastery_granularity: knowledge_point\nassessment_mode: {mode}\n",
            1,
        )
        boundary = f"## 学科评价边界\n\n> [!important] 证据使用边界\n> {BOUNDARIES[mode]}\n\n"
        if "## 追踪说明\n" not in text:
            raise SystemExit(f"缺少追踪说明段落：{path}")
        text = text.replace("## 追踪说明\n", f"{boundary}## 追踪说明\n", 1)
        if mode == "modeling_rubric":
            text = re.sub(r"^review_required:\s*false$", "review_required: true", text, count=1, flags=re.MULTILINE)
        text = re.sub(r"^updated:\s*.+$", "updated: 2026-07-13", text, count=1, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")
        changed += 1
    print(f"本次补充 {changed} 张；数学目标知识卡共 {len(cards)} 张")


if __name__ == "__main__":
    main()
