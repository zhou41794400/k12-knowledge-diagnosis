---
title: GitHub独立项目规划
tags:
  - project/k12-tracking
  - copyright/github
status: active
updated: 2026-06-10
---

# GitHub 独立项目规划

## 目标

- 将可执行代码、版本日志和发布说明拆分到独立 GitHub 仓库。
- 保留 Obsidian 作为产品知识库、过程记录和软著材料主容器。
- 保证代码、文档、日志三条线都能独立追踪。

## 建议仓库名

- `k12-knowledge-tracking`
- 或 `edu-k12-tracker`

## 建议仓库内容

1. `services/` 或 `src/` 下保留本地分析核心代码。
2. `docs/` 下保留安装、使用、版本和架构说明。
3. `logs/` 目录仅保留示例或脱敏样例，不纳入真实家庭数据。
4. `releases/` 或 `changelog/` 保留版本说明和发布记录。

## 当前仓库骨架

- `pyproject.toml`
- `README.md`
- `CHANGELOG.md`
- `docs/工程化说明.md`
- `docs/日志归档规范.md`
- `services/`
- `edu_tracker/`

## 日志规则

- 每次功能变更必须写变更记录。
- 每次验证必须保留命令、输出和日期。
- 关键里程碑必须同步到 Obsidian 的版本日志和绩效报告。

## 迁移顺序

1. 先确定仓库边界和目录结构。
2. 再把当前 `edu_tracker` 代码复制或迁入仓库。
3. 保留 Obsidian 的过程文档与软著材料生成稿。
4. 最后把发布与日志策略固化下来。

## 推荐一键命令

- `make check`
- `make report`
- `make materials`
- `make all`
- `make bundle`
- `make init-repo TARGET=/path/to/new-repo`
- `make release VERSION=0.1.1`
- `make tag VERSION=0.1.1`

## 建议 CI

- GitHub Actions 运行 `make check`
- 关键产物生成可由人工执行 `make report` 与 `make materials`
- 迁移包可通过 `make bundle` 输出到 `dist/`
- 新仓库初始化可通过 `make init-repo TARGET=/path/to/new-repo`
- 标签发布前必须确认仓库已有提交

## 迁移与发布参考

- [[../../docs/独立仓库迁移清单|独立仓库迁移清单]]
- [[../../docs/发布标签策略|发布标签策略]]
- [[../../docs/首版切分规则|首版切分规则]]

## 当前状态

- 规划已完成。
- 代码尚未拆分到独立 GitHub 仓库。
- 当前先以本地仓库持续迭代，待网络与账号流程确认后再正式拆分。
- 本地初始化脚本已可生成独立仓库初始目录。
