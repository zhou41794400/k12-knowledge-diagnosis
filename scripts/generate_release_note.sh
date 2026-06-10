#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "用法: sh scripts/generate_release_note.sh <版本号>" >&2
  exit 1
fi

VERSION="$1"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
OUTPUT_DIR="${ROOT_DIR}/releases"
OUTPUT_FILE="${OUTPUT_DIR}/${VERSION}.md"

mkdir -p "$OUTPUT_DIR"

awk -v version="## ${VERSION}" '
  $0 == version {flag=1; next}
  flag && /^## / {exit}
  flag {print}
' "${ROOT_DIR}/CHANGELOG.md" > "${OUTPUT_FILE}.body"

cat > "$OUTPUT_FILE" <<EOF
# 发布说明 - ${VERSION}

## 版本摘要
EOF

if [ -s "${OUTPUT_FILE}.body" ]; then
  sed -e 's/^[[:space:]]*-[[:space:]]*//' -e '/^$/d' "${OUTPUT_FILE}.body" | sed 's/^/- /' >> "$OUTPUT_FILE"
else
  cat >> "$OUTPUT_FILE" <<EOF
- 当前版本未在 CHANGELOG 中找到详细条目。
EOF
fi

cat >> "$OUTPUT_FILE" <<'EOF'

## 验证状态

- `make check`
- `make report`
- `make materials`
- `make bundle`
- `make init-repo TARGET=/path/to/new-repo`

## 备注

- 发布说明与 Obsidian 版本日志保持一致。
- 若要正式打标签，请先确认目标仓库边界。
EOF

rm -f "${OUTPUT_FILE}.body"

printf '%s\n' "$OUTPUT_FILE"
