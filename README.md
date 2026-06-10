# K12 教育知识点掌握程度跟踪系统

本仓库保存教育智能体项目的本地原型、过程文档、结果视图和软著材料生成稿。

## 当前能力

- 课标知识体系与知识点卡片
- 数据模型与事件流转
- 手动录题本地闭环
- 照片导入本地骨架
- 家长端与学生端结果视图
- 软著材料生成器

## 本地运行

```bash
make check
make report
make materials
make bundle
make init-repo TARGET=/path/to/new-repo
make release VERSION=0.1.1
make tag VERSION=0.1.1
```

或直接运行：

```bash
python3 -m edu_tracker manual --student-id s001 --subject 数学 --grade 二年级 --text "乘法口诀练习题" --answer "6" --student-answer "6"
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 二年级 --image-path /path/to/paper.jpg --ocr-text "乘法口诀练习题" --answer "6" --student-answer "6"
python3 -m edu_tracker report
python3 -m edu_tracker materials
```

## 目录说明

- `教育智能体/`：Obsidian 工作区与过程文档
- `services/`：本地分析服务实现
- `edu_tracker/`：命令行导入层
- `docs/`：工程化、发布与接续说明
- `Makefile`：一键验证与生成入口
- `dist/`：迁移包输出目录
- `releases/`：发布说明输出目录
- `scripts/`：迁移和初始化脚本

## 说明

- 外显内容优先使用中文。
- 本地优先，不做公网部署。
- 当前重点是让后续接手的人可以无缝续接。
- 首版切分规则见 `docs/首版切分规则.md`
- 独立仓库初始化说明见 `docs/独立仓库初始化说明.md`
- 发布说明模板见 `docs/发布说明模板.md`
- 标签发布流程见 `docs/标签发布流程.md`
