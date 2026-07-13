from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import List, Optional

from .knowledge_registry import knowledge_stats
from .reporting import load_jsonl


def now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def project_version(project_root: Path) -> str:
    text = (project_root / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'(?m)^version\s*=\s*"([^"]+)"', text)
    return match.group(1) if match else "未标记"


def build_system_overview(code_dir: Path, version: str) -> str:
    # Gather module stats
    modules = []
    for f in sorted(code_dir.rglob("*.py")):
        if "__pycache__" in str(f):
            continue
        lines = len(f.read_text().splitlines())
        modules.append((f.relative_to(code_dir.parent), lines))
    total_lines = sum(m[1] for m in modules)

    module_table = "\n".join(
        f"| `{m[0]}` | {m[1]} |" for m in modules
    )

    return f"""---
title: 系统说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {now_date()}
---

# 系统说明

## 一、软件名称

启智知踪 K12 智能学习诊断系统

- 当前原型版本：`{version}`
- 当前追踪模型：`rule-v2` 规则掌握度模型

## 二、软件用途

本系统面向家庭场景，由家长主导，帮助家长和学生追踪各学科知识点的掌握情况。核心解决三大痛点：

1. **信息黑箱**：家长不清楚孩子到底哪些知识点掌握了、哪些薄弱。
2. **时间匮乏**：家长没有精力系统梳理 K12 知识体系和逐题诊断。
3. **数据碎片**：试卷、作业分布在纸质和不同 App 中，无法跨平台整合分析。

## 三、目标用户

- **主要用户**：K12 阶段学生的家长（尤其是小学、初中阶段）
- **次要用户**：学生本人（查看掌握进度和复盘建议）
- **适用角色**：家庭场景，非学校/SaaS 规模化部署

## 四、系统架构

本系统当前版本采用 **本地优先（Local-First）** 架构，录题、规则匹配、报告生成和数据存储均在用户本地 macOS 环境中完成，默认不调用外部云服务。

```
┌─────────────────────────────────────────────────┐
│                 用户交互层                        │
│  ┌─────────────┐  ┌──────────────┐              │
│  │ CLI 命令行   │  │ Obsidian     │              │
│  │ (录题/生成)  │  │ (查看结果)   │              │
│  └──────┬──────┘  └──────┬───────┘              │
└─────────┼────────────────┼──────────────────────┘
          │                │
┌─────────▼────────────────▼──────────────────────┐
│                 业务逻辑层                        │
│  ┌──────────────┐  ┌─────────────┐               │
│  │ pipeline.py  │  │ reporting.py│               │
│  │ (录入→映射→  │  │ (结果视图    │               │
│  │  掌握更新)   │  │  与周报生成) │               │
│  └──────┬───────┘  └──────┬──────┘               │
│  ┌──────▼───────┐  ┌──────▼──────┐               │
│  │models.py     │  │ materials.py│               │
│  │(数据模型)    │  │(软著材料)   │               │
│  └──────────────┘  └─────────────┘               │
│  ┌──────────────┐                                 │
│  │ knowledge_   │                                 │
│  │ registry.py  │                                 │
│  │ (知识点注册)  │                                 │
│  └──────────────┘                                 │
└──────────────────┬────────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────────┐
│                 数据存储层                          │
│  ┌───────────┐ ┌──────────┐ ┌──────────┐          │
│  │ questions │ │ mastery  │ │ evidence │          │
│  │ .jsonl    │ │ .jsonl   │ │ .jsonl   │          │
│  └───────────┘ └──────────┘ └──────────┘          │
│  ┌──────────────┐ ┌─────────────┐                 │
│  │ ingest.jsonl │ │ audit.jsonl │                 │
│  └──────────────┘ └─────────────┘                 │
└───────────────────────────────────────────────────┘
```

## 五、模块说明

| 模块 | 行数 | 职责 |
| :--- | :---: | :--- |
{module_table}

### 5.1 核心分析管线（pipeline.py）

`pipeline.py` 是系统的核心处理引擎，负责：

- **录入接收**：接收手动输入或照片导入的题目数据。
- **知识点映射**：将题目文本与课标知识库进行匹配，确定所属学科、年级、知识点。
- **对错分流**：根据学生答案与标准答案比对，判断正确/错误，生成两套不同的处理逻辑：
  - **正确题**：增加掌握置信度，降低该知识点的复习优先级。
  - **错题**：唯一且可信的知识点映射会生成负向证据；未匹配、歧义或答案不足时进入人工复核，不更新掌握度。
- **掌握度更新**：基于正确/错误历史和证据强度，通过可解释的规则模型更新知识点掌握状态。
- **审计留痕**：每次操作生成审计事件，写入 `audit.jsonl`。

### 5.2 结果视图生成（reporting.py）

`reporting.py` 负责将追踪数据转化为可视化的 Markdown 报告页面：

- **家长端总览**：聚合展示各学科掌握概况、短板列表、最近题目、待复核项。
- **学生周报**：面向学生的每周摘要页，展示当前掌握度变化、推荐复习的知识点。
- **题目详情页**：每题一条记录，展示原题内容、学生答案、标准答案、映射知识点。

### 5.3 数据模型（models.py）

定义系统核心领域对象：

- **KnowledgePoint**：知识点实体，包含学科、年级、主题、掌握度、更新时间等字段。
- **QuestionRecord**：题目记录，包含题目文本、答案、学生答案、映射知识点 ID、题目类型等。
- **EvidenceEvent**：证据事件，记录每次掌握度变化的来源（题目/手动修正）。
- **MasteryState**：掌握状态快照，记录每个知识点在某一时刻的掌握概率。
- **AuditEvent**：审计日志，记录每次关键操作的原始内容。

### 5.4 知识点注册（knowledge_registry.py）

从 Obsidian frontmatter 动态加载知识点并执行候选匹配：

- 自动过滤学科、年级和发布状态。
- 未匹配或存在歧义时进入人工复核，不强制写入掌握度。
- 当前试点采用 `RULE`，尚未实现四参数 BKT。

### 5.5 CLI 入口（cli.py）

命令行接口，支持子命令：

| 子命令 | 功能 |
| :--- | :--- |
| `manual` | 手动录题 |
| `photo` | 照片导入并处理 |
| `report` | 生成结果视图 |
| `materials` | 生成软著申报材料 |
| `validate` | 运行数学映射研发验收题集 |

### 5.6 软著材料生成（materials.py）

自动化生成软著申报所需的文档材料，包括：

- 系统说明
- 用户操作手册
- 安装部署说明
- 版本说明
- 日志索引
- 源代码首末页提取

## 六、技术栈

| 类别 | 选择 | 说明 |
| :--- | :--- | :--- |
| 语言 | Python 3.9+ | 跨平台，生态丰富 |
| 命令行 | argparse | Python 标准库 |
| 数据存储 | SQLite + JSONL | SQLite 保存当前业务状态，JSONL 保留追加式审计与兼容输出 |
| 文档输出 | Markdown | 易于阅读和版本管理 |
| 知识库 | Obsidian Vault | 支持双向链接与图谱 |
| 构建工具 | Makefile | 一键执行常见任务 |

## 七、数据流

### 手动录题流程

```
用户输入题目 → CLI 解析 → pipeline.manual_ingest()
  → 知识点映射 → 对错分流
  ├─ 正确题 → 增加掌握置信度
  └─ 错题   → 唯一可信映射时生成负向证据；否则进入复核
  → 写入 questions.jsonl
  → 写入 mastery.jsonl
  → 写入 evidence.jsonl
  → 写入 audit.jsonl
  → 完成
```

### 照片导入流程

```
用户提供照片+OCR文本 → CLI 解析 → pipeline.photo_ingest()
  → 旁路文本验证（当前阶段）→ 同上分流更新
  → 写入 ingest.jsonl + questions.jsonl
  → 同上掌握更新与日志
```

### 报告生成流程

```
用户执行 report → reporting.generate_views()
  → 读取所有 JSONL → 聚合分析
  → 生成家长端总览（05-结果视图/家长端总览.md）
  → 生成学生周报（05-结果视图/学生端-s*.md）
  → 生成题目详情（05-结果视图/题目详情/q_*.md）
```

## 八、安全与隐私

- **本地优先**：当前命令行版本的数据存储和分析在用户本地完成，默认不上传云端。
- **无内置遥测**：当前代码未实现用户行为上报或第三方统计 SDK。
- **审计可追溯**：所有数据变更通过 audit.jsonl 完整记录。

## 九、合规说明

- 符合《个人信息保护法》对未成年人信息保护的合规框架设计。
- 用户协议、隐私政策、监护人授权书等法律文档随项目提供。
"""


