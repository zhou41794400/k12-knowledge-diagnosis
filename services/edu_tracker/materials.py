from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .reporting import load_jsonl


def now_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def build_system_overview(code_dir: Path) -> str:
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

启智知踪 K12 智能学习诊断系统 V1.0

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

本系统采用 **本地优先（Local-First）** 架构，所有数据存储和分析均在用户本地 macOS 环境中完成，不依赖于任何云服务。

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
  - **错题**：记录为「待复核」，触发薄弱标记，降低掌握度。
- **掌握度更新**：基于正确/错误历史，通过间隔重复和 BKT（贝叶斯知识追踪）混合策略更新知识点掌握状态。
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

管理知识点注册表和学科配置：

- 支持按学科区分追踪策略：BKT（词汇/语法类记忆型学科）与 RULE（数学/科学类规则型学科）。
- 提供知识点查找和学科列表查询接口。

### 5.5 CLI 入口（cli.py）

命令行接口，支持子命令：

| 子命令 | 功能 |
| :--- | :--- |
| `manual` | 手动录题 |
| `photo` | 照片导入并处理 |
| `report` | 生成结果视图 |
| `materials` | 生成软著申报材料 |

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
| 数据存储 | JSONL | 追加日志，适合本地场景 |
| 文档输出 | Markdown | 易于阅读和版本管理 |
| 知识库 | Obsidian Vault | 支持双向链接与图谱 |
| 构建工具 | Makefile | 一键执行常见任务 |

## 七、数据流

### 手动录题流程

