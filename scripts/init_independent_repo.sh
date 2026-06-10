#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "用法: sh scripts/init_independent_repo.sh <目标目录> [迁移包目录]" >&2
  exit 1
fi

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
TARGET_DIR="$1"
BUNDLE_DIR="${2:-${ROOT_DIR}/dist/transfer_bundle_$(date +%Y%m%d)}"

if [ ! -d "$BUNDLE_DIR" ]; then
  echo "迁移包不存在: $BUNDLE_DIR" >&2
  exit 1
fi

if [ -e "$TARGET_DIR" ] && [ "$(ls -A "$TARGET_DIR" 2>/dev/null | wc -l | tr -d ' ')" != "0" ]; then
  echo "目标目录已存在且非空: $TARGET_DIR" >&2
  exit 1
fi

mkdir -p "$TARGET_DIR"
cp -R "$BUNDLE_DIR"/. "$TARGET_DIR"/

if [ ! -d "$TARGET_DIR/.git" ]; then
  git -C "$TARGET_DIR" init -b main >/dev/null 2>&1 || git -C "$TARGET_DIR" init >/dev/null 2>&1
fi

cat > "$TARGET_DIR/INIT_NEXT_STEPS.md" <<'EOF'
# 初始化后下一步

1. 检查 `make check`、`make report`、`make materials`、`make bundle`。
2. 确认 `README.md`、`CHANGELOG.md`、`docs/` 与当前仓库一致。
3. 视需要调整仓库名和远程地址。
4. 生成首个发布标签或草拟版说明。
EOF

printf '%s\n' "$TARGET_DIR"
