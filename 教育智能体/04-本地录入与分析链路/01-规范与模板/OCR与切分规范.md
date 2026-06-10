---
title: OCR与切分规范
tags:
  - project/k12-tracking
  - local-pipeline/ocr
status: active
updated: 2026-06-10
---

# OCR与切分规范

## 目标

把照片输入转换成可分析的题目文本和结构化片段。

## 处理步骤

1. 识别页面文本。
2. 清理噪音字符和重复行。
3. 切分题号、题干、选项、答案区。
4. 保留原始图片引用，便于复核。

## 输出字段

- `raw_text`
- `segments`
- `question_blocks`
- `image_refs`
- `ocr_confidence`

## 中文展示

- 面向家长的结果页只显示清洗后的中文题目文本和必要摘要。