def build_user_manual() -> str:
    return f"""---
title: 用户操作手册
tags:
  - project/k12-tracking
  - copyright/materials
updated: {now_date()}
---

# 用户操作手册

## 一、安装环境

### 1.1 前置依赖

- macOS 操作系统（推荐 macOS 12+）
- Python 3.9 或更高版本
- Obsidian（用于查看结果视图和知识图谱，可选）

### 1.2 验证安装

```bash
python3 --version
# 应输出 Python 3.9.x 或更高

git --version
# 应输出 git 2.x 或更高
```

### 1.3 项目结构确认

```
教育智能体/
├── edu_tracker/          # Python 包
├── services/             # 核心服务
├── 教育智能体/            # Obsidian Vault
│   ├── 05-结果视图/       # 生成的结果视图
│   ├── 09-软著材料/       # 软著材料输出
│   └── logs/             # 日志文件
├── Makefile              # 一键任务
└── README.md             # 项目说明
```

## 二、家长使用指南

### 2.1 使用流程概览

```
录题 → 分析 → 查看结果 → 针对性辅导 → 再次录题 → 追踪进步
```

### 2.2 手动录题

手动录题是最基本的录入方式。家长将试卷或练习题中的题目内容、标准答案和学生答案通过命令行输入。

**命令模板：**

```bash
python3 -m edu_tracker manual \\
  --student-id s001 \\
  --subject <学科> \\
  --grade <年级> \\
  --text "<题目文字>" \\
  --answer "<标准答案>" \\
  --student-answer "<学生答案>"
```

**参数说明：**

| 参数 | 必填 | 说明 | 示例 |
| :--- | :---: | :--- | :--- |
| `--student-id` | 是 | 学生编号 | `s001` |
| `--subject` | 是 | 学科 | `数学`、`语文`、`英语` |
| `--grade` | 是 | 年级 | `二年级`、`三年级` |
| `--text` | 是 | 题目文字内容 | `"3 × 4 = ?"` |
| `--answer` | 是 | 标准答案 | `"12"` |
| `--student-answer` | 是 | 学生答案 | `"12"` 或 `"15"` |

**示例：录入一道乘法题**

```bash
python3 -m edu_tracker manual \\
  --student-id s001 \\
  --subject 数学 \\
  --grade 二年级 \\
  --text "3 × 4 = ?" \\
  --answer "12" \\
  --student-answer "12"
```

系统输出：
- 题目记录写入 `logs/questions.jsonl`
- 审计事件写入 `logs/audit.jsonl`
- 仅在命中已发布知识点且答案可判断时，掌握度与证据分别写入 `logs/mastery.jsonl`、`logs/evidence.jsonl`
- 未命中知识点时标记为待复核，不更新掌握度

### 2.3 照片导入

照片导入适用于已经完成的纸质试卷或练习册。系统使用本地 Tesseract 识别，首次识别只生成待确认记录，人工核对后才进入知识映射。

**命令模板：**

```bash
python3 -m edu_tracker photo \\
  --student-id s001 \\
  --subject <学科> \\
  --grade <年级> \\
  --image-path <图片路径> \\
  --ocr-text "<OCR 识别文本>" \\
  --answer "<标准答案>" \\
  --student-answer "<学生答案>"
```

**参数说明：**

| 参数 | 必填 | 说明 | 示例 |
| :--- | :---: | :--- | :--- |
| `--image-path` | 是 | 试卷照片文件路径 | `/path/to/paper.jpg` |
| `--ocr-text` | 确认时必填 | 人工核对或修正后的题目文本 | `"3 × 4 = ?"` |
| `--ingest-id` | 确认时必填 | 首次 OCR 返回的导入编号 | `i_xxx` |

**示例：**

```bash
python3 -m edu_tracker photo \\
  --student-id s001 \\
  --subject 数学 \\
  --grade 二年级 \\
  --image-path ./试卷/乘法练习1.jpg \\
  --ocr-text "3 × 4 = ?" \\
  --answer "12" \\
  --student-answer "12"
```

### 2.4 启动本地家长端

```bash
python3 -m edu_tracker web
```

浏览器打开 `http://127.0.0.1:8765`，可完成手动录题、图片上传、OCR 确认、复核处理、学生数据导出和删除。

### 2.5 生成结果视图

录完题目后，执行报告生成命令：

```bash
python3 -m edu_tracker report
```

系统将在 `05-结果视图/` 目录下生成：
- `家长端总览.md` — 学科掌握概况、短板列表、最近题目
- `学生端-s001.md` — 面向学生的周报
- `题目详情/q_xxxxxxxxxxxx.md` — 每道题的详细分析

### 2.6 查看分析结果

家长端总览包含：

1. **学科掌握度摘要**：按学科、知识主题展示平均掌握率。
2. **短板知识点**：掌握度低于阈值的知识点清单，按紧急程度排序。
3. **最近录入题目**：最近录入的题目列表，标注正确/错误状态。
4. **待复核项**：判定为「边缘正确」或「答案有歧义」的题目，需家长人工确认。

### 2.7 数据管理

- `python3 -m edu_tracker health`：查看数据库版本、复核和 outbox 状态。
- `python3 -m edu_tracker data-export --student-id s001`：导出学生数据。
- `python3 -m edu_tracker data-delete --student-id s001 --confirm s001`：二次确认后删除。
- `python3 -m edu_tracker backup`：创建完整备份。

### 2.8 生成软著材料

```bash
python3 -m edu_tracker materials
```

在 `09-软著材料/生成稿/` 目录下生成/更新：
- 系统说明
- 用户操作手册
- 安装部署说明
- 版本说明
- 日志索引
- 源代码页

## 三、学生使用指南

### 3.1 周报查看

学生通过 Obsidian 打开生成的 `05-结果视图/学生端-s001.md` 查看每周学习总结。

### 3.2 周报内容

1. **当前掌握结果**：展示已产生有效证据的知识点掌握状态。
2. **当前短板清单**：掌握度低于 60% 的知识点，按优先级排列。
3. **复习建议**：根据当前规则分数和最近题目生成复习优先级提示。
4. **原题回溯**：每个薄弱知识点可跳转到对应题目的详情页，查看原始题目内容。

## 四、常见问题

### 4.1 录题后没看到掌握变化？

首次录题时系统会建立初始掌握状态，可能需要 1-2 道题后才能看到趋势变化。建议连续录入 3-5 道同一知识点的题目以获得有意义的掌握度变化。

### 4.2 如何修改录错的题目？

自动映射未命中或出现歧义时，可在本地家长端复核区选择已发布知识点并确认对错。已生成的学生数据可先导出，再通过二次确认删除；不建议直接手改 JSONL。

### 4.3 支持哪些学科？

知识库已建立 15 个学科的课标骨架，但当前运行时仅发布小学二至三年级数学 9 个试点知识点。其他学科和尚未发布的数学知识卡不能作为自动诊断能力对外使用。

### 4.4 数据安全吗？

当前命令行版本默认在本地 macOS 中处理和保存数据，不调用外部云服务，也未内置遥测或第三方统计 SDK。用户仍应妥善保护本地目录、设备账号和备份文件，并按隐私政策处理未成年人信息。

## 五、注意事项

1. 照片导入已接入 Tesseract；首次识别只生成待确认记录，必须使用 `ingest_id` 确认或修正后再分析。
2. 命令参数中的空格和特殊字符建议用引号包裹。
3. 首次使用建议先通过手动录题熟悉流程，再尝试照片导入。
4. 建议每周至少录入 1-2 次题目以保持掌握度追踪的连续性。
"""


