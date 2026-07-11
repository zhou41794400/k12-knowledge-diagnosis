# 启智知踪 K12 智能学习诊断系统 V1.0

本仓库保存启智知踪项目的本地原型、过程文档、结果视图和软著材料生成稿。

## 项目简介

启智知踪是一款本地优先的 K12 学习诊断项目。当前 `0.1.2` 版本以小学二至三年级数学 9 个知识点为可运行试点，支持手动录题、Tesseract 中文 OCR、人工确认、复核处理和本地家长端；全学科覆盖与 BKT 属于后续目标。

## 当前能力

- 课标知识体系与知识点卡片，运行时动态读取已发布卡片
- 数据模型与事件流转
- 手动录题本地闭环
- 照片导入本地骨架
- 家长端、学生端结果视图与题目详情页，支持正确题/错题分流
- 软著材料生成器
- 未匹配题目进入人工复核，不写入掌握度证据
- `rule-v2` 可解释规则模型与标准库自动化测试

## 本地运行

```bash
make check
make validate
make report
make materials
make web
make bundle
make init-repo TARGET=/path/to/new-repo
make release VERSION=0.1.2
make tag VERSION=0.1.2
```

或直接运行：

```bash
python3 -m edu_tracker manual --student-id s001 --subject 数学 --grade 二年级 --text "乘法口诀练习题" --answer "6" --student-answer "6"
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 二年级 --image-path /path/to/paper.jpg --ocr-text "乘法口诀练习题" --answer "6" --student-answer "6"
python3 -m edu_tracker report
python3 -m edu_tracker materials
python3 -m edu_tracker validate
python3 -m edu_tracker web
python3 -m edu_tracker health
python3 -m edu_tracker data-export --student-id s001
python3 -m edu_tracker data-delete --student-id s001 --confirm s001
python3 -m edu_tracker backup
```

本地家长端默认地址为 `http://127.0.0.1:8765`，支持手动录题、图片上传、OCR 确认、复核处理和家长报告查看。

照片首次识别不更新掌握度。根据返回的 `ingest_id` 核对后确认：

```bash
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 二年级 --image-path /path/to/paper.jpg --ingest-id i_xxx --ocr-text "确认后的题目" --answer "6" --student-answer "6"
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
- `package.json`：前端依赖预留清单，当前尚未初始化可运行前端源码

## 说明

- 外显内容优先使用中文。
- 本地优先，不做公网部署。
- 当前重点是让后续接手的人可以无缝续接。
- 当前有 9 个小学二至三年级数学知识点处于 `published` 状态；其余知识卡不参与运行时匹配。
- `make validate` 执行数学映射研发基准集；该结果不等同于真实试卷准确率。
- 当前不应对外宣称已实现 BKT、整卷自动切题、公网 Web 服务或全学科自动诊断。
- 首版切分规则见 `docs/首版切分规则.md`
- 独立仓库初始化说明见 `docs/独立仓库初始化说明.md`
- 发布说明模板见 `docs/发布说明模板.md`
- 标签发布流程见 `docs/标签发布流程.md`
