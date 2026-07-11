---
title: 真实OCR与人工确认说明
tags:
  - project/k12-tracking
  - ingest/ocr
status: implemented
updated: 2026-07-11
---

# 真实 OCR 与人工确认说明

## 当前实现

- 本机使用 Tesseract 5.5.2，语言为 `chi_sim+eng`。
- 仅传图片时执行真实 OCR，结果写入导入记录并标记“待确认”。
- 待确认文本不会进入知识映射、证据或掌握度。
- 家长核对并修正后，通过 `--ocr-text` 再次提交才进入分析。

## 操作流程

```bash
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 三年级 --image-path /path/paper.png
python3 -m edu_tracker photo --student-id s001 --subject 数学 --grade 三年级 --image-path /path/paper.png --ingest-id i_xxx --ocr-text "人工确认后的题目" --answer "..." --student-answer "..."
```

> [!warning]
> 当前版本尚未自动切分整张试卷。建议一题一图，或先人工裁剪；低清晰度、手写体和复杂公式必须人工复核。

## 状态约束

- `待确认` 记录只能由同一学生使用对应 `ingest_id` 确认一次。
- 确认后原导入记录更新为 `已解析`，对应 OCR 复核任务关闭。
- OCR 失败会写入 SQLite、`ingest.jsonl`、`audit.jsonl` 和复核任务，不再静默丢失。
