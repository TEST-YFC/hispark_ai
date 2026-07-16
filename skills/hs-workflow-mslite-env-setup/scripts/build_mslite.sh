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

# 交叉工具链硬校验：MSLITE_ENABLE_MICRO=ON 会同时构建 nnacl_riscv 与 nnacl_arm 两条交叉库，
# 故 RISC-V（毕昇）与 ARM（musl GCC）工具链都必须就位。setup_env.sh 对缺失的工具链只告警
# （不阻断仅需 RISC-V 的 convert/build_static_lib 步骤），此处按编译实际需要硬校验，
# 给出明确修复指引，避免 build 在约 27% 的 nnacl_arm configure 处静默崩溃。
_miss=""
if [ -z "${BISHENG_ROOT:-}" ] || [ ! -x "${BISHENG_ROOT:-/nonexistent}/bin/clang" ]; then
    _miss="${_miss}  - 毕昇 RISC-V 工具链（BISHENG_ROOT，需含 bin/clang）\n"
fi
if [ -z "${ARM_TOOLCHAIN_ROOT:-}" ] || [ ! -x "${ARM_TOOLCHAIN_ROOT:-/nonexistent}/bin/arm-v01c01-linux-musleabi-gcc" ]; then
    _miss="${_miss}  - ARM musl GCC 工具链（ARM_TOOLCHAIN_ROOT，需含 bin/arm-v01c01-linux-musleabi-gcc）\n"
fi
if [ -n "$_miss" ]; then
    echo "[build_mslite] 错误: 编译需要以下交叉工具链，但未就位:" >&2
    printf '%b' "$_miss" >&2
    echo "  修复: source scripts/setup_env.sh（按告警中的下载/解压指引操作），或写入 ~/.hispark_env" >&2
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
# 注意: build.sh 失败时必须落到下方 grep 判断与错误处理分支，打印日志尾部。
# 因此处显式关闭第 5 行的 set -e, 否则 build.sh 返回非零会被 errexit 提前终结,
# 第 40-44 行的错误处理(含 tail 日志)永远不可达。退出码通过 EXIT_CODE 捕获后重新开启。
set +e
if [ "$1" = "-i" ]; then
    echo "[build_mslite] 增量编译模式"
    bash build.sh -I x86_64 -j$JOBS -i > "$LOG_FILE" 2>&1
else
    echo "[build_mslite] 全量编译模式"
    rm -rf "$BUILD_DIR"
    bash build.sh -I x86_64 -j$JOBS > "$LOG_FILE" 2>&1
fi
EXIT_CODE=$?
set -e
if grep -q "build success" "$LOG_FILE"; then
    echo "[build_mslite] 编译成功"
    ls -lh "$MSLITE_SRC"/output/mindspore-lite-*-linux-x64.tar.gz 2>/dev/null
else
    echo "[build_mslite] 编译失败 (exit=$EXIT_CODE), 查看日志: tail -50 $LOG_FILE"
    tail -30 "$LOG_FILE"
    exit 1
fi
