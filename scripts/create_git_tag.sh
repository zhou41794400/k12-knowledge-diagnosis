#!/bin/sh
set -eu

if [ "$#" -lt 1 ]; then
  echo "用法: sh scripts/create_git_tag.sh <版本号> [发布说明文件]" >&2
  exit 1
fi

VERSION="$1"
ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
RELEASE_FILE="${2:-${ROOT_DIR}/releases/${VERSION}.md}"
TAG_NAME="v${VERSION}"

if ! git -C "$ROOT_DIR" rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "当前仓库没有可用的 HEAD，先完成一次提交再打标签。" >&2
  exit 1
fi

if [ ! -f "$RELEASE_FILE" ]; then
  echo "发布说明不存在: $RELEASE_FILE" >&2
  exit 1
fi

git -C "$ROOT_DIR" tag -a "$TAG_NAME" -F "$RELEASE_FILE"
printf '%s\n' "$TAG_NAME"
