#!/bin/bash
# MindSpore Lite 源码编译脚本
# 用法: bash scripts/build_mslite.sh

set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

# 检查环境变量
if [ -z "$MSLITE_ENABLE_MICRO" ]; then
    echo "[build_mslite] 错误: 请先 source scripts/setup_env.sh"
    exit 1
fi

MSLITE_SRC="$HISPARK_AI_ROOT/src/mindspore-lite"
BUILD_DIR="$MSLITE_SRC/build"
LOG_FILE=/tmp/mslite_build.log
JOBS=${JOBS:-$(nproc)}

echo "[build_mslite] 开始编译 MindSpore Lite ..."
echo "[build_mslite] 线程数: $JOBS"
echo "[build_mslite] 日志: $LOG_FILE"

cd "$MSLITE_SRC"

# 增量编译或全量编译
if [ "$1" = "-i" ]; then
    echo "[build_mslite] 增量编译模式"
    bash build.sh -I x86_64 -j$JOBS -i > "$LOG_FILE" 2>&1
else
    echo "[build_mslite] 全量编译模式"
    rm -rf "$BUILD_DIR"
    bash build.sh -I x86_64 -j$JOBS > "$LOG_FILE" 2>&1
fi

EXIT_CODE=$?
if grep -q "build success" "$LOG_FILE"; then
    echo "[build_mslite] 编译成功"
    ls -lh "$MSLITE_SRC"/output/mindspore-lite-*-linux-x64.tar.gz 2>/dev/null
else
    echo "[build_mslite] 编译失败 (exit=$EXIT_CODE), 查看日志: tail -50 $LOG_FILE"
    tail -30 "$LOG_FILE"
    exit 1
fi
