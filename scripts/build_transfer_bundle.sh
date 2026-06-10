#!/bin/sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
STAMP="$(date +%Y%m%d)"
BUNDLE_DIR="${ROOT_DIR}/dist/transfer_bundle_${STAMP}"

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}"

copy_tree() {
  src="$1"
  dst="$2"
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
}

copy_tree "${ROOT_DIR}/README.md" "${BUNDLE_DIR}/README.md"
copy_tree "${ROOT_DIR}/CHANGELOG.md" "${BUNDLE_DIR}/CHANGELOG.md"
copy_tree "${ROOT_DIR}/pyproject.toml" "${BUNDLE_DIR}/pyproject.toml"
copy_tree "${ROOT_DIR}/Makefile" "${BUNDLE_DIR}/Makefile"
copy_tree "${ROOT_DIR}/.github" "${BUNDLE_DIR}/.github"
copy_tree "${ROOT_DIR}/docs" "${BUNDLE_DIR}/docs"
copy_tree "${ROOT_DIR}/services" "${BUNDLE_DIR}/services"
copy_tree "${ROOT_DIR}/edu_tracker" "${BUNDLE_DIR}/edu_tracker"
copy_tree "${ROOT_DIR}/教育智能体/00-项目总控" "${BUNDLE_DIR}/教育智能体/00-项目总控"
copy_tree "${ROOT_DIR}/教育智能体/01-需求与范围" "${BUNDLE_DIR}/教育智能体/01-需求与范围"
copy_tree "${ROOT_DIR}/教育智能体/02-课标与知识体系" "${BUNDLE_DIR}/教育智能体/02-课标与知识体系"
copy_tree "${ROOT_DIR}/教育智能体/03-数据模型" "${BUNDLE_DIR}/教育智能体/03-数据模型"
copy_tree "${ROOT_DIR}/教育智能体/04-本地录入与分析链路" "${BUNDLE_DIR}/教育智能体/04-本地录入与分析链路"
copy_tree "${ROOT_DIR}/教育智能体/05-结果视图" "${BUNDLE_DIR}/教育智能体/05-结果视图"
copy_tree "${ROOT_DIR}/教育智能体/06-开发任务" "${BUNDLE_DIR}/教育智能体/06-开发任务"
copy_tree "${ROOT_DIR}/教育智能体/07-测试验收" "${BUNDLE_DIR}/教育智能体/07-测试验收"
copy_tree "${ROOT_DIR}/教育智能体/08-日志与变更" "${BUNDLE_DIR}/教育智能体/08-日志与变更"
copy_tree "${ROOT_DIR}/教育智能体/09-软著材料" "${BUNDLE_DIR}/教育智能体/09-软著材料"
copy_tree "${ROOT_DIR}/教育智能体/欢迎.md" "${BUNDLE_DIR}/教育智能体/欢迎.md"

if [ -d "${BUNDLE_DIR}/教育智能体/logs" ]; then
  rm -rf "${BUNDLE_DIR}/教育智能体/logs"
fi

cat > "${BUNDLE_DIR}/TRANSFER_README.md" <<'EOF'
# 迁移包说明

该目录由 `scripts/build_transfer_bundle.sh` 生成。

## 内容

- 代码骨架
- 工程化文档
- Obsidian 过程文档
- 结果视图样例
- 软著材料生成稿

## 不包含

- 真实家庭日志
- 真实上传图片

## 下一步

1. 创建新的 GitHub 仓库。
2. 将本目录内容作为初始代码与文档导入。
3. 重新执行 `make check`、`make report`、`make materials`。
EOF

printf '%s\n' "${BUNDLE_DIR}"
