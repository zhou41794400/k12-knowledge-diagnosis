from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .reporting import load_jsonl


def now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_system_overview() -> str:
    return """---
title: 系统说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {date}
---

# 系统说明

## 软件名称

K12 教育知识点掌握程度跟踪系统

## 软件用途

用于家庭场景下的知识点掌握追踪、错题分析、短板识别、证据留痕和结果回写。

## 运行方式

- 本地优先
- 支持手动录题
- 支持照片导入的本地骨架
- 支持结果视图本地生成

## 主要能力

1. 建立课标知识体系。
2. 对题目进行知识点映射。
3. 生成证据事件和掌握状态。
4. 生成家长端和学生端结果页。
5. 留存审计日志，便于复盘与软著申报。
""".format(date=now_date())


def build_user_manual() -> str:
    return """---
title: 用户操作手册
tags:
  - project/k12-tracking
  - copyright/materials
updated: {date}
---

# 用户操作手册

## 家长使用步骤

1. 录入试卷照片或手动题目。
2. 运行本地分析链路。
3. 查看结果视图中的短板和最近题目。
4. 根据复核标记补充答案或修正题目。

## 学生使用步骤

1. 打开学生周报。
2. 查看当前掌握情况和短板清单。
3. 按系统建议优先复习薄弱知识点。

## 本地命令

- `python3 -m edu_tracker manual ...`
- `python3 -m edu_tracker photo ...`
- `python3 -m edu_tracker report`
- `python3 -m edu_tracker materials`

## 注意事项

- 图片导入当前支持旁路文本验证，正式 OCR 仍需后续接入。
- 页面展示尽可能使用中文。
""".format(date=now_date())


def build_installation_guide() -> str:
    return """---
title: 安装部署说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {date}
---

# 安装部署说明

## 环境要求

- macOS 本地环境
- Python 3.9+
- Obsidian Vault 可写权限

## 项目路径

- 仓库根目录：`/Users/mac/Documents/教育智能体`
- Obsidian 目录：`/Users/mac/Documents/教育智能体/教育智能体`

## 运行方式

```bash
python3 -m edu_tracker manual --student-id s001 --subject 数学 --grade 二年级 --text "乘法口诀练习题" --answer "6" --student-answer "6"
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 二年级 --image-path /path/to/paper.jpg --ocr-text "乘法口诀练习题" --answer "6" --student-answer "6"
python3 -m edu_tracker report
python3 -m edu_tracker materials
```

## 输出目录

- `教育智能体/logs/`
- `教育智能体/05-结果视图/`
- `教育智能体/09-软著材料/生成稿/`
""".format(date=now_date())


def build_version_note(questions: List[dict], mastery_rows: List[dict], ingest_rows: List[dict]) -> str:
    subject_counter = Counter(row.get("subject", "未知") for row in questions)
    return """---
title: 版本说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {date}
---

# 版本说明

## 当前版本特征

- 已打通手动录题最小闭环。
- 已打通照片导入本地骨架。
- 已具备家长端总览和学生周报生成器。

## 数据规模

- 题目记录数：{question_count}
- 掌握状态记录数：{mastery_count}
- 导入记录数：{ingest_count}

## 学科分布

{subject_lines}

## 版本说明

- 当前版本重点放在本地可执行、中文可读、日志完整。
- 后续版本将继续完善真实 OCR、LLM 分析和更多学科策略。
""".format(
        date=now_date(),
        question_count=len(questions),
        mastery_count=len(mastery_rows),
        ingest_count=len(ingest_rows),
        subject_lines="\n".join(f"- {subject}：{count}" for subject, count in subject_counter.most_common()) or "- 暂无数据",
    )


def build_log_index(log_dir: Path) -> str:
    files = sorted(p.name for p in log_dir.glob("*.jsonl"))
    lines = [
        "---",
        "title: 日志索引",
        "tags:",
        "  - project/k12-tracking",
        "  - copyright/materials",
        f"updated: {now_date()}",
        "---",
        "",
        "# 日志索引",
        "",
        "## 当前日志文件",
        "",
    ]
    if files:
        for name in files:
            lines.append(f"- `{name}`")
    else:
        lines.append("- 暂无日志文件。")
    return "\n".join(lines) + "\n"


def generate_materials(project_root: Path) -> List[Path]:
    vault_root = project_root / "教育智能体"
    output_dir = vault_root / "09-软著材料" / "生成稿"
    output_dir.mkdir(parents=True, exist_ok=True)

    log_dir = vault_root / "logs"
    questions = load_jsonl(log_dir / "questions.jsonl")
    mastery_rows = load_jsonl(log_dir / "mastery.jsonl")
    ingest_rows = load_jsonl(log_dir / "ingest.jsonl")

    outputs = {
        "系统说明.md": build_system_overview(),
        "用户操作手册.md": build_user_manual(),
        "安装部署说明.md": build_installation_guide(),
        "版本说明.md": build_version_note(questions, mastery_rows, ingest_rows),
        "日志索引.md": build_log_index(log_dir),
    }

    written: List[Path] = []
    for filename, content in outputs.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
    return written