def build_installation_guide() -> str:
    return f"""---
title: 安装部署说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {now_date()}
---

# 安装部署说明

## 一、环境要求

### 1.1 操作系统

- macOS 12（Monterey）或更高版本
- 推荐 macOS 14+（Apple Silicon / arm64）
- 尚未测试 Windows/Linux 环境，后续版本考虑支持

### 1.2 运行时

| 依赖 | 最低版本 | 说明 |
| :--- | :---: | :--- |
| Python | 3.9 | 推荐 3.11+ |
| pip | 21+ | Python 包管理器 |
| Git | 2.x | 版本管理与发布 |
| Make | 3.x | 任务编排 |

### 1.3 可选依赖

| 依赖 | 用途 |
| :--- | :--- |
| Obsidian | 查看 Markdown 结果视图和知识图谱 |
| pandoc | 将 Markdown 导出为 PDF/Word 格式 |

## 二、项目路径说明

| 目录 | 路径 | 用途 |
| :--- | :--- | :--- |
| 项目根目录 | `/Users/mac/Documents/教育智能体` | 代码与配置 |
| Obsidian Vault | `/Users/mac/Documents/教育智能体/教育智能体` | 知识库与结果视图 |
| 日志目录 | `教育智能体/logs/` | JSONL 数据文件 |
| 结果视图 | `教育智能体/05-结果视图/` | 生成的报告 |

## 三、安装步骤

### 3.1 获取代码

```bash
cd /Users/mac/Documents/教育智能体
```

项目已完整包含代码和 Obsidian Vault，无需额外克隆。

### 3.2 验证运行环境

```bash
python3 --version
# 应输出 Python 3.9.x 或更高
```

### 3.3 运行验证

```bash
make check
# 执行：检查 Python 版本、目录完整性、日志文件、结果视图生成
```

## 四、运行方式

### 4.1 手动录题

```bash
python3 -m edu_tracker manual \\
  --student-id s001 \\
  --subject 数学 \\
  --grade 二年级 \\
  --text "乘法口诀练习题" \\
  --answer "6" \\
  --student-answer "6"
```

### 4.2 照片导入

```bash
python3 -m edu_tracker photo \\
  --student-id s001 \\
  --subject 数学 \\
  --grade 二年级 \\
  --image-path /path/to/paper.jpg \\
  --ocr-text "乘法口诀练习题" \\
  --answer "6" \\
  --student-answer "6"
```

### 4.3 生成结果视图

```bash
python3 -m edu_tracker report
```

### 4.4 生成软著材料

```bash
python3 -m edu_tracker materials
# 或
make materials
```

## 五、输出目录说明

| 输出 | 路径 | 格式 |
| :--- | :--- | :--- |
| 题目记录 | `logs/questions.jsonl` | JSONL |
| 掌握状态 | `logs/mastery.jsonl` | JSONL |
| 证据事件 | `logs/evidence.jsonl` | JSONL |
| 导入记录 | `logs/ingest.jsonl` | JSONL |
| 审计日志 | `logs/audit.jsonl` | JSONL |
| 家长端总览 | `05-结果视图/家长端总览.md` | Markdown |
| 学生周报 | `05-结果视图/学生端-s*.md` | Markdown |
| 题目详情 | `05-结果视图/题目详情/q_*.md` | Markdown |
| 系统说明 | `09-软著材料/生成稿/系统说明.md` | Markdown |
| 用户手册 | `09-软著材料/生成稿/用户操作手册.md` | Markdown |
| 安装说明 | `09-软著材料/生成稿/安装部署说明.md` | Markdown |
| 版本说明 | `09-软著材料/生成稿/版本说明.md` | Markdown |

## 六、一键任务（Makefile）

| 命令 | 功能 |
| :--- | :--- |
| `make check` | 运行完整性检查 |
| `make validate` | 运行数学映射研发验收题集 |
| `make report` | 生成结果视图 |
| `make materials` | 生成软著材料 |
| `make bundle` | 打包迁移包到 `dist/` |
| `make init-repo` | 初始化独立仓库 |
| `make release VERSION=x.y.z` | 生成发布说明 |
| `make tag VERSION=x.y.z` | 创建 Git 标签 |
| `make all` | 完整流程（check → report → materials） |
"""