```
用户输入题目 → CLI 解析 → pipeline.manual_ingest()
  → 知识点映射 → 对错分流
  ├─ 正确题 → 增加掌握置信度
  └─ 错题   → 标记待复核 → 降低掌握度
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

- **本地优先**：所有数据存储在用户本地 macOS 中，不上传任何云端。
- **无数据收集**：系统不收集用户使用行为数据。
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
- 掌握度更新写入 `logs/mastery.jsonl`
- 证据事件写入 `logs/evidence.jsonl`

### 2.3 照片导入

照片导入适用于已经完成的纸质试卷或练习册。当前阶段支持旁路文本验证（OCR 文本由家长手动输入）。

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
| `--ocr-text` | 是 | 题目文本（当前手动输入） | `"3 × 4 = ?"` |

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

### 2.4 生成结果视图

录完题目后，执行报告生成命令：

```bash
python3 -m edu_tracker report
```

系统将在 `05-结果视图/` 目录下生成：
- `家长端总览.md` — 学科掌握概况、短板列表、最近题目
- `学生端-s001.md` — 面向学生的周报
- `题目详情/q_xxxxxxxxxxxx.md` — 每道题的详细分析

### 2.5 查看分析结果

家长端总览包含：

1. **学科掌握度摘要**：按学科、知识主题展示平均掌握率。
2. **短板知识点**：掌握度低于阈值的知识点清单，按紧急程度排序。
3. **最近录入题目**：最近录入的题目列表，标注正确/错误状态。
4. **待复核项**：判定为「边缘正确」或「答案有歧义」的题目，需家长人工确认。

### 2.6 生成软著材料

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

1. **本周掌握变化**：各知识点掌握度对比上周的变化。
2. **当前短板清单**：掌握度低于 60% 的知识点，按优先级排列。
3. **推荐复习知识点**：系统根据遗忘曲线推荐的 3-5 个复习知识点。
4. **原题回溯**：每个薄弱知识点可跳转到对应题目的详情页，查看原始题目内容。

## 四、常见问题

### 4.1 录题后没看到掌握变化？

首次录题时系统会建立初始掌握状态，可能需要 1-2 道题后才能看到趋势变化。建议连续录入 3-5 道同一知识点的题目以获得有意义的掌握度变化。

### 4.2 如何修改录错的题目？

当前版本暂不支持直接编辑已录入的题目。建议重新录入正确的版本，系统会合并分析。

### 4.3 支持哪些学科？

系统基于 2022 版国家课程标准，涵盖 15 个学科，包括：语文、数学、英语、科学、道德与法治、体育与健康、艺术、劳动、信息科技、思想政治、历史、地理、物理、化学、生物。

### 4.4 数据安全吗？

所有数据存储在本地 macOS 中，不连接任何云端服务。系统不收集任何用户数据，审计日志供用户自行追溯。

## 五、注意事项

1. 照片导入当前阶段 OCR 文本需手动输入，正式 OCR 接入将在后续版本完成。
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
| `make report` | 生成结果视图 |
| `make materials` | 生成软著材料 |
| `make bundle` | 打包迁移包到 `dist/` |
| `make init-repo` | 初始化独立仓库 |
| `make release VERSION=x.y.z` | 生成发布说明 |
| `make tag VERSION=x.y.z` | 创建 Git 标签 |
| `make all` | 完整流程（check → report → materials） |
"""


def build_version_note(questions: List[dict], mastery_rows: List[dict], ingest_rows: List[dict]) -> str:
    subject_counter = Counter(row.get("subject", "未知") for row in questions)
    subject_lines = "\n".join(f"- {subject}：{count} 条" for subject, count in subject_counter.most_common()) or "- 暂无数据"

    # Calculate grade distribution
    grade_counter = Counter(row.get("grade", "未知") for row in questions)
    grade_lines = "\n".join(f"- {grade}：{count} 条" for grade, count in grade_counter.most_common()) or "- 暂无数据"

    # Correct vs wrong stats
    correct = sum(1 for q in questions if q.get("student_answer") == q.get("answer"))
    wrong = len(questions) - correct

    return f"""---
title: 版本说明
tags:
  - project/k12-tracking
  - copyright/materials
updated: {now_date()}
---

# 版本说明

## 一、当前版本

当前版本：v0.1.1（首版草案）

## 二、版本特征

### 2.1 已完成能力

- **手动录题闭环**：支持通过命令行手动录入题目，完成知识点映射、对错分流、掌握度更新。
- **照片导入骨架**：支持通过命令行传入照片路径和 OCR 文本，完成与手动录题相同的分析链路。
- **结果视图生成**：可生成家长端总览页、学生周报、题目详情页。
- **软著材料生成**：可自动生成系统说明、用户操作手册、安装说明、版本说明、日志索引。
- **审计日志**：所有关键操作写入 JSONL 日志，支持回溯。
- **完整知识体系**：15 学科 709 知识点，基于国家 2022 版课程标准。

### 2.2 后续计划

- 接入真实 OCR（如 PaddleOCR、Tesseract）
- LLM 辅助知识点映射（当前基于规则匹配）
- 更多学科的双向链接和跨学科追踪
- 导出 PDF/Word 格式的软著申报材料

## 三、数据规模

| 指标 | 数值 |
| :--- | :---: |
| 题目记录数 | {len(questions)} |
| 掌握状态记录数 | {len(mastery_rows)} |
| 导入记录数 | {len(ingest_rows)} |
| 正确题数 | {correct} |
| 错题数 | {wrong} |

## 四、学科分布

{subject_lines}

## 五、年级分布

{grade_lines}

## 六、知识体系

| 指标 | 数值 |
| :--- | :---: |
| 覆盖学科 | 15 |
| 知识点卡片 | 709 |
| INDEX 文件 | 41 |
| 学段覆盖 | 小学（1-6 年级）✅ 初中（7-9 年级）✅ 高中 ✅ |

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
        "| `questions.jsonl` | 每题一比记录，含题目文字、答案、学生答案、映射知识点 |",
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
    current_file_lines: list[str] = []

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
            out_lines.append(f"{i:>5}| {escape_obsidian_link_syntax(line)}")
    else:
        out_lines.append("> 代码总量超过 60 页，提交首 30 页和末 30 页。")
        out_lines.append("")
        out_lines.append("## 前 30 页")
        out_lines.append("")
        first = all_lines[:lines_per_page * 30]
        for i, line in enumerate(first, 1):
            out_lines.append(f"{i:>5}| {escape_obsidian_link_syntax(line)}")
        out_lines.append("")
        out_lines.append("---")
        out_lines.append("")
        out_lines.append("## 后 30 页")
        out_lines.append("")
        last = all_lines[-lines_per_page * 30:]
        offset = total - len(last)
        for i, line in enumerate(last, 1):
            out_lines.append(f"{offset + i:>5}| {escape_obsidian_link_syntax(line)}")

    path = output_dir / "源代码.md"
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return path


def escape_obsidian_link_syntax(line: str) -> str:
    return line.replace("[[", "\\[\\[").replace("]]", "\\]\\]")


def generate_materials(project_root: Path) -> List[Path]:
    vault_root = project_root / "教育智能体"
    output_dir = vault_root / "09-软著材料" / "生成稿"
    output_dir.mkdir(parents=True, exist_ok=True)

    service_dir = project_root / "services" / "edu_tracker"

    log_dir = vault_root / "logs"
    questions = load_jsonl(log_dir / "questions.jsonl")
    mastery_rows = load_jsonl(log_dir / "mastery.jsonl")
    ingest_rows = load_jsonl(log_dir / "ingest.jsonl")

    outputs = {
        "系统说明.md": build_system_overview(service_dir),
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
        print(f"  ✅ {filename} ({len(content.splitlines())} 行)")

    # Generate source code extract
    src_path = build_source_code(service_dir, output_dir)
    written.append(src_path)
    print(f"  ✅ 源代码.md ({len(src_path.read_text().splitlines())} 行)")

    return written
