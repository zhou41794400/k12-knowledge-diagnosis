# 本地服务

`edu_tracker` 是启智知踪项目的最小本地分析壳子，当前已经支持“手动录题 -> 知识点匹配 -> 掌握度更新 -> 审计落盘”的闭环，也支持照片导入的本地骨架。
当前结果视图还会生成题目详情页，并按正确题/错题分流，串联题目、知识点页和周报页。

当前运行时从 Obsidian 知识卡动态读取 `published` 知识点，开放小学二至三年级数学 9 个知识点。学科、年级、关键词未命中或出现多候选歧义时，题目进入人工复核，不生成证据和掌握度。当前采用 `rule-v2` 规则模型和 Tesseract OCR，已提供只绑定本机的家长端 Web 入口，尚未实现 BKT、整卷自动切题和公网服务。

当前业务状态保存在 `教育智能体/logs/edu_tracker.sqlite3`，JSONL 文件继续作为追加式审计与兼容输出。旧 JSONL 掌握状态不会自动导入 SQLite。

## 运行

```bash
python3 -m edu_tracker manual --student-id s001 --subject 数学 --grade 二年级 --text "乘法口诀练习题" --answer "6" --student-answer "6"
```

```bash
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 二年级 --image-path /path/to/paper.jpg --ocr-text "乘法口诀练习题" --answer "6" --student-answer "6"
```

```bash
python3 -m edu_tracker report
```

```bash
python3 -m edu_tracker materials
```

```bash
python3 -m edu_tracker validate
```

```bash
python3 -m edu_tracker web
```

## 输出

- 控制台打印结构化 JSON
- `教育智能体/logs/questions.jsonl`
- `教育智能体/logs/evidence.jsonl`
- `教育智能体/logs/mastery.jsonl`
- `教育智能体/logs/audit.jsonl`
- `教育智能体/logs/ingest.jsonl`
- 照片入口支持同名 `.txt` 旁路文本，便于本地无 OCR 验证
- `教育智能体/05-结果视图/家长端总览.md`
- `教育智能体/05-结果视图/学生端-<学生ID>.md`
- `教育智能体/05-结果视图/题目详情/`
- `教育智能体/09-软著材料/生成稿/`