def build_version_note(
    questions: List[dict],
    mastery_rows: List[dict],
    ingest_rows: List[dict],
    version: str,
    stats: dict[str, int],
    evidence_rows: Optional[List[dict]] = None,
) -> str:
    evidence_rows = evidence_rows or []
    current_evidence = [row for row in evidence_rows if row.get("model_version") == "rule-v2"]
    legacy_evidence = [row for row in evidence_rows if row.get("model_version") != "rule-v2"]
    current_evidence_ids = {row.get("event_id") for row in current_evidence if row.get("event_id")}
    current_mastery_rows = [row for row in mastery_rows if row.get("last_evidence_id") in current_evidence_ids]
    subject_counter = Counter(row.get("subject", "未知") for row in questions)
    subject_lines = "\n".join(f"- {subject}：{count} 条" for subject, count in subject_counter.most_common()) or "- 暂无数据"

    # Calculate grade distribution
    grade_counter = Counter(row.get("grade", "未知") for row in questions)
    grade_lines = "\n".join(f"- {grade}：{count} 条" for grade, count in grade_counter.most_common()) or "- 暂无数据"

    # Correct vs wrong stats
    correct = sum(1 for q in questions if q.get("is_correct") is True)
    wrong = sum(1 for q in questions if q.get("is_correct") is False)
    pending = sum(1 for q in questions if q.get("is_correct") is None)

    return f"""---
title: 版本说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {now_date()}
---

# 版本说明

## 一、当前版本

当前版本：v{version}（本地原型）

## 二、版本特征

### 2.1 已完成能力

- **手动录题闭环**：支持通过命令行手动录入题目，完成知识点映射、对错分流、掌握度更新。
- **照片导入骨架**：支持通过命令行传入照片路径和 OCR 文本，完成与手动录题相同的分析链路。
- **结果视图生成**：可生成家长端总览页、学生周报、题目详情页。
- **软著材料生成**：可自动生成系统说明、用户操作手册、安装说明、版本说明、日志索引。
- **审计日志**：所有关键操作写入 JSONL 日志，支持回溯。
- **知识体系骨架**：当前包含 {stats['point_nodes']} 个编码节点，其中 {stats['trackable_cards']} 张为可追踪知识点卡，{stats['published']} 张已发布到运行时匹配。
- **追踪模型**：当前使用 `rule-v2` 规则掌握度模型，尚未实现四参数 BKT。

### 2.2 后续计划

- 完善整卷切题、公式识别和手写体 OCR（当前已接入 Tesseract 印刷体 OCR）
- LLM 辅助知识点映射（当前基于规则匹配）
- 更多学科的双向链接和跨学科追踪
- 导出 PDF/Word 格式的软著申报材料

## 三、数据规模

| 指标 | 数值 |
| :--- | :---: |
| 题目记录数 | {len(questions)} |
| 原始掌握状态记录数 | {len(mastery_rows)} |
| 当前模型有效掌握状态数 | {len(current_mastery_rows)} |
| 当前模型有效证据数 | {len(current_evidence)} |
| 已隔离旧模型证据数 | {len(legacy_evidence)} |
| 导入记录数 | {len(ingest_rows)} |
| 正确题数 | {correct} |
| 错题数 | {wrong} |
| 待判断题数 | {pending} |

## 四、学科分布

{subject_lines}

## 五、年级分布

{grade_lines}

## 六、知识体系

| 指标 | 数值 |
| :--- | :---: |
| 编码节点 | {stats['point_nodes']} |
| 可追踪知识点卡 | {stats['trackable_cards']} |
| 运行时已发布卡片 | {stats['published']} |
| 覆盖学科 | {stats['subjects']} |
| INDEX 文件 | {stats['index_files']} |
| 试点运行范围 | 小学二至三年级数学（已发布卡片） |

## 七、版本兼容性

| 项目 | 版本 |
| :--- | :--- |
| Python | 3.9+ |
| macOS | 12+ |
| Obsidian | 推荐 v1.5+ |
"""


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
        "## 一、日志文件列表",
        "",
    ]
    total_size = 0
    if files:
        for name in files:
            fp = log_dir / name
            sz = fp.stat().st_size
            total_size += sz
            rec_count = len(fp.read_text().splitlines())
            lines.append(f"- `{name}` — {sz:,} bytes, {rec_count} 条记录")
    else:
        lines.append("- 暂无日志文件。")

    lines += [
        "",
        "## 二、各日志用途",
        "",
        "| 文件 | 记录内容 |",
        "| :--- | :--- |",
        "| `questions.jsonl` | 每题一笔记录，含题目文字、答案、学生答案、映射知识点 |",
        "| `mastery.jsonl` | 知识点掌握度快照，每个知识点在各个时间点的掌握概率 |",
        "| `evidence.jsonl` | 证据事件，记录每次掌握度变化的原因和来源 |",
        "| `ingest.jsonl` | 导入记录，包含原始输入参数和时间戳 |",
        "| `audit.jsonl` | 审计日志，记录每次关键操作的完整上下文 |",
        "",
        "## 三、数据总览",
        "",
        f"- 日志总大小：{total_size:,} bytes",
        f"- 日志文件数：{len(files)}",
        "",
        "> 日志文件为追加写入的 JSONL 格式，每条记录独立一行，可直接用文本编辑器或 jq 解析。",
    ]
    return "\n".join(lines) + "\n"


def build_source_code(code_dir: Path, output_dir: Path, lines_per_page: int = 50) -> Path:
    """Extract source code into A4-ready format for soft copyright submission.

    Chinese soft copyright requires first 30 pages and last 30 pages of source code.
    At ~50 lines per A4 page, that's ~1,500 lines per section.
    If total code is < 60 pages (~3,000 lines), submit ALL code.
    """
    # Collect all .py files in order
    py_files = sorted(code_dir.rglob("*.py"))
    py_files = [f for f in py_files if "__pycache__" not in str(f)]
    py_files = sorted(py_files, key=lambda x: x.name)

    all_lines: list[str] = []
    for pf in py_files:
        rel = str(pf.relative_to(code_dir))
        all_lines.append(f"// {'='*70}")
        all_lines.append(f"// 文件: {rel}")
        all_lines.append(f"// {'='*70}")
        code = pf.read_text(encoding="utf-8")
        for line in code.splitlines():
            all_lines.append(line)
        all_lines.append("")  # blank line between files

    total = len(all_lines)

    # Build output
    out_lines = [
        "---",
        "title: 源代码",
        "tags:",
        "  - project/k12-tracking",
        "  - copyright/materials",
        f"updated: {now_date()}",
        "---",
        "",
        f"# 源代码",
        "",
        f"## 总览",
        "",
        f"- 代码文件：{len(py_files)} 个",
        f"- 总行数：{total}",
        f"- 每页约 {lines_per_page} 行（A4 排版标准）",
        f"- 换算页数：约 {total // lines_per_page} 页",
        "",
    ]

    if total <= lines_per_page * 60:
        out_lines.append("> 代码总量不足 60 页（A4 标准），按软著申报要求提交全部代码。")
        out_lines.append("")
        out_lines.append("---")
        out_lines.append("")
        # Output ALL code with line numbers
        for i, line in enumerate(all_lines, 1):
            out_lines.append(_numbered_source_line(i, line))
    else:
        out_lines.append("> 代码总量超过 60 页，提交首 30 页和末 30 页。")
        out_lines.append("")
        out_lines.append("## 前 30 页")
        out_lines.append("")
        first = all_lines[:lines_per_page * 30]
        for i, line in enumerate(first, 1):
            out_lines.append(_numbered_source_line(i, line))
        out_lines.append("")
        out_lines.append("---")
        out_lines.append("")
        out_lines.append("## 后 30 页")
        out_lines.append("")
        last = all_lines[-lines_per_page * 30:]
        offset = total - len(last)
        for i, line in enumerate(last, 1):
            out_lines.append(_numbered_source_line(offset + i, line))

    path = output_dir / "源代码.md"
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return path


def escape_obsidian_link_syntax(line: str) -> str:
    return line.replace("[[", "\\[\\[").replace("]]", "\\]\\]")


def _numbered_source_line(number: int, line: str) -> str:
    escaped = escape_obsidian_link_syntax(line)
    return f"{number:>5}| {escaped}" if escaped else f"{number:>5}|"


def generate_materials(project_root: Path) -> List[Path]:
    vault_root = project_root / "教育智能体"
    output_dir = vault_root / "09-软著材料" / "生成稿"
    output_dir.mkdir(parents=True, exist_ok=True)

    service_dir = project_root / "services" / "edu_tracker"

    log_dir = vault_root / "logs"
    questions = load_jsonl(log_dir / "questions.jsonl")
    mastery_rows = load_jsonl(log_dir / "mastery.jsonl")
    ingest_rows = load_jsonl(log_dir / "ingest.jsonl")
    evidence_rows = load_jsonl(log_dir / "evidence.jsonl")
    version = project_version(project_root)
    stats = knowledge_stats(vault_root / "02-课标与知识体系" / "02-国家课标知识树")

    outputs = {
        "系统说明.md": build_system_overview(service_dir, version),
        "用户操作手册.md": build_user_manual(),
        "安装部署说明.md": build_installation_guide(),
        "版本说明.md": build_version_note(questions, mastery_rows, ingest_rows, version, stats, evidence_rows),
        "日志索引.md": build_log_index(log_dir),
    }

    written: List[Path] = []
    for filename, content in outputs.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        written.append(path)
        print(f"  ✅ {filename} ({len(content.splitlines())} 行)")

    # Generate source code extract
    src_path = build_source_code(service_dir, output_dir)
    written.append(src_path)
    print(f"  ✅ 源代码.md ({len(src_path.read_text().splitlines())} 行)")

    return written
